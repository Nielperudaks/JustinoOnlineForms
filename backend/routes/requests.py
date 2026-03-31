from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, get_current_user, send_email_notification
import uuid
from datetime import datetime, timezone
from realtime import manager

requests_router = APIRouter(prefix="/requests", tags=["requests"])


class RequestCreate(BaseModel):
    form_template_id: str
    title: Optional[str] = None
    form_data: dict
    notes: Optional[str] = ""
    priority: Optional[str] = None


class RequestAction(BaseModel):
    action: str  # approve, reject, fulfill
    comments: Optional[str] = ""


@requests_router.get("")
async def list_requests(
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    my_requests: Optional[bool] = False,
    my_approvals: Optional[bool] = False,
    search: Optional[str] = None,
    offset: int = Query(0, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user)
):
    query = {}
    if status:
        if status == "pending":
            query["status"] = {"$in": ["in_progress", "pending"]}
        else:
            query["status"] = status
    if department_id:
        query["department_id"] = department_id
    if my_requests:
        query["requester_id"] = user["id"]
    if my_approvals:
        query["$or"] = [
            {
                "approvals": {
                    "$elemMatch": {
                        "approver_id": user["id"],
                        "status": "pending"
                    }
                },
                "status": "in_progress",
            },
            {
                "custodian.user_id": user["id"],
                "custodian.status": "pending",
                "status": "pending",
            },
        ]

    if search:
        escaped_search = search.strip()
        if escaped_search:
            search_query = {
                "$or": [
                    {"title": {"$regex": escaped_search, "$options": "i"}},
                    {"form_template_name": {"$regex": escaped_search, "$options": "i"}},
                    {"request_number": {"$regex": escaped_search, "$options": "i"}},
                ]
            }
            query = {"$and": [query, search_query]} if query else search_query

    # Non-super-admin: restrict to user-related requests (their requests + any request they're in the approval chain)
    role = user.get("role", "")
    if role != "super_admin":
        user_scope = {
            "$or": [
                {"requester_id": user["id"]},
                {"approvals": {"$elemMatch": {"approver_id": user["id"]}}},
                {"custodian.user_id": user["id"]},
            ]
        }
        query = {"$and": [query, user_scope]} if query else user_scope

    total = await db.requests.count_documents(query)
    skip = offset if offset else (page - 1) * limit
    reqs = await db.requests.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    return {"items": reqs, "total": total, "page": page, "limit": limit, "offset": skip}


@requests_router.get("/{request_id}")
async def get_request(request_id: str, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Non-super-admin can only view requests they created or are in the approval chain
    if user.get("role") != "super_admin":
        uid = user["id"]
        is_requester = req.get("requester_id") == uid
        is_approver = any(a.get("approver_id") == uid for a in req.get("approvals", []))
        is_custodian = req.get("custodian", {}).get("user_id") == uid
        if not is_requester and not is_approver and not is_custodian:
            raise HTTPException(status_code=403, detail="You do not have access to this request")
    # Populate requester_department_id for older requests that don't have it
    if "requester_department_id" not in req and req.get("requester_id"):
        requester = await db.users.find_one({"id": req["requester_id"]}, {"department_id": 1})
        if requester and requester.get("department_id"):
            req["requester_department_id"] = requester["department_id"]
    return req


@requests_router.post("", status_code=201)
async def create_request(req: RequestCreate, user=Depends(get_current_user)):
    role = user.get("role", "")
    if role not in ("requestor", "both", "manager", "super_admin"):
        raise HTTPException(status_code=403, detail="Only requestors can create requests")
    tmpl = await db.form_templates.find_one({"id": req.form_template_id, "is_active": True}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=400, detail="Form template not found or inactive")
    display_title = tmpl["name"]

    count = await db.requests.count_documents({})
    request_number = f"REQ-{count + 1:05d}"

    approvals = []
    requester_dept_id = user.get("department_id", "")
    seen_approver_ids = set()
    next_step_number = 1
    custodian_doc = None

    for step in tmpl.get("approver_chain", []):
        approver_id = step["user_id"]
        approver_name = step.get("user_name", "")

        if approver_id == "immediate_manager":
            if not requester_dept_id:
                raise HTTPException(
                    status_code=400,
                    detail="Requestor has no department assigned. Immediate Manager requires the requestor to have a department."
                )
            manager_user = await db.users.find_one(
                {"role": "manager", "department_id": requester_dept_id, "is_active": True},
                {"_id": 0}
            )
            if not manager_user:
                raise HTTPException(
                    status_code=400,
                    detail="No Immediate Manager (Manager role) found in requestor's department. Please assign a Manager to the requestor's department."
                )
            approver_id = manager_user["id"]
            approver_name = manager_user.get("name", "Immediate Manager")

        # Skip duplicate approvers so each user only appears once in the chain
        if approver_id in seen_approver_ids:
            continue

        seen_approver_ids.add(approver_id)

        approvals.append({
            "step": next_step_number,
            "approver_id": approver_id,
            "approver_name": approver_name,
            "status": "pending" if next_step_number == 1 else "waiting",
            "comments": "",
            "acted_at": None
        })

        next_step_number += 1

    tmpl_custodian = tmpl.get("custodian")
    if tmpl_custodian and tmpl_custodian.get("user_id"):
        custodian_user = await db.users.find_one(
            {"id": tmpl_custodian["user_id"], "is_active": True},
            {"_id": 0},
        )
        if not custodian_user:
            raise HTTPException(
                status_code=400,
                detail="The assigned custodian for this form is not available. Please update the form custodian.",
            )
        custodian_doc = {
            "user_id": custodian_user["id"],
            "user_name": tmpl_custodian.get("user_name") or custodian_user.get("name", "Custodian"),
            "status": "waiting" if approvals else "pending",
            "comments": "",
            "acted_at": None,
        }

    total_steps = len(approvals) + (1 if custodian_doc else 0)
    if approvals:
        initial_status = "in_progress"
        current_step = 1
    elif custodian_doc:
        initial_status = "pending"
        current_step = 1
    else:
        initial_status = "approved"
        current_step = 0

    request_doc = {
        "id": str(uuid.uuid4()),
        "request_number": request_number,
        "form_template_id": req.form_template_id,
        "form_template_name": tmpl["name"],
        "department_id": tmpl["department_id"],
        "requester_id": user["id"],
        "requester_name": user["name"],
        "requester_department_id": requester_dept_id,
        "requester_email": user.get("email", ""),
        "title": display_title,
        "form_data": req.form_data,
        "notes": req.notes or "",
        "status": initial_status,
        "current_approval_step": current_step,
        "total_approval_steps": total_steps,
        "approvals": approvals,
        "custodian": custodian_doc,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.requests.insert_one(request_doc)
    result = {k: v for k, v in request_doc.items() if k != "_id"}

    # Notify first approver or custodian
    if approvals:
        first_approver = await db.users.find_one({"id": approvals[0]["approver_id"]}, {"_id": 0})
        if first_approver:
            notif = {
                "id": str(uuid.uuid4()),
                "user_id": first_approver["id"],
                "request_id": result["id"],
                "request_number": request_number,
                "message": f"New request '{display_title}' from {user['name']} requires your approval",
                "type": "approval_required",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notif)
            await send_email_notification(
                first_approver.get("email", ""),
                f"Approval Required: {request_number} - {display_title}",
                f"<h3>New Request Pending Your Approval</h3><p><b>{request_number}</b> - {display_title}</p><p>From: {user['name']}</p><p>Please log in to review and approve.</p>"
            )
            await manager.broadcast(
                event="NOTIFICATION_CREATED",
                payload={
                    "user_id": notif["user_id"],
                    "notification_id": notif["id"],
                    "type": notif["type"]
                }
            )
    elif custodian_doc:
        custodian_user = await db.users.find_one({"id": custodian_doc["user_id"]}, {"_id": 0})
        notif = {
            "id": str(uuid.uuid4()),
            "user_id": custodian_doc["user_id"],
            "request_id": result["id"],
            "request_number": request_number,
            "message": f"Request '{display_title}' is ready for fulfillment confirmation",
            "type": "custodian_required",
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notif)
        await send_email_notification(
            custodian_user.get("email", "") if custodian_user else "",
            f"Fulfillment Required: {request_number} - {display_title}",
            f"<h3>Request Ready for Fulfillment</h3><p><b>{request_number}</b> - {display_title}</p><p>Requested by: {user['name']}</p><p>Please fulfill the request and confirm once it is completed.</p>"
        )
        await manager.broadcast(
            event="NOTIFICATION_CREATED",
            payload={
                "user_id": notif["user_id"],
                "notification_id": notif["id"],
                "type": notif["type"]
            }
        )

    await manager.broadcast(
        event="REQUEST_CREATED",
        payload={
            "request_id": result["id"],
            "request_number": result["request_number"],
            "department_id": result["department_id"],
            "requester_id": result["requester_id"],
            "status": result["status"]
        }
    )

    return result

@requests_router.post("/{request_id}/cancel")
async def cancel_request(request_id: str, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req["status"] != "in_progress":
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")

    # Only the requester (or super admin) can cancel their own request
    if user["id"] != req["requester_id"] and user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="You are not allowed to cancel this request")

    now = datetime.now(timezone.utc).isoformat()

    await db.requests.update_one(
        {"id": request_id},
        {
            "$set": {
                "status": "cancelled",
                "updated_at": now,
            }
        },
    )

    updated = await db.requests.find_one({"id": request_id}, {"_id": 0})

    # Broadcast cancellation events so dashboards and detail views update live
    await manager.broadcast(
        event="REQUEST_CANCELLED",
        payload={
            "request_id": updated["id"],
            "request_number": updated["request_number"],
            "department_id": updated["department_id"],
            "requester_id": updated["requester_id"],
            "status": updated["status"],
        },
    )

    await manager.broadcast(
        event="REQUEST_STATE_CHANGED",
        payload={
            "request_id": updated["id"],
            "status": updated["status"],
            "current_step": updated.get("current_approval_step", 0),
        },
    )

    return updated


@requests_router.post("/{request_id}/action")
async def action_request(request_id: str, action: RequestAction, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] not in ("in_progress", "pending"):
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")
    request_display_name = req.get("form_template_name") or req.get("title") or "Request"

    current_step = req.get("current_approval_step", 1)
    approvals = req.get("approvals", [])
    custodian = req.get("custodian")
    role = user.get("role", "")

    if action.action in ("approve", "reject") and role not in ("approver", "both", "manager", "super_admin"):
        raise HTTPException(status_code=403, detail="Only approvers can approve or reject requests")

    if action.action == "fulfill":
        if not custodian or custodian.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="You are not the assigned custodian for this request")
        if req["status"] != "pending" or custodian.get("status") != "pending":
            raise HTTPException(status_code=400, detail="This request is not awaiting custodian confirmation")

        now = datetime.now(timezone.utc).isoformat()
        custodian["status"] = "fulfilled"
        custodian["comments"] = action.comments or ""
        custodian["acted_at"] = now

        await db.requests.update_one(
            {"id": request_id},
            {"$set": {
                "custodian": custodian,
                "status": "approved",
                "current_approval_step": req.get("total_approval_steps", current_step),
                "updated_at": now
            }},
        )

        approver_ids = list({a.get("approver_id") for a in approvals if a.get("approver_id")})
        approver_users = []
        if approver_ids:
            approver_users = await db.users.find(
                {"id": {"$in": approver_ids}},
                {"_id": 0},
            ).to_list(len(approver_ids))

        for approver_user in approver_users:
            notif = {
                "id": str(uuid.uuid4()),
                "user_id": approver_user["id"],
                "request_id": request_id,
                "request_number": req["request_number"],
                "message": f"Request '{request_display_name}' was fulfilled and confirmed by {user['name']}",
                "type": "request_completed",
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(notif)
            await send_email_notification(
                approver_user.get("email", ""),
                f"Request Completed: {req['request_number']}",
                f"<h3>Request Completed</h3><p><b>{req['request_number']}</b> - {request_display_name}</p><p>Confirmed by custodian: {user['name']}</p><p>Comments: {action.comments or 'None'}</p>"
            )
            await manager.broadcast(
                event="NOTIFICATION_CREATED",
                payload={
                    "user_id": notif["user_id"],
                    "notification_id": notif["id"],
                    "type": notif["type"]
                }
            )

        requester_notif = {
            "id": str(uuid.uuid4()),
            "user_id": req["requester_id"],
            "request_id": request_id,
            "request_number": req["request_number"],
            "message": f"Your request '{request_display_name}' has been fulfilled",
            "type": "request_approved",
            "is_read": False,
            "created_at": now
        }
        await db.notifications.insert_one(requester_notif)
        await send_email_notification(
            req.get("requester_email", ""),
            f"Request Approved: {req['request_number']}",
            f"<h3>Request Fulfilled</h3><p><b>{req['request_number']}</b> - {request_display_name}</p><p>Confirmed by custodian: {user['name']}</p><p>Your request is now complete.</p>"
        )
        await manager.broadcast(
            event="NOTIFICATION_CREATED",
            payload={
                "user_id": requester_notif["user_id"],
                "notification_id": requester_notif["id"],
                "type": requester_notif["type"]
            }
        )
        await manager.broadcast(
            event="REQUEST_APPROVED",
            payload={
                "request_id": request_id,
                "request_number": req["request_number"],
                "department_id": req["department_id"],
                "status": "approved"
            }
        )

        updated = await db.requests.find_one({"id": request_id}, {"_id": 0})
        await manager.broadcast(
            event="REQUEST_STATE_CHANGED",
            payload={
                "request_id": updated["id"],
                "status": updated["status"],
                "current_step": updated.get("current_approval_step", 0)
            }
        )
        return updated

    current_approval = None
    for a in approvals:
        if a["step"] == current_step and a["approver_id"] == user["id"]:
            current_approval = a
            break

    if not current_approval:
        raise HTTPException(status_code=403, detail="You are not the current approver for this request")
    if current_approval["status"] != "pending":
        raise HTTPException(status_code=400, detail="This step has already been acted upon")

    now = datetime.now(timezone.utc).isoformat()

    if action.action == "reject":
        for a in approvals:
            if a["step"] == current_step and a["approver_id"] == user["id"]:
                a["status"] = "rejected"
                a["comments"] = action.comments or ""
                a["acted_at"] = now
        await db.requests.update_one({"id": request_id}, {"$set": {
            "approvals": approvals,
            "status": "rejected",
            "updated_at": now
        }})
        # Notify requester
        notif = {
            "id": str(uuid.uuid4()),
            "user_id": req["requester_id"],
            "request_id": request_id,
            "request_number": req["request_number"],
            "message": f"Your request '{request_display_name}' was rejected by {user['name']}",
            "type": "request_rejected",
            "is_read": False,
            "created_at": now
        }
        await db.notifications.insert_one(notif)
        await send_email_notification(
            req.get("requester_email", ""),
            f"Request Rejected: {req['request_number']}",
            f"<h3>Request Rejected</h3><p><b>{req['request_number']}</b> - {request_display_name}</p><p>Rejected by: {user['name']}</p><p>Comments: {action.comments or 'None'}</p>"
        )
        await manager.broadcast(
            event="NOTIFICATION_CREATED",
            payload={
                "user_id": notif["user_id"],
                "notification_id": notif["id"],
                "type": notif["type"]
            }
        )
        await manager.broadcast(
            event="REQUEST_REJECTED",
            payload={
                "request_id": request_id,
                "request_number": req["request_number"],
                "acted_by": user["id"],
                "department_id": req["department_id"],
                "status": "rejected"
            }
        )

    elif action.action == "approve":
        for a in approvals:
            if a["step"] == current_step and a["approver_id"] == user["id"]:
                a["status"] = "approved"
                a["comments"] = action.comments or ""
                a["acted_at"] = now

        next_step = current_step + 1
        has_next = any(a["step"] == next_step for a in approvals)

        if has_next:
            for a in approvals:
                if a["step"] == next_step:
                    a["status"] = "pending"
            await db.requests.update_one({"id": request_id}, {"$set": {
                "approvals": approvals,
                "current_approval_step": next_step,
                "updated_at": now
            }})
            next_approver_data = next((a for a in approvals if a["step"] == next_step), None)
            if next_approver_data:
                next_approver = await db.users.find_one({"id": next_approver_data["approver_id"]}, {"_id": 0})
                if next_approver:
                    notif = {
                        "id": str(uuid.uuid4()),
                        "user_id": next_approver["id"],
                        "request_id": request_id,
                        "request_number": req["request_number"],
                        "message": f"Request '{request_display_name}' requires your approval (Step {next_step})",
                        "type": "approval_required",
                        "is_read": False,
                        "created_at": now
                    }
                    await db.notifications.insert_one(notif)
                    await send_email_notification(
                        next_approver.get("email", ""),
                        f"Approval Required (Step {next_step}): {req['request_number']}",
                        f"<h3>Approval Required</h3><p><b>{req['request_number']}</b> - {request_display_name}</p><p>Step {next_step} of {req['total_approval_steps']}</p>"
                    )
                    await manager.broadcast(
                        event="NOTIFICATION_CREATED",
                        payload={
                            "user_id": notif["user_id"],
                            "notification_id": notif["id"],
                            "type": notif["type"]
                        }
                    )
                    await manager.broadcast(
                        event="REQUEST_UPDATED",
                        payload={
                            "request_id": request_id,
                            "request_number": req["request_number"],
                            "current_step": next_step,
                            "status": "in_progress",
                            "department_id": req["department_id"]
                        }
                    )

        else:
            if custodian and custodian.get("user_id"):
                custodian["status"] = "pending"
                await db.requests.update_one({"id": request_id}, {"$set": {
                    "approvals": approvals,
                    "custodian": custodian,
                    "status": "pending",
                    "current_approval_step": current_step + 1,
                    "updated_at": now
                }})
                custodian_user = await db.users.find_one({"id": custodian["user_id"]}, {"_id": 0})
                if custodian_user:
                    notif = {
                        "id": str(uuid.uuid4()),
                        "user_id": custodian_user["id"],
                        "request_id": request_id,
                        "request_number": req["request_number"],
                        "message": f"Request '{request_display_name}' is ready for fulfillment confirmation",
                        "type": "custodian_required",
                        "is_read": False,
                        "created_at": now
                    }
                    await db.notifications.insert_one(notif)
                    await send_email_notification(
                        custodian_user.get("email", ""),
                        f"Fulfillment Required: {req['request_number']}",
                        f"<h3>Request Ready for Fulfillment</h3><p><b>{req['request_number']}</b> - {request_display_name}</p><p>All approvers have approved this request.</p><p>Please fulfill it and confirm completion.</p>"
                    )
                    await manager.broadcast(
                        event="NOTIFICATION_CREATED",
                        payload={
                            "user_id": notif["user_id"],
                            "notification_id": notif["id"],
                            "type": notif["type"]
                        }
                    )
            else:
                await db.requests.update_one({"id": request_id}, {"$set": {
                    "approvals": approvals,
                    "status": "approved",
                    "updated_at": now
                }})
                notif = {
                    "id": str(uuid.uuid4()),
                    "user_id": req["requester_id"],
                    "request_id": request_id,
                    "request_number": req["request_number"],
                    "message": f"Your request '{request_display_name}' has been fully approved!",
                    "type": "request_approved",
                    "is_read": False,
                    "created_at": now
                }
                await db.notifications.insert_one(notif)
                await send_email_notification(
                    req.get("requester_email", ""),
                    f"Request Approved: {req['request_number']}",
                    f"<h3>Request Approved</h3><p><b>{req['request_number']}</b> - {request_display_name}</p><p>All approvers have signed off.</p>"
                )
                await manager.broadcast(
                    event="NOTIFICATION_CREATED",
                    payload={
                        "user_id": notif["user_id"],
                        "notification_id": notif["id"],
                        "type": notif["type"]
                    }
                )
                await manager.broadcast(
                    event="REQUEST_APPROVED",
                    payload={
                        "request_id": request_id,
                        "request_number": req["request_number"],
                        "department_id": req["department_id"],
                        "status": "approved"
                    }
                )

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve', 'reject', or 'fulfill'")

    updated = await db.requests.find_one({"id": request_id}, {"_id": 0})

    await manager.broadcast(
    event="REQUEST_STATE_CHANGED",
        payload={
            "request_id": updated["id"],
            "status": updated["status"],
            "current_step": updated.get("current_approval_step", 0)
        }
    )

    return updated

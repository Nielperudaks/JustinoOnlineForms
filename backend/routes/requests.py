from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, get_current_user, send_email_notification
import uuid
from datetime import datetime, timezone

requests_router = APIRouter(prefix="/requests", tags=["requests"])


class RequestCreate(BaseModel):
    form_template_id: str
    title: str
    form_data: dict
    notes: Optional[str] = ""
    priority: Optional[str] = "normal"  # low, normal, high, urgent


class RequestAction(BaseModel):
    action: str  # approve, reject
    comments: Optional[str] = ""


@requests_router.get("")
async def list_requests(
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    my_requests: Optional[bool] = False,
    my_approvals: Optional[bool] = False,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if department_id:
        query["department_id"] = department_id
    if my_requests:
        query["requester_id"] = user["id"]
    if my_approvals:
        query["approvals"] = {
            "$elemMatch": {
                "approver_id": user["id"],
                "status": "pending"
            }
        }
        query["status"] = "in_progress"

    total = await db.requests.count_documents(query)
    skip = (page - 1) * limit
    reqs = await db.requests.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    if search:
        s = search.lower()
        reqs = [r for r in reqs if s in r.get("title", "").lower() or s in r.get("request_number", "").lower()]

    return {"items": reqs, "total": total, "page": page, "limit": limit}


@requests_router.get("/{request_id}")
async def get_request(request_id: str, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@requests_router.post("/")
async def create_request(req: RequestCreate, user=Depends(get_current_user)):
    tmpl = await db.form_templates.find_one({"id": req.form_template_id, "is_active": True}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=400, detail="Form template not found or inactive")

    count = await db.requests.count_documents({})
    request_number = f"REQ-{count + 1:05d}"

    approvals = []
    for step in tmpl.get("approver_chain", []):
        approvals.append({
            "step": step["step"],
            "approver_id": step["user_id"],
            "approver_name": step.get("user_name", ""),
            "status": "pending" if step["step"] == 1 else "waiting",
            "comments": "",
            "acted_at": None
        })

    initial_status = "in_progress" if approvals else "approved"

    request_doc = {
        "id": str(uuid.uuid4()),
        "request_number": request_number,
        "form_template_id": req.form_template_id,
        "form_template_name": tmpl["name"],
        "department_id": tmpl["department_id"],
        "requester_id": user["id"],
        "requester_name": user["name"],
        "requester_email": user.get("email", ""),
        "title": req.title,
        "form_data": req.form_data,
        "notes": req.notes or "",
        "priority": req.priority or "normal",
        "status": initial_status,
        "current_approval_step": 1 if approvals else 0,
        "total_approval_steps": len(approvals),
        "approvals": approvals,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    await db.requests.insert_one(request_doc)
    result = {k: v for k, v in request_doc.items() if k != "_id"}

    # Notify first approver
    if approvals:
        first_approver = await db.users.find_one({"id": approvals[0]["approver_id"]}, {"_id": 0})
        if first_approver:
            notif = {
                "id": str(uuid.uuid4()),
                "user_id": first_approver["id"],
                "request_id": result["id"],
                "request_number": request_number,
                "message": f"New request '{req.title}' from {user['name']} requires your approval",
                "type": "approval_required",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notif)
            await send_email_notification(
                first_approver.get("email", ""),
                f"Approval Required: {request_number} - {req.title}",
                f"<h3>New Request Pending Your Approval</h3><p><b>{request_number}</b> - {req.title}</p><p>From: {user['name']}</p><p>Please log in to review and approve.</p>"
            )

    return result


@requests_router.post("/{request_id}/action")
async def action_request(request_id: str, action: RequestAction, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "in_progress":
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")

    current_step = req.get("current_approval_step", 1)
    approvals = req.get("approvals", [])

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
            "message": f"Your request '{req['title']}' was rejected by {user['name']}",
            "type": "request_rejected",
            "is_read": False,
            "created_at": now
        }
        await db.notifications.insert_one(notif)
        await send_email_notification(
            req.get("requester_email", ""),
            f"Request Rejected: {req['request_number']}",
            f"<h3>Request Rejected</h3><p><b>{req['request_number']}</b> - {req['title']}</p><p>Rejected by: {user['name']}</p><p>Comments: {action.comments or 'None'}</p>"
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
                        "message": f"Request '{req['title']}' requires your approval (Step {next_step})",
                        "type": "approval_required",
                        "is_read": False,
                        "created_at": now
                    }
                    await db.notifications.insert_one(notif)
                    await send_email_notification(
                        next_approver.get("email", ""),
                        f"Approval Required (Step {next_step}): {req['request_number']}",
                        f"<h3>Approval Required</h3><p><b>{req['request_number']}</b> - {req['title']}</p><p>Step {next_step} of {req['total_approval_steps']}</p>"
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
                "message": f"Your request '{req['title']}' has been fully approved!",
                "type": "request_approved",
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(notif)
            await send_email_notification(
                req.get("requester_email", ""),
                f"Request Approved: {req['request_number']}",
                f"<h3>Request Approved</h3><p><b>{req['request_number']}</b> - {req['title']}</p><p>All approvers have signed off.</p>"
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")

    updated = await db.requests.find_one({"id": request_id}, {"_id": 0})
    return updated

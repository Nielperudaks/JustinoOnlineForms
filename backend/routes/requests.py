from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, get_current_user, render_request_email, send_email_notification
from utils.form_fields import validate_table_field_rows
from utils.roles import (
    APPROVER_ROLES,
    EXECUTIVE_LEVEL,
    EXECUTIVE_ROLES,
    FORM_MANAGER_ROLES,
    MANAGER_LEVEL,
    MANAGER_ROLES,
    SUPER_ADMIN,
    SUPERVISOR,
    SUPERVISOR_LEVEL,
    is_requestor_capable,
    user_hierarchy_level,
)
from utils.cache import invalidate_stats_cache
import uuid
from datetime import datetime, time, timezone
from realtime import manager

requests_router = APIRouter(prefix="/requests", tags=["requests"])

REQUEST_LIST_PROJECTION = {
    "_id": 0,
    "form_fields": 0,
    "form_data": 0,
    "notes": 0,
    "requester_email": 0,
    "approvals": 0,
    "custodian.comments": 0,
    "custodian.acted_at": 0,
}


class RequestCreate(BaseModel):
    form_template_id: str
    title: Optional[str] = None
    form_data: dict
    notes: Optional[str] = ""
    priority: Optional[str] = None


class RequestAction(BaseModel):
    action: str  # approve, reject, fulfill
    comments: Optional[str] = ""


class RequestCancel(BaseModel):
    comments: str


# Role-based approval steps that are resolved against the requestor's
# department hierarchy when a request is created.
ROLE_BASED_APPROVER_IDS = {
    "immediate_supervisor",  # requestor's department-group supervisor
    "requestor_manager",  # requestor's department manager
    "immediate_manager",  # legacy alias of requestor_manager
    "department_executive",  # requestor's department executive
    "immediate_head",  # lowest available head above the requestor's level
}


async def find_group_supervisor(user, department):
    """Active supervisor of the requestor's department group, or None."""
    dept_id = (department or {}).get("id")
    for group in (department or {}).get("department_groups", []):
        if user.get("id") in group.get("member_ids", []):
            return await db.users.find_one(
                {
                    "id": group.get("supervisor_id"),
                    "role": SUPERVISOR,
                    "department_id": dept_id,
                    "is_active": True,
                },
                {"_id": 0, "password_hash": 0},
            )
    return None


async def find_department_manager(department):
    """Active manager assigned to the department, or None.

    Prefers the explicit hierarchy assignment; falls back to an active
    manager-role user belonging to the department so pre-hierarchy data
    keeps routing correctly.
    """
    if not department:
        return None
    manager_id = department.get("manager_id")
    if manager_id:
        assigned = await db.users.find_one(
            {"id": manager_id, "role": {"$in": list(FORM_MANAGER_ROLES)}, "is_active": True},
            {"_id": 0, "password_hash": 0},
        )
        if assigned:
            return assigned
    return await db.users.find_one(
        {
            "role": {"$in": list(MANAGER_ROLES)},
            "department_id": department.get("id"),
            "is_active": True,
        },
        {"_id": 0, "password_hash": 0},
    )


async def find_department_executive(department):
    """Active executive assigned to the department, or None.

    Prefers the explicit hierarchy assignment; falls back to an active
    executive-role user belonging to the department.
    """
    if not department:
        return None
    executive_id = department.get("executive_id")
    if executive_id:
        assigned = await db.users.find_one(
            {"id": executive_id, "role": {"$in": list(EXECUTIVE_ROLES)}, "is_active": True},
            {"_id": 0, "password_hash": 0},
        )
        if assigned:
            return assigned
    return await db.users.find_one(
        {
            "role": {"$in": list(EXECUTIVE_ROLES)},
            "department_id": department.get("id"),
            "is_active": True,
        },
        {"_id": 0, "password_hash": 0},
    )


async def find_head_at_level(user, department, level):
    if level == SUPERVISOR_LEVEL:
        return await find_group_supervisor(user, department)
    if level == MANAGER_LEVEL:
        return await find_department_manager(department)
    if level == EXECUTIVE_LEVEL:
        return await find_department_executive(department)
    return None


async def resolve_role_based_approver(approver_id, user, department):
    """Resolve a role-based approval step to (user_id, name), or None to skip.

    Raises HTTP 400 when a mandatory head (the department executive) is
    missing from the requestor's department hierarchy.
    """
    requester_level = user_hierarchy_level(user)

    if approver_id == "immediate_supervisor":
        # Skips when the requestor has no group supervisor, or already sits
        # at or above the supervisor level.
        if requester_level >= SUPERVISOR_LEVEL:
            return None
        supervisor = await find_group_supervisor(user, department)
        if not supervisor or supervisor["id"] == user.get("id"):
            return None
        return supervisor["id"], supervisor.get("name", "Supervisor")

    if approver_id in ("requestor_manager", "immediate_manager"):
        # Skips when the requestor's department has no manager, or the
        # requestor is at or above the manager level.
        if requester_level >= MANAGER_LEVEL:
            return None
        manager_user = await find_department_manager(department)
        if not manager_user or manager_user["id"] == user.get("id"):
            return None
        return manager_user["id"], manager_user.get("name", "Manager")

    if approver_id == "department_executive":
        # Mandatory: every department must have an executive assigned.
        if requester_level >= EXECUTIVE_LEVEL:
            return None
        if not department:
            raise HTTPException(
                status_code=400,
                detail="Requestor has no department assigned. The Executive approval step requires the requestor to have a department.",
            )
        executive = await find_department_executive(department)
        if not executive:
            raise HTTPException(
                status_code=400,
                detail="No Executive is assigned to the requestor's department. Please ask the Super Admin to assign one in the Departments tab.",
            )
        if executive["id"] == user.get("id"):
            return None
        return executive["id"], executive.get("name", "Executive")

    if approver_id == "immediate_head":
        # Dynamic: walk up from the level right above the requestor's role
        # (supervisor -> manager -> executive) and pick the first head found.
        if requester_level >= EXECUTIVE_LEVEL:
            return None
        if not department:
            raise HTTPException(
                status_code=400,
                detail="Requestor has no department assigned. The Immediate Head approval step requires the requestor to have a department.",
            )
        start_level = max(requester_level + 1, SUPERVISOR_LEVEL)
        for level in range(start_level, EXECUTIVE_LEVEL + 1):
            head = await find_head_at_level(user, department, level)
            if head and head["id"] != user.get("id"):
                return head["id"], head.get("name", "Immediate Head")
        raise HTTPException(
            status_code=400,
            detail="No Immediate Head found for the requestor's department. Please ask the Super Admin to assign an Executive in the Departments tab.",
        )

    return None


@requests_router.get("")
async def list_requests(
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    form_template_id: Optional[str] = None,
    requester_id: Optional[str] = None,
    custodian_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
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
            query["custodian.status"] = {"$ne": "pending"}
        elif status == "approved":
            query["status"] = status
            query["custodian.status"] = {"$ne": "fulfilled"}
        else:
            query["status"] = status
    if department_id:
        query["department_id"] = department_id
    if form_template_id:
        query["form_template_id"] = form_template_id
    if requester_id:
        query["requester_id"] = requester_id
    if custodian_status:
        query["custodian.status"] = custodian_status
    created_at_filter = {}
    if date_from:
        try:
            start_date = datetime.fromisoformat(date_from).date()
            created_at_filter["$gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc).isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from")
    if date_to:
        try:
            end_date = datetime.fromisoformat(date_to).date()
            created_at_filter["$lte"] = datetime.combine(end_date, time.max, tzinfo=timezone.utc).isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to")
    if created_at_filter:
        query["created_at"] = created_at_filter
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

    # Non-super-admin: restrict to user-related requests. Managers can also
    # inspect requests owned by their department.
    role = user.get("role", "")
    if role != SUPER_ADMIN:
        user_scope_options = [
            {"requester_id": user["id"]},
            {"approvals": {"$elemMatch": {"approver_id": user["id"]}}},
            {"custodian.user_id": user["id"]},
        ]
        if role in FORM_MANAGER_ROLES and user.get("department_id"):
            user_scope_options.append({"department_id": user["department_id"]})
        user_scope = {"$or": user_scope_options}
        query = {"$and": [query, user_scope]} if query else user_scope

    total = await db.requests.count_documents(query)
    skip = offset if offset else (page - 1) * limit
    reqs = await db.requests.find(query, REQUEST_LIST_PROJECTION).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    return {"items": reqs, "total": total, "page": page, "limit": limit, "offset": skip}


@requests_router.get("/requesters")
async def list_request_requesters(user=Depends(get_current_user)):
    """Return the distinct set of requesters visible to the current user.

    Uses the same scope rules as list_requests so the filter options always
    match exactly what the user can actually see — no department limitation,
    no role-based user-table access required.
    """
    role = user.get("role", "")

    if role == SUPER_ADMIN:
        scope_query = {}
    else:
        scope_options = [
            {"requester_id": user["id"]},
            {"approvals": {"$elemMatch": {"approver_id": user["id"]}}},
            {"custodian.user_id": user["id"]},
        ]
        if role in FORM_MANAGER_ROLES and user.get("department_id"):
            scope_options.append({"department_id": user["department_id"]})
        scope_query = {"$or": scope_options}

    pipeline = [
        {"$match": scope_query},
        {
            "$group": {
                "_id": "$requester_id",
                "name": {"$first": "$requester_name"},
            }
        },
        {"$project": {"_id": 0, "id": "$_id", "name": 1}},
        {"$sort": {"name": 1}},
    ]

    requesters = await db.requests.aggregate(pipeline).to_list(500)
    return requesters


@requests_router.get("/{request_id}")
async def get_request(request_id: str, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    # Non-super-admin can only view requests they created, are assigned to, or
    # manage by department.
    if user.get("role") != SUPER_ADMIN:
        uid = user["id"]
        is_requester = req.get("requester_id") == uid
        is_approver = any(a.get("approver_id") == uid for a in req.get("approvals", []))
        is_custodian = (req.get("custodian") or {}).get("user_id") == uid
        is_department_manager = (
            user.get("role") in FORM_MANAGER_ROLES
            and user.get("department_id")
            and req.get("department_id") == user.get("department_id")
        )
        if not is_requester and not is_approver and not is_custodian and not is_department_manager:
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
    if not is_requestor_capable(user):
        raise HTTPException(status_code=403, detail="Only requestors can create requests")
    tmpl = await db.form_templates.find_one({"id": req.form_template_id, "is_active": True}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=400, detail="Form template not found or inactive")
    display_title = tmpl["name"]

    for field in tmpl.get("fields", []):
        if field.get("type") == "table":
            validate_table_field_rows(field, req.form_data.get(field.get("name")))

    count = await db.requests.count_documents({})
    request_number = f"REQ-{count + 1:05d}"

    approvals = []
    requester_dept_id = user.get("department_id", "")
    seen_approver_ids = set()
    next_step_number = 1
    custodian_doc = None

    requester_department = None
    if requester_dept_id:
        requester_department = await db.departments.find_one({"id": requester_dept_id}, {"_id": 0})

    for step in tmpl.get("approver_chain", []):
        approver_id = step["user_id"]
        approver_name = step.get("user_name", "")

        if approver_id in ROLE_BASED_APPROVER_IDS:
            resolved = await resolve_role_based_approver(approver_id, user, requester_department)
            if resolved is None:
                # No head exists for this optional step (or the requestor is
                # at/above its level) — skip to the next approval step.
                continue
            approver_id, approver_name = resolved

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
        "form_fields": tmpl.get("fields", []),
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
    invalidate_stats_cache()
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
                f"Approval Required: {display_title} - {request_number}",
                render_request_email(
                    heading="New Request Pending Your Approval",
                    request_id=result["id"],
                    request_number=request_number,
                    request_title=display_title,
                    intro="A new request is waiting for your review.",
                    requester_name=user["name"],
                    status_label=f"Step 1 of {total_steps}",
                    action_label="Review request",
                ),
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
            f"Fulfillment Required: {display_title} - {request_number}",
            render_request_email(
                heading="Request Ready for Fulfillment",
                request_id=result["id"],
                request_number=request_number,
                request_title=display_title,
                intro="This request is ready for fulfillment confirmation.",
                requester_name=user["name"],
                status_label="Awaiting custodian confirmation",
                action_label="Review request",
            ),
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
async def cancel_request(request_id: str, cancellation: RequestCancel, user=Depends(get_current_user)):
    req = await db.requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    cancellation_reason = cancellation.comments.strip()
    if not cancellation_reason:
        raise HTTPException(status_code=400, detail="Cancellation reason is required")

    if req["status"] in ("cancelled", "rejected", "approved"):
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")

    approvals = req.get("approvals", [])
    custodian = req.get("custodian") or {}
    is_super_admin = user.get("role") == SUPER_ADMIN

    if not is_super_admin and (not approvals or all(a.get("status") == "approved" for a in approvals)):
        raise HTTPException(
            status_code=400,
            detail="Request can no longer be cancelled because all approvers have approved it",
        )

    # Requester can cancel while approvers are still pending. Super admin can cancel any active request.
    if user["id"] != req["requester_id"] and not is_super_admin:
        raise HTTPException(status_code=403, detail="You are not allowed to cancel this request")

    now = datetime.now(timezone.utc).isoformat()
    request_display_name = req.get("form_template_name") or req.get("title") or "Request"

    for approval in approvals:
        if approval.get("status") in ("pending", "waiting"):
            approval["status"] = "cancelled"
            approval["comments"] = cancellation_reason
            approval["acted_at"] = now

    if custodian.get("status") in ("pending", "waiting"):
        custodian["status"] = "cancelled"
        custodian["comments"] = cancellation_reason
        custodian["acted_at"] = now

    await db.requests.update_one(
        {"id": request_id},
        {
            "$set": {
                "approvals": approvals,
                "custodian": custodian,
                "status": "cancelled",
                "cancellation_reason": cancellation_reason,
                "cancelled_by": user["id"],
                "cancelled_by_name": user.get("name", ""),
                "cancelled_at": now,
                "updated_at": now,
            }
        },
    )
    invalidate_stats_cache()

    updated = await db.requests.find_one({"id": request_id}, {"_id": 0})

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
            "message": f"Request '{request_display_name}' was cancelled by {user.get('name', 'the requester')}: {cancellation_reason}",
            "type": "request_cancelled",
            "is_read": False,
            "created_at": now,
        }
        await db.notifications.insert_one(notif)
        await send_email_notification(
            approver_user.get("email", ""),
            f"Request Cancelled: {request_display_name} - {req['request_number']}",
            render_request_email(
                heading="Request Cancelled",
                request_id=request_id,
                request_number=req["request_number"],
                request_title=request_display_name,
                intro="A request assigned to your approval chain has been cancelled.",
                requester_name=req.get("requester_name", ""),
                actor_name=user.get("name", ""),
                status_label="Cancelled",
                comments=cancellation_reason,
                action_label="View request",
            ),
        )
        await manager.broadcast(
            event="NOTIFICATION_CREATED",
            payload={
                "user_id": notif["user_id"],
                "notification_id": notif["id"],
                "type": notif["type"],
            },
        )

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

    if action.action in ("approve", "reject") and role not in APPROVER_ROLES:
        raise HTTPException(status_code=403, detail="Only approvers can approve or reject requests")

    # AFTER
    if action.action in ("fulfill", "custodian_reject"):
        if not custodian or custodian.get("user_id") != user["id"]:
            raise HTTPException(status_code=403, detail="You are not the assigned custodian for this request")
        if req["status"] != "pending" or custodian.get("status") != "pending":
            raise HTTPException(status_code=400, detail="This request is not awaiting custodian confirmation")

        now = datetime.now(timezone.utc).isoformat()

        if action.action == "custodian_reject":
            if not (action.comments or "").strip():
                raise HTTPException(status_code=400, detail="A rejection reason is required")

            custodian["status"] = "rejected"
            custodian["comments"] = action.comments.strip()
            custodian["acted_at"] = now

            await db.requests.update_one(
                {"id": request_id},
                {"$set": {
                    "custodian": custodian,
                    "status": "rejected",
                    "updated_at": now,
                }},
            )
            invalidate_stats_cache()

            # Notify requester
            notif = {
                "id": str(uuid.uuid4()),
                "user_id": req["requester_id"],
                "request_id": request_id,
                "request_number": req["request_number"],
                "message": f"Your request '{request_display_name}' was rejected by custodian {user['name']}",
                "type": "request_rejected",
                "is_read": False,
                "created_at": now,
            }
            await db.notifications.insert_one(notif)
            await send_email_notification(
                req.get("requester_email", ""),
                f"Request Rejected: {request_display_name} - {req['request_number']}",
                render_request_email(
                    heading="Request Rejected by Custodian",
                    request_id=request_id,
                    request_number=req["request_number"],
                    request_title=request_display_name,
                    intro="Your request was rejected during custodian review.",
                    requester_name=req.get("requester_name", ""),
                    actor_name=user["name"],
                    status_label="Rejected by custodian",
                    comments=custodian["comments"],
                    action_label="View request",
                ),
            )
            await manager.broadcast(
                event="NOTIFICATION_CREATED",
                payload={
                    "user_id": notif["user_id"],
                    "notification_id": notif["id"],
                    "type": notif["type"],
                },
            )
            await manager.broadcast(
                event="REQUEST_REJECTED",
                payload={
                    "request_id": request_id,
                    "request_number": req["request_number"],
                    "acted_by": user["id"],
                    "department_id": req["department_id"],
                    "status": "rejected",
                },
            )
            updated = await db.requests.find_one({"id": request_id}, {"_id": 0})
            await manager.broadcast(
                event="REQUEST_STATE_CHANGED",
                payload={
                    "request_id": updated["id"],
                    "status": updated["status"],
                    "current_step": updated.get("current_approval_step", 0),
                },
            )
            return updated

        # --- fulfill path continues below ---
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
        invalidate_stats_cache()

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
                f"Request Completed: {req['request_number']} - {request_display_name}",
                render_request_email(
                    heading="Request Completed",
                    request_id=request_id,
                    request_number=req["request_number"],
                    request_title=request_display_name,
                    intro="A request you approved has been fulfilled and confirmed.",
                    requester_name=req.get("requester_name", ""),
                    actor_name=user["name"],
                    status_label="Completed",
                    comments=action.comments or "None",
                    action_label="View request",
                ),
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
            f"Request Approved: {req['request_number']} - {request_display_name}",
            render_request_email(
                heading="Request Fulfilled",
                request_id=request_id,
                request_number=req["request_number"],
                request_title=request_display_name,
                intro="Your request has been fulfilled and is now complete.",
                requester_name=req.get("requester_name", ""),
                actor_name=user["name"],
                status_label="Completed",
                action_label="View request",
            ),
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
        invalidate_stats_cache()
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
            f"Request Rejected: {request_display_name} - {req['request_number']}",
            render_request_email(
                heading="Request Rejected",
                request_id=request_id,
                request_number=req["request_number"],
                request_title=request_display_name,
                intro="Your request was rejected during approval review.",
                requester_name=req.get("requester_name", ""),
                actor_name=user["name"],
                status_label=f"Rejected at step {current_step}",
                comments=action.comments or "None",
                action_label="View request",
            ),
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
            invalidate_stats_cache()
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
                        f"Approval Required (Step {next_step}): {request_display_name} - {req['request_number']}",
                        render_request_email(
                            heading="Approval Required",
                            request_id=request_id,
                            request_number=req["request_number"],
                            request_title=request_display_name,
                            intro="This request has moved to your approval step.",
                            requester_name=req.get("requester_name", ""),
                            status_label=f"Step {next_step} of {req['total_approval_steps']}",
                            action_label="Review request",
                        ),
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
                invalidate_stats_cache()
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
                        f"Fulfillment Required: {request_display_name} - {req['request_number']}",
                        render_request_email(
                            heading="Request Ready for Fulfillment",
                            request_id=request_id,
                            request_number=req["request_number"],
                            request_title=request_display_name,
                            intro="All approval steps are complete. Please fulfill the request and confirm completion.",
                            requester_name=req.get("requester_name", ""),
                            status_label="Awaiting custodian confirmation",
                            action_label="Review request",
                        ),
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
                invalidate_stats_cache()
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
                    render_request_email(
                        heading="Request Approved",
                        request_id=request_id,
                        request_number=req["request_number"],
                        request_title=request_display_name,
                        intro="All approvers have signed off on your request.",
                        requester_name=req.get("requester_name", ""),
                        status_label="Approved",
                        action_label="View request",
                    ),
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

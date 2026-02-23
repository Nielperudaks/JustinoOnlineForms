from fastapi import APIRouter, Depends
from utils.helpers import db, get_current_user

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    uid = user["id"]
    role = user["role"]

    if role == "super_admin":
        total = await db.requests.count_documents({})
        pending = await db.requests.count_documents({"status": "in_progress"})
        approved = await db.requests.count_documents({"status": "approved"})
        rejected = await db.requests.count_documents({"status": "rejected"})
        cancelled = await db.requests.count_documents({"status": "cancelled"})
        total_users = await db.users.count_documents({})
        total_templates = await db.form_templates.count_documents({"is_active": True})
    else:
        user_scope = {
            "$or": [
                {"requester_id": uid},
                {"approvals": {"$elemMatch": {"approver_id": uid}}},
            ]
        }
        total = await db.requests.count_documents(user_scope)
        pending = await db.requests.count_documents({**user_scope, "status": "in_progress"})
        approved = await db.requests.count_documents({**user_scope, "status": "approved"})
        rejected = await db.requests.count_documents({**user_scope, "status": "rejected"})
        cancelled = await db.requests.count_documents({**user_scope, "status": "cancelled"})
        total_users = 0
        total_templates = 0

    my_pending_approvals = await db.requests.count_documents({
        "approvals": {"$elemMatch": {"approver_id": uid, "status": "pending"}},
        "status": "in_progress"
    })

    unread_notifs = await db.notifications.count_documents({"user_id": uid, "is_read": False})

    return {
        "total_requests": total,
        "pending_requests": pending,
        "approved_requests": approved,
        "rejected_requests": rejected,
        "cancelled_requests": cancelled,
        "my_pending_approvals": my_pending_approvals,
        "unread_notifications": unread_notifs,
        "total_users": total_users,
        "total_templates": total_templates
    }

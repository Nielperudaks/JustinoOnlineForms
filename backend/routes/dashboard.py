from fastapi import APIRouter, Depends
from utils.helpers import db, get_current_user
from utils.cache import stats_cache

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats")
async def get_dashboard_stats(user=Depends(get_current_user)):
    cache_key = (user["id"], user["role"], user.get("department_id", ""))
    return await stats_cache.get_or_set("dashboard_stats", cache_key, lambda: compute_dashboard_stats(user))


async def compute_dashboard_stats(user):
    uid = user["id"]
    role = user["role"]

    if role == "super_admin":
        request_match = {}
        total_users = await db.users.count_documents({})
        total_templates = await db.form_templates.count_documents({"is_active": True})
    else:
        request_match = {
            "$or": [
                {"requester_id": uid},
                {"approvals": {"$elemMatch": {"approver_id": uid}}},
                {"custodian.user_id": uid},
            ]
        }
        total_users = 0
        total_templates = 0

    request_stats = await db.requests.aggregate([
        {"$match": request_match},
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "pending_requests": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$in": ["$status", ["in_progress", "pending"]]},
                                    {"$ne": ["$custodian.status", "pending"]},
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "approved_requests": {
                    "$sum": {
                        "$cond": [
                            {
                                "$and": [
                                    {"$eq": ["$status", "approved"]},
                                    {"$ne": ["$custodian.status", "fulfilled"]},
                                ]
                            },
                            1,
                            0,
                        ]
                    }
                },
                "custodian_pending_requests": {
                    "$sum": {"$cond": [{"$eq": ["$custodian.status", "pending"]}, 1, 0]}
                },
                "custodian_fulfilled_requests": {
                    "$sum": {"$cond": [{"$eq": ["$custodian.status", "fulfilled"]}, 1, 0]}
                },
                "rejected_requests": {
                    "$sum": {"$cond": [{"$eq": ["$status", "rejected"]}, 1, 0]}
                },
                "cancelled_requests": {
                    "$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}
                },
            }
        },
    ]).to_list(1)
    request_stats = request_stats[0] if request_stats else {}

    my_pending_approvals = await db.requests.count_documents({
        "$or": [
            {
                "approvals": {"$elemMatch": {"approver_id": uid, "status": "pending"}},
                "status": "in_progress"
            },
            {
                "custodian.user_id": uid,
                "custodian.status": "pending",
                "status": "pending"
            },
        ]
    })

    unread_notifs = await db.notifications.count_documents({"user_id": uid, "is_read": False})

    return {
        "total_requests": request_stats.get("total_requests", 0),
        "pending_requests": request_stats.get("pending_requests", 0),
        "approved_requests": request_stats.get("approved_requests", 0),
        "custodian_pending_requests": request_stats.get("custodian_pending_requests", 0),
        "custodian_fulfilled_requests": request_stats.get("custodian_fulfilled_requests", 0),
        "rejected_requests": request_stats.get("rejected_requests", 0),
        "cancelled_requests": request_stats.get("cancelled_requests", 0),
        "my_pending_approvals": my_pending_approvals,
        "unread_notifications": unread_notifs,
        "total_users": total_users,
        "total_templates": total_templates
    }

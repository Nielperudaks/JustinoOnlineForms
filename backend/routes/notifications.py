from fastapi import APIRouter, Depends, Query
from utils.helpers import db, get_current_user
import uuid
from datetime import datetime, timezone

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("")
async def list_notifications(
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if unread_only:
        query["is_read"] = False
    total = await db.notifications.count_documents(query)
    unread_count = await db.notifications.count_documents({"user_id": user["id"], "is_read": False})
    skip = (page - 1) * limit
    notifs = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"items": notifs, "total": total, "unread_count": unread_count, "page": page}


@notifications_router.post("/{notification_id}/read")
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"is_read": True}}
    )
    return {"message": "Marked as read"}


@notifications_router.post("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": user["id"], "is_read": False},
        {"$set": {"is_read": True}}
    )
    return {"message": "All notifications marked as read"}

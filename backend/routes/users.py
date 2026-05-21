from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, hash_password, require_admin, require_form_manager, get_current_user
from utils.cache import invalidate_metadata_cache, invalidate_stats_cache, metadata_cache
import uuid
from datetime import datetime, timezone

users_router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str  # super_admin, requestor, approver, both
    department_id: str


class UserUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None
    has_viewed_tutorial: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@users_router.get("")
async def list_users(
    department_id: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    current=Depends(require_form_manager)
):
    cache_key = (
        current.get("role"),
        current.get("department_id", ""),
        department_id or "",
        role or "",
        search or "",
    )
    return await metadata_cache.get_or_set(
        "users",
        cache_key,
        lambda: _list_users_uncached(department_id, role, search, current),
    )


async def _list_users_uncached(department_id, role, search, current):
    query = {}
    if current.get("role") == "manager":
        query["department_id"] = current.get("department_id")
    elif department_id:
        query["department_id"] = department_id
    if role:
        query["role"] = role
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(1000)
    if search:
        search_lower = search.lower()
        users = [u for u in users if search_lower in u.get("name", "").lower() or search_lower in u.get("email", "").lower()]
    return users


@users_router.post("", status_code=201)
async def create_user(req: UserCreate, admin=Depends(require_admin)):
    existing = await db.users.find_one({"email": req.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    dept = await db.departments.find_one({"id": req.department_id}, {"_id": 0})
    if not dept:
        raise HTTPException(status_code=400, detail="Department not found")
    user = {
        "id": str(uuid.uuid4()),
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "name": req.name,
        "role": req.role,
        "department_id": req.department_id,
        "has_viewed_tutorial": False,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    invalidate_metadata_cache()
    invalidate_stats_cache()
    return {k: v for k, v in user.items() if k not in ("_id", "password_hash")}


@users_router.put("/{user_id}")
async def update_user(user_id: str, req: UserUpdate, admin=Depends(require_admin)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "email" in updates:
        email = updates["email"].lower()
        existing = await db.users.find_one({"email": email}, {"_id": 0})
        if existing and existing.get("id") != user_id:
            raise HTTPException(status_code=400, detail="Email already registered")
        updates["email"] = email

    if "password" in updates:
        password = updates.pop("password")
        if not password:
            raise HTTPException(status_code=400, detail="Password cannot be empty")
        updates["password_hash"] = hash_password(password)

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.users.update_one({"id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    invalidate_metadata_cache()
    invalidate_stats_cache()
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return user


@users_router.delete("/{user_id}")
async def delete_user(user_id: str, admin=Depends(require_admin)):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    invalidate_metadata_cache()
    invalidate_stats_cache()
    return {"message": "User deleted"}


@users_router.get("/approvers")
async def list_approvers(department_id: Optional[str] = None, user=Depends(get_current_user)):
    cache_key = (user.get("role"), user.get("department_id", ""), department_id or "")
    return await metadata_cache.get_or_set(
        "approvers",
        cache_key,
        lambda: _list_approvers_uncached(department_id, user),
    )


async def _list_approvers_uncached(department_id, user):
    query = {"role": {"$in": ["approver", "both", "manager", "super_admin"]}}
    if user.get("role") == "manager":
        query["department_id"] = user.get("department_id")
    elif department_id:
        query["department_id"] = department_id
    approvers = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(500)
    return approvers


@users_router.get("/custodians")
async def list_custodians(department_id: Optional[str] = None, user=Depends(get_current_user)):
    cache_key = (user.get("role"), user.get("department_id", ""), department_id or "")
    return await metadata_cache.get_or_set(
        "custodians",
        cache_key,
        lambda: _list_custodians_uncached(department_id, user),
    )


async def _list_custodians_uncached(department_id, user):
    query = {"is_active": True}
    if user.get("role") == "manager":
        query["department_id"] = user.get("department_id")
    elif department_id:
        query["department_id"] = department_id
    custodians = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(500)
    return custodians


@users_router.put("/{user_id}/password")
async def change_password(user_id: str, req: PasswordChange, current=Depends(get_current_user)):
    from utils.helpers import verify_password
    if current["id"] != user_id and current["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current["id"] == user_id and not verify_password(req.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": hash_password(req.new_password)}})
    invalidate_metadata_cache()
    return {"message": "Password changed"}

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, hash_password, require_admin, get_current_user
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
    name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


@users_router.get("/")
async def list_users(
    department_id: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    admin=Depends(require_admin)
):
    query = {}
    if department_id:
        query["department_id"] = department_id
    if role:
        query["role"] = role
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(1000)
    if search:
        search_lower = search.lower()
        users = [u for u in users if search_lower in u.get("name", "").lower() or search_lower in u.get("email", "").lower()]
    return users


@users_router.post("/")
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
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    return {k: v for k, v in user.items() if k not in ("_id", "password_hash")}


@users_router.put("/{user_id}")
async def update_user(user_id: str, req: UserUpdate, admin=Depends(require_admin)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.users.update_one({"id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return user


@users_router.delete("/{user_id}")
async def delete_user(user_id: str, admin=Depends(require_admin)):
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@users_router.get("/approvers")
async def list_approvers(department_id: Optional[str] = None, user=Depends(get_current_user)):
    query = {"role": {"$in": ["approver", "both", "super_admin"]}}
    if department_id:
        query["department_id"] = department_id
    approvers = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(500)
    return approvers


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
    return {"message": "Password changed"}

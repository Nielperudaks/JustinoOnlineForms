from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from utils.helpers import db, require_admin, get_current_user
import uuid
from datetime import datetime, timezone

departments_router = APIRouter(prefix="/departments", tags=["departments"])


class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = ""


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@departments_router.get("")
async def list_departments(user=Depends(get_current_user)):
    depts = await db.departments.find({"is_active": True}, {"_id": 0}).to_list(100)
    return depts


@departments_router.get("/all")
async def list_all_departments(admin=Depends(require_admin)):
    depts = await db.departments.find({}, {"_id": 0}).to_list(100)
    return depts


@departments_router.post("/")
async def create_department(req: DepartmentCreate, admin=Depends(require_admin)):
    existing = await db.departments.find_one({"code": req.code.upper()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    dept = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "code": req.code.upper(),
        "description": req.description or "",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.departments.insert_one(dept)
    return {k: v for k, v in dept.items() if k != "_id"}


@departments_router.put("/{dept_id}")
async def update_department(dept_id: str, req: DepartmentUpdate, admin=Depends(require_admin)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.departments.update_one({"id": dept_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    dept = await db.departments.find_one({"id": dept_id}, {"_id": 0})
    return dept

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from utils.helpers import db, require_admin, get_current_user
from utils.cache import invalidate_metadata_cache, metadata_cache
from utils.realtime_events import metadata_changed_payload
from utils.roles import EXECUTIVE_ROLES, FORM_MANAGER_ROLES, SUPER_ADMIN, SUPERVISOR
from realtime import manager
import uuid
from datetime import datetime, timezone

departments_router = APIRouter(prefix="/departments", tags=["departments"])


class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = ""


class DepartmentGroup(BaseModel):
    id: Optional[str] = None
    name: str
    supervisor_id: str
    member_ids: List[str] = Field(default_factory=list)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    department_groups: Optional[List[DepartmentGroup]] = None


async def normalize_department_groups(dept_id: str, groups: List[DepartmentGroup]):
    user_ids = set()
    for group in groups:
        user_ids.add(group.supervisor_id)
        user_ids.update(group.member_ids)

    users = await db.users.find(
        {"id": {"$in": list(user_ids)}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(user_ids) or 1)
    users_by_id = {user["id"]: user for user in users}
    seen_members = set()
    normalized = []

    for group in groups:
        name = group.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Department group name is required")

        supervisor = users_by_id.get(group.supervisor_id)
        if (
            not supervisor
            or supervisor.get("department_id") != dept_id
            or supervisor.get("role") != SUPERVISOR
            or supervisor.get("is_active") is False
        ):
            raise HTTPException(
                status_code=400,
                detail="Department group supervisor must be an active supervisor in this department",
            )

        member_ids = []
        for member_id in group.member_ids:
            if member_id in seen_members:
                raise HTTPException(status_code=400, detail="A user can belong to only one department group")

            member = users_by_id.get(member_id)
            member_role = member.get("role") if member else ""
            if (
                not member
                or member.get("department_id") != dept_id
                or member.get("is_active") is False
                or member_role in FORM_MANAGER_ROLES
                or member_role in EXECUTIVE_ROLES
                or member_role in {SUPERVISOR, SUPER_ADMIN}
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Department group members must be active non-manager department users",
                )

            seen_members.add(member_id)
            member_ids.append(member_id)

        normalized.append(
            {
                "id": group.id or str(uuid.uuid4()),
                "name": name,
                "supervisor_id": group.supervisor_id,
                "member_ids": member_ids,
            }
        )

    return normalized


@departments_router.get("")
async def list_departments(user=Depends(get_current_user)):
    return await metadata_cache.get_or_set(
        "departments",
        ("active",),
        lambda: db.departments.find({"is_active": True}, {"_id": 0}).to_list(100),
    )


@departments_router.get("/all")
async def list_all_departments(admin=Depends(require_admin)):
    return await metadata_cache.get_or_set(
        "departments",
        ("all",),
        lambda: db.departments.find({}, {"_id": 0}).to_list(100),
    )


@departments_router.post("", status_code=201)
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
    invalidate_metadata_cache()
    await manager.broadcast(
        event="ADMIN_METADATA_CHANGED",
        payload=metadata_changed_payload("departments", "created", item_id=dept["id"]),
    )
    return {k: v for k, v in dept.items() if k != "_id"}


@departments_router.put("/{dept_id}")
async def update_department(dept_id: str, req: DepartmentUpdate, admin=Depends(require_admin)):
    updates = {k: v for k, v in req.model_dump(exclude={"department_groups"}).items() if v is not None}
    if req.department_groups is not None:
        updates["department_groups"] = await normalize_department_groups(dept_id, req.department_groups)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "code" in updates:
        updates["code"] = updates["code"].upper()
        existing = await db.departments.find_one(
            {"code": updates["code"], "id": {"$ne": dept_id}},
            {"_id": 0},
        )
        if existing:
            raise HTTPException(status_code=400, detail="Department code already exists")
    result = await db.departments.update_one({"id": dept_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    invalidate_metadata_cache()
    dept = await db.departments.find_one({"id": dept_id}, {"_id": 0})
    await manager.broadcast(
        event="ADMIN_METADATA_CHANGED",
        payload=metadata_changed_payload("departments", "updated", item_id=dept["id"]),
    )
    return dept


@departments_router.delete("/{dept_id}")
async def delete_department(dept_id: str, admin=Depends(require_admin)):
    dept = await db.departments.find_one({"id": dept_id}, {"_id": 0})
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    assigned_users = await db.users.count_documents({"department_id": dept_id})
    if assigned_users > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete department while users are still assigned to it.",
        )

    existing_templates = await db.form_templates.count_documents({"department_id": dept_id})
    if existing_templates > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete department while forms still belong to it.",
        )

    result = await db.departments.delete_one({"id": dept_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    invalidate_metadata_cache()
    await manager.broadcast(
        event="ADMIN_METADATA_CHANGED",
        payload=metadata_changed_payload("departments", "deleted", item_id=dept_id),
    )

    return {"message": "Department deleted"}

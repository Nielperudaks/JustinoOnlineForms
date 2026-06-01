from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, require_form_manager, get_current_user
from utils.cache import invalidate_metadata_cache, invalidate_stats_cache, metadata_cache
from utils.realtime_events import metadata_changed_payload
from utils.roles import APPROVER_ROLES, FORM_MANAGER_ROLES, SUPER_ADMIN, is_super_admin
from realtime import manager
import uuid
from datetime import datetime, timezone

templates_router = APIRouter(prefix="/form-templates", tags=["form-templates"])

MAX_APPROVER_STEPS = 8
SPECIAL_APPROVER_IDS = {"immediate_manager", "immediate_supervisor"}


def manager_department_id(user):
    return user.get("department_id") or ""


def ensure_manager_can_access_department(user, department_id):
    if is_super_admin(user):
        return
    if user.get("role") not in FORM_MANAGER_ROLES or manager_department_id(user) != department_id:
        raise HTTPException(status_code=403, detail="Managers can only manage forms in their department")


def validate_approver_chain_limit(approver_chain=None):
    if len(approver_chain or []) > MAX_APPROVER_STEPS:
        raise HTTPException(
            status_code=400,
            detail=f"Forms can have a maximum of {MAX_APPROVER_STEPS} approvers",
        )


async def ensure_manager_can_access_template(user, template_id):
    tmpl = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    ensure_manager_can_access_department(user, tmpl.get("department_id"))
    return tmpl


async def validate_manager_assignments(user, approver_chain=None, custodian=None):
    if is_super_admin(user):
        return

    dept_id = manager_department_id(user)
    for approver in approver_chain or []:
        approver_id = approver.user_id if hasattr(approver, "user_id") else approver.get("user_id")
        if approver_id in SPECIAL_APPROVER_IDS:
            continue
        approver_user = await db.users.find_one(
            {
                "id": approver_id,
                "department_id": dept_id,
                "is_active": True,
                "role": {"$in": list(APPROVER_ROLES)},
            },
            {"_id": 0},
        )
        if not approver_user:
            raise HTTPException(
                status_code=400,
                detail="Managers can only assign active approvers from their department",
            )

    if custodian:
        custodian_id = custodian.user_id if hasattr(custodian, "user_id") else custodian.get("user_id")
        custodian_user = await db.users.find_one(
            {
                "id": custodian_id,
                "department_id": dept_id,
                "is_active": True,
            },
            {"_id": 0},
        )
        if not custodian_user:
            raise HTTPException(
                status_code=400,
                detail="Managers can only assign active custodians from their department",
            )


class FormField(BaseModel):
    name: str
    label: str
    type: str  # text, link, textarea, number, date, select, table, dropzone
    required: bool = True
    options: Optional[List[str]] = None
    is_multiselect: bool = False
    placeholder: Optional[str] = ""
    # Table field config
    table_title: Optional[str] = None
    column_headers: Optional[List[str]] = None
    num_rows: Optional[int] = None


class ApproverStep(BaseModel):
    step: int
    user_id: str
    user_name: Optional[str] = ""


class CustodianAssignment(BaseModel):
    user_id: str
    user_name: Optional[str] = ""


class TemplateCreate(BaseModel):
    department_id: str
    name: str
    description: Optional[str] = ""
    fields: List[FormField]
    approver_chain: List[ApproverStep] = []
    custodian: Optional[CustodianAssignment] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[FormField]] = None
    approver_chain: Optional[List[ApproverStep]] = None
    custodian: Optional[CustodianAssignment] = None
    is_active: Optional[bool] = None


@templates_router.get("")
async def list_templates(
    department_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    cache_key = (department_id or "",)
    return await metadata_cache.get_or_set(
        "templates",
        cache_key,
        lambda: _list_templates_uncached(department_id),
    )


async def _list_templates_uncached(department_id):
    query = {"is_active": True}
    if department_id:
        query["department_id"] = department_id
    return await db.form_templates.find(query, {"_id": 0}).to_list(500)


@templates_router.get("/all")
async def list_all_templates(current=Depends(require_form_manager)):
    cache_key = (current.get("role"), manager_department_id(current))
    return await metadata_cache.get_or_set(
        "all_templates",
        cache_key,
        lambda: _list_all_templates_uncached(current),
    )


async def _list_all_templates_uncached(current):
    query = {}
    if not is_super_admin(current):
        query["department_id"] = manager_department_id(current)
    return await db.form_templates.find(query, {"_id": 0}).to_list(500)


@templates_router.get("/{template_id}")
async def get_template(template_id: str, user=Depends(get_current_user)):
    tmpl = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@templates_router.post("", status_code=201)
async def create_template(req: TemplateCreate, current=Depends(require_form_manager)):
    ensure_manager_can_access_department(current, req.department_id)
    validate_approver_chain_limit(req.approver_chain)
    await validate_manager_assignments(current, req.approver_chain, req.custodian)
    dept = await db.departments.find_one({"id": req.department_id}, {"_id": 0})
    if not dept:
        raise HTTPException(status_code=400, detail="Department not found")
    tmpl = {
        "id": str(uuid.uuid4()),
        "department_id": req.department_id,
        "name": req.name,
        "description": req.description or "",
        "fields": [f.model_dump() for f in req.fields],
        "approver_chain": [a.model_dump() for a in req.approver_chain],
        "custodian": req.custodian.model_dump() if req.custodian else None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.form_templates.insert_one(tmpl)
    invalidate_metadata_cache()
    invalidate_stats_cache()
    await manager.broadcast(
        event="ADMIN_METADATA_CHANGED",
        payload=metadata_changed_payload(
            "templates",
            "created",
            item_id=tmpl["id"],
            department_id=tmpl["department_id"],
        ),
    )
    return {k: v for k, v in tmpl.items() if k != "_id"}


@templates_router.put("/{template_id}")
async def update_template(template_id: str, req: TemplateUpdate, current=Depends(require_form_manager)):
    await ensure_manager_can_access_template(current, template_id)
    data = req.model_dump(exclude_unset=True)
    if "approver_chain" in data:
        validate_approver_chain_limit(req.approver_chain)
    if "approver_chain" in data or "custodian" in data:
        await validate_manager_assignments(
            current,
            req.approver_chain if "approver_chain" in data else None,
            req.custodian if "custodian" in data else None,
        )
    updates = {}
    for k, v in data.items():
        if k == "fields":
            updates[k] = [f if isinstance(f, dict) else f.model_dump() for f in v]
        elif k == "approver_chain":
            updates[k] = [a if isinstance(a, dict) else a.model_dump() for a in v]
        elif k == "custodian":
            updates[k] = None if v is None else (v if isinstance(v, dict) else v.model_dump())
        else:
            updates[k] = v
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.form_templates.update_one({"id": template_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    invalidate_metadata_cache()
    invalidate_stats_cache()
    tmpl = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    await manager.broadcast(
        event="ADMIN_METADATA_CHANGED",
        payload=metadata_changed_payload(
            "templates",
            "updated",
            item_id=tmpl["id"],
            department_id=tmpl.get("department_id"),
        ),
    )
    return tmpl


@templates_router.delete("/{template_id}")
async def delete_template(template_id: str, current=Depends(require_form_manager)):
    """
    Permanently delete a form template.

    A template can only be deleted if there are no pending/active requests
    that still reference it. This keeps approval flows and history consistent.
    """
    tmpl = await ensure_manager_can_access_template(current, template_id)

    # Block deletion if there are pending/active requests using this template
    active_count = await db.requests.count_documents(
        {
            "form_template_id": template_id,
            "status": {"$in": ["in_progress"]},
        }
    )
    if active_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete form: there are pending or active requests using this form.",
        )

    result = await db.form_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    invalidate_metadata_cache()
    invalidate_stats_cache()
    await manager.broadcast(
        event="ADMIN_METADATA_CHANGED",
        payload=metadata_changed_payload(
            "templates",
            "deleted",
            item_id=template_id,
            department_id=tmpl.get("department_id"),
        ),
    )
    return {"message": "Template deleted"}

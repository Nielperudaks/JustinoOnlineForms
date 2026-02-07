from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from utils.helpers import db, require_admin, get_current_user
import uuid
from datetime import datetime, timezone

templates_router = APIRouter(prefix="/form-templates", tags=["form-templates"])


class FormField(BaseModel):
    name: str
    label: str
    type: str  # text, textarea, number, date, select, file
    required: bool = True
    options: Optional[List[str]] = None
    placeholder: Optional[str] = ""


class ApproverStep(BaseModel):
    step: int
    user_id: str
    user_name: Optional[str] = ""


class TemplateCreate(BaseModel):
    department_id: str
    name: str
    description: Optional[str] = ""
    fields: List[FormField]
    approver_chain: List[ApproverStep] = []


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[FormField]] = None
    approver_chain: Optional[List[ApproverStep]] = None
    is_active: Optional[bool] = None


@templates_router.get("")
async def list_templates(
    department_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    query = {"is_active": True}
    if department_id:
        query["department_id"] = department_id
    templates = await db.form_templates.find(query, {"_id": 0}).to_list(500)
    return templates


@templates_router.get("/all")
async def list_all_templates(admin=Depends(require_admin)):
    templates = await db.form_templates.find({}, {"_id": 0}).to_list(500)
    return templates


@templates_router.get("/{template_id}")
async def get_template(template_id: str, user=Depends(get_current_user)):
    tmpl = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@templates_router.post("", status_code=201)
async def create_template(req: TemplateCreate, admin=Depends(require_admin)):
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
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.form_templates.insert_one(tmpl)
    return {k: v for k, v in tmpl.items() if k != "_id"}


@templates_router.put("/{template_id}")
async def update_template(template_id: str, req: TemplateUpdate, admin=Depends(require_admin)):
    updates = {}
    data = req.model_dump()
    for k, v in data.items():
        if v is not None:
            if k == "fields":
                updates[k] = [f if isinstance(f, dict) else f.model_dump() for f in v]
            elif k == "approver_chain":
                updates[k] = [a if isinstance(a, dict) else a.model_dump() for a in v]
            else:
                updates[k] = v
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.form_templates.update_one({"id": template_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    tmpl = await db.form_templates.find_one({"id": template_id}, {"_id": 0})
    return tmpl


@templates_router.delete("/{template_id}")
async def delete_template(template_id: str, admin=Depends(require_admin)):
    result = await db.form_templates.update_one({"id": template_id}, {"$set": {"is_active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deactivated"}

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import form_templates


class FakeCursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self, _limit):
        return list(self.items)


class FakeResult:
    def __init__(self, matched_count=0, deleted_count=0):
        self.matched_count = matched_count
        self.deleted_count = deleted_count


class FakeCollection:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.inserted = []

    def find(self, query=None, projection=None):
        query = query or {}
        return FakeCursor([self._project(item, projection) for item in self.items if self._matches(item, query)])

    async def find_one(self, query, projection=None):
        for item in self.items:
            if self._matches(item, query):
                return self._project(item, projection)
        return None

    async def insert_one(self, item):
        self.items.append(item)
        self.inserted.append(item)
        return FakeResult()

    async def update_one(self, query, update):
        for item in self.items:
            if self._matches(item, query):
                item.update(update.get("$set", {}))
                return FakeResult(matched_count=1)
        return FakeResult(matched_count=0)

    async def delete_one(self, query):
        for index, item in enumerate(self.items):
            if self._matches(item, query):
                self.items.pop(index)
                return FakeResult(deleted_count=1)
        return FakeResult(deleted_count=0)

    async def count_documents(self, query):
        return len([item for item in self.items if self._matches(item, query)])

    def _project(self, item, projection):
        if not projection:
            return dict(item)
        if any(value == 0 for value in projection.values()):
            return {key: value for key, value in item.items() if projection.get(key) != 0}
        return {key: item[key] for key, include in projection.items() if include and key in item}

    def _matches(self, item, query):
        for key, expected in query.items():
            actual = item.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                continue
            if actual != expected:
                return False
        return True


class FakeDb:
    def __init__(self):
        self.departments = FakeCollection(
            [
                {"id": "dept-a", "name": "Department A", "is_active": True},
                {"id": "dept-b", "name": "Department B", "is_active": True},
            ]
        )
        self.users = FakeCollection(
            [
                {"id": "approver-a", "name": "Approver A", "role": "approver", "department_id": "dept-a", "is_active": True},
                {"id": "both-a", "name": "Both A", "role": "both", "department_id": "dept-a", "is_active": True},
                {"id": "requestor-a", "name": "Requestor A", "role": "requestor", "department_id": "dept-a", "is_active": True},
                {"id": "approver-b", "name": "Approver B", "role": "approver", "department_id": "dept-b", "is_active": True},
                {"id": "inactive-a", "name": "Inactive A", "role": "approver", "department_id": "dept-a", "is_active": False},
            ]
        )
        self.form_templates = FakeCollection(
            [
                {
                    "id": "template-a",
                    "department_id": "dept-a",
                    "name": "A Form",
                    "description": "",
                    "fields": [],
                    "approver_chain": [],
                    "custodian": None,
                    "is_active": True,
                },
                {
                    "id": "template-b",
                    "department_id": "dept-b",
                    "name": "B Form",
                    "description": "",
                    "fields": [],
                    "approver_chain": [],
                    "custodian": None,
                    "is_active": True,
                },
            ]
        )
        self.requests = FakeCollection([])


def run(coro):
    return asyncio.run(coro)


def manager():
    return {"id": "manager-a", "role": "manager_ops", "department_id": "dept-a", "name": "Manager A"}


def super_admin():
    return {"id": "admin", "role": "super_admin", "department_id": "dept-b", "name": "Admin"}


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(form_templates, "db", db)
    form_templates.invalidate_metadata_cache()
    return db


def make_template_create(department_id="dept-a", approver_chain=None, custodian=None, fields=None):
    return form_templates.TemplateCreate(
        department_id=department_id,
        name="New Form",
        description="",
        fields=fields or [],
        approver_chain=approver_chain or [],
        custodian=custodian,
    )


def test_manager_lists_only_templates_from_their_department(fake_db):
    templates = run(form_templates.list_all_templates(current=manager()))

    assert [template["id"] for template in templates] == ["template-a"]


def test_super_admin_lists_all_templates(fake_db):
    templates = run(form_templates.list_all_templates(current=super_admin()))

    assert {template["id"] for template in templates} == {"template-a", "template-b"}


def test_public_template_list_excludes_disabled_templates(fake_db):
    fake_db.form_templates.items.append(
        {
            "id": "template-disabled",
            "department_id": "dept-a",
            "name": "Disabled Form",
            "description": "",
            "fields": [],
            "approver_chain": [],
            "custodian": None,
            "is_active": False,
        }
    )

    templates = run(form_templates.list_templates(department_id="dept-a", user=manager()))

    assert [template["id"] for template in templates] == ["template-a"]


def test_admin_template_list_includes_disabled_templates(fake_db):
    fake_db.form_templates.items.append(
        {
            "id": "template-disabled",
            "department_id": "dept-a",
            "name": "Disabled Form",
            "description": "",
            "fields": [],
            "approver_chain": [],
            "custodian": None,
            "is_active": False,
        }
    )

    templates = run(form_templates.list_all_templates(current=manager()))

    assert [template["id"] for template in templates] == [
        "template-a",
        "template-disabled",
    ]


def test_manager_cannot_create_template_for_another_department(fake_db):
    with pytest.raises(HTTPException) as exc:
        run(form_templates.create_template(make_template_create(department_id="dept-b"), current=manager()))

    assert exc.value.status_code == 403


def test_manager_can_assign_department_approval_capable_approver(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=1, user_id="approver-a", user_name="Approver A"),
            form_templates.ApproverStep(step=2, user_id="both-a", user_name="Both A"),
            form_templates.ApproverStep(step=3, user_id="immediate_manager", user_name="Immediate Manager"),
        ]
    )

    created = run(form_templates.create_template(req, current=manager()))

    assert created["department_id"] == "dept-a"
    assert [step["user_id"] for step in created["approver_chain"]] == ["approver-a", "both-a", "immediate_manager"]


def test_manager_can_assign_immediate_supervisor_placeholder(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=1, user_id="immediate_supervisor", user_name="Immediate Supervisor"),
        ]
    )

    created = run(form_templates.create_template(req, current=manager()))

    assert created["approver_chain"][0]["user_id"] == "immediate_supervisor"


def test_template_accepts_eight_approval_steps(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=step, user_id="immediate_manager", user_name="Immediate Manager")
            for step in range(1, 9)
        ]
    )

    created = run(form_templates.create_template(req, current=manager()))

    assert len(created["approver_chain"]) == 8
    assert created["approver_chain"][-1]["step"] == 8


def test_template_rejects_more_than_eight_approval_steps(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=step, user_id="immediate_manager", user_name="Immediate Manager")
            for step in range(1, 10)
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(form_templates.create_template(req, current=manager()))

    assert exc.value.status_code == 400
    assert "8 approvers" in exc.value.detail


def test_manager_cannot_assign_requestor_as_approver(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=1, user_id="requestor-a", user_name="Requestor A"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(form_templates.create_template(req, current=manager()))

    assert exc.value.status_code == 400
    assert "approver" in exc.value.detail.lower()


def test_manager_cannot_assign_cross_department_approver(fake_db):
    req = make_template_create(
        approver_chain=[
            form_templates.ApproverStep(step=1, user_id="approver-b", user_name="Approver B"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(form_templates.create_template(req, current=manager()))

    assert exc.value.status_code == 400


def test_manager_can_assign_any_active_department_user_as_custodian(fake_db):
    req = make_template_create(
        custodian=form_templates.CustodianAssignment(user_id="requestor-a", user_name="Requestor A")
    )

    created = run(form_templates.create_template(req, current=manager()))

    assert created["custodian"]["user_id"] == "requestor-a"


def test_manager_cannot_assign_cross_department_custodian(fake_db):
    req = make_template_create(
        custodian=form_templates.CustodianAssignment(user_id="approver-b", user_name="Approver B")
    )

    with pytest.raises(HTTPException) as exc:
        run(form_templates.create_template(req, current=manager()))

    assert exc.value.status_code == 400
    assert "custodian" in exc.value.detail.lower()


def test_manager_cannot_update_template_outside_department(fake_db):
    update = form_templates.TemplateUpdate(name="Changed")

    with pytest.raises(HTTPException) as exc:
        run(form_templates.update_template("template-b", update, current=manager()))

    assert exc.value.status_code == 403


def test_manager_cannot_delete_template_outside_department(fake_db):
    with pytest.raises(HTTPException) as exc:
        run(form_templates.delete_template("template-b", current=manager()))

    assert exc.value.status_code == 403


def test_template_persists_typed_table_columns_and_unique_flags(fake_db):
    req = make_template_create(
        fields=[
            {
                "name": "items",
                "label": "Items",
                "type": "table",
                "required": True,
                "table_title": "Line Items",
                "columns": [
                    {"label": "Date", "type": "date", "unique": False},
                    {"label": "Time", "type": "time", "unique": False},
                    {"label": "Description", "type": "text", "unique": True},
                    {"label": "Qty", "type": "number", "unique": False},
                ],
                "num_rows": 3,
            }
        ],
    )

    created = run(form_templates.create_template(req, current=manager()))

    table = created["fields"][0]
    assert table["columns"][0]["type"] == "date"
    assert table["columns"][1]["type"] == "time"
    assert table["columns"][2]["unique"] is True

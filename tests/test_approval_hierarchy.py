import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import requests
from backend.utils.roles import APPROVER_ROLES, REQUESTOR_ROLES, hierarchy_level


class FakeResult:
    def __init__(self, inserted_id=None):
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.inserted = []

    async def find_one(self, query, projection=None):
        for item in self.items:
            if self._matches(item, query):
                return self._project(item, projection)
        return None

    async def count_documents(self, query):
        return len([item for item in self.items if self._matches(item, query)])

    async def insert_one(self, item):
        self.items.append(item)
        self.inserted.append(item)
        return FakeResult()

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
                if "$ne" in expected and actual == expected["$ne"]:
                    return False
                continue
            if actual != expected:
                return False
        return True


class FakeManager:
    async def broadcast(self, **_kwargs):
        return None


async def send_email_noop(*_args, **_kwargs):
    return None


class FakeDb:
    def __init__(self):
        self.departments = FakeCollection(
            [
                {
                    "id": "dept-a",
                    "executive_id": "executive-a",
                    "manager_id": "manager-a",
                    "department_groups": [
                        {
                            "id": "group-a",
                            "name": "Team A",
                            "supervisor_id": "supervisor-a",
                            "member_ids": ["requestor-a"],
                        }
                    ],
                }
            ]
        )
        self.form_templates = FakeCollection(
            [
                {
                    "id": "template-1",
                    "department_id": "dept-a",
                    "name": "Leave Form",
                    "fields": [],
                    "approver_chain": [],
                    "is_active": True,
                }
            ]
        )
        self.users = FakeCollection(
            [
                {
                    "id": "manager-a",
                    "name": "Manager A",
                    "email": "manager@example.com",
                    "role": "manager",
                    "department_id": "dept-a",
                    "is_active": True,
                },
                {
                    "id": "executive-a",
                    "name": "Executive A",
                    "email": "executive@example.com",
                    "role": "executive",
                    "department_id": "corporate",
                    "is_active": True,
                },
                {
                    "id": "supervisor-a",
                    "name": "Supervisor A",
                    "email": "supervisor@example.com",
                    "role": "supervisor",
                    "department_id": "dept-a",
                    "is_active": True,
                },
            ]
        )
        self.requests = FakeCollection([])
        self.notifications = FakeCollection([])


def run(coro):
    return asyncio.run(coro)


def make_request():
    return requests.RequestCreate(
        form_template_id="template-1",
        form_data={"reason": "Annual leave"},
    )


REQUESTOR_A = {
    "id": "requestor-a",
    "name": "Requestor A",
    "email": "requestor@example.com",
    "role": "requestor",
    "department_id": "dept-a",
}

REQUESTOR_B = {  # not in any department group
    "id": "requestor-b",
    "name": "Requestor B",
    "email": "requestor.b@example.com",
    "role": "requestor",
    "department_id": "dept-a",
}

SUPERVISOR_A = {
    "id": "supervisor-a",
    "name": "Supervisor A",
    "email": "supervisor@example.com",
    "role": "supervisor",
    "department_id": "dept-a",
}

MANAGER_A = {
    "id": "manager-a",
    "name": "Manager A",
    "email": "manager@example.com",
    "role": "manager",
    "department_id": "dept-a",
}

EXECUTIVE_A = {
    "id": "executive-a",
    "name": "Executive A",
    "email": "executive@example.com",
    "role": "executive",
    "department_id": "corporate",
}


def submit_as(user, monkeypatch, approver_ids=("immediate_head",), db=None):
    db = db or FakeDb()
    db.form_templates.items[0]["approver_chain"] = [
        {"step": index + 1, "user_id": approver_id, "user_name": approver_id}
        for index, approver_id in enumerate(approver_ids)
    ]
    monkeypatch.setattr(requests, "db", db)
    monkeypatch.setattr(requests, "manager", FakeManager())
    monkeypatch.setattr(requests, "send_email_notification", send_email_noop)

    return run(requests.create_request(make_request(), user=user))


def approver_ids_of(created):
    return [a["approver_id"] for a in created["approvals"]]


def test_core_roles_can_request_and_approve():
    for role in ("supervisor", "manager", "executive"):
        assert role in REQUESTOR_ROLES
        assert role in APPROVER_ROLES
    assert hierarchy_level("requestor") == 0
    assert hierarchy_level("supervisor") == 1
    assert hierarchy_level("manager") == 2
    assert hierarchy_level("executive") == 3
    # Legacy roles keep working as aliases
    assert hierarchy_level("manager_ops") == 2
    assert hierarchy_level("executive_sup") == 3


# ── Supervisor step ──

def test_group_member_supervisor_step_routes_to_group_supervisor(monkeypatch):
    created = submit_as(REQUESTOR_A, monkeypatch, ("immediate_supervisor",))
    assert approver_ids_of(created) == ["supervisor-a"]


def test_supervisor_step_skips_when_requestor_has_no_group(monkeypatch):
    created = submit_as(REQUESTOR_B, monkeypatch, ("immediate_supervisor",))
    assert approver_ids_of(created) == []
    assert created["status"] == "approved"


def test_supervisor_step_skips_for_supervisor_requestor(monkeypatch):
    created = submit_as(
        SUPERVISOR_A, monkeypatch, ("immediate_supervisor", "requestor_manager")
    )
    assert approver_ids_of(created) == ["manager-a"]


# ── Requestor's Manager step ──

def test_manager_step_routes_to_assigned_department_manager(monkeypatch):
    created = submit_as(REQUESTOR_A, monkeypatch, ("requestor_manager",))
    assert approver_ids_of(created) == ["manager-a"]


def test_legacy_immediate_manager_id_aliases_to_requestor_manager(monkeypatch):
    created = submit_as(REQUESTOR_A, monkeypatch, ("immediate_manager",))
    assert approver_ids_of(created) == ["manager-a"]


def test_manager_step_skips_when_department_has_no_manager(monkeypatch):
    db = FakeDb()
    db.departments.items[0]["manager_id"] = None
    db.users.items = [u for u in db.users.items if u["id"] != "manager-a"]
    created = submit_as(REQUESTOR_A, monkeypatch, ("requestor_manager",), db=db)
    assert approver_ids_of(created) == []
    assert created["status"] == "approved"


def test_manager_step_falls_back_to_department_manager_role_when_unassigned(monkeypatch):
    db = FakeDb()
    db.departments.items[0]["manager_id"] = None
    created = submit_as(REQUESTOR_A, monkeypatch, ("requestor_manager",), db=db)
    assert approver_ids_of(created) == ["manager-a"]


def test_manager_step_skips_for_manager_requestor(monkeypatch):
    created = submit_as(
        MANAGER_A, monkeypatch, ("requestor_manager", "department_executive")
    )
    assert approver_ids_of(created) == ["executive-a"]


# ── Executive step ──

def test_executive_step_routes_to_assigned_department_executive(monkeypatch):
    created = submit_as(REQUESTOR_A, monkeypatch, ("department_executive",))
    assert approver_ids_of(created) == ["executive-a"]


def test_executive_step_errors_when_department_has_no_executive(monkeypatch):
    db = FakeDb()
    db.departments.items[0]["executive_id"] = None
    with pytest.raises(HTTPException) as exc:
        submit_as(REQUESTOR_A, monkeypatch, ("department_executive",), db=db)
    assert exc.value.status_code == 400
    assert "Executive" in exc.value.detail


def test_executive_step_skips_for_executive_requestor(monkeypatch):
    created = submit_as(EXECUTIVE_A, monkeypatch, ("department_executive",))
    assert approver_ids_of(created) == []
    assert created["status"] == "approved"


# ── Immediate Head step ──

def test_immediate_head_prefers_group_supervisor_for_members(monkeypatch):
    created = submit_as(REQUESTOR_A, monkeypatch, ("immediate_head",))
    assert approver_ids_of(created) == ["supervisor-a"]


def test_immediate_head_uses_manager_when_no_supervisor(monkeypatch):
    created = submit_as(REQUESTOR_B, monkeypatch, ("immediate_head",))
    assert approver_ids_of(created) == ["manager-a"]


def test_immediate_head_for_supervisor_requestor_is_manager(monkeypatch):
    created = submit_as(SUPERVISOR_A, monkeypatch, ("immediate_head",))
    assert approver_ids_of(created) == ["manager-a"]


def test_immediate_head_for_manager_requestor_is_executive(monkeypatch):
    created = submit_as(MANAGER_A, monkeypatch, ("immediate_head",))
    assert approver_ids_of(created) == ["executive-a"]


def test_immediate_head_falls_back_to_executive_when_no_supervisor_or_manager(monkeypatch):
    db = FakeDb()
    db.departments.items[0]["manager_id"] = None
    db.departments.items[0]["department_groups"] = []
    db.users.items = [u for u in db.users.items if u["id"] != "manager-a"]
    created = submit_as(REQUESTOR_A, monkeypatch, ("immediate_head",), db=db)
    assert approver_ids_of(created) == ["executive-a"]


def test_immediate_head_errors_when_department_has_no_heads_at_all(monkeypatch):
    db = FakeDb()
    db.departments.items[0]["manager_id"] = None
    db.departments.items[0]["executive_id"] = None
    db.departments.items[0]["department_groups"] = []
    db.users.items = []
    with pytest.raises(HTTPException) as exc:
        submit_as(REQUESTOR_A, monkeypatch, ("immediate_head",), db=db)
    assert exc.value.status_code == 400


def test_duplicate_resolved_heads_collapse_into_one_step(monkeypatch):
    # Supervisor step and Immediate Head both resolve to the same supervisor.
    created = submit_as(
        REQUESTOR_A,
        monkeypatch,
        ("immediate_supervisor", "immediate_head", "department_executive"),
    )
    assert approver_ids_of(created) == ["supervisor-a", "executive-a"]
    assert [a["step"] for a in created["approvals"]] == [1, 2]

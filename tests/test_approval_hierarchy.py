import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import requests
from backend.utils.roles import APPROVER_ROLES, REQUESTOR_ROLES


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
                    "approver_chain": [
                        {
                            "step": 1,
                            "user_id": "immediate_manager",
                            "user_name": "Immediate Manager",
                        }
                    ],
                    "is_active": True,
                }
            ]
        )
        self.users = FakeCollection(
            [
                {
                    "id": "manager-ops-a",
                    "name": "Manager OPS A",
                    "email": "manager.ops@example.com",
                    "role": "manager_ops",
                    "department_id": "dept-a",
                    "is_active": True,
                },
                {
                    "id": "manager-sup-a",
                    "name": "Manager SUP A",
                    "email": "manager.sup@example.com",
                    "role": "manager_sup",
                    "department_id": "dept-a",
                    "is_active": True,
                },
                {
                    "id": "executive-ops",
                    "name": "Executive OPS",
                    "email": "exec.ops@example.com",
                    "role": "executive_ops",
                    "department_id": "executive",
                    "is_active": True,
                },
                {
                    "id": "executive-sup",
                    "name": "Executive SUP",
                    "email": "exec.sup@example.com",
                    "role": "executive_sup",
                    "department_id": "executive",
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


def submit_as(user, monkeypatch, approver_id="immediate_manager"):
    db = FakeDb()
    db.form_templates.items[0]["approver_chain"][0] = {
        "step": 1,
        "user_id": approver_id,
        "user_name": "Immediate Supervisor" if approver_id == "immediate_supervisor" else "Immediate Manager",
    }
    monkeypatch.setattr(requests, "db", db)
    monkeypatch.setattr(requests, "manager", FakeManager())
    monkeypatch.setattr(requests, "send_email_notification", send_email_noop)

    return run(requests.create_request(make_request(), user=user))


def test_supervisor_role_can_request_and_approve():
    assert "supervisor" in REQUESTOR_ROLES
    assert "supervisor" in APPROVER_ROLES


def test_non_manager_user_routes_immediate_manager_to_department_manager(monkeypatch):
    created = submit_as(
        {
            "id": "requestor-a",
            "name": "Requestor A",
            "email": "requestor@example.com",
            "role": "requestor",
            "department_id": "dept-a",
        },
        monkeypatch,
    )

    assert created["approvals"][0]["approver_id"] == "manager-ops-a"
    assert created["approvals"][0]["approver_name"] == "Manager OPS A"


def test_manager_ops_routes_immediate_manager_to_executive_ops(monkeypatch):
    created = submit_as(
        {
            "id": "manager-ops-a",
            "name": "Manager OPS A",
            "email": "manager.ops@example.com",
            "role": "manager_ops",
            "department_id": "dept-a",
        },
        monkeypatch,
    )

    assert created["approvals"][0]["approver_id"] == "executive-ops"
    assert created["approvals"][0]["approver_name"] == "Executive OPS"


def test_manager_sup_routes_immediate_manager_to_executive_sup(monkeypatch):
    created = submit_as(
        {
            "id": "manager-sup-a",
            "name": "Manager SUP A",
            "email": "manager.sup@example.com",
            "role": "manager_sup",
            "department_id": "dept-a",
        },
        monkeypatch,
    )

    assert created["approvals"][0]["approver_id"] == "executive-sup"
    assert created["approvals"][0]["approver_name"] == "Executive SUP"


def test_group_member_routes_immediate_supervisor_to_group_supervisor(monkeypatch):
    created = submit_as(
        {
            "id": "requestor-a",
            "name": "Requestor A",
            "email": "requestor@example.com",
            "role": "requestor",
            "department_id": "dept-a",
        },
        monkeypatch,
        approver_id="immediate_supervisor",
    )

    assert created["approvals"][0]["approver_id"] == "supervisor-a"
    assert created["approvals"][0]["approver_name"] == "Supervisor A"


def test_supervisor_requestor_routes_immediate_supervisor_to_manager(monkeypatch):
    created = submit_as(
        {
            "id": "supervisor-a",
            "name": "Supervisor A",
            "email": "supervisor@example.com",
            "role": "supervisor",
            "department_id": "dept-a",
        },
        monkeypatch,
        approver_id="immediate_supervisor",
    )

    assert created["approvals"][0]["approver_id"] == "manager-ops-a"


def test_non_group_member_routes_immediate_supervisor_to_manager(monkeypatch):
    created = submit_as(
        {
            "id": "requestor-b",
            "name": "Requestor B",
            "email": "requestor.b@example.com",
            "role": "requestor",
            "department_id": "dept-a",
        },
        monkeypatch,
        approver_id="immediate_supervisor",
    )

    assert created["approvals"][0]["approver_id"] == "manager-ops-a"

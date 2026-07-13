import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import departments


class FakeCursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self, _limit):
        return list(self.items)


class FakeResult:
    def __init__(self, matched_count=0):
        self.matched_count = matched_count


class FakeCollection:
    def __init__(self, items=None):
        self.items = list(items or [])

    def find(self, query=None, projection=None):
        query = query or {}
        return FakeCursor([self._project(item, projection) for item in self.items if self._matches(item, query)])

    async def find_one(self, query, projection=None):
        for item in self.items:
            if self._matches(item, query):
                return self._project(item, projection)
        return None

    async def update_one(self, query, update):
        for item in self.items:
            if self._matches(item, query):
                item.update(update.get("$set", {}))
                return FakeResult(matched_count=1)
        return FakeResult(matched_count=0)

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


class FakeDb:
    def __init__(self):
        self.departments = FakeCollection(
            [
                {
                    "id": "dept-a",
                    "name": "Department A",
                    "code": "A",
                    "description": "",
                    "is_active": True,
                },
            ]
        )
        self.users = FakeCollection(
            [
                {"id": "supervisor-a", "name": "Supervisor A", "role": "supervisor", "department_id": "dept-a", "is_active": True},
                {"id": "supervisor-b", "name": "Supervisor B", "role": "supervisor", "department_id": "dept-a", "is_active": True},
                {"id": "requestor-a", "name": "Requestor A", "role": "requestor", "department_id": "dept-a", "is_active": True},
                {"id": "both-a", "name": "Both A", "role": "both", "department_id": "dept-a", "is_active": True},
                {"id": "executive-a", "name": "Executive A", "role": "executive", "department_id": "dept-a", "is_active": True},
                {"id": "manager-a", "name": "Manager A", "role": "manager_ops", "department_id": "dept-a", "is_active": True},
                {"id": "requestor-b", "name": "Requestor B", "role": "requestor", "department_id": "dept-b", "is_active": True},
            ]
        )


def run(coro):
    return asyncio.run(coro)


def admin():
    return {"id": "admin", "role": "super_admin"}


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(departments, "db", db)
    monkeypatch.setattr(departments, "manager", FakeManager())
    return db


def test_update_department_accepts_valid_department_groups(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {
                "name": "Purchasing Team",
                "supervisor_id": "supervisor-a",
                "member_ids": ["requestor-a", "both-a"],
            }
        ]
    )

    updated = run(departments.update_department("dept-a", req, admin=admin()))

    assert updated["department_groups"][0]["name"] == "Purchasing Team"
    assert updated["department_groups"][0]["supervisor_id"] == "supervisor-a"
    assert updated["department_groups"][0]["member_ids"] == ["requestor-a", "both-a"]
    assert updated["department_groups"][0]["id"]


def test_update_department_rejects_executive_as_group_member(fake_db):
    # Executives are managerial heads in the department hierarchy and can no
    # longer be regular department-group members.
    req = departments.DepartmentUpdate(
        department_groups=[
            {
                "name": "Executive Team",
                "supervisor_id": "supervisor-a",
                "member_ids": ["executive-a"],
            }
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400


def test_update_department_rejects_duplicate_group_member(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {"name": "One", "supervisor_id": "supervisor-a", "member_ids": ["requestor-a"]},
            {"name": "Two", "supervisor_id": "supervisor-b", "member_ids": ["requestor-a"]},
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "one department group" in exc.value.detail.lower()


def test_update_department_rejects_non_supervisor_group_supervisor(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {"name": "Purchasing", "supervisor_id": "requestor-a", "member_ids": ["both-a"]},
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "supervisor" in exc.value.detail.lower()


def test_update_department_rejects_manager_as_group_member(fake_db):
    req = departments.DepartmentUpdate(
        department_groups=[
            {"name": "Purchasing", "supervisor_id": "supervisor-a", "member_ids": ["manager-a"]},
        ]
    )

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "member" in exc.value.detail.lower()

def test_update_department_assigns_executive_and_manager(fake_db):
    req = departments.DepartmentUpdate(executive_id="executive-a", manager_id="manager-a")

    updated = run(departments.update_department("dept-a", req, admin=admin()))

    assert updated["executive_id"] == "executive-a"
    assert updated["manager_id"] == "manager-a"


def test_update_department_rejects_non_executive_as_department_executive(fake_db):
    req = departments.DepartmentUpdate(executive_id="requestor-a")

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "Executive" in exc.value.detail


def test_update_department_rejects_non_manager_as_department_manager(fake_db):
    req = departments.DepartmentUpdate(manager_id="supervisor-a")

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "Manager" in exc.value.detail


def test_update_department_rejects_manager_already_heading_another_department(fake_db):
    fake_db.departments.items.append(
        {
            "id": "dept-b",
            "name": "Department B",
            "code": "B",
            "description": "",
            "manager_id": "manager-a",
            "is_active": True,
        }
    )
    req = departments.DepartmentUpdate(manager_id="manager-a")

    with pytest.raises(HTTPException) as exc:
        run(departments.update_department("dept-a", req, admin=admin()))

    assert exc.value.status_code == 400
    assert "one department" in exc.value.detail.lower()


def test_update_department_allows_clearing_head_assignments(fake_db):
    fake_db.departments.items[0]["executive_id"] = "executive-a"
    fake_db.departments.items[0]["manager_id"] = "manager-a"
    req = departments.DepartmentUpdate(executive_id="", manager_id="")

    updated = run(departments.update_department("dept-a", req, admin=admin()))

    assert updated["executive_id"] is None
    assert updated["manager_id"] is None


def test_same_executive_can_head_multiple_departments(fake_db):
    fake_db.departments.items.append(
        {
            "id": "dept-b",
            "name": "Department B",
            "code": "B",
            "description": "",
            "executive_id": "executive-a",
            "is_active": True,
        }
    )
    req = departments.DepartmentUpdate(executive_id="executive-a")

    updated = run(departments.update_department("dept-a", req, admin=admin()))

    assert updated["executive_id"] == "executive-a"

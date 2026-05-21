import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import users
from backend.utils.helpers import hash_password, verify_password


class FakeResult:
    def __init__(self, matched_count=0):
        self.matched_count = matched_count


class FakeCollection:
    def __init__(self, items=None):
        self.items = list(items or [])

    async def find_one(self, query, projection=None):
        for item in self.items:
            if all(item.get(key) == value for key, value in query.items()):
                return self._project(item, projection)
        return None

    async def update_one(self, query, update):
        for item in self.items:
            if all(item.get(key) == value for key, value in query.items()):
                item.update(update.get("$set", {}))
                return FakeResult(matched_count=1)
        return FakeResult(matched_count=0)

    def _project(self, item, projection):
        if not projection:
            return dict(item)
        if any(value == 0 for value in projection.values()):
            return {key: value for key, value in item.items() if projection.get(key) != 0}
        return {key: item[key] for key, include in projection.items() if include and key in item}


class FakeDb:
    def __init__(self):
        self.users = FakeCollection(
            [
                {
                    "id": "user-1",
                    "email": "old@example.com",
                    "password_hash": hash_password("old-password"),
                    "name": "Old Name",
                    "role": "requestor",
                    "department_id": "dept-a",
                },
                {
                    "id": "user-2",
                    "email": "taken@example.com",
                    "password_hash": hash_password("other-password"),
                    "name": "Taken User",
                    "role": "approver",
                    "department_id": "dept-a",
                },
            ]
        )


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(users, "db", db)
    return db


def admin():
    return {"id": "admin", "role": "super_admin"}


def test_admin_can_update_user_email_and_password(fake_db):
    req = users.UserUpdate(email="New.Email@Example.COM", password="new-password")

    updated = run(users.update_user("user-1", req, admin=admin()))

    stored = fake_db.users.items[0]
    assert updated["email"] == "new.email@example.com"
    assert "password_hash" not in updated
    assert verify_password("new-password", stored["password_hash"]) is True
    assert verify_password("old-password", stored["password_hash"]) is False


def test_admin_cannot_update_user_to_duplicate_email(fake_db):
    req = users.UserUpdate(email="Taken@Example.com")

    with pytest.raises(HTTPException) as exc:
        run(users.update_user("user-1", req, admin=admin()))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Email already registered"
    assert fake_db.users.items[0]["email"] == "old@example.com"

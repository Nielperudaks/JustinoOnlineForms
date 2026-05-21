import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import requests


class ChainCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, *_args):
        return self

    def skip(self, count):
        self.items = self.items[count:]
        return self

    def limit(self, count):
        self.items = self.items[:count]
        return self

    async def to_list(self, _limit):
        return list(self.items)


class RequestCollection:
    def __init__(self, items):
        self.items = list(items)

    def find(self, query=None, projection=None):
        results = [item for item in self.items if self._matches(item, query or {})]
        if projection and all(value == 0 for value in projection.values()):
            results = [
                {key: value for key, value in item.items() if projection.get(key) != 0}
                for item in results
            ]
        else:
            results = [dict(item) for item in results]
        return ChainCursor(results)

    async def find_one(self, query, projection=None):
        for item in self.items:
            if self._matches(item, query):
                return dict(item)
        return None

    async def count_documents(self, query):
        return len([item for item in self.items if self._matches(item, query)])

    def _matches(self, item, query):
        for key, expected in query.items():
            if key == "$and":
                if not all(self._matches(item, subquery) for subquery in expected):
                    return False
                continue
            if key == "$or":
                if not any(self._matches(item, subquery) for subquery in expected):
                    return False
                continue
            actual = self._get_nested(item, key)
            if isinstance(expected, dict):
                if "$elemMatch" in expected:
                    if not any(self._matches(element, expected["$elemMatch"]) for element in actual or []):
                        return False
                    continue
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                continue
            if actual != expected:
                return False
        return True

    def _get_nested(self, item, dotted_key):
        current = item
        for part in dotted_key.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current


class UserCollection:
    async def find_one(self, query, projection=None):
        return None


class FakeDb:
    def __init__(self):
        self.requests = RequestCollection(
            [
                {
                    "id": "req-dept",
                    "request_number": "REQ-00001",
                    "department_id": "dept-a",
                    "requester_id": "requestor-a",
                    "requester_name": "Ana",
                    "form_template_name": "Department Request",
                    "form_data": {"purpose": "Office supplies"},
                    "approvals": [],
                    "custodian": None,
                    "status": "in_progress",
                    "created_at": "2026-05-21T00:00:00+00:00",
                },
                {
                    "id": "req-other",
                    "request_number": "REQ-00002",
                    "department_id": "dept-b",
                    "requester_id": "requestor-b",
                    "requester_name": "Ben",
                    "form_template_name": "Other Request",
                    "form_data": {"purpose": "Laptop"},
                    "approvals": [],
                    "custodian": None,
                    "status": "in_progress",
                    "created_at": "2026-05-21T00:00:00+00:00",
                },
            ]
        )
        self.users = UserCollection()


def run(coro):
    return asyncio.run(coro)


def manager():
    return {"id": "manager-a", "role": "manager", "department_id": "dept-a"}


def test_manager_lists_department_requests_without_heavy_details(monkeypatch):
    monkeypatch.setattr(requests, "db", FakeDb())

    result = run(requests.list_requests(offset=0, page=1, limit=50, user=manager()))

    assert [item["id"] for item in result["items"]] == ["req-dept"]
    assert "form_data" not in result["items"][0]


def test_manager_can_open_department_request_details(monkeypatch):
    monkeypatch.setattr(requests, "db", FakeDb())

    result = run(requests.get_request("req-dept", user=manager()))

    assert result["form_data"] == {"purpose": "Office supplies"}

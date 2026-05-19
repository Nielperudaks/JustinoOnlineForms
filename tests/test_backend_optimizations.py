import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import dashboard, requests
from backend.utils.cache import TTLCache


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
        self.last_projection = None
        self.aggregate_calls = []
        self.count_calls = []

    def find(self, _query=None, projection=None):
        self.last_projection = projection
        projected = []
        for item in self.items:
            if projection and all(value == 0 for value in projection.values()):
                projected.append({key: value for key, value in item.items() if projection.get(key) != 0})
            else:
                projected.append(dict(item))
        return ChainCursor(projected)

    async def count_documents(self, query):
        self.count_calls.append(query)
        return len(self.items)

    def aggregate(self, pipeline):
        self.aggregate_calls.append(pipeline)
        return ChainCursor(
            [
                {
                    "_id": None,
                    "total_requests": 3,
                    "pending_requests": 1,
                    "approved_requests": 1,
                    "rejected_requests": 1,
                    "cancelled_requests": 0,
                }
            ]
        )


class CountCollection:
    def __init__(self, count=0):
        self.count = count

    async def count_documents(self, _query):
        return self.count


class FakeDb:
    def __init__(self):
        self.requests = RequestCollection(
            [
                {
                    "id": "req-1",
                    "request_number": "REQ-00001",
                    "form_template_name": "Laptop Request",
                    "title": "Laptop Request",
                    "requester_id": "user-1",
                    "requester_name": "Ana",
                    "requester_email": "ana@example.com",
                    "department_id": "dept-1",
                    "status": "in_progress",
                    "current_approval_step": 1,
                    "total_approval_steps": 2,
                    "created_at": "2026-05-19T00:00:00+00:00",
                    "updated_at": "2026-05-19T00:00:00+00:00",
                    "form_data": {"attachment": {"base64": "x" * 5000}},
                    "notes": "large internal note",
                    "approvals": [{"comments": "heavy history"}],
                    "custodian": {"comments": "heavy custodian history"},
                }
            ]
        )
        self.users = CountCollection(9)
        self.form_templates = CountCollection(4)
        self.notifications = CountCollection(2)


def run(coro):
    return asyncio.run(coro)


def test_request_list_omits_heavy_detail_fields(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(requests, "db", db)

    result = run(
        requests.list_requests(
            offset=0,
            page=1,
            limit=50,
            user={"id": "admin", "role": "super_admin"},
        )
    )

    assert result["items"][0]["id"] == "req-1"
    assert "form_data" not in result["items"][0]
    assert "notes" not in result["items"][0]
    assert "requester_email" not in result["items"][0]
    assert "approvals" not in result["items"][0]
    assert "custodian" not in result["items"][0]
    assert db.requests.last_projection == requests.REQUEST_LIST_PROJECTION


def test_dashboard_stats_uses_single_request_aggregation(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(dashboard, "db", db)

    result = run(dashboard.get_dashboard_stats(user={"id": "admin", "role": "super_admin"}))

    assert result["total_requests"] == 3
    assert result["pending_requests"] == 1
    assert len(db.requests.aggregate_calls) == 1
    assert len(db.requests.count_calls) == 1


def test_ttl_cache_reuses_value_until_expiry():
    clock = {"now": 100.0}
    cache = TTLCache(default_ttl_seconds=10, now=lambda: clock["now"])
    calls = {"count": 0}

    async def factory():
        calls["count"] += 1
        return {"value": calls["count"]}

    first = run(cache.get_or_set("stats", ("user-1",), factory))
    second = run(cache.get_or_set("stats", ("user-1",), factory))
    clock["now"] = 111.0
    third = run(cache.get_or_set("stats", ("user-1",), factory))

    assert first == {"value": 1}
    assert second == {"value": 1}
    assert third == {"value": 2}

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
        query = _query or {}
        projected = []
        for item in [item for item in self.items if self._matches(item, query)]:
            if projection and all(value == 0 for value in projection.values()):
                projected.append({key: value for key, value in item.items() if projection.get(key) != 0})
            else:
                projected.append(dict(item))
        return ChainCursor(projected)

    async def count_documents(self, query):
        self.count_calls.append(query)
        return len([item for item in self.items if self._matches(item, query)])

    def aggregate(self, pipeline):
        self.aggregate_calls.append(pipeline)
        return ChainCursor(
            [
                {
                    "_id": None,
                    "total_requests": 3,
                    "pending_requests": 1,
                    "approved_requests": 1,
                    "custodian_pending_requests": 1,
                    "custodian_fulfilled_requests": 1,
                    "rejected_requests": 1,
                    "cancelled_requests": 0,
                }
            ]
        )

    def _matches(self, item, query):
        for key, expected in query.items():
            if key == "$and":
                return all(self._matches(item, subquery) for subquery in expected)
            actual = self._get_nested(item, key)
            if isinstance(expected, dict):
                if "$gte" in expected and actual < expected["$gte"]:
                    return False
                if "$lte" in expected and actual > expected["$lte"]:
                    return False
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                if "$ne" in expected and actual == expected["$ne"]:
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
                    "form_template_id": "template-1",
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
                    "form_fields": [{"name": "reference_url", "type": "link"}],
                    "form_data": {"attachment": {"base64": "x" * 5000}},
                    "notes": "large internal note",
                    "approvals": [{"comments": "heavy history"}],
                    "custodian": {
                        "status": "pending",
                        "user_name": "Carlo",
                        "comments": "heavy custodian history",
                    },
                }
                ,
                {
                    "id": "req-2",
                    "request_number": "REQ-00002",
                    "form_template_id": "template-1",
                    "form_template_name": "Laptop Request",
                    "title": "Laptop Request",
                    "requester_id": "user-1",
                    "requester_name": "Ana",
                    "department_id": "dept-1",
                    "status": "approved",
                    "custodian": {"status": "fulfilled", "user_name": "Carlo"},
                    "current_approval_step": 1,
                    "total_approval_steps": 2,
                    "created_at": "2026-04-30T23:59:59.999999+00:00",
                    "updated_at": "2026-04-30T23:59:59.999999+00:00",
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
    assert "form_fields" not in result["items"][0]
    assert "notes" not in result["items"][0]
    assert "requester_email" not in result["items"][0]
    assert "approvals" not in result["items"][0]
    assert result["items"][0]["custodian"]["status"] == "pending"
    assert db.requests.last_projection == requests.REQUEST_LIST_PROJECTION


def test_request_list_filters_by_custodian_status(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(requests, "db", db)

    result = run(
        requests.list_requests(
            custodian_status="fulfilled",
            offset=0,
            page=1,
            limit=50,
            user={"id": "admin", "role": "super_admin"},
        )
    )

    query = db.requests.count_calls[0]
    assert query["custodian.status"] == "fulfilled"
    assert [item["id"] for item in result["items"]] == ["req-2"]


def test_approved_filter_excludes_fulfilled_custodian_requests(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(requests, "db", db)

    result = run(
        requests.list_requests(
            status="approved",
            offset=0,
            page=1,
            limit=50,
            user={"id": "admin", "role": "super_admin"},
        )
    )

    query = db.requests.count_calls[0]
    assert query["status"] == "approved"
    assert query["custodian.status"] == {"$ne": "fulfilled"}
    assert result["items"] == []


def test_request_list_filters_by_form_and_created_date(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(requests, "db", db)

    result = run(
        requests.list_requests(
            form_template_id="template-1",
            date_from="2026-05-01",
            date_to="2026-05-21",
            offset=0,
            page=1,
            limit=50,
            user={"id": "admin", "role": "super_admin"},
        )
    )

    query = db.requests.count_calls[0]
    assert query["form_template_id"] == "template-1"
    assert query["created_at"]["$gte"] == "2026-05-01T00:00:00+00:00"
    assert query["created_at"]["$lte"] == "2026-05-21T23:59:59.999999+00:00"
    assert [item["id"] for item in result["items"]] == ["req-1"]


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

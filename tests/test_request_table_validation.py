import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

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


class Collection:
    def __init__(self, items):
        self.items = list(items)

    def find(self, query=None, projection=None):
        query = query or {}
        items = [item for item in self.items if self._matches(item, query)]
        return ChainCursor([dict(item) for item in items])

    async def find_one(self, query, projection=None):
        for item in self.items:
            if self._matches(item, query):
                return dict(item)
        return None

    async def count_documents(self, query):
        return len([item for item in self.items if self._matches(item, query)])

    async def insert_one(self, item):
        self.items.append(item)

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
        self.form_templates = Collection(
            [
                {
                    "id": "template-table",
                    "department_id": "dept-a",
                    "name": "Table Form",
                    "description": "",
                    "fields": [
                        {
                            "name": "items",
                            "label": "Items",
                            "type": "table",
                            "required": True,
                            "table_title": "Line Items",
                            "columns": [
                                {"label": "Date", "type": "date", "unique": False},
                                {"label": "Description", "type": "text", "unique": True},
                                {"label": "Qty", "type": "number", "unique": False},
                            ],
                            "num_rows": 3,
                        }
                    ],
                    "approver_chain": [],
                    "custodian": None,
                    "is_active": True,
                }
            ]
        )
        self.departments = Collection([{"id": "dept-a", "executive_id": None, "manager_id": None, "department_groups": []}])
        self.requests = Collection([])
        self.users = Collection([])
        self.notifications = Collection([])


def run(coro):
    return asyncio.run(coro)


def requestor():
    return {"id": "requestor-a", "role": "requestor", "department_id": "dept-a", "name": "Requestor A"}


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDb()
    monkeypatch.setattr(requests, "db", db)
    return db


def test_create_request_rejects_duplicate_rows_in_selected_table_columns(fake_db):
    req = requests.RequestCreate(
        form_template_id="template-table",
        form_data={
            "items": {
                "rows": [
                    ["2026-06-20", "Duplicate", "1"],
                    ["2026-06-21", "Duplicate", "2"],
                ]
            }
        },
    )

    with pytest.raises(HTTPException) as exc:
        run(requests.create_request(req, user=requestor()))

    assert exc.value.status_code == 400
    assert "duplicate" in exc.value.detail.lower()


def test_create_request_allows_same_non_unique_values_when_selected_columns_differ(fake_db):
    req = requests.RequestCreate(
        form_template_id="template-table",
        form_data={
            "items": {
                "rows": [
                    ["2026-06-20", "Alpha", "1"],
                    ["2026-06-20", "Beta", "1"],
                ]
            }
        },
    )

    created = run(requests.create_request(req, user=requestor()))

    assert created["form_data"]["items"]["rows"][1][1] == "Beta"

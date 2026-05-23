import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.routes import requests


class FakeRequestCollection:
    def __init__(self, request):
        self.request = dict(request)

    async def find_one(self, query, projection=None):
        if query.get("id") != self.request.get("id"):
            return None
        return dict(self.request)

    async def update_one(self, query, update):
        if query.get("id") != self.request.get("id"):
            return
        for key, value in update.get("$set", {}).items():
            self.request[key] = value


class FakeUserCursor:
    def __init__(self, users):
        self.users = users

    async def to_list(self, _limit):
        return list(self.users)


class FakeUserCollection:
    def __init__(self, users):
        self.users = list(users)

    def find(self, query, projection=None):
        ids = set(query.get("id", {}).get("$in", []))
        return FakeUserCursor([user for user in self.users if user.get("id") in ids])


class FakeNotificationCollection:
    def __init__(self):
        self.items = []

    async def insert_one(self, item):
        self.items.append(dict(item))


class FakeDb:
    def __init__(self, request, users):
        self.requests = FakeRequestCollection(request)
        self.users = FakeUserCollection(users)
        self.notifications = FakeNotificationCollection()


class FakeManager:
    def __init__(self):
        self.events = []

    async def broadcast(self, event, payload):
        self.events.append((event, payload))


def run(coro):
    return asyncio.run(coro)


def requester():
    return {"id": "requester-1", "name": "Ana", "role": "requestor"}


def make_request(status="in_progress", approvals=None):
    return {
        "id": "req-1",
        "request_number": "REQ-00001",
        "department_id": "dept-1",
        "requester_id": "requester-1",
        "requester_name": "Ana",
        "requester_email": "ana@example.com",
        "form_template_name": "Purchase Request",
        "title": "Purchase Request",
        "status": status,
        "current_approval_step": 2,
        "approvals": approvals
        if approvals is not None
        else [
            {
                "step": 1,
                "approver_id": "approver-1",
                "approver_name": "Ben",
                "status": "approved",
            },
            {
                "step": 2,
                "approver_id": "approver-2",
                "approver_name": "Cora",
                "status": "pending",
            },
        ],
    }


def test_cancel_requires_a_reason(monkeypatch):
    monkeypatch.setattr(requests, "db", FakeDb(make_request(), []))

    with pytest.raises(HTTPException) as exc:
        run(requests.cancel_request("req-1", requests.RequestCancel(comments="   "), user=requester()))

    assert exc.value.status_code == 400
    assert exc.value.detail == "Cancellation reason is required"


def test_cancel_allowed_until_all_approvers_have_approved_and_notifies_approvers(monkeypatch):
    fake_db = FakeDb(
        make_request(status="pending"),
        [
            {"id": "approver-1", "name": "Ben", "email": "ben@example.com"},
            {"id": "approver-2", "name": "Cora", "email": "cora@example.com"},
        ],
    )
    fake_manager = FakeManager()
    sent_emails = []

    async def fake_email(to_email, subject, html):
        sent_emails.append((to_email, subject, html))

    monkeypatch.setattr(requests, "db", fake_db)
    monkeypatch.setattr(requests, "manager", fake_manager)
    monkeypatch.setattr(requests, "send_email_notification", fake_email)
    monkeypatch.setattr(requests, "invalidate_stats_cache", lambda: None)

    result = run(
        requests.cancel_request(
            "req-1",
            requests.RequestCancel(comments="Budget was withdrawn"),
            user=requester(),
        )
    )

    assert result["status"] == "cancelled"
    assert result["cancellation_reason"] == "Budget was withdrawn"
    assert result["cancelled_by"] == "requester-1"
    assert {email[0] for email in sent_emails} == {"ben@example.com", "cora@example.com"}
    assert all("Request Cancelled: REQ-00001" == email[1] for email in sent_emails)
    assert all("Budget was withdrawn" in email[2] for email in sent_emails)
    assert len(fake_db.notifications.items) == 2
    assert {item["type"] for item in fake_db.notifications.items} == {"request_cancelled"}
    assert any(event[0] == "REQUEST_CANCELLED" for event in fake_manager.events)


def test_cancel_rejected_after_all_approvers_have_approved(monkeypatch):
    fake_db = FakeDb(
        make_request(
            status="pending",
            approvals=[
                {
                    "step": 1,
                    "approver_id": "approver-1",
                    "approver_name": "Ben",
                    "status": "approved",
                },
                {
                    "step": 2,
                    "approver_id": "approver-2",
                    "approver_name": "Cora",
                    "status": "approved",
                },
            ],
        ),
        [],
    )
    monkeypatch.setattr(requests, "db", fake_db)

    with pytest.raises(HTTPException) as exc:
        run(
            requests.cancel_request(
                "req-1",
                requests.RequestCancel(comments="No longer needed"),
                user=requester(),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "Request can no longer be cancelled because all approvers have approved it"

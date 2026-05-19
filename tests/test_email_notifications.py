import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.utils.helpers import build_request_url, render_request_email


def test_build_request_url_points_to_dashboard_request_query(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://forms.example.com/")

    assert build_request_url("request-123") == "https://forms.example.com/?request=request-123"


def test_render_request_email_includes_link_details_and_escaped_comments(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://forms.example.com")

    html = render_request_email(
        heading="Approval Required",
        request_id="request-123",
        request_number="REQ-00042",
        request_title="Purchase <Laptop>",
        intro="A request needs your review.",
        requester_name="Ana Reyes",
        actor_name="Ben Cruz",
        status_label="Step 2 of 8",
        comments="<please approve>",
        action_label="Review request",
    )

    assert "https://forms.example.com/?request=request-123" in html
    assert "REQ-00042" in html
    assert "Purchase &lt;Laptop&gt;" in html
    assert "Ana Reyes" in html
    assert "Ben Cruz" in html
    assert "Step 2 of 8" in html
    assert "&lt;please approve&gt;" in html
    assert "Review request" in html

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.utils.realtime_events import metadata_changed_payload


def test_metadata_changed_payload_only_contains_invalidation_fields():
    payload = metadata_changed_payload(
        resource="templates",
        action="updated",
        item_id="template-1",
        department_id="dept-a",
    )

    assert payload == {
        "resource": "templates",
        "action": "updated",
        "id": "template-1",
        "department_id": "dept-a",
    }


def test_metadata_changed_payload_omits_empty_optional_fields():
    payload = metadata_changed_payload(resource="departments", action="deleted")

    assert payload == {
        "resource": "departments",
        "action": "deleted",
    }

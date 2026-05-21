import sys
from pathlib import Path

from pymongo.errors import OperationFailure

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend import server


def test_startup_tasks_default_off_on_railway(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("SEED_ON_STARTUP", raising=False)

    assert server.should_run_startup_task("SEED_ON_STARTUP") is False


def test_startup_tasks_can_be_enabled_on_railway(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("SEED_ON_STARTUP", "true")

    assert server.should_run_startup_task("SEED_ON_STARTUP") is True


def test_low_disk_operation_failure_is_detected():
    exc = OperationFailure(
        "available disk space is less than required minimum",
        details={"code": 14031, "codeName": "OutOfDiskSpace"},
    )

    assert server.is_low_disk_operation_failure(exc) is True

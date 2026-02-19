"""Tests for precheck layer."""
import pytest

from schedule_app.models import Config, Constraints, Lecturer, Project, Student, TimeSlot
from schedule_app.solver.precheck import PrecheckError, ensure_ok, precheck


def _cfg_ok() -> Config:
    cfg = Config()
    cfg.timeslots = [
        TimeSlot(id="TS1", date="2026-01-01", start="09:00", end="09:30"),
        TimeSlot(id="TS2", date="2026-01-01", start="09:30", end="10:00"),
    ]
    cfg.lecturers = [
        Lecturer(id="L1", name="Dr One", available_slot_ids=["TS1","TS2"]),
        Lecturer(id="L2", name="Dr Two", available_slot_ids=["TS1","TS2"]),
    ]
    cfg.students  = [Student(id="S1", name="Student A")]
    cfg.projects  = [Project(id="P1", title="Proj", student_ids=["S1"], supervisor_lecturer_id="L1")]
    cfg.constraints.rooms      = 1
    cfg.constraints.panel_size = 2
    return cfg


def test_ok_config_passes() -> None:
    errors, warnings = precheck(_cfg_ok())
    assert errors == []


def test_capacity_error() -> None:
    cfg = _cfg_ok()
    cfg.constraints.rooms = 1          # 1 room × 2 slots = 2 capacity
    cfg.projects.append(Project(id="P2", title="P2"))
    cfg.projects.append(Project(id="P3", title="P3"))
    # Now 3 projects but only 2 slots × 1 room
    errors, _ = precheck(cfg)
    assert any("capacity" in e.lower() or "not enough" in e.lower() for e in errors)


def test_panel_too_large() -> None:
    cfg = _cfg_ok()
    cfg.constraints.panel_size = 99
    errors, _ = precheck(cfg)
    assert any("panel_size" in e for e in errors)


def test_missing_supervisor_available_slots() -> None:
    cfg = _cfg_ok()
    cfg.lecturers[0].available_slot_ids = []
    _, warnings = precheck(cfg)
    assert any("L1" in w for w in warnings)


def test_unknown_slot_id_in_lunch() -> None:
    cfg = _cfg_ok()
    cfg.constraints.lunch_slot_ids = ["DOES_NOT_EXIST"]
    errors, _ = precheck(cfg)
    assert any("DOES_NOT_EXIST" in e for e in errors)


def test_ensure_ok_raises_on_errors() -> None:
    cfg = _cfg_ok()
    cfg.constraints.panel_size = 99
    with pytest.raises(PrecheckError):
        ensure_ok(cfg)

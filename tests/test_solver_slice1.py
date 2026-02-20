"""Tests for solver slice 1 — basic assignment without panel constraints."""

from schedule_app.models import Config, Lecturer, Project, Student, TimeSlot
from schedule_app.solver.slice1 import solve_slice1


def _feasible_cfg() -> Config:
    cfg = Config()
    cfg.timeslots = [
        TimeSlot(id="TS1", date="2026-01-01", start="09:00", end="09:30"),
        TimeSlot(id="TS2", date="2026-01-01", start="09:30", end="10:00"),
    ]
    cfg.lecturers = [
        Lecturer(id="L1", name="Alice", available_slot_ids=["TS1","TS2"]),
        Lecturer(id="L2", name="Bob",   available_slot_ids=["TS1","TS2"]),
    ]
    cfg.students  = [Student(id="S1", name="Emma")]
    cfg.projects  = [
        Project(id="P1", title="Proj A", student_ids=["S1"], supervisor_lecturer_id="L1"),
        Project(id="P2", title="Proj B", student_ids=[],      supervisor_lecturer_id="L2"),
    ]
    cfg.constraints.rooms      = 1
    cfg.constraints.panel_size = 2
    return cfg


def test_feasible_returns_optimal_or_feasible() -> None:
    result = solve_slice1(_feasible_cfg())
    assert result.status in ("OPTIMAL", "FEASIBLE")


def test_all_projects_scheduled() -> None:
    cfg    = _feasible_cfg()
    result = solve_slice1(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    scheduled = {e.project_id for e in result.entries}
    expected  = {p.id for p in cfg.projects}
    assert scheduled == expected


def test_no_room_conflicts() -> None:
    cfg    = _feasible_cfg()
    result = solve_slice1(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    slot_room_pairs = [(e.timeslot_id, e.room) for e in result.entries]
    assert len(slot_room_pairs) == len(set(slot_room_pairs)), "Room conflict detected"


def test_student_unavailability_respected() -> None:
    cfg = _feasible_cfg()
    cfg.students[0].unavailable_slot_ids = ["TS1"]
    result = solve_slice1(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    p1_entry = next(e for e in result.entries if e.project_id == "P1")
    assert p1_entry.timeslot_id != "TS1"

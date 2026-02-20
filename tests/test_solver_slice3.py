# tests for slice3 - full model with weighted objectives
# slice3 adds workload balance and lunch avoidance on top of slice2
# so most tests are similar but also check the soft objectives

from schedule_app.models import Config, Constraints, Lecturer, Project, Student, TimeSlot, Weights
from schedule_app.solver.slice3 import solve_slice3


def _base_cfg():
    cfg = Config()
    cfg.timeslots = [
        TimeSlot(id="TS1", date="2026-01-01", start="09:00", end="09:30"),
        TimeSlot(id="TS2", date="2026-01-01", start="12:00", end="12:30"),  # lunch slot
        TimeSlot(id="TS3", date="2026-01-01", start="14:00", end="14:30"),
    ]
    cfg.lecturers = [
        Lecturer(id="L1", name="Alice", available_slot_ids=["TS1", "TS2", "TS3"]),
        Lecturer(id="L2", name="Bob",   available_slot_ids=["TS1", "TS2", "TS3"]),
        Lecturer(id="L3", name="Carol", available_slot_ids=["TS1", "TS2", "TS3"]),
    ]
    cfg.students = [Student(id="S1", name="Emma")]
    cfg.projects = [
        Project(id="P1", title="Project Alpha", student_ids=["S1"], supervisor_lecturer_id="L1"),
        Project(id="P2", title="Project Beta",  student_ids=[],     supervisor_lecturer_id="L2"),
    ]
    cfg.constraints.rooms = 1
    cfg.constraints.panel_size = 2
    cfg.constraints.must_include_supervisor = True
    return cfg


def test_slice3_basic_feasible():
    result = solve_slice3(_base_cfg())
    assert result.status in ("OPTIMAL", "FEASIBLE")


def test_slice3_all_projects_scheduled():
    cfg = _base_cfg()
    result = solve_slice3(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert {e.project_id for e in result.entries} == {"P1", "P2"}


def test_slice3_supervisor_in_panel():
    cfg = _base_cfg()
    result = solve_slice3(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    for entry in result.entries:
        proj = cfg.get_project(entry.project_id)
        if proj and proj.supervisor_lecturer_id:
            assert proj.supervisor_lecturer_id in entry.panel_lecturer_ids


def test_slice3_lunch_avoidance():
    # with high lunch weight, the solver should prefer TS1 and TS3 over TS2
    cfg = _base_cfg()
    cfg.constraints.lunch_slot_ids = ["TS2"]
    cfg.constraints.weights.lunch = 50   # high penalty for lunch slots
    cfg.constraints.weights.span = 0     # don't care about compactness for this test
    result = solve_slice3(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    lunch_slots_used = [e for e in result.entries if e.timeslot_id == "TS2"]
    # with only 2 projects and 3 slots, the solver should be able to avoid TS2 entirely
    assert len(lunch_slots_used) == 0, "Solver should avoid lunch slot TS2 when weight is high"


def test_slice3_lunch_weight_zero_doesnt_crash():
    # setting all weights to 0 should still work (just returns any feasible solution)
    cfg = _base_cfg()
    cfg.constraints.weights.span = 0
    cfg.constraints.weights.workload_balance = 0
    cfg.constraints.weights.lunch = 0
    result = solve_slice3(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")


def test_slice3_stats_present():
    # slice3 should return stats dict with timing info
    cfg = _base_cfg()
    result = solve_slice3(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    assert result.stats is not None
    assert "wall_time_s" in result.stats


def test_slice3_infeasible_no_availability():
    # same issue as slice2 - need to disable supervisor check first
    # otherwise precheck raises PrecheckError before the solver gets called
    cfg = _base_cfg()
    cfg.constraints.must_include_supervisor = False
    for lec in cfg.lecturers:
        lec.available_slot_ids = []
    result = solve_slice3(cfg)
    assert result.status == "INFEASIBLE"

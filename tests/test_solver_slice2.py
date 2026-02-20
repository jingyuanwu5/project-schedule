# tests for slice2 - panel assignment and lecturer availability
# based on the same pattern as test_solver_slice1.py

from schedule_app.models import Config, Constraints, Lecturer, Project, Student, TimeSlot
from schedule_app.solver.slice2 import solve_slice2


def _base_cfg():
    # 2 projects, 3 lecturers, 2 timeslots, panel size 2
    # this is the simplest config that actually exercises the panel constraints
    cfg = Config()
    cfg.timeslots = [
        TimeSlot(id="TS1", date="2026-01-01", start="09:00", end="09:30"),
        TimeSlot(id="TS2", date="2026-01-01", start="09:30", end="10:00"),
    ]
    cfg.lecturers = [
        Lecturer(id="L1", name="Alice", available_slot_ids=["TS1", "TS2"]),
        Lecturer(id="L2", name="Bob",   available_slot_ids=["TS1", "TS2"]),
        Lecturer(id="L3", name="Carol", available_slot_ids=["TS1", "TS2"]),
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


def test_slice2_basic_feasible():
    result = solve_slice2(_base_cfg())
    assert result.status in ("OPTIMAL", "FEASIBLE")


def test_slice2_all_projects_scheduled():
    cfg = _base_cfg()
    result = solve_slice2(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    scheduled_ids = {e.project_id for e in result.entries}
    assert scheduled_ids == {"P1", "P2"}


def test_slice2_panel_size_correct():
    cfg = _base_cfg()
    result = solve_slice2(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    for entry in result.entries:
        assert len(entry.panel_lecturer_ids) == cfg.constraints.panel_size


def test_slice2_supervisor_in_panel():
    # supervisor must be on the panel when must_include_supervisor = True
    cfg = _base_cfg()
    result = solve_slice2(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    for entry in result.entries:
        proj = cfg.get_project(entry.project_id)
        if proj and proj.supervisor_lecturer_id:
            assert proj.supervisor_lecturer_id in entry.panel_lecturer_ids, \
                f"Supervisor {proj.supervisor_lecturer_id} missing from panel for {proj.id}"


def test_slice2_lecturer_availability_respected():
    # L3 is only available at TS2, so any project assigned to TS1 should not have L3 on the panel
    cfg = _base_cfg()
    cfg.lecturers[2].available_slot_ids = ["TS2"]  # L3 only free at TS2
    result = solve_slice2(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    for entry in result.entries:
        if entry.timeslot_id == "TS1":
            assert "L3" not in entry.panel_lecturer_ids, \
                "L3 should not appear in TS1 (unavailable)"


def test_slice2_infeasible_when_no_availability():
    # clearing all availability causes INFEASIBLE
    # need to turn off must_include_supervisor first, otherwise precheck
    # catches it before the solver even runs (supervisor has no available slots)
    # found this out when the test was failing with PrecheckError
    cfg = _base_cfg()
    cfg.constraints.must_include_supervisor = False
    for lec in cfg.lecturers:
        lec.available_slot_ids = []
    result = solve_slice2(cfg)
    assert result.status == "INFEASIBLE"


def test_slice2_max_per_day():
    # L1 is supervisor of P1 and must be on that panel
    # if max_per_day = 1, L1 cannot also appear on P2's panel on the same day
    cfg = _base_cfg()
    cfg.lecturers[0].max_per_day = 1  # L1 max 1 per day
    cfg.constraints.must_include_supervisor = False  # relax this so it's not infeasible
    result = solve_slice2(cfg)
    assert result.status in ("OPTIMAL", "FEASIBLE")
    # count how many times L1 appears across all panels
    l1_count = sum(1 for e in result.entries if "L1" in e.panel_lecturer_ids)
    assert l1_count <= 1, f"L1 appears {l1_count} times but max_per_day is 1"

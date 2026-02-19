import json
from pathlib import Path
from schedule_app.io_json import load_config
from schedule_app.solver.slice1 import solve_slice1


def test_slice1_feasible(tmp_path: Path):
    d = {
        "meta": {},
        "timeslots": [
            {"id": "S1", "date": "2026-03-10", "start": "09:00", "end": "09:30"},
            {"id": "S2", "date": "2026-03-10", "start": "09:30", "end": "10:00"},
        ],
        "lecturers": [{"id": "L1", "name": "A", "available_slot_ids": ["S1", "S2"]}],
        "students":  [{"id": "ST1", "name": "B", "unavailable_slot_ids": []}],
        "projects":  [
            {"id": "P1", "title": "P1", "student_ids": ["ST1"], "supervisor_lecturer_id": "L1"},
            {"id": "P2", "title": "P2", "student_ids": ["ST1"], "supervisor_lecturer_id": "L1"},
        ],
        "constraints": {
            "rooms": 1, "panel_size": 1, "must_include_supervisor": True,
            "solver": {"max_time_in_seconds": 3},
        },
    }
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    cfg = load_config(p)
    res = solve_slice1(cfg)
    assert res.status in ("OPTIMAL", "FEASIBLE")
    assert len(res.entries) == 2
    assert {e.project_id for e in res.entries} == {"P1", "P2"}
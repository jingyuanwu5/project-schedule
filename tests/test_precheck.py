import json, pytest
from pathlib import Path
from schedule_app.io_json import load_config
from schedule_app.solver.precheck import ensure_ok, PrecheckError


def test_capacity_error(tmp_path):
    d = {
        "meta": {},
        "timeslots": [{"id": "S1", "date": "2026-03-10", "start": "09:00", "end": "09:30"}],
        "lecturers": [{"id": "L1", "name": "A", "available_slot_ids": ["S1"]}],
        "students":  [{"id": "ST1", "name": "B", "unavailable_slot_ids": []}],
        "projects":  [
            {"id": "P1", "title": "P1", "student_ids": ["ST1"], "supervisor_lecturer_id": "L1"},
            {"id": "P2", "title": "P2", "student_ids": ["ST1"], "supervisor_lecturer_id": "L1"},
        ],
        "constraints": {"rooms": 1, "panel_size": 1, "must_include_supervisor": True},
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(d), encoding="utf-8")
    cfg = load_config(p)
    with pytest.raises(PrecheckError, match="Not enough capacity"):
        ensure_ok(cfg)
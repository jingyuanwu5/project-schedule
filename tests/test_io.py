import json
from pathlib import Path
from schedule_app.io_json import load_config, save_config
from schedule_app.models import Config


def _base_dict():
    return {
        "meta": {},
        "timeslots": [
            {"id": "S1", "date": "2026-03-10", "start": "09:00", "end": "09:30"},
            {"id": "S2", "date": "2026-03-10", "start": "09:30", "end": "10:00"},
        ],
        "lecturers": [{"id": "L1", "name": "Alice", "available_slot_ids": ["S1"]}],
        "students":  [{"id": "ST1", "name": "Bob",  "unavailable_slot_ids": []}],
        "projects":  [{"id": "P1", "title": "Proj", "student_ids": ["ST1"],
                       "supervisor_lecturer_id": "L1"}],
        "constraints": {"rooms": 1, "panel_size": 1, "must_include_supervisor": True},
    }


def test_roundtrip(tmp_path: Path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(_base_dict()), encoding="utf-8")
    cfg = load_config(p)
    assert isinstance(cfg, Config)
    assert cfg.projects[0].supervisor_lecturer_id == "L1"
    out = tmp_path / "out.json"
    save_config(cfg, out)
    cfg2 = load_config(out)
    assert cfg2.lecturers[0].name == "Alice"
"""Tests for JSON load/save roundtrip and structural validation."""
import json
from pathlib import Path

import pytest

from schedule_app.io_json import ConfigError, load_config, save_config
from schedule_app.models import Config, Lecturer, Project, Student, TimeSlot


def _make_minimal_config() -> Config:
    cfg = Config()
    cfg.timeslots = [TimeSlot(id="TS1", date="2026-01-01", start="09:00", end="09:30")]
    cfg.lecturers = [
        Lecturer(id="L1", name="Dr One", available_slot_ids=["TS1"]),
        Lecturer(id="L2", name="Dr Two", available_slot_ids=["TS1"]),
    ]
    cfg.students  = [Student(id="S1", name="Student A")]
    cfg.projects  = [Project(id="P1", title="Proj", student_ids=["S1"], supervisor_lecturer_id="L1")]
    cfg.constraints.rooms      = 1
    cfg.constraints.panel_size = 2
    return cfg


def test_roundtrip(tmp_path: Path) -> None:
    cfg  = _make_minimal_config()
    path = tmp_path / "test.json"
    save_config(cfg, path)
    cfg2 = load_config(path)
    assert cfg2.timeslots[0].id == "TS1"
    assert cfg2.lecturers[0].name == "Dr One"
    assert cfg2.projects[0].title == "Proj"
    assert cfg2.constraints.rooms == 1


def test_missing_key_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"timeslots": [], "lecturers": [], "students": []}))
    with pytest.raises(ConfigError):
        load_config(path)


def test_null_meta_allowed(tmp_path: Path) -> None:
    """meta: null should not crash — guarded by `raw.get("meta") or {}`."""
    cfg  = _make_minimal_config()
    path = tmp_path / "null_meta.json"
    save_config(cfg, path)
    raw = json.loads(path.read_text())
    raw["meta"] = None
    path.write_text(json.dumps(raw))
    cfg2 = load_config(path)
    assert isinstance(cfg2.meta, dict)


def test_num_search_workers_compat(tmp_path: Path) -> None:
    """Old JSON with num_search_workers should still load."""
    cfg  = _make_minimal_config()
    path = tmp_path / "old.json"
    save_config(cfg, path)
    raw = json.loads(path.read_text())
    raw["constraints"]["solver"] = {"max_time_in_seconds": 5.0, "num_search_workers": 4}
    path.write_text(json.dumps(raw))
    cfg2 = load_config(path)
    assert cfg2.constraints.solver.num_workers == 4


def test_duplicate_ids_raise(tmp_path: Path) -> None:
    cfg = _make_minimal_config()
    cfg.lecturers.append(Lecturer(id="L1", name="Duplicate"))
    path = tmp_path / "dup.json"
    save_config(cfg, path)
    with pytest.raises(ConfigError, match="Duplicate"):
        load_config(path)

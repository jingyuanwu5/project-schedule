"""
JSON serialisation / deserialisation for Config objects.

Uses only the Python standard-library json module.  The docs warn that
parsing large or deeply nested JSON from untrusted sources can be expensive,
so basic structural validation is applied before domain objects are built.

Reference: Python docs — json
https://docs.python.org/3/library/json.html
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from schedule_app.models import (Config, Constraints, Lecturer, Project,
    SolverParams, Student, TimeSlot, Weights)


class ConfigError(ValueError):
    """Raised when the config JSON is structurally invalid."""


def _require(obj: Dict[str, Any], key: str, ctx: str) -> Any:
    if key not in obj:
        raise ConfigError(f"Missing required key '{key}' in {ctx}")
    return obj[key]


def _as_list(obj: Any, ctx: str) -> List[Any]:
    if not isinstance(obj, list):
        raise ConfigError(f"Expected a JSON array in {ctx}, got {type(obj).__name__}")
    return obj


def _as_dict(obj: Any, ctx: str) -> Dict[str, Any]:
    if not isinstance(obj, dict):
        raise ConfigError(
            f"Expected a JSON object in {ctx}, got {type(obj).__name__}"
        )
    return obj


def _check_unique_ids(items: list, ctx: str) -> None:
    seen: set = set()
    dupes: set = set()
    for item in items:
        item_id = getattr(item, "id", None)
        if not item_id:
            raise ConfigError(f"Empty or missing 'id' in {ctx}")
        if item_id in seen:
            dupes.add(item_id)
        seen.add(item_id)
    if dupes:
        raise ConfigError(f"Duplicate ids in {ctx}: {sorted(dupes)}")


def load_config(path: str | Path) -> Config:
    """Load and validate a Config from a JSON file."""
    with Path(path).open("r", encoding="utf-8") as f:
        raw = json.load(f)

    raw  = _as_dict(raw, "root")
    meta = _as_dict(raw.get("meta", {}), "meta")

    timeslots_raw   = _as_list(_require(raw, "timeslots", "root"), "timeslots")
    lecturers_raw   = _as_list(_require(raw, "lecturers",  "root"), "lecturers")
    students_raw    = _as_list(_require(raw, "students",   "root"), "students")
    projects_raw    = _as_list(_require(raw, "projects",   "root"), "projects")
    constraints_raw = _as_dict(raw.get("constraints", {}), "constraints")

    timeslots = [
        TimeSlot(
            id    = str(_require(ts, "id",    f"timeslots[{i}]")),
            date  = str(_require(ts, "date",  f"timeslots[{i}]")),
            start = str(_require(ts, "start", f"timeslots[{i}]")),
            end   = str(_require(ts, "end",   f"timeslots[{i}]")),
            label = str(ts.get("label", "")),
        )
        for i, ts in enumerate(timeslots_raw)
    ]

    lecturers = [
        Lecturer(
            id                 = str(_require(l, "id",   f"lecturers[{i}]")),
            name               = str(_require(l, "name", f"lecturers[{i}]")),
            available_slot_ids = [str(x) for x in l.get("available_slot_ids", [])],
            max_per_day        = l.get("max_per_day"),
            max_total          = l.get("max_total"),
        )
        for i, l in enumerate(lecturers_raw)
    ]

    students = [
        Student(
            id                   = str(_require(s, "id",   f"students[{i}]")),
            name                 = str(_require(s, "name", f"students[{i}]")),
            unavailable_slot_ids = [str(x) for x in s.get("unavailable_slot_ids", [])],
        )
        for i, s in enumerate(students_raw)
    ]

    projects = [
        Project(
            id                     = str(_require(p, "id",    f"projects[{i}]")),
            title                  = str(_require(p, "title", f"projects[{i}]")),
            student_ids            = [str(x) for x in p.get("student_ids", [])],
            supervisor_lecturer_id = str(p.get("supervisor_lecturer_id", "")),
        )
        for i, p in enumerate(projects_raw)
    ]

    weights_raw = _as_dict(constraints_raw.get("weights", {}), "constraints.weights")
    solver_raw  = _as_dict(constraints_raw.get("solver",  {}), "constraints.solver")

    constraints = Constraints(
        rooms                   = int(constraints_raw.get("rooms", 1)),
        panel_size              = int(constraints_raw.get("panel_size", 2)),
        must_include_supervisor = bool(constraints_raw.get("must_include_supervisor", True)),
        lunch_slot_ids          = [str(x) for x in constraints_raw.get("lunch_slot_ids", [])],
        weights = Weights(
            span             = int(weights_raw.get("span", 1)),
            workload_balance = int(weights_raw.get("workload_balance", 10)),
            lunch            = int(weights_raw.get("lunch", 3)),
        ),
        solver = SolverParams(
            max_time_in_seconds = float(solver_raw.get("max_time_in_seconds", 10.0)),
            num_search_workers  = int(solver_raw.get("num_search_workers", 8)),
        ),
    )

    cfg = Config(
        meta        = meta,
        timeslots   = timeslots,
        lecturers   = lecturers,
        students    = students,
        projects    = projects,
        constraints = constraints,
    )
    cfg.validate()
    _check_unique_ids(cfg.timeslots, "timeslots")
    _check_unique_ids(cfg.lecturers, "lecturers")
    _check_unique_ids(cfg.students,  "students")
    _check_unique_ids(cfg.projects,  "projects")
    return cfg


def save_config(cfg: Config, path: str | Path) -> None:
    """Serialise Config to JSON, creating parent directories if needed."""
    cfg.validate()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        # ensure_ascii=False preserves accented names.
        # sort_keys=True keeps diffs readable in version control.
        json.dump(cfg.to_dict(), f, ensure_ascii=False, indent=2, sort_keys=True)
# io_json.py - load and save Config objects from/to JSON files
# using the built-in json module, no external dependencies needed
# reference: https://docs.python.org/3/library/json.html

import json
from pathlib import Path

from schedule_app.models import (
    Config, Constraints, Lecturer, Project,
    SolverParams, Student, TimeSlot, Weights,
)


class ConfigError(ValueError):
    pass


# helper functions to validate the JSON structure
def _require(obj, key, ctx):
    if key not in obj:
        raise ConfigError(f"Missing '{key}' in {ctx}")
    return obj[key]


def _as_list(obj, ctx):
    if not isinstance(obj, list):
        raise ConfigError(f"Expected a list in {ctx}, got {type(obj).__name__}")
    return obj


def _as_dict(obj, ctx):
    if not isinstance(obj, dict):
        raise ConfigError(f"Expected an object in {ctx}, got {type(obj).__name__}")
    return obj


def _check_unique_ids(items, ctx):
    seen = set()
    dupes = set()
    for item in items:
        item_id = getattr(item, "id", None)
        if not item_id:
            raise ConfigError(f"Empty or missing 'id' in {ctx}")
        if item_id in seen:
            dupes.add(item_id)
        seen.add(item_id)
    if dupes:
        raise ConfigError(f"Duplicate ids in {ctx}: {sorted(dupes)}")


def load_config(path) -> Config:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = json.load(f)

    raw = _as_dict(raw, "root")
    meta = _as_dict(raw.get("meta") or {}, "meta")

    timeslots_raw   = _as_list(_require(raw, "timeslots", "root"), "timeslots")
    lecturers_raw   = _as_list(_require(raw, "lecturers",  "root"), "lecturers")
    students_raw    = _as_list(_require(raw, "students",   "root"), "students")
    projects_raw    = _as_list(_require(raw, "projects",   "root"), "projects")
    constraints_raw = _as_dict(raw.get("constraints") or {}, "constraints")

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
            id                 = str(_require(lec, "id",   f"lecturers[{i}]")),
            name               = str(_require(lec, "name", f"lecturers[{i}]")),
            available_slot_ids = [str(x) for x in lec.get("available_slot_ids", [])],
            max_per_day        = lec.get("max_per_day"),
            max_total          = lec.get("max_total"),
        )
        for i, lec in enumerate(lecturers_raw)
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

    # parse constraints - all optional with defaults
    cr = constraints_raw
    wr = _as_dict(cr.get("weights") or {}, "constraints.weights")
    sr = _as_dict(cr.get("solver") or {}, "constraints.solver")

    # support old JSON that uses num_search_workers instead of num_workers
    num_workers = sr.get("num_workers", sr.get("num_search_workers", 0))

    constraints = Constraints(
        rooms=int(cr.get("rooms", 1)),
        panel_size=int(cr.get("panel_size", 2)),
        must_include_supervisor=bool(cr.get("must_include_supervisor", True)),
        lunch_slot_ids=[str(x) for x in cr.get("lunch_slot_ids", [])],
        weights=Weights(
            span=int(wr.get("span", 1)),
            workload_balance=int(wr.get("workload_balance", 10)),
            lunch=int(wr.get("lunch", 3)),
        ),
        solver=SolverParams(
            max_time_in_seconds=float(sr.get("max_time_in_seconds", 10.0)),
            num_workers=int(num_workers),
        ),
    )

    cfg = Config(
        meta=meta,
        timeslots=timeslots,
        lecturers=lecturers,
        students=students,
        projects=projects,
        constraints=constraints,
    )

    # check for duplicate IDs - these would cause weird solver bugs
    _check_unique_ids(cfg.timeslots,  "timeslots")
    _check_unique_ids(cfg.lecturers,  "lecturers")
    _check_unique_ids(cfg.students,   "students")
    _check_unique_ids(cfg.projects,   "projects")

    return cfg


def save_config(cfg: Config, path) -> None:
    with Path(path).open("w", encoding="utf-8") as f:
        json.dump(cfg.to_dict(), f, ensure_ascii=False, indent=2)

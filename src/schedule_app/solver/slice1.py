"""
Solver Slice 1 — assign each project to exactly one (timeslot, room).
No panel assignment at this level; lecturer availability not yet enforced.

OR-Tools CP-SAT API used here:
  new_bool_var()      create a 0/1 decision variable
  add()               post a linear constraint
  add_at_most_one()   efficient at-most-one propagator for BoolVars
  only_enforce_if()   conditional constraint — active only when a BoolVar is 1

Reference: OR-Tools CP-SAT Python API
https://developers.google.com/optimization/reference/python/sat/python/cp_model

num_workers note:
  solver.parameters.num_workers is the current preferred field (0 = auto).
  Reference: OR-Tools sat_parameters.proto
"""

from __future__ import annotations

from ortools.sat.python import cp_model

from .precheck import build_index, ensure_ok
from .result import ScheduleEntry, SolveResult
from ..models import Config


def _status_str(s: int) -> str:
    return {
        cp_model.OPTIMAL:       "OPTIMAL",
        cp_model.FEASIBLE:      "FEASIBLE",
        cp_model.INFEASIBLE:    "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }.get(s, "UNKNOWN")


def solve_slice1(cfg: Config) -> SolveResult:
    ensure_ok(cfg)
    idx = build_index(cfg)

    P = len(cfg.projects)
    T = len(cfg.timeslots)
    R = cfg.constraints.rooms

    model = cp_model.CpModel()

    # x[p,t,r] = 1  iff  project p is in slot t, room r
    x = {
        (p, t, r): model.new_bool_var(f"x_p{p}_t{t}_r{r}")
        for p in range(P) for t in range(T) for r in range(R)
    }

    # Each project is scheduled exactly once
    for p in range(P):
        model.add(sum(x[p, t, r] for t in range(T) for r in range(R)) == 1)

    # At most one project per (slot, room)
    # add_at_most_one uses a more efficient propagator than sum <= 1
    for t in range(T):
        for r in range(R):
            model.add_at_most_one(x[p, t, r] for p in range(P))

    # Student unavailability
    for p_i, proj in enumerate(cfg.projects):
        blocked: set[str] = set()
        for sid in proj.student_ids:
            blocked.update(cfg.students[idx.student_id_to_idx[sid]].unavailable_slot_ids)
        for slot_id in blocked:
            t = idx.slot_id_to_idx[slot_id]
            for r in range(R):
                model.add(x[p_i, t, r] == 0)

    # Soft objective: compact schedule — minimise the index of the last used slot.
    # only_enforce_if makes the lower-bound constraint conditional on x[p,t,r] = 1.
    # Reference: https://developers.google.com/optimization/reference/python/sat/python/cp_model#only_enforce_if
    last_t = model.new_int_var(0, max(T - 1, 0), "last_t")
    for p in range(P):
        for t in range(T):
            for r in range(R):
                model.add(last_t >= t).only_enforce_if(x[p, t, r])
    model.minimize(last_t)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.constraints.solver.max_time_in_seconds
    solver.parameters.num_workers         = cfg.constraints.solver.num_workers
    status = solver.solve(model)
    name   = _status_str(status)

    if name not in ("OPTIMAL", "FEASIBLE"):
        return SolveResult(status=name, diagnostics=["No feasible schedule (slice1)."])

    entries = [
        ScheduleEntry(
            project_id  = cfg.projects[p].id,
            timeslot_id = cfg.timeslots[t].id,
            room        = r,
        )
        for p in range(P) for t in range(T) for r in range(R)
        if solver.value(x[p, t, r]) == 1
    ]
    return SolveResult(
        status          = name,
        objective_value = int(solver.objective_value),
        entries         = entries,
        stats           = {
            "num_conflicts": solver.num_conflicts,
            "wall_time_s":   round(solver.wall_time, 3),
        },
    )

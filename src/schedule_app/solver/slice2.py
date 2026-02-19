"""
Solver Slice 2 — adds panel assignment and lecturer availability as hard constraints.

New variables:
  y[p,l]     = 1  iff lecturer l is in the panel for project p
  z[p,l,t,r] = x[p,t,r] AND y[p,l]   (linearised conjunction)

Linearising the product of two binary variables a, b into c = a AND b:
  c <= a
  c <= b
  c >= a + b - 1
This is the standard linearisation for binary products in integer programming.
Reference: Williams, H.P. "Model Building in Mathematical Programming",
           5th ed., Wiley (2013), Section 9.3.

BUG FIX — supervisor constraint direction:
  The original src/demo.py in this repository had:
      model.add(y[p_supervisor] == 0)
  which forces the supervisor OUT of the panel — the opposite of the requirement.
  The correct constraint is:
      model.add(y[p_supervisor] == 1)
  This file implements the corrected version.

max_per_day constraint:
  If a lecturer has max_per_day set, we group timeslots by date and add
  a per-day upper bound on the number of panel appearances.
"""

from __future__ import annotations

from collections import defaultdict

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


def solve_slice2(cfg: Config) -> SolveResult:
    ensure_ok(cfg)
    idx = build_index(cfg)

    P          = len(cfg.projects)
    T          = len(cfg.timeslots)
    R          = cfg.constraints.rooms
    L          = len(cfg.lecturers)
    panel_size = cfg.constraints.panel_size

    model = cp_model.CpModel()

    x = {(p, t, r): model.new_bool_var(f"x_p{p}_t{t}_r{r}")
         for p in range(P) for t in range(T) for r in range(R)}
    y = {(p, l): model.new_bool_var(f"y_p{p}_l{l}")
         for p in range(P) for l in range(L)}
    z = {(p, l, t, r): model.new_bool_var(f"z_p{p}_l{l}_t{t}_r{r}")
         for p in range(P) for l in range(L) for t in range(T) for r in range(R)}

    # Linearise z = x AND y
    for p in range(P):
        for l in range(L):
            for t in range(T):
                for r in range(R):
                    model.add(z[p, l, t, r] <= x[p, t, r])
                    model.add(z[p, l, t, r] <= y[p, l])
                    model.add(z[p, l, t, r] >= x[p, t, r] + y[p, l] - 1)

    # Each project scheduled exactly once
    for p in range(P):
        model.add(sum(x[p, t, r] for t in range(T) for r in range(R)) == 1)

    # Room capacity
    for t in range(T):
        for r in range(R):
            model.add_at_most_one(x[p, t, r] for p in range(P))

    # Each project needs exactly panel_size lecturers
    for p in range(P):
        model.add(sum(y[p, l] for l in range(L)) == panel_size)

    # Supervisor MUST be in the panel (== 1, not == 0 — see module docstring)
    if cfg.constraints.must_include_supervisor:
        for p_i, proj in enumerate(cfg.projects):
            if proj.supervisor_lecturer_id:
                sup_i = idx.lecturer_id_to_idx[proj.supervisor_lecturer_id]
                model.add(y[p_i, sup_i] == 1)

    # Lecturer availability: z[p,l,t,r] must be 0 when l is unavailable at t
    slot_id_at = [s.id for s in cfg.timeslots]
    available  = [set(cfg.lecturers[l].available_slot_ids) for l in range(L)]
    for l in range(L):
        for t in range(T):
            if slot_id_at[t] not in available[l]:
                for p in range(P):
                    for r in range(R):
                        model.add(z[p, l, t, r] == 0)

    # No lecturer in two simultaneous assessments
    for l in range(L):
        for t in range(T):
            model.add(
                sum(z[p, l, t, r] for p in range(P) for r in range(R)) <= 1
            )

    # max_per_day: group slots by date, add per-day upper bound per lecturer
    date_to_slots: dict[str, list[int]] = defaultdict(list)
    for t, slot in enumerate(cfg.timeslots):
        date_to_slots[slot.date].append(t)

    for l, lec in enumerate(cfg.lecturers):
        if lec.max_per_day is not None:
            for date_slots in date_to_slots.values():
                model.add(
                    sum(z[p, l, t, r]
                        for p in range(P)
                        for t in date_slots
                        for r in range(R)) <= lec.max_per_day
                )

    # Student unavailability
    for p_i, proj in enumerate(cfg.projects):
        blocked: set[str] = set()
        for sid in proj.student_ids:
            blocked.update(cfg.students[idx.student_id_to_idx[sid]].unavailable_slot_ids)
        for slot_id in blocked:
            t = idx.slot_id_to_idx[slot_id]
            for r in range(R):
                model.add(x[p_i, t, r] == 0)

    # Soft: compact schedule
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
        return SolveResult(status=name, diagnostics=["No feasible schedule (slice2)."])

    entries = []
    for p in range(P):
        for t in range(T):
            for r in range(R):
                if solver.value(x[p, t, r]) == 1:
                    panel = [cfg.lecturers[l].id for l in range(L)
                             if solver.value(y[p, l]) == 1]
                    entries.append(ScheduleEntry(
                        project_id         = cfg.projects[p].id,
                        timeslot_id        = cfg.timeslots[t].id,
                        room               = r,
                        panel_lecturer_ids = panel,
                    ))
                    break

    return SolveResult(
        status          = name,
        objective_value = int(solver.objective_value),
        entries         = entries,
    )

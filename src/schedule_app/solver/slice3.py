"""
Solver Slice 3 — full model with a weighted soft-constraint objective.

Objective (minimise weighted sum):
  w_span      * last_t           compact schedule
  w_workload  * (max_c - min_c)  balanced panel load across lecturers
  w_lunch     * lunch_penalty    avoid lunch slots

add_max_equality / add_min_equality are CP-SAT native constraints for
expressing max/min over integer variables without big-M formulations.
Reference: OR-Tools CP-SAT Python API — CpModel.add_max_equality
https://developers.google.com/optimization/reference/python/sat/python/cp_model#add_max_equality

max_per_day constraint:
  Grouping timeslots by date and summing z variables per lecturer per day,
  then bounding by Lecturer.max_per_day when set.
"""

from __future__ import annotations

from collections import defaultdict

from ortools.sat.python import cp_model

from schedule_app.solver.precheck import build_index, ensure_ok
from schedule_app.solver.result import ScheduleEntry, SolveResult
from schedule_app.models import Config


def _status_str(s: object) -> str:
    """Convert a CP-SAT solver status value to a readable string."""
    mapping = {
        int(cp_model.OPTIMAL):       "OPTIMAL",
        int(cp_model.FEASIBLE):      "FEASIBLE",
        int(cp_model.INFEASIBLE):    "INFEASIBLE",
        int(cp_model.MODEL_INVALID): "MODEL_INVALID",
    }
    return mapping.get(int(s), "UNKNOWN")  # type: ignore[call-overload]


def solve_slice3(cfg: Config) -> SolveResult:
    ensure_ok(cfg)
    idx = build_index(cfg)

    P          = len(cfg.projects)
    T          = len(cfg.timeslots)
    R          = cfg.constraints.rooms
    L          = len(cfg.lecturers)
    panel_size = cfg.constraints.panel_size
    w_span     = cfg.constraints.weights.span
    w_workload = cfg.constraints.weights.workload_balance
    w_lunch    = cfg.constraints.weights.lunch

    lunch_t = {
        idx.slot_id_to_idx[sid]
        for sid in cfg.constraints.lunch_slot_ids
        if sid in idx.slot_id_to_idx
    }

    model = cp_model.CpModel()

    x = {(p, t, r): model.new_bool_var(f"x_p{p}_t{t}_r{r}")
         for p in range(P) for t in range(T) for r in range(R)}
    y = {(p, l): model.new_bool_var(f"y_p{p}_l{li}")
         for p in range(P) for li in range(L)}
    z = {(p, l, t, r): model.new_bool_var(f"z_p{p}_l{li}_t{t}_r{r}")
         for p in range(P) for li in range(L) for t in range(T) for r in range(R)}

    # Linearise z = x AND y  (standard binary product linearisation)
    for p in range(P):
        for li in range(L):
            for t in range(T):
                for r in range(R):
                    model.add(z[p, li, t, r] <= x[p, t, r])
                    model.add(z[p, li, t, r] <= y[p, li])
                    model.add(z[p, li, t, r] >= x[p, t, r] + y[p, li] - 1)

    for p in range(P):
        model.add(sum(x[p, t, r] for t in range(T) for r in range(R)) == 1)

    for t in range(T):
        for r in range(R):
            model.add_at_most_one(x[p, t, r] for p in range(P))

    for p in range(P):
        model.add(sum(y[p, li] for li in range(L)) == panel_size)

    # Supervisor in panel (corrected: == 1, not == 0)
    if cfg.constraints.must_include_supervisor:
        for p_i, proj in enumerate(cfg.projects):
            if proj.supervisor_lecturer_id:
                sup_i = idx.lecturer_id_to_idx[proj.supervisor_lecturer_id]
                model.add(y[p_i, sup_i] == 1)

    slot_id_at = [s.id for s in cfg.timeslots]
    available  = [set(cfg.lecturers[li].available_slot_ids) for li in range(L)]
    for li in range(L):
        for t in range(T):
            if slot_id_at[t] not in available[li]:
                for p in range(P):
                    for r in range(R):
                        model.add(z[p, li, t, r] == 0)

    for li in range(L):
        for t in range(T):
            model.add(
                sum(z[p, li, t, r] for p in range(P) for r in range(R)) <= 1
            )

    # max_per_day
    date_to_slots: dict[str, list[int]] = defaultdict(list)
    for t, slot in enumerate(cfg.timeslots):
        date_to_slots[slot.date].append(t)

    for li, lec in enumerate(cfg.lecturers):
        if lec.max_per_day is not None:
            for date_slots in date_to_slots.values():
                model.add(
                    sum(z[p, li, t, r]
                        for p in range(P)
                        for t in date_slots
                        for r in range(R)) <= lec.max_per_day
                )

    for p_i, proj in enumerate(cfg.projects):
        blocked: set[str] = set()
        for sid in proj.student_ids:
            blocked.update(cfg.students[idx.student_id_to_idx[sid]].unavailable_slot_ids)
        for slot_id in blocked:
            t = idx.slot_id_to_idx[slot_id]
            for r in range(R):
                model.add(x[p_i, t, r] == 0)

    # ── soft objectives ───────────────────────────────────────────────────────

    # 1. Compact schedule
    last_t = model.new_int_var(0, max(T - 1, 0), "last_t")
    for p in range(P):
        for t in range(T):
            for r in range(R):
                model.add(last_t >= t).only_enforce_if(x[p, t, r])

    # 2. Lunch penalty
    lunch_penalty = model.new_int_var(0, P, "lunch_penalty")
    if lunch_t:
        model.add(lunch_penalty == sum(
            x[p, t, r]
            for p in range(P) for t in lunch_t for r in range(R)
        ))
    else:
        model.add(lunch_penalty == 0)

    # 3. Workload balance via add_max_equality / add_min_equality
    counts = []
    for li in range(L):
        c = model.new_int_var(0, P, f"count_l{li}")
        model.add(c == sum(
            z[p, li, t, r]
            for p in range(P) for t in range(T) for r in range(R)
        ))
        counts.append(c)

    max_c     = model.new_int_var(0, P, "max_c")
    min_c     = model.new_int_var(0, P, "min_c")
    imbalance = model.new_int_var(0, P, "imbalance")
    model.add_max_equality(max_c, counts)
    model.add_min_equality(min_c, counts)
    model.add(imbalance == max_c - min_c)

    obj = []
    if w_span     > 0:
        obj.append(w_span     * last_t)
    if w_workload > 0:
        obj.append(w_workload  * imbalance)
    if w_lunch    > 0:
        obj.append(w_lunch     * lunch_penalty)
    model.minimize(sum(obj) if obj else 0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.constraints.solver.max_time_in_seconds
    solver.parameters.num_workers         = cfg.constraints.solver.num_workers
    status = solver.solve(model)
    name   = _status_str(status)

    if name not in ("OPTIMAL", "FEASIBLE"):
        return SolveResult(status=name, diagnostics=["No feasible schedule (slice3)."])

    entries = []
    for p in range(P):
        for t in range(T):
            for r in range(R):
                if solver.value(x[p, t, r]) == 1:
                    panel = [cfg.lecturers[li].id for li in range(L)
                             if solver.value(y[p, li]) == 1]
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
        stats           = {
            "last_t":        int(solver.value(last_t)),
            "imbalance":     int(solver.value(imbalance)),
            "lunch_penalty": int(solver.value(lunch_penalty)),
            "wall_time_s":   round(solver.wall_time, 3),
        },
    )

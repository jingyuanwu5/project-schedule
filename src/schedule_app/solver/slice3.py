# slice3.py - full model with soft objectives (span, workload balance, lunch avoidance)
# this is the "real" solver, slice1 and slice2 were for testing
#
# soft objectives:
#   1. compact schedule - minimize last timeslot used
#   2. workload balance - minimize difference between busiest and least busy lecturer
#   3. lunch avoidance - penalize assessments in lunch slots
#
# references:
#   OR-Tools CP-SAT: https://github.com/google/or-tools
#   add_max_equality / add_min_equality:
#     https://developers.google.com/optimization/reference/python/sat/python/cp_model

from collections import defaultdict
from ortools.sat.python import cp_model

from schedule_app.solver.precheck import build_index, ensure_ok
from schedule_app.solver.result import ScheduleEntry, SolveResult
from schedule_app.models import Config


def _status_str(s):
    mapping = {
        int(cp_model.OPTIMAL):       "OPTIMAL",
        int(cp_model.FEASIBLE):      "FEASIBLE",
        int(cp_model.INFEASIBLE):    "INFEASIBLE",
        int(cp_model.MODEL_INVALID): "MODEL_INVALID",
    }
    return mapping.get(int(s), "UNKNOWN")


def solve_slice3(cfg: Config) -> SolveResult:
    ensure_ok(cfg)
    idx = build_index(cfg)

    P = len(cfg.projects)
    T = len(cfg.timeslots)
    R = cfg.constraints.rooms
    L = len(cfg.lecturers)
    panel_size = cfg.constraints.panel_size
    w_span     = cfg.constraints.weights.span
    w_workload = cfg.constraints.weights.workload_balance
    w_lunch    = cfg.constraints.weights.lunch

    # which timeslot indices are lunch slots
    lunch_t = set()
    for sid in cfg.constraints.lunch_slot_ids:
        if sid in idx.slot_id_to_idx:
            lunch_t.add(idx.slot_id_to_idx[sid])

    model = cp_model.CpModel()

    # decision variables - same structure as slice2
    x = {}
    for p in range(P):
        for t in range(T):
            for r in range(R):
                x[(p, t, r)] = model.new_bool_var(f"x_p{p}_t{t}_r{r}")

    y = {}
    for p in range(P):
        for l in range(L):
            y[(p, l)] = model.new_bool_var(f"y_p{p}_l{l}")

    z = {}
    for p in range(P):
        for l in range(L):
            for t in range(T):
                for r in range(R):
                    z[(p, l, t, r)] = model.new_bool_var(f"z_p{p}_l{l}_t{t}_r{r}")

    # z = x AND y (same linearisation as slice2)
    for p in range(P):
        for l in range(L):
            for t in range(T):
                for r in range(R):
                    model.add(z[p, l, t, r] <= x[p, t, r])
                    model.add(z[p, l, t, r] <= y[p, l])
                    model.add(z[p, l, t, r] >= x[p, t, r] + y[p, l] - 1)

    # hard constraints (same as slice2)
    for p in range(P):
        model.add(sum(x[p, t, r] for t in range(T) for r in range(R)) == 1)

    for t in range(T):
        for r in range(R):
            model.add_at_most_one(x[p, t, r] for p in range(P))

    for p in range(P):
        model.add(sum(y[p, l] for l in range(L)) == panel_size)

    if cfg.constraints.must_include_supervisor:
        for p_i, proj in enumerate(cfg.projects):
            if proj.supervisor_lecturer_id:
                sup_i = idx.lecturer_id_to_idx[proj.supervisor_lecturer_id]
                model.add(y[p_i, sup_i] == 1)

    slot_id_at = [s.id for s in cfg.timeslots]
    available = [set(cfg.lecturers[l].available_slot_ids) for l in range(L)]
    for l in range(L):
        for t in range(T):
            if slot_id_at[t] not in available[l]:
                for p in range(P):
                    for r in range(R):
                        model.add(z[p, l, t, r] == 0)

    for l in range(L):
        for t in range(T):
            model.add(
                sum(z[p, l, t, r] for p in range(P) for r in range(R)) <= 1
            )

    # max per day constraint
    date_to_slots = defaultdict(list)
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

    # student unavailability
    for p_i, proj in enumerate(cfg.projects):
        blocked = set()
        for sid in proj.student_ids:
            blocked.update(cfg.students[idx.student_id_to_idx[sid]].unavailable_slot_ids)
        for slot_id in blocked:
            t = idx.slot_id_to_idx[slot_id]
            for r in range(R):
                model.add(x[p_i, t, r] == 0)

    # soft objective 1: compact schedule
    last_t = model.new_int_var(0, max(T - 1, 0), "last_t")
    for p in range(P):
        for t in range(T):
            for r in range(R):
                model.add(last_t >= t).only_enforce_if(x[p, t, r])

    # soft objective 2: avoid lunch slots
    lunch_penalty = model.new_int_var(0, P, "lunch_penalty")
    if lunch_t:
        model.add(lunch_penalty == sum(
            x[p, t, r]
            for p in range(P) for t in lunch_t for r in range(R)
        ))
    else:
        model.add(lunch_penalty == 0)

    # soft objective 3: workload balance
    # count how many panels each lecturer appears in, then minimize max-min
    counts = []
    for l in range(L):
        c = model.new_int_var(0, P, f"count_l{l}")
        model.add(c == sum(
            z[p, l, t, r]
            for p in range(P) for t in range(T) for r in range(R)
        ))
        counts.append(c)

    max_c = model.new_int_var(0, P, "max_c")
    min_c = model.new_int_var(0, P, "min_c")
    imbalance = model.new_int_var(0, P, "imbalance")
    model.add_max_equality(max_c, counts)
    model.add_min_equality(min_c, counts)
    model.add(imbalance == max_c - min_c)

    # combine objectives using weights from config
    obj_terms = []
    if w_span > 0:
        obj_terms.append(w_span * last_t)
    if w_workload > 0:
        obj_terms.append(w_workload * imbalance)
    if w_lunch > 0:
        obj_terms.append(w_lunch * lunch_penalty)

    if obj_terms:
        model.minimize(sum(obj_terms))
    else:
        model.minimize(0)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.constraints.solver.max_time_in_seconds
    solver.parameters.num_workers = cfg.constraints.solver.num_workers
    status = solver.solve(model)
    name = _status_str(status)

    if name not in ("OPTIMAL", "FEASIBLE"):
        return SolveResult(status=name, diagnostics=["No feasible schedule found (slice3)."])

    entries = []
    for p in range(P):
        for t in range(T):
            for r in range(R):
                if solver.value(x[p, t, r]) == 1:
                    panel = [cfg.lecturers[l].id for l in range(L)
                             if solver.value(y[p, l]) == 1]
                    entries.append(ScheduleEntry(
                        project_id=cfg.projects[p].id,
                        timeslot_id=cfg.timeslots[t].id,
                        room=r,
                        panel_lecturer_ids=panel,
                    ))
                    break

    return SolveResult(
        status=name,
        objective_value=int(solver.objective_value),
        entries=entries,
        stats={
            "last_t": int(solver.value(last_t)),
            "imbalance": int(solver.value(imbalance)),
            "lunch_penalty": int(solver.value(lunch_penalty)),
            "wall_time_s": round(solver.wall_time, 3),
        },
    )

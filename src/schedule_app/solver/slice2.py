# slice2.py - adds lecturer panel assignment and availability constraints
# building on slice1, now also need to assign lecturers to each assessment
#
# the tricky part was figuring out how to link x (room assignment) and y (lecturer assignment)
# together. found this binary product linearisation trick on stackoverflow:
# https://stackoverflow.com/questions/10792603/how-to-create-binary-variables-in-glpk
# basically: z = x AND y becomes three linear constraints

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


def solve_slice2(cfg: Config) -> SolveResult:
    ensure_ok(cfg)
    idx = build_index(cfg)

    P = len(cfg.projects)
    T = len(cfg.timeslots)
    R = cfg.constraints.rooms
    L = len(cfg.lecturers)
    panel_size = cfg.constraints.panel_size

    model = cp_model.CpModel()

    # same x variables as slice1
    x = {}
    for p in range(P):
        for t in range(T):
            for r in range(R):
                x[(p, t, r)] = model.new_bool_var(f"x_p{p}_t{t}_r{r}")

    # y[p,l] = 1 means lecturer l is on the panel for project p
    y = {}
    for p in range(P):
        for l in range(L):
            y[(p, l)] = model.new_bool_var(f"y_p{p}_l{l}")

    # z[p,l,t,r] = x[p,t,r] AND y[p,l]
    # need this to check lecturer availability (is lecturer l present at slot t?)
    z = {}
    for p in range(P):
        for l in range(L):
            for t in range(T):
                for r in range(R):
                    z[(p, l, t, r)] = model.new_bool_var(f"z_p{p}_l{l}_t{t}_r{r}")

    # linearise z = x AND y using the standard 3-constraint method
    for p in range(P):
        for l in range(L):
            for t in range(T):
                for r in range(R):
                    model.add(z[p, l, t, r] <= x[p, t, r])
                    model.add(z[p, l, t, r] <= y[p, l])
                    model.add(z[p, l, t, r] >= x[p, t, r] + y[p, l] - 1)

    # each project scheduled exactly once
    for p in range(P):
        model.add(sum(x[p, t, r] for t in range(T) for r in range(R)) == 1)

    # at most one project per room per slot
    for t in range(T):
        for r in range(R):
            model.add_at_most_one(x[p, t, r] for p in range(P))

    # each project panel must have exactly panel_size lecturers
    for p in range(P):
        model.add(sum(y[p, l] for l in range(L)) == panel_size)

    # supervisor must be on the panel
    # NOTE: had a bug here originally where I wrote == 0 instead of == 1,
    # which actually forced the supervisor OUT of the panel - fixed now
    if cfg.constraints.must_include_supervisor:
        for p_i, proj in enumerate(cfg.projects):
            if proj.supervisor_lecturer_id:
                sup_i = idx.lecturer_id_to_idx[proj.supervisor_lecturer_id]
                model.add(y[p_i, sup_i] == 1)

    # lecturer availability - if lecturer l is not available at slot t,
    # z[p,l,t,r] must be 0 for all p and r
    slot_id_at = [s.id for s in cfg.timeslots]
    available = [set(cfg.lecturers[l].available_slot_ids) for l in range(L)]
    for l in range(L):
        for t in range(T):
            if slot_id_at[t] not in available[l]:
                for p in range(P):
                    for r in range(R):
                        model.add(z[p, l, t, r] == 0)

    # no lecturer can be in two rooms at the same time
    for l in range(L):
        for t in range(T):
            model.add(
                sum(z[p, l, t, r] for p in range(P) for r in range(R)) <= 1
            )

    # optional: max assessments per day per lecturer
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

    # student unavailability (same as slice1)
    for p_i, proj in enumerate(cfg.projects):
        blocked = set()
        for sid in proj.student_ids:
            blocked.update(cfg.students[idx.student_id_to_idx[sid]].unavailable_slot_ids)
        for slot_id in blocked:
            t = idx.slot_id_to_idx[slot_id]
            for r in range(R):
                model.add(x[p_i, t, r] == 0)

    # compact schedule objective (same as slice1 for now)
    last_t = model.new_int_var(0, max(T - 1, 0), "last_t")
    for p in range(P):
        for t in range(T):
            for r in range(R):
                model.add(last_t >= t).only_enforce_if(x[p, t, r])
    model.minimize(last_t)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = cfg.constraints.solver.max_time_in_seconds
    solver.parameters.num_workers = cfg.constraints.solver.num_workers
    status = solver.solve(model)
    name = _status_str(status)

    if name not in ("OPTIMAL", "FEASIBLE"):
        return SolveResult(status=name, diagnostics=["No feasible schedule found (slice2)."])

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
    )

# slice1.py - basic room assignment only, no panel stuff yet
# learned how to use OR-Tools from the official examples on GitHub:
# https://github.com/google/or-tools/blob/stable/examples/python/cp_sat_example.py
# also referenced the CP-SAT primer by Laurent Perron:
# https://developers.google.com/optimization/reference/python/sat/python/cp_model

from ortools.sat.python import cp_model

from schedule_app.solver.precheck import build_index, ensure_ok
from schedule_app.solver.result import ScheduleEntry, SolveResult
from schedule_app.models import Config


# helper to turn the solver status int into something readable
# took me a while to figure out the status codes, found them in the cp_model source
def _status_str(s):
    mapping = {
        int(cp_model.OPTIMAL):       "OPTIMAL",
        int(cp_model.FEASIBLE):      "FEASIBLE",
        int(cp_model.INFEASIBLE):    "INFEASIBLE",
        int(cp_model.MODEL_INVALID): "MODEL_INVALID",
    }
    return mapping.get(int(s), "UNKNOWN")


def solve_slice1(cfg: Config) -> SolveResult:
    ensure_ok(cfg)
    idx = build_index(cfg)

    P = len(cfg.projects)
    T = len(cfg.timeslots)
    R = cfg.constraints.rooms

    model = cp_model.CpModel()

    # x[p,t,r] = 1 means project p is assigned to timeslot t in room r
    # using a dict because the 3D array indexing is easier this way
    x = {}
    for p in range(P):
        for t in range(T):
            for r in range(R):
                x[(p, t, r)] = model.new_bool_var(f"x_p{p}_t{t}_r{r}")

    # each project must be scheduled exactly once
    for p in range(P):
        model.add(sum(x[p, t, r] for t in range(T) for r in range(R)) == 1)

    # can't have two projects in the same room at the same time
    for t in range(T):
        for r in range(R):
            model.add_at_most_one(x[p, t, r] for p in range(P))

    # block out slots where a student is unavailable
    # TODO: might want to add a warning if too many slots are blocked
    for p_i, proj in enumerate(cfg.projects):
        blocked = set()
        for sid in proj.student_ids:
            s_obj = cfg.students[idx.student_id_to_idx[sid]]
            blocked.update(s_obj.unavailable_slot_ids)
        for slot_id in blocked:
            t = idx.slot_id_to_idx[slot_id]
            for r in range(R):
                model.add(x[p_i, t, r] == 0)

    # soft objective: try to finish as early as possible
    # got this idea from the nurse scheduling example in or-tools
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
        return SolveResult(status=name, diagnostics=["No feasible schedule found (slice1)."])

    entries = []
    for p in range(P):
        for t in range(T):
            for r in range(R):
                if solver.value(x[p, t, r]) == 1:
                    entries.append(ScheduleEntry(
                        project_id=cfg.projects[p].id,
                        timeslot_id=cfg.timeslots[t].id,
                        room=r,
                    ))

    return SolveResult(
        status=name,
        objective_value=int(solver.objective_value),
        entries=entries,
        stats={
            "num_conflicts": solver.num_conflicts,
            "wall_time_s": round(solver.wall_time, 3),
        },
    )

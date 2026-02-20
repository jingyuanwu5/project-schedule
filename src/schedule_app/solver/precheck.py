# precheck.py - checks the config before running the solver
# better to catch obvious problems here than wait for OR-Tools to say INFEASIBLE
# with no explanation

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from schedule_app.models import Config


class PrecheckError(ValueError):
    pass


@dataclass(frozen=True)
class IdIndex:
    slot_id_to_idx: Dict[str, int]
    lecturer_id_to_idx: Dict[str, int]
    student_id_to_idx: Dict[str, int]
    project_id_to_idx: Dict[str, int]


def build_index(cfg: Config) -> IdIndex:
    return IdIndex(
        slot_id_to_idx={s.id: i for i, s in enumerate(cfg.timeslots)},
        lecturer_id_to_idx={l.id: i for i, l in enumerate(cfg.lecturers)},
        student_id_to_idx={s.id: i for i, s in enumerate(cfg.students)},
        project_id_to_idx={p.id: i for i, p in enumerate(cfg.projects)},
    )


def precheck(cfg: Config) -> Tuple[List[str], List[str]]:
    errors = []
    warnings = []

    idx = build_index(cfg)
    capacity = cfg.constraints.rooms * len(cfg.timeslots)

    if capacity < len(cfg.projects):
        errors.append(
            f"Not enough slots: {cfg.constraints.rooms} room(s) x "
            f"{len(cfg.timeslots)} slot(s) = {capacity}, "
            f"but need {len(cfg.projects)} slots for projects."
        )

    if cfg.constraints.panel_size > len(cfg.lecturers):
        errors.append(
            f"panel_size ({cfg.constraints.panel_size}) is bigger than "
            f"number of lecturers ({len(cfg.lecturers)})."
        )

    known_slots: Set[str] = set(idx.slot_id_to_idx)

    for p in cfg.projects:
        if cfg.constraints.must_include_supervisor:
            if not p.supervisor_lecturer_id:
                errors.append(
                    f"Project '{p.id}' has no supervisor set but "
                    f"must_include_supervisor is True."
                )
            elif p.supervisor_lecturer_id not in idx.lecturer_id_to_idx:
                errors.append(
                    f"Project '{p.id}' has unknown supervisor id "
                    f"'{p.supervisor_lecturer_id}'."
                )
            else:
                sup = cfg.get_lecturer(p.supervisor_lecturer_id)
                if sup and not sup.available_slot_ids:
                    errors.append(
                        f"Project '{p.id}' supervisor '{sup.id}' has no available slots."
                    )
        for sid in p.student_ids:
            if sid not in idx.student_id_to_idx:
                errors.append(f"Project '{p.id}' references unknown student '{sid}'.")

    for l in cfg.lecturers:
        bad = [s for s in l.available_slot_ids if s not in known_slots]
        if bad:
            errors.append(f"Lecturer '{l.id}' has unknown slot ids: {bad}")
        if not l.available_slot_ids:
            warnings.append(f"Lecturer '{l.id}' has no available slots.")

    for s in cfg.students:
        bad = [t for t in s.unavailable_slot_ids if t not in known_slots]
        if bad:
            errors.append(f"Student '{s.id}' has unknown slot ids: {bad}")

    bad_lunch = [t for t in cfg.constraints.lunch_slot_ids if t not in known_slots]
    if bad_lunch:
        errors.append(f"lunch_slot_ids has unknown slot ids: {bad_lunch}")

    return errors, warnings


def ensure_ok(cfg: Config):
    errors, _ = precheck(cfg)
    if errors:
        raise PrecheckError("\n".join(errors))

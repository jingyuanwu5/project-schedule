"""
Pre-solve feasibility checks that run before the solver is invoked.

Catching trivially infeasible configs here means the coordinator sees
plain-English error messages rather than a raw INFEASIBLE solver status.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from ..models import Config


class PrecheckError(ValueError):
    """Raised by ensure_ok() when hard errors are present."""


@dataclass(frozen=True)
class IdIndex:
    slot_id_to_idx:     Dict[str, int]
    lecturer_id_to_idx: Dict[str, int]
    student_id_to_idx:  Dict[str, int]
    project_id_to_idx:  Dict[str, int]


def build_index(cfg: Config) -> IdIndex:
    return IdIndex(
        slot_id_to_idx     = {s.id: i for i, s in enumerate(cfg.timeslots)},
        lecturer_id_to_idx = {l.id: i for i, l in enumerate(cfg.lecturers)},
        student_id_to_idx  = {s.id: i for i, s in enumerate(cfg.students)},
        project_id_to_idx  = {p.id: i for i, p in enumerate(cfg.projects)},
    )


def precheck(cfg: Config) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings). errors = definitely INFEASIBLE."""
    errors:   List[str] = []
    warnings: List[str] = []

    idx      = build_index(cfg)
    capacity = cfg.constraints.rooms * len(cfg.timeslots)

    if capacity < len(cfg.projects):
        errors.append(
            f"Not enough capacity: {cfg.constraints.rooms} room(s) x "
            f"{len(cfg.timeslots)} slot(s) = {capacity}, "
            f"but {len(cfg.projects)} project(s) need scheduling."
        )

    if cfg.constraints.panel_size > len(cfg.lecturers):
        errors.append(
            f"panel_size ({cfg.constraints.panel_size}) exceeds "
            f"lecturer count ({len(cfg.lecturers)})."
        )

    known_slots: Set[str] = set(idx.slot_id_to_idx)

    for p in cfg.projects:
        if cfg.constraints.must_include_supervisor:
            if not p.supervisor_lecturer_id:
                errors.append(
                    f"Project '{p.id}' has no supervisor but "
                    f"must_include_supervisor is True."
                )
            elif p.supervisor_lecturer_id not in idx.lecturer_id_to_idx:
                errors.append(
                    f"Project '{p.id}' references unknown supervisor "
                    f"'{p.supervisor_lecturer_id}'."
                )
            else:
                # Supervisor exists — check they have at least one available slot
                sup = cfg.get_lecturer(p.supervisor_lecturer_id)
                if sup and not sup.available_slot_ids:
                    errors.append(
                        f"Project '{p.id}' supervisor '{sup.id}' has no available "
                        f"slots — any assessment supervised by them will be INFEASIBLE."
                    )
        for sid in p.student_ids:
            if sid not in idx.student_id_to_idx:
                errors.append(
                    f"Project '{p.id}' references unknown student '{sid}'."
                )

    for l in cfg.lecturers:
        bad = [s for s in l.available_slot_ids if s not in known_slots]
        if bad:
            errors.append(f"Lecturer '{l.id}' lists unknown slot id(s): {bad}")
        if not l.available_slot_ids:
            warnings.append(
                f"Lecturer '{l.id}' has no available slots — any project "
                f"supervised by them will be INFEASIBLE."
            )

    for s in cfg.students:
        bad = [t for t in s.unavailable_slot_ids if t not in known_slots]
        if bad:
            errors.append(f"Student '{s.id}' lists unknown slot id(s): {bad}")

    bad_lunch = [t for t in cfg.constraints.lunch_slot_ids if t not in known_slots]
    if bad_lunch:
        errors.append(f"lunch_slot_ids contains unknown slot id(s): {bad_lunch}")

    return errors, warnings


def ensure_ok(cfg: Config) -> None:
    errors, _ = precheck(cfg)
    if errors:
        raise PrecheckError("\n".join(errors))

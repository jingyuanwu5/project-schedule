"""
Data model layer — plain Python dataclasses for every domain object.

dataclasses.dataclass generates __init__, __repr__ and __eq__ from the
field declarations, removing boilerplate while keeping the types explicit.

Reference: Python docs — dataclasses
https://docs.python.org/3/library/dataclasses.html
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TimeSlot:
    """One assessment slot, e.g. 2026-03-10 09:00-09:30."""
    id:    str
    date:  str   # YYYY-MM-DD
    start: str   # HH:MM
    end:   str   # HH:MM
    label: str = ""


@dataclass
class Lecturer:
    id:   str
    name: str
    # IDs of slots this lecturer is available for.
    # Stored as a flat list of references — not embedded objects — so that
    # changing a slot definition does not require touching every lecturer.
    available_slot_ids: List[str] = field(default_factory=list)
    max_per_day:  Optional[int] = None
    max_total:    Optional[int] = None


@dataclass
class Student:
    id:   str
    name: str
    unavailable_slot_ids: List[str] = field(default_factory=list)


@dataclass
class Project:
    id:    str
    title: str
    # student_ids holds references by ID rather than embedding Student objects.
    # This is the "flat entities + ID links" pattern that avoids coupling when
    # students move between projects or projects gain multiple students.
    student_ids:            List[str] = field(default_factory=list)
    supervisor_lecturer_id: str       = ""


@dataclass
class Weights:
    """Coefficients for the soft-constraint objective function."""
    span:             int = 1   # minimise index of the last used slot
    workload_balance: int = 10  # minimise max-minus-min panel load across lecturers
    lunch:            int = 3   # penalise slots listed in constraints.lunch_slot_ids


@dataclass
class SolverParams:
    max_time_in_seconds: float = 10.0
    num_search_workers:  int   = 8


@dataclass
class Constraints:
    rooms:                   int        = 1
    panel_size:              int        = 2
    must_include_supervisor: bool       = True
    lunch_slot_ids:          List[str]  = field(default_factory=list)
    weights:                 Weights    = field(default_factory=Weights)
    solver:                  SolverParams = field(default_factory=SolverParams)


@dataclass
class Config:
    meta:        Dict[str, Any]  = field(default_factory=dict)
    timeslots:   List[TimeSlot]  = field(default_factory=list)
    lecturers:   List[Lecturer]  = field(default_factory=list)
    students:    List[Student]   = field(default_factory=list)
    projects:    List[Project]   = field(default_factory=list)
    constraints: Constraints     = field(default_factory=Constraints)

    def to_dict(self) -> Dict[str, Any]:
        # asdict() recursively converts nested dataclasses to plain dicts.
        # Reference: https://docs.python.org/3/library/dataclasses.html#dataclasses.asdict
        return asdict(self)

    def validate(self) -> None:
        if self.constraints.rooms < 1:
            raise ValueError("constraints.rooms must be >= 1")
        if self.constraints.panel_size < 1:
            raise ValueError("constraints.panel_size must be >= 1")
        if min(
            self.constraints.weights.span,
            self.constraints.weights.workload_balance,
            self.constraints.weights.lunch,
        ) < 0:
            raise ValueError("All constraint weights must be non-negative")

    # ── convenience look-ups ──────────────────────────────────────────────────

    def get_lecturer(self, lid: str) -> Optional[Lecturer]:
        return next((l for l in self.lecturers if l.id == lid), None)

    def get_student(self, sid: str) -> Optional[Student]:
        return next((s for s in self.students if s.id == sid), None)

    def get_project(self, pid: str) -> Optional[Project]:
        return next((p for p in self.projects if p.id == pid), None)
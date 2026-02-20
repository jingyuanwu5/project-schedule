"""
Data model layer for the assessment timetable scheduler.

Every domain object is a plain Python dataclass. The @dataclass decorator
generates __init__, __repr__ and __eq__ automatically from field declarations.

Reference: Python Software Foundation. "dataclasses — Data Classes."
https://docs.python.org/3/library/dataclasses.html

Design note — flat entities with ID references:
  Students are independent top-level objects. Projects hold student_ids
  (a list of string IDs) rather than embedding Student objects directly.
  Supervisor feedback: "separate student and project objects and link from
  students to projects rather than embed students in project objects directly."

OR-Tools worker parameter note:
  SolverParams uses num_workers as the primary field (0 = auto-detect cores).
  The older num_search_workers is read from JSON for backwards compatibility
  but is deprecated upstream.
  Reference: OR-Tools sat_parameters.proto,
  https://github.com/google/or-tools
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
    label: str   = ""


@dataclass
class Lecturer:
    id:   str
    name: str
    available_slot_ids: List[str] = field(default_factory=list)
    max_per_day: Optional[int]    = None
    max_total:   Optional[int]    = None


@dataclass
class Student:
    id:   str
    name: str
    unavailable_slot_ids: List[str] = field(default_factory=list)


@dataclass
class Project:
    id:    str
    title: str
    student_ids:            List[str] = field(default_factory=list)
    supervisor_lecturer_id: str       = ""


@dataclass
class Weights:
    """Coefficients for the soft-constraint objective. 0 = ignore that term."""
    span:             int = 1
    workload_balance: int = 10
    lunch:            int = 3


@dataclass
class SolverParams:
    max_time_in_seconds: float = 10.0
    # 0 = use all available cores (OR-Tools default).
    # Preferred over the deprecated num_search_workers field.
    num_workers: int = 0


@dataclass
class Constraints:
    rooms:                   int          = 1
    panel_size:              int          = 2
    must_include_supervisor: bool         = True
    lunch_slot_ids:          List[str]    = field(default_factory=list)
    weights:                 Weights      = field(default_factory=Weights)
    solver:                  SolverParams = field(default_factory=SolverParams)


@dataclass
class Config:
    meta:        Dict[str, Any] = field(default_factory=dict)
    timeslots:   List[TimeSlot] = field(default_factory=list)
    lecturers:   List[Lecturer] = field(default_factory=list)
    students:    List[Student]  = field(default_factory=list)
    projects:    List[Project]  = field(default_factory=list)
    constraints: Constraints    = field(default_factory=Constraints)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def validate(self) -> None:
        if self.constraints.rooms < 1:
            raise ValueError("constraints.rooms must be >= 1")
        if self.constraints.panel_size < 1:
            raise ValueError("constraints.panel_size must be >= 1")
        w = self.constraints.weights
        if min(w.span, w.workload_balance, w.lunch) < 0:
            raise ValueError("All objective weights must be >= 0")

    def get_lecturer(self, lid: str) -> Optional[Lecturer]:
        return next((lec for lec in self.lecturers if lec.id == lid), None)

    def get_student(self, sid: str) -> Optional[Student]:
        return next((s for s in self.students if s.id == sid), None)

    def get_project(self, pid: str) -> Optional[Project]:
        return next((p for p in self.projects if p.id == pid), None)

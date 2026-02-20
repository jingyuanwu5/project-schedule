# models.py - data classes for the scheduler
# using Python dataclasses to avoid writing __init__ manually
# reference: https://docs.python.org/3/library/dataclasses.html

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TimeSlot:
    # frozen=True means you can't accidentally change a timeslot after creating it
    id: str
    date: str    # format: YYYY-MM-DD
    start: str   # format: HH:MM
    end: str     # format: HH:MM
    label: str = ""


@dataclass
class Lecturer:
    id: str
    name: str
    available_slot_ids: List[str] = field(default_factory=list)
    max_per_day: Optional[int] = None
    max_total: Optional[int] = None  # not used by solver yet, TODO


@dataclass
class Student:
    id: str
    name: str
    unavailable_slot_ids: List[str] = field(default_factory=list)


@dataclass
class Project:
    id: str
    title: str
    student_ids: List[str] = field(default_factory=list)
    supervisor_lecturer_id: str = ""


@dataclass
class Weights:
    # weights for the soft objective function in slice3
    # set to 0 to disable that objective
    span: int = 1
    workload_balance: int = 10
    lunch: int = 3


@dataclass
class SolverParams:
    max_time_in_seconds: float = 10.0
    num_workers: int = 0  # 0 = use all cores


@dataclass
class Constraints:
    rooms: int = 1
    panel_size: int = 2
    must_include_supervisor: bool = True
    lunch_slot_ids: List[str] = field(default_factory=list)
    weights: Weights = field(default_factory=Weights)
    solver: SolverParams = field(default_factory=SolverParams)


@dataclass
class Config:
    meta: Dict[str, Any] = field(default_factory=dict)
    timeslots: List[TimeSlot] = field(default_factory=list)
    lecturers: List[Lecturer] = field(default_factory=list)
    students: List[Student] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    constraints: Constraints = field(default_factory=Constraints)

    def to_dict(self):
        return asdict(self)

    def validate(self):
        if self.constraints.rooms < 1:
            raise ValueError("constraints.rooms must be >= 1")
        if self.constraints.panel_size < 1:
            raise ValueError("constraints.panel_size must be >= 1")
        w = self.constraints.weights
        if min(w.span, w.workload_balance, w.lunch) < 0:
            raise ValueError("weights must be >= 0")

    def get_lecturer(self, lid: str):
        return next((l for l in self.lecturers if l.id == lid), None)

    def get_student(self, sid: str):
        return next((s for s in self.students if s.id == sid), None)

    def get_project(self, pid: str):
        return next((p for p in self.projects if p.id == pid), None)

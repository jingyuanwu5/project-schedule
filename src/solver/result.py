from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ScheduleEntry:
    project_id:         str
    timeslot_id:        str
    room:               int
    panel_lecturer_ids: List[str] = field(default_factory=list)


@dataclass
class SolveResult:
    status:          str                    # OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN
    objective_value: Optional[int]  = None
    entries:         List[ScheduleEntry] = field(default_factory=list)
    diagnostics:     List[str]       = field(default_factory=list)
    stats:           Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
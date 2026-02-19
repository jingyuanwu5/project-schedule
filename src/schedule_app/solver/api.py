from __future__ import annotations
from schedule_app.models import Config
from schedule_app.solver.result import SolveResult
from schedule_app.solver.slice1 import solve_slice1
from schedule_app.solver.slice2 import solve_slice2
from schedule_app.solver.slice3 import solve_slice3


def solve(cfg: Config, level: str = "slice3") -> SolveResult:
    level = (level or "").lower()
    if level in ("1", "slice1"):
        return solve_slice1(cfg)
    if level in ("2", "slice2"):
        return solve_slice2(cfg)
    if level in ("3", "slice3", "full"):
        return solve_slice3(cfg)
    raise ValueError(f"Unknown solver level: {level!r}")

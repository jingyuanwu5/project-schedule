"""
Command-line interface for the assessment timetable scheduler.

Usage:
    python -m schedule_app.cli --config data/sample_feasible.json
    python -m schedule_app.cli --config data/sample_feasible.json --out result.json --solver slice3

Exit codes:
    0 — OPTIMAL or FEASIBLE
    1 — argument / config / precheck error
    2 — INFEASIBLE or MODEL_INVALID
"""

from __future__ import annotations

import argparse
import json
import sys

from .io_json import ConfigError, load_config
from .solver.api import solve
from .solver.precheck import PrecheckError, precheck


def main() -> None:
    parser = argparse.ArgumentParser(description="Assessment timetable scheduler")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    parser.add_argument("--out",    default=None,  help="Write result JSON to this path")
    parser.add_argument(
        "--solver",
        default="slice3",
        choices=["slice1", "slice2", "slice3"],
        help="Solver level (default: slice3 = full weighted objective)",
    )
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (ConfigError, ValueError) as e:
        print(f"[ERROR] Config load failed: {e}", file=sys.stderr)
        sys.exit(1)

    errors, warnings = precheck(cfg)
    for w in warnings:
        print(f"[WARNING] {w}")
    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = solve(cfg, args.solver)
    except PrecheckError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Status:    {result.status}")
    if result.objective_value is not None:
        print(f"Objective: {result.objective_value}")
    if result.diagnostics:
        for d in result.diagnostics:
            print(f"[DIAG] {d}")
    if result.stats:
        print(f"Stats:     {result.stats}")
    print(f"Entries:   {len(result.entries)}")
    for entry in result.entries:
        print(f"  {entry.timeslot_id}  room={entry.room+1}  project={entry.project_id}"
              f"  panel={entry.panel_lecturer_ids}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"Result written to {args.out}")

    sys.exit(0 if result.status in ("OPTIMAL", "FEASIBLE") else 2)


if __name__ == "__main__":
    main()

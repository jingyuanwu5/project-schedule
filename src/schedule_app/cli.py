"""
Command-line interface for the 4YP assessment timetable scheduler.

Usage examples:
    python -m schedule_app.cli --config data/sample_feasible.json
    python -m schedule_app.cli --config data/sample_feasible.json --out result.json
    python -m schedule_app.cli --config data/sample_feasible.json --solver slice2

Exit codes:
    0  schedule produced (OPTIMAL or FEASIBLE)
    1  bad arguments, unreadable config, or precheck found blocking errors
    2  solver returned INFEASIBLE or MODEL_INVALID
"""

from __future__ import annotations

import argparse
import json
import sys

from schedule_app.io_json import ConfigError, load_config
from schedule_app.solver.api import solve
from schedule_app.solver.precheck import PrecheckError, precheck


def main() -> None:
    parser = argparse.ArgumentParser(
        description="4YP assessment timetable scheduler — command-line mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  schedule-cli --config data/sample_feasible.json\n"
            "  schedule-cli --config cfg.json --out result.json --solver slice3\n"
        ),
    )
    parser.add_argument("--config", required=True, metavar="FILE",
                        help="path to the schedule config JSON")
    parser.add_argument("--out",    default=None,  metavar="FILE",
                        help="write result JSON to this path (optional)")
    parser.add_argument(
        "--solver",
        default="slice3",
        choices=["slice1", "slice2", "slice3"],
        help=(
            "solver level to use  "
            "[slice1 = room assignment only, "
            "slice2 = + panel/availability, "
            "slice3 = full weighted objective]  "
            "(default: slice3)"
        ),
    )
    args = parser.parse_args()

    # ── 1. load config ────────────────────────────────────────────────────────
    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    except (ConfigError, ValueError) as e:
        print(f"[ERROR] Could not load config: {e}", file=sys.stderr)
        sys.exit(1)

    # ── 2. precheck — catch obvious infeasibility before handing to solver ────
    try:
        errors, warnings = precheck(cfg)
    except Exception as e:
        print(f"[ERROR] Precheck crashed unexpectedly: {e}", file=sys.stderr)
        sys.exit(1)

    for w in warnings:
        print(f"[WARNING] {w}")

    if errors:
        print(
            f"\n[ERROR] {len(errors)} precheck error(s) found — "
            "schedule cannot be produced until these are fixed:\n",
            file=sys.stderr,
        )
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}", file=sys.stderr)
        sys.exit(1)

    # ── 3. solve ──────────────────────────────────────────────────────────────
    print(f"Running solver ({args.solver})…")
    try:
        result = solve(cfg, args.solver)
    except PrecheckError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Solver crashed: {e}", file=sys.stderr)
        sys.exit(1)

    # ── 4. print summary ──────────────────────────────────────────────────────
    print(f"\nStatus    : {result.status}")
    if result.objective_value is not None:
        print(f"Objective : {result.objective_value}")
    if result.stats:
        for k, v in result.stats.items():
            print(f"  {k}: {v}")
    if result.diagnostics:
        for d in result.diagnostics:
            print(f"[DIAG] {d}")

    print(f"\nSchedule ({len(result.entries)} entries):")
    slot_map  = {s.id: s   for s in cfg.timeslots}
    proj_map  = {p.id: p.title for p in cfg.projects}
    lec_map   = {lec.id: lec.name  for lec in cfg.lecturers}
    slot_order = {s.id: i for i, s in enumerate(cfg.timeslots)}

    sorted_entries = sorted(
        result.entries,
        key=lambda e: (slot_order.get(e.timeslot_id, 999), e.room),
    )
    for entry in sorted_entries:
        slot = slot_map.get(entry.timeslot_id)
        time_str = f"{slot.date} {slot.start}–{slot.end}" if slot else entry.timeslot_id
        panel    = ", ".join(lec_map.get(lid, lid) for lid in entry.panel_lecturer_ids)
        proj     = proj_map.get(entry.project_id, entry.project_id)
        print(f"  [{time_str}  room {entry.room + 1}]  {proj}  |  {panel}")

    # ── 5. write output file (optional) ──────────────────────────────────────
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\nResult written to: {args.out}")

    sys.exit(0 if result.status in ("OPTIMAL", "FEASIBLE") else 2)


if __name__ == "__main__":
    main()

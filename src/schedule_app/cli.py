# cli.py - command line version of the scheduler (useful for testing without the GUI)
# usage:
#   python -m schedule_app.cli --config data/sample_feasible.json
#   python -m schedule_app.cli --config data/sample_feasible.json --out result.json --solver slice2

import argparse
import json
import sys

from schedule_app.io_json import ConfigError, load_config
from schedule_app.solver.api import solve
from schedule_app.solver.precheck import PrecheckError, precheck


def main():
    parser = argparse.ArgumentParser(description="4YP assessment timetable scheduler (CLI)")
    parser.add_argument("--config",  required=True, help="path to schedule JSON config file")
    parser.add_argument("--out",     default=None,  help="save result to this JSON file")
    parser.add_argument("--solver",  default="slice3",
                        choices=["slice1", "slice2", "slice3"],
                        help="which solver level to use (default: slice3)")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except (ConfigError, FileNotFoundError) as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    errors, warnings = precheck(cfg)
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = solve(cfg, args.solver)
    except PrecheckError as e:
        print(f"Precheck failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Status: {result.status}")
    if result.objective_value is not None:
        print(f"Objective: {result.objective_value}")
    if result.stats:
        print(f"Stats: {result.stats}")

    if result.entries:
        print(f"\n{len(result.entries)} assessment(s) scheduled:\n")
        slot_map  = {s.id: s   for s in cfg.timeslots}
        proj_map  = {p.id: p.title for p in cfg.projects}
        lec_map   = {l.id: l.name  for l in cfg.lecturers}
        slot_order = {s.id: i for i, s in enumerate(cfg.timeslots)}

        sorted_entries = sorted(result.entries, key=lambda e: slot_order.get(e.timeslot_id, 999))
        for entry in sorted_entries:
            slot  = slot_map.get(entry.timeslot_id)
            time  = f"{slot.date} {slot.start}-{slot.end}" if slot else entry.timeslot_id
            panel = ", ".join(lec_map.get(lid, lid) for lid in entry.panel_lecturer_ids)
            proj  = proj_map.get(entry.project_id, entry.project_id)
            print(f"  {time}  Room {entry.room + 1}  |  {proj}  |  [{panel}]")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"\nResult saved to {args.out}")

    if result.status not in ("OPTIMAL", "FEASIBLE"):
        sys.exit(2)


if __name__ == "__main__":
    main()

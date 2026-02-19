from __future__ import annotations

import argparse, json
from pathlib import Path

from schedule_app.io_json import ConfigError, load_config
from schedule_app.solver.api import solve
from schedule_app.solver.precheck import PrecheckError, precheck


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Assessment timetable scheduler (OR-Tools CP-SAT).")
    p.add_argument("--config",  required=True, help="Input config JSON path.")
    p.add_argument("--solver",  default="slice3", help="slice1 | slice2 | slice3")
    p.add_argument("--out",     default="", help="Optional output JSON path.")
    args = p.parse_args(argv)

    cfg = load_config(args.config)
    res = solve(cfg, level=args.solver)

    print(f"status={res.status}  objective={res.objective_value}")
    for d in res.diagnostics:
        print(f"  {d}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(res.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"Result written to: {out}")

    return 0 if res.status in ("OPTIMAL", "FEASIBLE") else 2


if __name__ == "__main__":
    raise SystemExit(main())
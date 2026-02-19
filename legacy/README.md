# Legacy / Archive Files

These files are preserved for reference and to show the development history,
but they are **not part of the main application**.

## scheduling_4yp.py

Early draft written while learning OR-Tools. Contains syntax errors
(`if status == ... or if status == ...` blocks that are not valid Python)
and does not implement the full set of assessment constraints.
Kept here as evidence of the initial exploration phase.

## demo.py

Concept-verification script. Demonstrates the core CP-SAT modelling patterns
(availability, conflicts, objective functions) that were later built into the
proper solver layer.

Two known issues:
1. Reads from `data/*.json` files that were not committed to the repository,
   so it cannot be run as-is.
2. The supervisor constraint was written as `model.add(y[p_supervisor] == 0)`,
   which forces the supervisor *out* of the panel — the opposite of the
   requirement. This bug is fixed in `src/schedule_app/solver/slice2.py` and
   `slice3.py` (corrected to `== 1`).

## What to use instead

The main application is in `src/schedule_app/`. Run it with:

    pip install -e .
    python main.py       # GUI
    python -m schedule_app.cli --config data/sample_feasible.json   # CLI

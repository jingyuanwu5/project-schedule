# 4YP Project Status Report
**Project:** Assessment Timetable Scheduler  
**Student:** Kyra (DCU, CSC — 4th Year Project)  
**Date:** February 2026  
**Supervisor:** [Supervisor Name]

---

## 1. Project Overview

This project delivers a desktop application that automates the scheduling of 4th-year project assessments at DCU. The system takes a set of lecturers, students, projects, and available timeslots as input, then uses constraint programming (Google OR-Tools CP-SAT) to produce a feasible — and ideally optimal — timetable that respects hard constraints (room capacity, panel size, supervisor availability) and minimises soft penalties (schedule compactness, workload imbalance, assessments during lunch).

The application is built entirely in Python and ships both a graphical desktop interface (tkinter) and a command-line interface.

---

## 2. Work Completed

### 2.1 Data Model (`models.py`)
All domain objects are implemented as Python dataclasses: `TimeSlot`, `Lecturer`, `Student`, `Project`, `Constraints`, and `Config`. The design uses a flat-entity pattern with ID references rather than nested objects — for example, a `Project` holds a list of `student_ids` rather than embedding `Student` objects directly. This was a specific requirement from earlier supervisor feedback.

### 2.2 JSON Configuration I/O (`io_json.py`)
The application can load a full schedule configuration from a JSON file and save it back after editing. The loader validates structure and converts raw dictionaries to typed dataclass instances. A `ConfigError` exception provides user-friendly error messages when the file is malformed.

### 2.3 Constraint Programming Solver (`solver/`)
The solver is implemented as three incremental "slices", each adding more constraints:

- **Slice 1** — assigns projects to timeslot–room pairs only (fastest; useful for testing feasibility quickly).
- **Slice 2** — adds panel assignment and lecturer availability constraints. Ensures each project is assessed by a panel of the required size, and that no lecturer is assigned to a slot they marked as unavailable.
- **Slice 3** — full model with a weighted soft-constraint objective. Minimises a weighted sum of: schedule span (compactness), workload imbalance across lecturers, and penalty for assessments placed in lunch slots. Weights are user-configurable.

Additional hard constraints enforced across all slices include: no lecturer in two rooms simultaneously, supervisor must be on the panel (optional toggle), and per-day assessment limits per lecturer.

A pre-solve checker (`precheck.py`) runs before the solver to catch obviously infeasible configurations (e.g. not enough available slots for the number of projects) and reports plain-English errors rather than a raw `INFEASIBLE` solver status.

### 2.4 Graphical User Interface (`ui_tk/`)
The GUI is a four-tab tkinter application:

- **Entities tab** — manage lecturers, students, projects, and timeslots. Includes a batch timeslot generator that creates a full day of slots given a date, start time, end time, and slot duration. All add/delete operations write directly to the in-memory config object.
- **Availability tab** — canvas-based grid showing lecturers as rows and timeslots as columns. Users click cells to toggle availability (green = available). Supports scroll on large grids.
- **Constraints tab** — spinboxes and checkboxes for all constraint parameters: number of rooms, panel size, supervisor requirement, soft-constraint weights, solver time limit, and number of CPU workers. Lunch slots are selected via a multi-select listbox — no JSON hand-editing required.
- **Run & Output tab** — solver level selector (Slice 1 / 2 / 3), a Run button, a results table sorted chronologically, a diagnostics pane, and Export JSON / Export CSV buttons. The CSV uses UTF-8 with BOM so it opens correctly in Excel.

The application starts with a welcome screen that guides users to create a new schedule or open an existing JSON file before any editing can begin. Keyboard shortcuts (Ctrl+N, Ctrl+O, Ctrl+S) are supported.

### 2.5 Command-Line Interface (`cli.py`)
A fully functional CLI allows the solver to be run without the GUI:

```
python -m schedule_app.cli --config data/sample_feasible.json --out result.json --solver slice3
```

The CLI runs the pre-solve checker and reports numbered errors before attempting to solve. Results are printed in a human-readable table and optionally written to a JSON file. Exit codes follow Unix conventions (0 = success, 1 = config error, 2 = infeasible).

### 2.6 Testing
Fifteen unit tests pass across three test modules:
- `test_io.py` — JSON load/save round-trip
- `test_precheck.py` — all precheck error and warning conditions
- `test_solver_slice1.py` — Slice 1 solver correctness on sample configs

```
15 passed in 1.37s
```

### 2.7 Developer Experience
- `pyrightconfig.json` and `.vscode/settings.json` configured so VS Code / Pylance resolves all imports without errors.
- All imports use absolute paths (`from schedule_app.models import ...`) so the package works correctly whether run via `python main.py`, `python -m schedule_app.ui_tk.app`, or the installed `schedule-gui` entry point.
- `pyproject.toml` defines both `schedule-gui` and `schedule-cli` as installable console scripts.

**Total codebase size: ~2,450 lines of Python across 18 source files.**

---

## 3. Challenges Encountered

**Import resolution in VS Code.** The project uses a `src/` layout (source code under `src/schedule_app/`) which is standard Python packaging practice but requires explicit configuration for Pylance to resolve imports. This was resolved by adding `python.analysis.extraPaths: ["src"]` to both `pyrightconfig.json` and `.vscode/settings.json`.

**GUI initialisation order.** On first launch, all tab panels have `self.cfg = None`. Every data-manipulation method checks this guard and returns early, meaning buttons appeared to do nothing if a config had not been loaded first. This was fixed by adding a welcome screen that clearly guides the user to either create a new schedule or open an existing JSON file before any editing begins, making the intended workflow obvious.

**Relative imports vs. absolute imports.** The project initially used relative imports (`from ..models import Config`) throughout the solver and UI modules, which caused `reportMissingImports` errors in Pylance and occasional runtime failures depending on how the application was launched. All imports were refactored to absolute (`from schedule_app.models import Config`).

**Solver output ordering.** The results table in the Run tab was initially sorted by timeslot ID string, which produced incorrect ordering when IDs were not lexicographically sequential (e.g. `TS10` sorts before `TS9`). This was fixed by sorting entries by the position of each timeslot in the `cfg.timeslots` list, which reflects the order the coordinator originally defined them.

---

## 4. Current Project Status

| Component | Status |
|---|---|
| Data model | Complete |
| JSON I/O | Complete |
| Solver — Slice 1 (room assignment) | Complete, tested |
| Solver — Slice 2 (panel + availability) | Complete |
| Solver — Slice 3 (weighted objective) | Complete |
| Pre-solve checker | Complete, tested |
| GUI — Entities tab | Complete |
| GUI — Availability tab | Complete |
| GUI — Constraints tab | Complete |
| GUI — Run & Output tab | Complete |
| CLI | Complete |
| Unit tests | 15 / 15 passing |
| VS Code / Pylance configuration | Complete |

---

## 5. Remaining Work

- **Slice 2 / Slice 3 solver tests** — unit tests currently cover only Slice 1. Adding tests for the more complex solver models would improve confidence in correctness under edge cases.
- **GUI integration tests** — the current tests cover only the non-GUI modules. Automated testing of the interface (e.g. using `pytest-tk` or manual test scripts) would strengthen the test suite.
- **User documentation / README** — the README has not yet been updated to reflect the current UI workflow and the new command-line options.
- **Packaging** — PyInstaller is listed as a dev dependency but a standalone executable has not yet been produced or tested. This would make distribution to coordinators easier.

---

## 6. Next Steps

1. Write Slice 2 and Slice 3 solver unit tests.
2. Update README with screenshots and a step-by-step usage guide.
3. Produce a PyInstaller build and verify it runs correctly on a clean machine.
4. Conduct end-to-end testing with a realistic DCU dataset (real room counts, lecturer availability, project numbers).

---

*Report prepared: February 2026*

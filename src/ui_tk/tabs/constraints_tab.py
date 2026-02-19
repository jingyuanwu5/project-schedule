"""
Constraints Tab — GUI for editing constraints.Constraints and its sub-fields.

All values are read from the Config on refresh() and written back on
write_back().  The tab intentionally mirrors the JSON structure so that
coordinators who open the JSON file directly see familiar field names.

ttk.Spinbox is used for integer fields.  It was added in Python 3.8.
Reference: Python docs — tkinter.ttk.Spinbox
https://docs.python.org/3/library/tkinter.ttk.html#spinbox
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from schedule_app.models import Config


class ConstraintsTab(ttk.Frame):

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.cfg: Optional[Config] = None
        self._vars: dict[str, tk.Variable] = {}
        self._build()

    def _build(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(padx=20, pady=16, fill="both", expand=True)

        # ── Basic ─────────────────────────────────────────────────────────────
        basic = ttk.LabelFrame(outer, text="Basic")
        basic.pack(fill="x", pady=(0, 10))
        self._int_row(basic, 0, "rooms",
                      "Assessment rooms (parallel sessions):",
                      from_=1, to=20)

        # ── Panel ─────────────────────────────────────────────────────────────
        panel = ttk.LabelFrame(outer, text="Panel")
        panel.pack(fill="x", pady=(0, 10))
        self._int_row(panel, 0, "panel_size",
                      "Lecturers per panel:", from_=1, to=10)
        self._bool_row(panel, 1, "must_include_supervisor",
                       "Supervisor must be in the panel")

        # ── Soft-constraint weights ───────────────────────────────────────────
        weights = ttk.LabelFrame(outer, text="Objective weights  (0 = ignore)")
        weights.pack(fill="x", pady=(0, 10))
        self._int_row(weights, 0, "w_span",
                      "Minimise schedule span:", from_=0, to=100)
        self._int_row(weights, 1, "w_workload",
                      "Balance lecturer workload:", from_=0, to=100)
        self._int_row(weights, 2, "w_lunch",
                      "Avoid lunch slots:", from_=0, to=100)

        # ── Solver parameters ─────────────────────────────────────────────────
        solver = ttk.LabelFrame(outer, text="Solver")
        solver.pack(fill="x", pady=(0, 10))
        self._float_row(solver, 0, "max_time",
                        "Time limit (seconds):")
        self._int_row(solver, 1, "num_workers",
                      "Search workers:", from_=1, to=32)

        # ── Info label ────────────────────────────────────────────────────────
        ttk.Label(
            outer,
            text="Lunch slot IDs are set directly in the JSON file "
                 "(constraints.lunch_slot_ids).",
            foreground="grey",
            font=("TkDefaultFont", 8),
        ).pack(anchor="w", pady=(4, 0))

    # ── widget helpers ────────────────────────────────────────────────────────

    def _int_row(self, parent, row, key, label, from_=0, to=100) -> None:
        var = tk.IntVar(value=1)
        self._vars[key] = var
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        ttk.Spinbox(
            parent, from_=from_, to=to,
            textvariable=var, width=6,
        ).grid(row=row, column=1, sticky="w", padx=6)

    def _float_row(self, parent, row, key, label) -> None:
        var = tk.DoubleVar(value=10.0)
        self._vars[key] = var
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=10, pady=5
        )
        ttk.Entry(parent, textvariable=var, width=8).grid(
            row=row, column=1, sticky="w", padx=6
        )

    def _bool_row(self, parent, row, key, label) -> None:
        var = tk.BooleanVar(value=True)
        self._vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=10, pady=5
        )

    # ── public API ────────────────────────────────────────────────────────────

    def refresh(self, cfg: Config) -> None:
        """Populate widgets from config."""
        self.cfg = cfg
        c = cfg.constraints
        self._vars["rooms"].set(c.rooms)
        self._vars["panel_size"].set(c.panel_size)
        self._vars["must_include_supervisor"].set(c.must_include_supervisor)
        self._vars["w_span"].set(c.weights.span)
        self._vars["w_workload"].set(c.weights.workload_balance)
        self._vars["w_lunch"].set(c.weights.lunch)
        self._vars["max_time"].set(c.solver.max_time_in_seconds)
        self._vars["num_workers"].set(c.solver.num_search_workers)

    def write_back(self, cfg: Config) -> None:
        """Write widget values back to config before saving or solving."""
        c = cfg.constraints
        c.rooms                   = int(self._vars["rooms"].get())
        c.panel_size              = int(self._vars["panel_size"].get())
        c.must_include_supervisor = bool(self._vars["must_include_supervisor"].get())
        c.weights.span            = int(self._vars["w_span"].get())
        c.weights.workload_balance = int(self._vars["w_workload"].get())
        c.weights.lunch           = int(self._vars["w_lunch"].get())
        c.solver.max_time_in_seconds = float(self._vars["max_time"].get())
        c.solver.num_search_workers  = int(self._vars["num_workers"].get())
"""
Constraints Tab — GUI for editing all constraint fields.

Sections:
  1. Basic          rooms (Spinbox)
  2. Panel          panel_size, must_include_supervisor
  3. Lunch slots    multi-select Listbox (no more JSON hand-editing!)
  4. Weights        span, workload_balance, lunch (Spinboxes)
  5. Solver         max_time_in_seconds, num_workers

ttk.Spinbox is available from Python 3.7+.
This project targets Python 3.10+.
Reference: https://docs.python.org/3/library/tkinter.ttk.html

Lunch slot Listbox:
  This replaces the previous approach of requiring coordinators to manually
  edit lunch_slot_ids in the JSON file. Now coordinators can select lunch
  slots directly from the list of configured timeslots — directly addressing
  the supervisor requirement for a "user-friendly interface to capture
  constraints."
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ...models import Config

_PAD = {"padx": 12, "pady": 4}


class ConstraintsTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.cfg: Optional[Config] = None
        self._build()

    # ── layout ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        canvas = tk.Canvas(self)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._build_basic(inner)
        self._build_panel(inner)
        self._build_lunch(inner)
        self._build_weights(inner)
        self._build_solver(inner)

    def _section(self, parent: tk.Widget, title: str) -> ttk.LabelFrame:
        lf = ttk.LabelFrame(parent, text=title, padding=8)
        lf.pack(fill="x", padx=12, pady=6)
        return lf

    def _labeled_spinbox(
        self, parent: tk.Widget, label: str, var: tk.StringVar,
        row: int, from_: int, to: int
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", **_PAD)
        ttk.Spinbox(parent, textvariable=var, from_=from_, to=to, width=8).grid(
            row=row, column=1, sticky="w", **_PAD
        )

    # ── sections ─────────────────────────────────────────────────────────────

    def _build_basic(self, parent: tk.Widget) -> None:
        lf = self._section(parent, "Basic")
        self._rooms = tk.StringVar(value="1")
        self._labeled_spinbox(lf, "Rooms:", self._rooms, 0, from_=1, to=20)

    def _build_panel(self, parent: tk.Widget) -> None:
        lf = self._section(parent, "Panel")
        self._panel_size = tk.StringVar(value="2")
        self._must_sup   = tk.BooleanVar(value=True)
        self._labeled_spinbox(lf, "Panel size:", self._panel_size, 0, from_=1, to=10)
        ttk.Checkbutton(
            lf,
            text="Must include supervisor",
            variable=self._must_sup,
        ).grid(row=1, column=0, columnspan=2, sticky="w", **_PAD)

    def _build_lunch(self, parent: tk.Widget) -> None:
        lf = self._section(parent, "Lunch slots  (select slots to penalise)")
        ttk.Label(
            lf,
            text="Hold Ctrl / Cmd to select multiple.",
            font=("TkDefaultFont", 8),
            foreground="#555",
        ).pack(anchor="w")

        frm = ttk.Frame(lf)
        frm.pack(fill="x")
        self._lunch_lb = tk.Listbox(
            frm,
            selectmode=tk.MULTIPLE,
            height=6,
            exportselection=False,
        )
        sb = ttk.Scrollbar(frm, orient="vertical", command=self._lunch_lb.yview)
        self._lunch_lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._lunch_lb.pack(side="left", fill="x", expand=True)

    def _build_weights(self, parent: tk.Widget) -> None:
        lf = self._section(parent, "Objective weights  (0 = ignore)")
        self._w_span     = tk.StringVar(value="1")
        self._w_workload = tk.StringVar(value="10")
        self._w_lunch    = tk.StringVar(value="3")
        self._labeled_spinbox(lf, "Span (compact schedule):",   self._w_span,     0, 0, 100)
        self._labeled_spinbox(lf, "Workload balance:",           self._w_workload, 1, 0, 100)
        self._labeled_spinbox(lf, "Lunch avoidance:",            self._w_lunch,    2, 0, 100)

    def _build_solver(self, parent: tk.Widget) -> None:
        lf = self._section(parent, "Solver")
        self._max_time   = tk.StringVar(value="10.0")
        self._num_workers = tk.StringVar(value="0")

        ttk.Label(lf, text="Time limit (seconds):").grid(row=0, column=0, sticky="w", **_PAD)
        ttk.Entry(lf, textvariable=self._max_time, width=10).grid(
            row=0, column=1, sticky="w", **_PAD
        )

        self._labeled_spinbox(lf, "Workers (0 = auto):", self._num_workers, 1, from_=0, to=32)
        ttk.Label(
            lf,
            text="0 = use all available CPU cores  (OR-Tools num_workers default)",
            font=("TkDefaultFont", 8),
            foreground="#555",
        ).grid(row=2, column=0, columnspan=2, sticky="w", **_PAD)

    # ── public API ────────────────────────────────────────────────────────────

    def refresh(self, cfg: Config) -> None:
        self.cfg = cfg
        c = cfg.constraints

        self._rooms.set(str(c.rooms))
        self._panel_size.set(str(c.panel_size))
        self._must_sup.set(c.must_include_supervisor)
        self._w_span.set(str(c.weights.span))
        self._w_workload.set(str(c.weights.workload_balance))
        self._w_lunch.set(str(c.weights.lunch))
        self._max_time.set(str(c.solver.max_time_in_seconds))
        self._num_workers.set(str(c.solver.num_workers))

        # Populate lunch Listbox with current timeslots
        self._lunch_lb.delete(0, tk.END)
        for slot in cfg.timeslots:
            label = slot.label or f"{slot.date} {slot.start}"
            self._lunch_lb.insert(tk.END, f"{slot.id}  {label}")

        # Re-select previously chosen lunch slots
        lunch_set = set(c.lunch_slot_ids)
        for i, slot in enumerate(cfg.timeslots):
            if slot.id in lunch_set:
                self._lunch_lb.selection_set(i)

    def write_back(self, cfg: Config) -> None:
        """Write widget values back to the Config object (called before save/solve)."""
        c = cfg.constraints
        try:
            c.rooms      = max(1, int(self._rooms.get()))
            c.panel_size = max(1, int(self._panel_size.get()))
        except ValueError:
            pass
        c.must_include_supervisor = self._must_sup.get()

        # Collect selected lunch slots
        sel_indices = self._lunch_lb.curselection()
        c.lunch_slot_ids = [cfg.timeslots[i].id for i in sel_indices
                            if i < len(cfg.timeslots)]

        try:
            c.weights.span             = max(0, int(self._w_span.get()))
            c.weights.workload_balance = max(0, int(self._w_workload.get()))
            c.weights.lunch            = max(0, int(self._w_lunch.get()))
        except ValueError:
            pass

        try:
            c.solver.max_time_in_seconds = float(self._max_time.get())
        except ValueError:
            pass
        try:
            c.solver.num_workers = max(0, int(self._num_workers.get()))
        except ValueError:
            pass

# constraints_tab.py - edit solver parameters and constraints through the GUI
# so the user doesn't have to manually edit the JSON file
#
# layout: scrollable frame containing labelled sections
# each section is a LabelFrame (ttk doesn't have one, using tk.LabelFrame)
# TODO: might be nice to add validation highlighting when values are out of range

import tkinter as tk
from tkinter import ttk
from typing import Optional

from schedule_app.models import Config


class ConstraintsTab(ttk.Frame):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.cfg: Optional[Config] = None
        self._build()

    def _build(self) -> None:
        # wrap everything in a scrollable canvas
        # reference: https://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-group-of-widgets-in-tkinter
        canvas = tk.Canvas(self)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        self._build_basic(inner)
        self._build_panel(inner)
        self._build_lunch(inner)
        self._build_weights(inner)
        self._build_solver(inner)

    def _section(self, parent, title):
        lf = ttk.LabelFrame(parent, text=title, padding=8)
        lf.pack(fill="x", padx=12, pady=6)
        return lf

    def _spinbox_row(self, parent, label, var, row, from_, to, hint=""):
        # helper to add a label + spinbox + optional hint on one row
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=12, pady=4)
        ttk.Spinbox(parent, textvariable=var, from_=from_, to=to, width=8).grid(
            row=row, column=1, sticky="w", padx=12, pady=4
        )
        if hint:
            ttk.Label(
                parent, text=hint,
                font=("TkDefaultFont", 8), foreground="#666",
            ).grid(row=row, column=2, sticky="w", padx=4)

    def _build_basic(self, parent) -> None:
        lf = self._section(parent, "Basic")
        self._rooms = tk.StringVar(value="1")
        self._spinbox_row(lf, "Rooms:", self._rooms, 0, from_=1, to=20,
                          hint="Number of rooms available at the same time")

    def _build_panel(self, parent) -> None:
        lf = self._section(parent, "Panel")
        self._panel_size = tk.StringVar(value="2")
        self._must_sup   = tk.BooleanVar(value=True)
        self._spinbox_row(lf, "Panel size:", self._panel_size, 0, from_=1, to=10,
                          hint="How many lecturers on each panel")
        ttk.Checkbutton(
            lf,
            text="Supervisor must be on the panel",
            variable=self._must_sup,
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=4)

    def _build_lunch(self, parent) -> None:
        lf = self._section(parent, "Lunch slots")
        ttk.Label(
            lf,
            text="Select slots to mark as lunch (hold Ctrl to select multiple).",
            font=("TkDefaultFont", 8), foreground="#555",
        ).pack(anchor="w")
        ttk.Label(
            lf,
            text="Tip: add your timeslots in the Entities tab first.",
            font=("TkDefaultFont", 8), foreground="#999",
        ).pack(anchor="w", pady=(0, 4))

        frm = ttk.Frame(lf)
        frm.pack(fill="x", pady=(4, 0))
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

    def _build_weights(self, parent) -> None:
        lf = self._section(parent, "Objective weights  (set to 0 to disable)")
        self._w_span     = tk.StringVar(value="1")
        self._w_workload = tk.StringVar(value="10")
        self._w_lunch    = tk.StringVar(value="3")
        self._spinbox_row(lf, "Compact schedule:",  self._w_span,     0, 0, 100,
                          hint="Minimize time between first and last assessment")
        self._spinbox_row(lf, "Workload balance:",   self._w_workload, 1, 0, 100,
                          hint="Try to give lecturers similar number of panels")
        self._spinbox_row(lf, "Avoid lunch slots:",  self._w_lunch,    2, 0, 100,
                          hint="How hard to avoid scheduling in lunch slots")

    def _build_solver(self, parent) -> None:
        lf = self._section(parent, "Solver settings")
        self._max_time    = tk.StringVar(value="10.0")
        self._num_workers = tk.StringVar(value="0")

        ttk.Label(lf, text="Time limit (s):").grid(row=0, column=0, sticky="w", padx=12, pady=4)
        ttk.Entry(lf, textvariable=self._max_time, width=10).grid(
            row=0, column=1, sticky="w", padx=12, pady=4
        )
        ttk.Label(
            lf, text="Stop after this many seconds and return best result found",
            font=("TkDefaultFont", 8), foreground="#666",
        ).grid(row=0, column=2, sticky="w", padx=4)

        self._spinbox_row(lf, "Workers:", self._num_workers, 1, from_=0, to=32)
        ttk.Label(
            lf,
            text="0 = use all CPU cores  |  1 = single thread (same result every time)",
            font=("TkDefaultFont", 8), foreground="#666",
        ).grid(row=1, column=2, sticky="w", padx=4)

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

        # rebuild the lunch slot listbox
        self._lunch_lb.delete(0, tk.END)
        lunch_set = set(c.lunch_slot_ids)
        for i, slot in enumerate(cfg.timeslots):
            label = slot.label or f"{slot.date} {slot.start}"
            self._lunch_lb.insert(tk.END, f"{slot.id}  {label}")
            if slot.id in lunch_set:
                self._lunch_lb.selection_set(i)

    def write_back(self, cfg: Config) -> None:
        # push widget values back into the config object
        # called before saving or running the solver
        c = cfg.constraints
        try:
            c.rooms      = max(1, int(self._rooms.get()))
            c.panel_size = max(1, int(self._panel_size.get()))
        except ValueError:
            pass  # keep old value if someone typed something weird
        c.must_include_supervisor = self._must_sup.get()

        sel = self._lunch_lb.curselection()
        c.lunch_slot_ids = [cfg.timeslots[i].id for i in sel if i < len(cfg.timeslots)]

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

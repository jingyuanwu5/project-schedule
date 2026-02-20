# run_tab.py - the tab where you actually run the solver and see results
# has a solver level picker, run button, results table, and export buttons
#
# solver levels:
#   slice1 - just assigns projects to rooms, ignores lecturers (fastest)
#   slice2 - adds panel assignment and lecturer availability
#   slice3 - full model with weighted objectives (default)

import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from schedule_app.models import Config
from schedule_app.solver.result import SolveResult

# colours for the status label
_STATUS_COLOURS = {
    "OPTIMAL":       "#2e7d32",
    "FEASIBLE":      "#1565c0",
    "INFEASIBLE":    "#c62828",
    "MODEL_INVALID": "#c62828",
    "UNKNOWN":       "#555555",
}

_SOLVER_LEVELS = [
    ("slice3", "Slice 3 — full weighted objective (recommended)"),
    ("slice2", "Slice 2 — panel + availability only"),
    ("slice1", "Slice 1 — room assignment only (fastest)"),
]


class RunTab(ttk.Frame):
    def __init__(self, parent, on_run: Callable[[], None]) -> None:
        super().__init__(parent)
        self._on_run = on_run
        self._result: Optional[SolveResult] = None
        self._cfg:    Optional[Config] = None
        self._build()

    def get_solver_level(self) -> str:
        # translate the combobox display string back to the key (slice1/slice2/slice3)
        display = self._solver_var.get()
        return self._level_map.get(display, "slice3")

    def _build(self) -> None:
        # top bar: solver picker, run button, status
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Solver level:").pack(side="left")
        self._solver_var = tk.StringVar(value="slice3")
        solver_cb = ttk.Combobox(
            top,
            textvariable=self._solver_var,
            values=[label for _, label in _SOLVER_LEVELS],
            state="readonly",
            width=44,
        )
        solver_cb.pack(side="left", padx=(4, 16))
        self._level_map = {label: key for key, label in _SOLVER_LEVELS}
        self._level_display = {key: label for key, label in _SOLVER_LEVELS}
        solver_cb.set(self._level_display["slice3"])

        self._run_btn = ttk.Button(top, text="Run", command=self._on_run, width=10)
        self._run_btn.pack(side="left", padx=(0, 16))

        self._status_var = tk.StringVar(value="No result yet")
        ttk.Label(
            top,
            textvariable=self._status_var,
            font=("TkDefaultFont", 11, "bold"),
        ).pack(side="left")

        # results table
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=8)

        cols    = ("slot", "date", "time", "room", "project", "panel")
        widths  = (80, 100, 90, 60, 200, 260)
        headers = ("Slot ID", "Date", "Time", "Room", "Project", "Panel")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        for col, w, h in zip(cols, widths, headers):
            self.tree.heading(col, text=h)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(frm, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # diagnostics text box (shows warnings and error messages from solver)
        ttk.Label(self, text="Diagnostics:").pack(anchor="w", padx=8)
        self._diag = tk.Text(
            self, height=5, state="disabled",
            foreground="#c62828", font=("TkDefaultFont", 9)
        )
        self._diag.pack(fill="x", padx=8, pady=4)

        # export buttons
        btn_row = ttk.Frame(self, padding=4)
        btn_row.pack(anchor="w", padx=8)
        ttk.Button(btn_row, text="Export JSON…", command=self._export_json).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Export CSV…",  command=self._export_csv).pack(side="left")

    def show_result(self, result: SolveResult, cfg: Config) -> None:
        self._result = result
        self._cfg    = cfg

        obj_str = f"  (obj={result.objective_value})" if result.objective_value is not None else ""
        self._status_var.set(f"Status: {result.status}{obj_str}")

        self._diag.configure(state="normal")
        self._diag.delete("1.0", tk.END)
        if result.diagnostics:
            self._diag.insert(tk.END, "\n".join(result.diagnostics))
        self._diag.configure(state="disabled")

        self.tree.delete(*self.tree.get_children())
        if not result.entries:
            return

        # sort by timeslot position (not string ID) so table reads chronologically
        slot_order = {s.id: i for i, s in enumerate(cfg.timeslots)}
        slot_map   = {s.id: s for s in cfg.timeslots}
        proj_map   = {p.id: p.title for p in cfg.projects}
        lec_map    = {l.id: l.name for l in cfg.lecturers}

        sorted_entries = sorted(
            result.entries,
            key=lambda e: (slot_order.get(e.timeslot_id, 999), e.room),
        )

        for entry in sorted_entries:
            slot = slot_map.get(entry.timeslot_id)
            panel_names = ", ".join(lec_map.get(lid, lid) for lid in entry.panel_lecturer_ids)
            self.tree.insert("", "end", values=(
                entry.timeslot_id,
                slot.date  if slot else "",
                f"{slot.start}-{slot.end}" if slot else "",
                entry.room + 1,
                proj_map.get(entry.project_id, entry.project_id),
                panel_names,
            ))

        if result.status == "INFEASIBLE":
            messagebox.showwarning(
                "No schedule found",
                "The solver could not find a valid schedule.\n\n"
                "Things to try:\n"
                "  - Add more timeslots or rooms\n"
                "  - Mark more lecturer availability\n"
                "  - Reduce the panel size\n"
                "  - Check the diagnostics box for specific errors",
            )

    def _export_json(self) -> None:
        if not self._result:
            messagebox.showinfo("No result", "Run the solver first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save result JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._result.to_dict(), f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Saved", f"Saved to {path}")

    def _export_csv(self) -> None:
        if not self._result or not self._cfg:
            messagebox.showinfo("No result", "Run the solver first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save result CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path: return

        slot_order = {s.id: i for i, s in enumerate(self._cfg.timeslots)}
        slot_map   = {s.id: s for s in self._cfg.timeslots}
        proj_map   = {p.id: p.title for p in self._cfg.projects}
        lec_map    = {l.id: l.name for l in self._cfg.lecturers}
        sorted_entries = sorted(
            self._result.entries,
            key=lambda e: (slot_order.get(e.timeslot_id, 999), e.room),
        )

        # utf-8-sig adds a BOM so Excel opens it correctly without encoding issues
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Slot ID", "Date", "Start", "End", "Room",
                        "Project ID", "Project Title", "Panel"])
            for entry in sorted_entries:
                slot = slot_map.get(entry.timeslot_id)
                w.writerow([
                    entry.timeslot_id,
                    slot.date  if slot else "",
                    slot.start if slot else "",
                    slot.end   if slot else "",
                    entry.room + 1,
                    entry.project_id,
                    proj_map.get(entry.project_id, ""),
                    "; ".join(lec_map.get(lid, lid) for lid in entry.panel_lecturer_ids),
                ])
        messagebox.showinfo("Saved", f"CSV saved to {path}")

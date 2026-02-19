"""
Run & Output Tab — trigger solver, display results, export.

The Treeview rows are sorted by timeslot_id so the output reads
chronologically top-to-bottom.

CSV export uses utf-8-sig (BOM variant) so that Excel on Windows opens
the file without needing an explicit encoding selection.

Reference: Python docs — csv
https://docs.python.org/3/library/csv.html
"""

from __future__ import annotations

import csv
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections.abc import Callable
from typing import Optional

from schedule_app.models import Config
from schedule_app.solver.result import SolveResult


class RunTab(ttk.Frame):

    def __init__(self, parent: tk.Widget, on_run: Callable[[], None]) -> None:
        super().__init__(parent)
        self._on_run     = on_run
        self._last_result: Optional[SolveResult] = None
        self.cfg         = None
        self._build()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=12, pady=10)

        self._run_btn = ttk.Button(
            top,
            text="▶  Produce assessment timetable",
            command=self._do_run,
        )
        self._run_btn.pack(side="left")

        ttk.Button(top, text="Export JSON…", command=self._export_json).pack(
            side="left", padx=8
        )
        ttk.Button(top, text="Export CSV…",  command=self._export_csv).pack(
            side="left"
        )

        self._status_var = tk.StringVar(value="")
        ttk.Label(top, textvariable=self._status_var).pack(side="left", padx=16)

        # Diagnostics text (shown when there are errors or warnings)
        self._diag_text = tk.Text(
            self, height=3, state="disabled",
            foreground="#a00000", font=("TkFixedFont", 9),
        )
        self._diag_text.pack(fill="x", padx=12, pady=(0, 4))

        # Result table
        cols = ("timeslot", "room", "project", "panel")
        self._tree = ttk.Treeview(self, columns=cols, show="headings")
        for c, w in [("timeslot", 210), ("room", 55), ("project", 120), ("panel", 380)]:
            self._tree.heading(c, text=c.capitalize())
            self._tree.column(c, width=w)

        sb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=4)

    def _do_run(self) -> None:
        self._run_btn.configure(state="disabled", text="⏳  Solving…")
        self.update()
        try:
            self._on_run()
        finally:
            self._run_btn.configure(
                state="normal", text="▶  Produce assessment timetable"
            )

    def show_result(self, result: SolveResult, cfg) -> None:
        self._last_result = result
        self.cfg          = cfg

        ok = result.status in ("OPTIMAL", "FEASIBLE")
        self._status_var.set(
            f"Status: {result.status}   objective: {result.objective_value}"
        )

        self._diag_text.configure(state="normal")
        self._diag_text.delete("1.0", "end")
        if result.diagnostics:
            self._diag_text.insert("end", "\n".join(result.diagnostics))
        self._diag_text.configure(state="disabled")

        self._tree.delete(*self._tree.get_children())
        if not ok:
            messagebox.showwarning(
                "No solution",
                "The solver could not find a valid timetable.\n\n"
                "Suggestions:\n"
                "  • Add more timeslots or rooms\n"
                "  • Mark more slots as available for lecturers\n"
                "  • Reduce panel_size",
            )
            return

        slot_label = {
            s.id: (s.label or f"{s.date} {s.start}–{s.end}")
            for s in cfg.timeslots
        }
        for e in sorted(result.entries, key=lambda e: e.timeslot_id):
            self._tree.insert("", "end", values=(
                slot_label.get(e.timeslot_id, e.timeslot_id),
                e.room,
                e.project_id,
                ", ".join(e.panel_lecturer_ids),
            ))

    def clear(self) -> None:
        self._last_result = None
        self._status_var.set("")
        self._diag_text.configure(state="normal")
        self._diag_text.delete("1.0", "end")
        self._diag_text.configure(state="disabled")
        self._tree.delete(*self._tree.get_children())

    # ── export ────────────────────────────────────────────────────────────────

    def _export_json(self) -> None:
        if not self._last_result or not self._last_result.entries:
            messagebox.showinfo("Nothing to export", "Run the solver first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")]
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._last_result.to_dict(), f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Exported", f"Saved: {path}")

    def _export_csv(self) -> None:
        if not self._last_result or not self._last_result.entries:
            messagebox.showinfo("Nothing to export", "Run the solver first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        # utf-8-sig writes a BOM so Excel on Windows auto-detects encoding
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Timeslot", "Room", "Project ID", "Panel"])
            for e in sorted(self._last_result.entries, key=lambda e: e.timeslot_id):
                writer.writerow([
                    e.timeslot_id, e.room,
                    e.project_id,
                    "; ".join(e.panel_lecturer_ids),
                ])
        messagebox.showinfo("Exported", f"Saved: {path}")
"""
Run & Output Tab — trigger the solver and display results.

Key fix from review:
  Results are sorted by the position of each timeslot in cfg.timeslots
  (i.e. the order the coordinator defined them), NOT by timeslot_id string.
  This ensures the output always shows chronological order regardless of
  whether the IDs are TS1/TS2 or Mon-09:00 or anything else.

CSV export uses utf-8-sig (BOM) encoding so Excel opens it correctly
without needing to specify the encoding manually.
Reference: Python csv docs — https://docs.python.org/3/library/csv.html
"""

from __future__ import annotations

import csv
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from schedule_app.models import Config
from schedule_app.solver.result import SolveResult

_STATUS_COLOURS = {
    "OPTIMAL":       "#2e7d32",
    "FEASIBLE":      "#1565c0",
    "INFEASIBLE":    "#c62828",
    "MODEL_INVALID": "#c62828",
    "UNKNOWN":       "#555555",
}


class RunTab(ttk.Frame):
    def __init__(self, parent: tk.Widget, on_run: Callable[[], None]) -> None:
        super().__init__(parent)
        self._on_run    = on_run
        self._result:   Optional[SolveResult] = None
        self._cfg:      Optional[Config]       = None
        self._build()

    def _build(self) -> None:
        # ── top: run button + status ──────────────────────────────────────────
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        self._run_btn = ttk.Button(
            top,
            text="▶  Produce assessment timetable",
            command=self._on_run,
            width=36,
        )
        self._run_btn.pack(side="left")

        self._status_var = tk.StringVar(value="No result yet")
        ttk.Label(top, textvariable=self._status_var, font=("TkDefaultFont", 11, "bold")).pack(
            side="left", padx=16
        )

        # ── middle: results treeview ───────────────────────────────────────────
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=8)

        cols = ("slot", "date", "time", "room", "project", "panel")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=14)
        widths    = (80, 100, 90, 60, 200, 260)
        headers   = ("Slot ID", "Date", "Time", "Room", "Project", "Panel")
        for col, w, h in zip(cols, widths, headers):
            self.tree.heading(col, text=h)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(frm, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frm, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # ── diagnostics ────────────────────────────────────────────────────────
        ttk.Label(self, text="Diagnostics / warnings:").pack(anchor="w", padx=8)
        self._diag = tk.Text(self, height=5, state="disabled",
                             foreground="#c62828", font=("TkDefaultFont", 9))
        self._diag.pack(fill="x", padx=8, pady=4)

        # ── export buttons ─────────────────────────────────────────────────────
        btn_row = ttk.Frame(self, padding=4)
        btn_row.pack(anchor="w", padx=8)
        ttk.Button(btn_row, text="Export JSON…", command=self._export_json).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Export CSV…",  command=self._export_csv).pack(side="left")

    # ── public API ─────────────────────────────────────────────────────────────

    def show_result(self, result: SolveResult, cfg: Config) -> None:
        self._result = result
        self._cfg    = cfg
        colour = _STATUS_COLOURS.get(result.status, "#555")
        obj_str = f"  (obj={result.objective_value})" if result.objective_value is not None else ""
        self._status_var.set(f"Status: {result.status}{obj_str}")
        self._status_var._label_widget = None  # type: ignore[attr-defined]

        # Find the label widget that shows the status and recolour it
        for widget in self.winfo_children():
            for child in widget.winfo_children():
                if isinstance(child, ttk.Label) and "Status:" in (child.cget("textvariable") or ""):
                    child.configure(foreground=colour)

        # Diagnostics
        self._diag.configure(state="normal")
        self._diag.delete("1.0", tk.END)
        if result.diagnostics:
            self._diag.insert(tk.END, "\n".join(result.diagnostics))
        self._diag.configure(state="disabled")

        # Results table
        self.tree.delete(*self.tree.get_children())
        if not result.entries: return

        # Build timeslot index for chronological sorting (key fix from review)
        slot_order = {s.id: i for i, s in enumerate(cfg.timeslots)}
        slot_map   = {s.id: s for s in cfg.timeslots}
        proj_map   = {p.id: p.title for p in cfg.projects}
        lec_map    = {l.id: l.name for l in cfg.lecturers}

        sorted_entries = sorted(
            result.entries,
            key=lambda e: (slot_order.get(e.timeslot_id, 999), e.room),
        )

        for entry in sorted_entries:
            slot       = slot_map.get(entry.timeslot_id)
            panel_names = ", ".join(lec_map.get(lid, lid) for lid in entry.panel_lecturer_ids)
            self.tree.insert("", "end", values=(
                entry.timeslot_id,
                slot.date  if slot else "",
                f"{slot.start}–{slot.end}" if slot else "",
                entry.room + 1,                  # display as 1-based
                proj_map.get(entry.project_id, entry.project_id),
                panel_names,
            ))

        if result.status == "INFEASIBLE":
            messagebox.showwarning(
                "No schedule found",
                "The solver could not find a feasible schedule.\n\n"
                "Suggestions:\n"
                "  • Add more timeslots or rooms\n"
                "  • Mark more slots as available for lecturers\n"
                "  • Reduce panel size\n"
                "  • Check diagnostics below for specific issues",
            )

    # ── export ─────────────────────────────────────────────────────────────────

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
        messagebox.showinfo("Saved", f"Result saved to {path}")

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
        lec_map    = {l.id: l.name  for l in self._cfg.lecturers}
        sorted_entries = sorted(
            self._result.entries,
            key=lambda e: (slot_order.get(e.timeslot_id, 999), e.room),
        )

        # utf-8-sig adds a BOM so Excel auto-detects UTF-8 encoding
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

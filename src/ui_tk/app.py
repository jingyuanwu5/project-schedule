"""
Main application window.

Keyboard shortcuts follow platform conventions:
  Ctrl+O  Open
  Ctrl+S  Save

Reference: Python docs — tkinter
https://docs.python.org/3/library/tkinter.html
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Optional

from schedule_app.io_json import ConfigError, load_config, save_config
from schedule_app.models import Config
from schedule_app.solver.api import solve
from schedule_app.solver.precheck import PrecheckError, precheck
from schedule_app.ui_tk.tabs import AvailabilityTab, ConstraintsTab, EntitiesTab, RunTab


class ScheduleApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()
        self.title("Assessment Timetable Scheduler")
        self.geometry("1150x720")
        self.minsize(900, 560)

        self.cfg:       Optional[Config] = None
        self.cfg_path:  Optional[Path]   = None

        self._build_menu()
        self._build_notebook()
        self._build_statusbar()

    # ── menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        mb = tk.Menu(self)

        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="Open JSON…",  command=self.on_open,    accelerator="Ctrl+O")
        fm.add_command(label="Save",         command=self.on_save,    accelerator="Ctrl+S")
        fm.add_command(label="Save As…",     command=self.on_save_as)
        fm.add_separator()
        fm.add_command(label="Exit",         command=self.destroy)
        mb.add_cascade(label="File", menu=fm)
        self.config(menu=mb)

        self.bind_all("<Control-o>", lambda _: self.on_open())
        self.bind_all("<Control-s>", lambda _: self.on_save())

    # ── notebook ──────────────────────────────────────────────────────────────

    def _build_notebook(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_entities    = EntitiesTab(nb, on_change=self._on_entities_change)
        self.tab_avail       = AvailabilityTab(nb)
        self.tab_constraints = ConstraintsTab(nb)
        self.tab_run         = RunTab(nb, on_run=self.on_run_solver)

        nb.add(self.tab_entities,    text="Entities")
        nb.add(self.tab_avail,       text="Availability")
        nb.add(self.tab_constraints, text="Constraints")
        nb.add(self.tab_run,         text="Run & Output")

    def _on_entities_change(self) -> None:
        """Called by EntitiesTab whenever lecturers/students/projects change."""
        if self.cfg:
            self.tab_avail.refresh(self.cfg)

    # ── status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self) -> None:
        self._status_var = tk.StringVar(value="No file loaded.")
        tk.Label(
            self, textvariable=self._status_var,
            relief=tk.SUNKEN, anchor="w", padx=6,
        ).pack(side="bottom", fill="x")

    def _set_status(self, msg: str) -> None:
        self._status_var.set(msg)

    # ── file operations ───────────────────────────────────────────────────────

    def on_open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open config JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            cfg = load_config(path)
        except (ConfigError, ValueError, OSError) as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        self.cfg      = cfg
        self.cfg_path = Path(path)

        errors, warnings = precheck(cfg)
        if warnings:
            messagebox.showwarning("Precheck warnings", "\n".join(warnings))
        if errors:
            messagebox.showerror("Precheck errors", "\n".join(errors))

        self.tab_entities.refresh(cfg)
        self.tab_avail.refresh(cfg)
        self.tab_constraints.refresh(cfg)
        self.tab_run.clear()
        self._set_status(f"Loaded: {self.cfg_path.name}")

    def on_save(self) -> None:
        if self.cfg is None:
            return
        if self.cfg_path is None:
            self.on_save_as()
            return
        self._flush_and_save(self.cfg_path)

    def on_save_as(self) -> None:
        if self.cfg is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save config JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        self.cfg_path = Path(path)
        self._flush_and_save(self.cfg_path)

    def _flush_and_save(self, path: Path) -> None:
        # Pull latest values from all tabs before writing
        self.tab_avail.flush_to_config()
        self.tab_constraints.write_back(self.cfg)
        try:
            save_config(self.cfg, path)
            self._set_status(f"Saved: {path.name}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    # ── solver ────────────────────────────────────────────────────────────────

    def on_run_solver(self) -> None:
        if self.cfg is None:
            messagebox.showinfo("No config", "Open a JSON file first.")
            return
        # Flush latest edits before solving
        self.tab_avail.flush_to_config()
        self.tab_constraints.write_back(self.cfg)
        try:
            result = solve(self.cfg, level="slice3")
        except PrecheckError as exc:
            messagebox.showerror("Precheck failed", str(exc))
            return
        except Exception as exc:
            messagebox.showerror("Solver error", str(exc))
            return
        self.tab_run.show_result(result, self.cfg)
        self._set_status(f"Solve complete — status: {result.status}")


def main() -> None:
    app = ScheduleApp()
    app.mainloop()


if __name__ == "__main__":
    main()
"""
Main application window.

Four tabs:
  1. Entities      — manage lecturers, students, projects, timeslots
  2. Availability  — canvas grid for lecturer × timeslot availability
  3. Constraints   — all constraint parameters (no JSON hand-editing needed)
  4. Run & Output  — solver execution and result display

Keyboard shortcuts:  Ctrl+O  open,  Ctrl+S  save
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from ..io_json import ConfigError, load_config, save_config
from ..models import Config
from ..solver.api import solve
from ..solver.precheck import PrecheckError, precheck
from .tabs import AvailabilityTab, ConstraintsTab, EntitiesTab, RunTab


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("4YP Assessment Timetable Scheduler")
        self.geometry("1100x700")
        self.minsize(800, 560)

        self._cfg:      Optional[Config] = None
        self._filepath: Optional[Path]   = None

        self._build_menu()
        self._build_tabs()
        self._build_statusbar()

    # ── menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        self.configure(menu=menu)

        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open…",     accelerator="Ctrl+O", command=self.on_open)
        file_menu.add_command(label="Save",       accelerator="Ctrl+S", command=self.on_save)
        file_menu.add_command(label="Save As…",                         command=self.on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",                              command=self.quit)

        self.bind_all("<Control-o>", lambda _: self.on_open())
        self.bind_all("<Control-s>", lambda _: self.on_save())

    # ── tabs ──────────────────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        self._nb = ttk.Notebook(self)
        self._nb.pack(fill="both", expand=True, padx=6, pady=6)

        self._entities    = EntitiesTab(self._nb, on_change=self._mark_dirty)
        self._availability = AvailabilityTab(self._nb)
        self._constraints  = ConstraintsTab(self._nb)
        self._run_tab      = RunTab(self._nb, on_run=self.on_run_solver)

        self._nb.add(self._entities,     text="Entities")
        self._nb.add(self._availability, text="Availability")
        self._nb.add(self._constraints,  text="Constraints")
        self._nb.add(self._run_tab,      text="Run & Output")

    def _build_statusbar(self) -> None:
        self._status_var = tk.StringVar(value="No file loaded. Use File → Open to start.")
        bar = ttk.Label(self, textvariable=self._status_var,
                        relief="sunken", anchor="w", padding=(6, 2))
        bar.pack(side="bottom", fill="x")

    # ── file operations ───────────────────────────────────────────────────────

    def on_open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path: return
        try:
            cfg = load_config(path)
        except (ConfigError, ValueError) as e:
            messagebox.showerror("Load error", str(e))
            return

        errors, warnings = precheck(cfg)
        if errors or warnings:
            msgs = []
            if errors:   msgs.append("Errors:\n"   + "\n".join(f"  • {e}" for e in errors))
            if warnings: msgs.append("Warnings:\n" + "\n".join(f"  • {w}" for w in warnings))
            messagebox.showwarning("Precheck results", "\n\n".join(msgs))

        self._cfg      = cfg
        self._filepath = Path(path)
        self._refresh_all_tabs()
        self._status_var.set(f"Loaded: {path}")

    def on_save(self) -> None:
        if self._cfg is None:
            messagebox.showinfo("Nothing to save", "Open a config file first.")
            return
        if self._filepath is None:
            self.on_save_as()
            return
        self._flush_all()
        try:
            save_config(self._cfg, self._filepath)
            self._status_var.set(f"Saved: {self._filepath}")
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def on_save_as(self) -> None:
        if self._cfg is None:
            messagebox.showinfo("Nothing to save", "Open a config file first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save config as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path: return
        self._filepath = Path(path)
        self.on_save()

    # ── solver ────────────────────────────────────────────────────────────────

    def on_run_solver(self) -> None:
        if self._cfg is None:
            messagebox.showinfo("No config", "Open a config file first.")
            return
        self._flush_all()

        errors, warnings = precheck(self._cfg)
        if errors:
            msgs = "\n".join(f"  • {e}" for e in errors)
            messagebox.showerror("Precheck failed", f"Cannot solve:\n{msgs}")
            return
        if warnings:
            msgs = "\n".join(f"  • {w}" for w in warnings)
            if not messagebox.askyesno("Warnings", f"{msgs}\n\nContinue anyway?"):
                return

        self._status_var.set("Solving… please wait")
        self.update()
        try:
            result = solve(self._cfg, "slice3")
        except PrecheckError as e:
            messagebox.showerror("Solve error", str(e))
            self._status_var.set("Solve failed.")
            return
        except Exception as e:
            messagebox.showerror("Unexpected error", str(e))
            self._status_var.set("Solve failed.")
            return

        self._run_tab.show_result(result, self._cfg)
        self._nb.select(3)   # switch to Run & Output tab
        self._status_var.set(f"Solve complete — {result.status}")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _refresh_all_tabs(self) -> None:
        if self._cfg is None: return
        self._entities.refresh(self._cfg)
        self._availability.refresh(self._cfg)
        self._constraints.refresh(self._cfg)

    def _flush_all(self) -> None:
        """Write all tab widget values back to self._cfg before save/solve."""
        if self._cfg is None: return
        self._availability.flush_to_config()
        self._constraints.write_back(self._cfg)

    def _mark_dirty(self) -> None:
        if self._filepath:
            self._status_var.set(f"Modified (unsaved): {self._filepath}")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

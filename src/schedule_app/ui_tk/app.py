"""
Main application window — 4YP Assessment Timetable Scheduler.

Tabs:
  1. Entities      — lecturers, students, projects, timeslots
  2. Availability  — click-to-toggle grid
  3. Constraints   — rooms, panel size, lunch slots, weights, solver params
  4. Run & Output  — run solver, view results, export

Start: File → New (blank config) or File → Open (existing JSON).
Without loading a config first, the Add/Delete buttons have nothing to
work on and will silently return — that's why the welcome screen matters.

Keyboard shortcuts:  Ctrl+N  new,  Ctrl+O  open,  Ctrl+S  save
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from schedule_app.io_json import ConfigError, load_config, save_config
from schedule_app.models import Config, Constraints
from schedule_app.solver.api import solve
from schedule_app.solver.precheck import PrecheckError, precheck
from schedule_app.ui_tk.tabs import AvailabilityTab, ConstraintsTab, EntitiesTab, RunTab


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("4YP Assessment Timetable Scheduler")
        self.geometry("1100x720")
        self.minsize(800, 560)

        self._cfg:      Optional[Config] = None
        self._filepath: Optional[Path]   = None

        self._build_menu()
        self._build_welcome()   # shown until a config is loaded/created
        self._build_tabs()
        self._build_statusbar()

        # start with the notebook hidden; welcome panel visible
        self._nb.pack_forget()

    # ── menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        self.configure(menu=menu)

        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New",      accelerator="Ctrl+N", command=self.on_new)
        file_menu.add_command(label="Open…",    accelerator="Ctrl+O", command=self.on_open)
        file_menu.add_separator()
        file_menu.add_command(label="Save",     accelerator="Ctrl+S", command=self.on_save)
        file_menu.add_command(label="Save As…",                        command=self.on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",                            command=self.quit)

        self.bind_all("<Control-n>", lambda _: self.on_new())
        self.bind_all("<Control-o>", lambda _: self.on_open())
        self.bind_all("<Control-s>", lambda _: self.on_save())

    # ── welcome screen ────────────────────────────────────────────────────────

    def _build_welcome(self) -> None:
        """Shown on startup before any config is loaded."""
        self._welcome = ttk.Frame(self)
        self._welcome.pack(fill="both", expand=True)

        # centre the content vertically
        ttk.Frame(self._welcome).pack(expand=True)   # spacer top

        inner = ttk.Frame(self._welcome)
        inner.pack()

        ttk.Label(
            inner,
            text="4YP Assessment Timetable Scheduler",
            font=("TkDefaultFont", 16, "bold"),
        ).pack(pady=(0, 8))

        ttk.Label(
            inner,
            text="Schedule your 4th-year project assessments without editing any JSON.",
            font=("TkDefaultFont", 10),
            foreground="#555",
        ).pack(pady=(0, 24))

        btn_frame = ttk.Frame(inner)
        btn_frame.pack()

        ttk.Button(
            btn_frame,
            text="＋  New empty schedule",
            width=26,
            command=self.on_new,
        ).pack(side="left", padx=8, ipady=6)

        ttk.Button(
            btn_frame,
            text="📂  Open existing JSON",
            width=26,
            command=self.on_open,
        ).pack(side="left", padx=8, ipady=6)

        ttk.Frame(self._welcome).pack(expand=True)   # spacer bottom

    # ── tabs ──────────────────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        self._nb = ttk.Notebook(self)
        # not packed yet — shown only after a config is available

        self._tab_entities     = EntitiesTab(self._nb, on_change=self._mark_dirty)
        self._tab_availability = AvailabilityTab(self._nb)
        self._tab_constraints  = ConstraintsTab(self._nb)
        self._tab_run          = RunTab(self._nb, on_run=self.on_run_solver)

        self._nb.add(self._tab_entities,     text="Entities")
        self._nb.add(self._tab_availability, text="Availability")
        self._nb.add(self._tab_constraints,  text="Constraints")
        self._nb.add(self._tab_run,          text="Run & Output")

    def _build_statusbar(self) -> None:
        self._status_var = tk.StringVar(
            value="Welcome — use File → New or File → Open to get started."
        )
        bar = ttk.Label(
            self, textvariable=self._status_var,
            relief="sunken", anchor="w", padding=(6, 2),
        )
        bar.pack(side="bottom", fill="x")

    # ── switch between welcome and editor ─────────────────────────────────────

    def _show_editor(self) -> None:
        self._welcome.pack_forget()
        self._nb.pack(fill="both", expand=True, padx=6, pady=6)

    # ── file operations ───────────────────────────────────────────────────────

    def on_new(self) -> None:
        """Create a blank config so the user can start adding data immediately."""
        if self._cfg is not None:
            if not messagebox.askyesno(
                "Unsaved changes",
                "Creating a new schedule will discard unsaved changes.\nContinue?",
            ):
                return

        self._cfg      = Config(meta={"description": "New schedule", "version": "1.0"})
        self._cfg.constraints = Constraints()
        self._filepath = None
        self._show_editor()
        self._refresh_all_tabs()
        self._status_var.set(
            "New schedule created — go to Entities to add timeslots, lecturers, and projects."
        )

    def on_open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open schedule config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            cfg = load_config(path)
        except (ConfigError, ValueError) as e:
            messagebox.showerror("Load error", str(e))
            return

        errors, warnings = precheck(cfg)
        if errors or warnings:
            msgs: list[str] = []
            if errors:
                msgs.append("Errors:\n" + "\n".join(f"  • {e}" for e in errors))
            if warnings:
                msgs.append("Warnings:\n" + "\n".join(f"  • {w}" for w in warnings))
            messagebox.showwarning("Precheck results", "\n\n".join(msgs))

        self._cfg      = cfg
        self._filepath = Path(path)
        self._show_editor()
        self._refresh_all_tabs()
        self._status_var.set(f"Loaded: {path}")

    def on_save(self) -> None:
        if self._cfg is None:
            messagebox.showinfo("Nothing to save", "Create or open a schedule first.")
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
            messagebox.showinfo("Nothing to save", "Create or open a schedule first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save schedule as",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self._filepath = Path(path)
        self.on_save()

    # ── solver ────────────────────────────────────────────────────────────────

    def on_run_solver(self) -> None:
        if self._cfg is None:
            messagebox.showinfo("No schedule", "Create or open a schedule first.")
            return
        self._flush_all()

        errors, warnings = precheck(self._cfg)
        if errors:
            msgs = "\n".join(f"  • {e}" for e in errors)
            messagebox.showerror("Cannot solve", f"Please fix these issues first:\n\n{msgs}")
            return
        if warnings:
            msgs = "\n".join(f"  • {w}" for w in warnings)
            if not messagebox.askyesno("Warnings", f"{msgs}\n\nContinue anyway?"):
                return

        self._status_var.set("Solving — please wait…")
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

        self._tab_run.show_result(result, self._cfg)
        self._nb.select(3)
        self._status_var.set(f"Done — {result.status}")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _refresh_all_tabs(self) -> None:
        if self._cfg is None:
            return
        self._tab_entities.refresh(self._cfg)
        self._tab_availability.refresh(self._cfg)
        self._tab_constraints.refresh(self._cfg)

    def _flush_all(self) -> None:
        """Push widget values back to self._cfg before any save or solve."""
        if self._cfg is None:
            return
        self._tab_availability.flush_to_config()
        self._tab_constraints.write_back(self._cfg)

    def _mark_dirty(self) -> None:
        if self._filepath:
            self._status_var.set(f"Unsaved changes — {self._filepath.name}")
        else:
            self._status_var.set("Unsaved changes (not yet saved to a file)")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

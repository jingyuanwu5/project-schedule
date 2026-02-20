# app.py - main application window
# four tabs: Entities, Availability, Constraints, Run & Output
#
# the workflow is:
#   1. File -> New or File -> Open to load a config
#   2. Entities tab to add lecturers/students/projects/timeslots
#   3. Availability tab to mark when lecturers are free
#   4. Constraints tab to set panel size etc
#   5. Run & Output tab to run the solver and see results

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
        self.minsize(820, 560)

        self._cfg: Optional[Config] = None
        self._filepath: Optional[Path] = None

        self._build_menu()
        self._build_welcome()
        self._build_tabs()
        self._build_statusbar()

        # start on the welcome screen, hide tabs until a file is loaded
        self._nb.pack_forget()

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        self.configure(menu=menu)

        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New",       accelerator="Ctrl+N", command=self.on_new)
        file_menu.add_command(label="Open...",   accelerator="Ctrl+O", command=self.on_open)
        file_menu.add_separator()
        file_menu.add_command(label="Save",      accelerator="Ctrl+S", command=self.on_save)
        file_menu.add_command(label="Save As...",                       command=self.on_save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit",                             command=self.quit)

        self.bind_all("<Control-n>", lambda _: self.on_new())
        self.bind_all("<Control-o>", lambda _: self.on_open())
        self.bind_all("<Control-s>", lambda _: self.on_save())

    def _build_welcome(self) -> None:
        self._welcome = ttk.Frame(self)
        self._welcome.pack(fill="both", expand=True)

        ttk.Frame(self._welcome).pack(expand=True)  # spacer

        inner = ttk.Frame(self._welcome)
        inner.pack()

        ttk.Label(
            inner,
            text="4YP Assessment Timetable Scheduler",
            font=("TkDefaultFont", 17, "bold"),
        ).pack(pady=(0, 6))

        ttk.Label(
            inner,
            text=(
                "Schedule 4th-year project assessments using constraint programming.\n"
                "No JSON editing required — use the tabs to enter all your data."
            ),
            font=("TkDefaultFont", 10),
            foreground="#555",
            justify="center",
        ).pack(pady=(0, 28))

        btn_row = ttk.Frame(inner)
        btn_row.pack()

        ttk.Button(
            btn_row, text="New empty schedule",
            width=26, command=self.on_new,
        ).pack(side="left", padx=10, ipady=8)

        ttk.Button(
            btn_row, text="Open existing JSON",
            width=26, command=self.on_open,
        ).pack(side="left", padx=10, ipady=8)

        ttk.Label(
            inner,
            text="Tip: start with Entities → Time Slots → Generate batch... to create timeslots quickly.",
            font=("TkDefaultFont", 8),
            foreground="#888",
        ).pack(pady=(20, 0))

        ttk.Frame(self._welcome).pack(expand=True)  # spacer

    def _build_tabs(self) -> None:
        self._nb = ttk.Notebook(self)

        self._tab_entities     = EntitiesTab(self._nb, on_change=self._on_entity_change)
        self._tab_availability = AvailabilityTab(self._nb)
        self._tab_constraints  = ConstraintsTab(self._nb)
        self._tab_run          = RunTab(self._nb, on_run=self.on_run_solver)

        self._nb.add(self._tab_entities,     text="Entities")
        self._nb.add(self._tab_availability, text="Availability")
        self._nb.add(self._tab_constraints,  text="Constraints")
        self._nb.add(self._tab_run,          text="Run & Output")

    def _build_statusbar(self) -> None:
        self._status_var = tk.StringVar(
            value="No file loaded.  Use File → New or File → Open to get started."
        )
        bar = ttk.Label(
            self,
            textvariable=self._status_var,
            relief="sunken",
            anchor="w",
            padding=(6, 2),
        )
        bar.pack(side="bottom", fill="x")

    def _show_editor(self) -> None:
        self._welcome.pack_forget()
        self._nb.pack(fill="both", expand=True, padx=6, pady=6)

    # ---- file menu actions ----

    def on_new(self) -> None:
        if self._cfg is not None:
            if not messagebox.askyesno(
                "Discard current schedule?",
                "This will discard unsaved changes. Continue?",
            ):
                return
        self._cfg = Config(meta={"description": "New schedule", "version": "1.0"})
        self._cfg.constraints = Constraints()
        self._filepath = None
        self._show_editor()
        self._refresh_all_tabs()
        self._status_var.set("New schedule — add timeslots, lecturers, and projects in the Entities tab.")

    def on_open(self) -> None:
        path = filedialog.askopenfilename(
            title="Open schedule config",
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
            parts = []
            if errors:
                parts.append("Errors:\n" + "\n".join(f"  * {e}" for e in errors))
            if warnings:
                parts.append("Warnings:\n" + "\n".join(f"  * {w}" for w in warnings))
            messagebox.showwarning("Precheck results", "\n\n".join(parts))

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
        if not path: return
        self._filepath = Path(path)
        self.on_save()

    # ---- solver ----

    def on_run_solver(self) -> None:
        if self._cfg is None:
            messagebox.showinfo("No schedule", "Create or open a schedule first.")
            return
        self._flush_all()

        errors, warnings = precheck(self._cfg)
        if errors:
            msg = "\n".join(f"  * {e}" for e in errors)
            messagebox.showerror(
                "Cannot solve",
                f"Fix these issues before running:\n\n{msg}",
            )
            return
        if warnings:
            msg = "\n".join(f"  * {w}" for w in warnings)
            if not messagebox.askyesno("Warnings", f"{msg}\n\nContinue anyway?"):
                return

        solver_level = self._tab_run.get_solver_level()
        self._status_var.set(f"Solving with {solver_level}... please wait")
        self.update()  # force the UI to update before blocking on solver

        try:
            result = solve(self._cfg, solver_level)
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

    # ---- helpers ----

    def _refresh_all_tabs(self) -> None:
        if self._cfg is None: return
        self._tab_entities.refresh(self._cfg)
        self._tab_availability.refresh(self._cfg)
        self._tab_constraints.refresh(self._cfg)

    def _flush_all(self) -> None:
        # write widget values back into cfg before saving or running solver
        if self._cfg is None: return
        self._tab_availability.flush_to_config()
        self._tab_constraints.write_back(self._cfg)

    def _on_entity_change(self) -> None:
        # called whenever something changes in the Entities tab
        # need to refresh Availability and Constraints so they stay in sync
        # e.g. if you delete a lecturer, their row should disappear from the grid immediately
        name = self._filepath.name if self._filepath else "unsaved file"
        self._status_var.set(f"Unsaved changes — {name}")
        if self._cfg is None: return
        self._tab_availability.refresh(self._cfg)
        self._tab_constraints.refresh(self._cfg)


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

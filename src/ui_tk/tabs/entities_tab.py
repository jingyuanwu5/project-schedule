"""
Entities Tab — manage lecturers, students and projects.

Students are kept as independent objects linked to projects by ID,
not embedded inside project objects.  This directly implements the
"flat entities + ID references" pattern from the project plan.

ttk.Treeview is used for all three lists.
Reference: Python docs — tkinter.ttk Treeview
https://docs.python.org/3/library/tkinter.ttk.html#treeview
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from collections.abc import Callable
from typing import Optional

from schedule_app.models import Config, Lecturer, Project, Student, TimeSlot


class EntitiesTab(ttk.Frame):
    """
    Three-column layout:
      Left   — Lecturers
      Centre — Students
      Right  — Projects
    """

    def __init__(self, parent: tk.Widget, on_change: Callable[[], None]) -> None:
        super().__init__(parent)
        # on_change is called whenever the config is mutated so that other
        # tabs (e.g. AvailabilityTab) can redraw themselves.
        self._on_change = on_change
        self.cfg: Optional[Config] = None
        self._build()

    # ── layout ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_lecturers(col=0)
        self._build_students(col=1)
        self._build_projects(col=2)

    def _make_panel(self, title: str, col: int) -> ttk.LabelFrame:
        frm = ttk.LabelFrame(self, text=title)
        frm.grid(row=0, column=col, sticky="nsew", padx=8, pady=8)
        frm.columnconfigure(0, weight=1)
        frm.rowconfigure(0, weight=1)
        return frm

    # ── Lecturers ─────────────────────────────────────────────────────────────

    def _build_lecturers(self, col: int) -> None:
        frm = self._make_panel("Lecturers", col)

        self.lec_tree = ttk.Treeview(
            frm, columns=("id", "name", "avail"), show="headings", height=16
        )
        for c, w, label in [
            ("id",    80,  "ID"),
            ("name",  160, "Name"),
            ("avail", 60,  "Slots"),
        ]:
            self.lec_tree.heading(c, text=label)
            self.lec_tree.column(c, width=w, anchor="center")
        self.lec_tree.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(btn_row, text="Add",    command=self._add_lecturer).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Delete", command=self._del_lecturer).pack(side="left")

    def _add_lecturer(self) -> None:
        if self.cfg is None:
            return
        lec_id = simpledialog.askstring("Add Lecturer", "Lecturer ID (e.g. L03):", parent=self)
        if not lec_id:
            return
        if any(l.id == lec_id for l in self.cfg.lecturers):
            messagebox.showerror("Duplicate ID", f"Lecturer ID '{lec_id}' already exists.")
            return
        name = simpledialog.askstring("Add Lecturer", "Full name:", parent=self)
        if not name:
            return
        self.cfg.lecturers.append(Lecturer(id=lec_id, name=name))
        self._refresh_lecturers()
        self._on_change()

    def _del_lecturer(self) -> None:
        if self.cfg is None:
            return
        sel = self.lec_tree.selection()
        if not sel:
            return
        lec_id = self.lec_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete lecturer '{lec_id}'?\n"
                                   "Projects supervised by them will lose their supervisor."):
            return
        self.cfg.lecturers = [l for l in self.cfg.lecturers if l.id != lec_id]
        # Clear dangling supervisor references
        for p in self.cfg.projects:
            if p.supervisor_lecturer_id == lec_id:
                p.supervisor_lecturer_id = ""
        self._refresh_lecturers()
        self._refresh_projects()
        self._on_change()

    def _refresh_lecturers(self) -> None:
        self.lec_tree.delete(*self.lec_tree.get_children())
        if self.cfg is None:
            return
        for l in self.cfg.lecturers:
            self.lec_tree.insert(
                "", "end",
                values=(l.id, l.name, len(l.available_slot_ids)),
            )

    # ── Students ──────────────────────────────────────────────────────────────

    def _build_students(self, col: int) -> None:
        frm = self._make_panel("Students", col)

        self.stu_tree = ttk.Treeview(
            frm, columns=("id", "name", "project"), show="headings", height=16
        )
        for c, w, label in [
            ("id",      80,  "ID"),
            ("name",    140, "Name"),
            ("project", 120, "Project"),
        ]:
            self.stu_tree.heading(c, text=label)
            self.stu_tree.column(c, width=w, anchor="center")
        self.stu_tree.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(btn_row, text="Add",    command=self._add_student).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Delete", command=self._del_student).pack(side="left")

    def _add_student(self) -> None:
        if self.cfg is None:
            return
        if not self.cfg.projects:
            messagebox.showinfo("No projects", "Add at least one project first.")
            return

        stu_id = simpledialog.askstring("Add Student", "Student ID (e.g. S04):", parent=self)
        if not stu_id:
            return
        if any(s.id == stu_id for s in self.cfg.students):
            messagebox.showerror("Duplicate ID", f"Student ID '{stu_id}' already exists.")
            return
        name = simpledialog.askstring("Add Student", "Full name:", parent=self)
        if not name:
            return

        # Pick a project using a small modal — students are linked to projects
        # by ID rather than embedded in them (flat-entity design).
        proj_id = self._pick_project(title="Assign to project")
        if proj_id is None:
            return

        student = Student(id=stu_id, name=name)
        self.cfg.students.append(student)
        proj = self.cfg.get_project(proj_id)
        if proj:
            proj.student_ids.append(stu_id)

        self._refresh_students()
        self._refresh_projects()
        self._on_change()

    def _del_student(self) -> None:
        if self.cfg is None:
            return
        sel = self.stu_tree.selection()
        if not sel:
            return
        stu_id = self.stu_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete student '{stu_id}'?"):
            return
        self.cfg.students = [s for s in self.cfg.students if s.id != stu_id]
        # Remove ID from any project that referenced this student
        for p in self.cfg.projects:
            if stu_id in p.student_ids:
                p.student_ids.remove(stu_id)
        self._refresh_students()
        self._refresh_projects()
        self._on_change()

    def _refresh_students(self) -> None:
        self.stu_tree.delete(*self.stu_tree.get_children())
        if self.cfg is None:
            return
        # Build a reverse map: student_id -> project title
        stu_to_proj: dict[str, str] = {}
        for p in self.cfg.projects:
            for sid in p.student_ids:
                stu_to_proj[sid] = p.title
        for s in self.cfg.students:
            self.stu_tree.insert(
                "", "end",
                values=(s.id, s.name, stu_to_proj.get(s.id, "—")),
            )

    # ── Projects ──────────────────────────────────────────────────────────────

    def _build_projects(self, col: int) -> None:
        frm = self._make_panel("Projects", col)

        self.proj_tree = ttk.Treeview(
            frm, columns=("id", "title", "supervisor", "students"),
            show="headings", height=16,
        )
        for c, w, label in [
            ("id",         70,  "ID"),
            ("title",      170, "Title"),
            ("supervisor", 90,  "Supervisor"),
            ("students",   90,  "Students"),
        ]:
            self.proj_tree.heading(c, text=label)
            self.proj_tree.column(c, width=w, anchor="center")
        self.proj_tree.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(btn_row, text="Add",             command=self._add_project).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Delete",           command=self._del_project).pack(side="left")
        ttk.Button(btn_row, text="Set supervisor…", command=self._set_supervisor).pack(side="left", padx=4)

    def _add_project(self) -> None:
        if self.cfg is None:
            return
        proj_id = simpledialog.askstring("Add Project", "Project ID (e.g. P04):", parent=self)
        if not proj_id:
            return
        if any(p.id == proj_id for p in self.cfg.projects):
            messagebox.showerror("Duplicate ID", f"Project ID '{proj_id}' already exists.")
            return
        title = simpledialog.askstring("Add Project", "Project title:", parent=self)
        if not title:
            return
        self.cfg.projects.append(Project(id=proj_id, title=title))
        self._refresh_projects()
        self._on_change()

    def _del_project(self) -> None:
        if self.cfg is None:
            return
        sel = self.proj_tree.selection()
        if not sel:
            return
        proj_id = self.proj_tree.item(sel[0], "values")[0]
        proj = self.cfg.get_project(proj_id)
        if proj is None:
            return
        if not messagebox.askyesno("Confirm",
                                   f"Delete project '{proj_id}'?\n"
                                   f"Its {len(proj.student_ids)} student(s) will be unlinked."):
            return
        # Remove student → project links
        for sid in list(proj.student_ids):
            pass  # students remain; only the link is removed
        self.cfg.projects = [p for p in self.cfg.projects if p.id != proj_id]
        self._refresh_projects()
        self._refresh_students()
        self._on_change()

    def _set_supervisor(self) -> None:
        if self.cfg is None:
            return
        sel = self.proj_tree.selection()
        if not sel:
            messagebox.showinfo("Select project", "Select a project first.")
            return
        proj_id = self.proj_tree.item(sel[0], "values")[0]
        proj = self.cfg.get_project(proj_id)
        if proj is None:
            return
        lec_id = self._pick_lecturer(title=f"Supervisor for '{proj.title}'")
        if lec_id is None:
            return
        proj.supervisor_lecturer_id = lec_id
        self._refresh_projects()
        self._on_change()

    def _refresh_projects(self) -> None:
        self.proj_tree.delete(*self.proj_tree.get_children())
        if self.cfg is None:
            return
        for p in self.cfg.projects:
            self.proj_tree.insert(
                "", "end",
                values=(
                    p.id,
                    p.title,
                    p.supervisor_lecturer_id or "—",
                    len(p.student_ids),
                ),
            )

    # ── helper modals ─────────────────────────────────────────────────────────

    def _pick_project(self, title: str) -> Optional[str]:
        """Small modal for choosing a project by title. Returns project id or None."""
        if not self.cfg or not self.cfg.projects:
            return None
        win = tk.Toplevel(self)
        win.title(title)
        win.resizable(False, False)
        win.grab_set()

        var = tk.StringVar(value=self.cfg.projects[0].id)
        for p in self.cfg.projects:
            ttk.Radiobutton(win, text=f"{p.id}  {p.title}",
                            variable=var, value=p.id).pack(anchor="w", padx=16, pady=2)

        result: list[Optional[str]] = [None]

        def ok():
            result[0] = var.get()
            win.destroy()

        def cancel():
            win.destroy()

        btn_row = ttk.Frame(win)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="OK",     command=ok).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel", command=cancel).pack(side="left")
        win.wait_window()
        return result[0]

    def _pick_lecturer(self, title: str) -> Optional[str]:
        """Small modal for choosing a lecturer. Returns lecturer id or None."""
        if not self.cfg or not self.cfg.lecturers:
            messagebox.showinfo("No lecturers", "Add lecturers first.")
            return None
        win = tk.Toplevel(self)
        win.title(title)
        win.resizable(False, False)
        win.grab_set()

        var = tk.StringVar(value=self.cfg.lecturers[0].id)
        for l in self.cfg.lecturers:
            ttk.Radiobutton(win, text=f"{l.id}  {l.name}",
                            variable=var, value=l.id).pack(anchor="w", padx=16, pady=2)

        result: list[Optional[str]] = [None]

        def ok():
            result[0] = var.get()
            win.destroy()

        def cancel():
            win.destroy()

        btn_row = ttk.Frame(win)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="OK",     command=ok).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel", command=cancel).pack(side="left")
        win.wait_window()
        return result[0]

    # ── public API ────────────────────────────────────────────────────────────

    def refresh(self, cfg: Config) -> None:
        self.cfg = cfg
        self._refresh_lecturers()
        self._refresh_students()
        self._refresh_projects()
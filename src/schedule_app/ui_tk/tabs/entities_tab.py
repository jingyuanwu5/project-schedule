"""
Entities Tab — manage lecturers, students, projects and timeslots.

Students are independent objects linked to projects by ID, never embedded
inside project objects. This is the flat-entity pattern required by the
supervisor feedback: "separate student and project objects and link from
students to projects rather than embed students in project objects directly."

ttk.Treeview is used for all lists.
Reference: Python Software Foundation. "tkinter.ttk — Tk themed widgets."
https://docs.python.org/3/library/tkinter.ttk.html#treeview

ttk widgets (including Spinbox, Treeview, Notebook) are available from
Python 3.7 onwards. This project targets Python 3.10+.
Reference: https://docs.python.org/3/library/tkinter.ttk.html
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Optional

from schedule_app.models import Config, Lecturer, Project, Student, TimeSlot


class EntitiesTab(ttk.Frame):
    """
    Four-panel layout inside a sub-Notebook:
      Lecturers | Students | Projects | Time Slots
    """

    def __init__(self, parent: tk.Widget, on_change: Callable[[], None]) -> None:
        super().__init__(parent)
        self._on_change = on_change
        self.cfg: Optional[Config] = None
        self._build()

    # ── layout ───────────────────────────────────────────────────────────────

    def _build(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        self._lec_frame  = ttk.Frame(nb)
        self._stu_frame  = ttk.Frame(nb)
        self._proj_frame = ttk.Frame(nb)
        self._slot_frame = ttk.Frame(nb)

        nb.add(self._lec_frame,  text="Lecturers")
        nb.add(self._stu_frame,  text="Students")
        nb.add(self._proj_frame, text="Projects")
        nb.add(self._slot_frame, text="Time Slots")

        self._build_lecturers()
        self._build_students()
        self._build_projects()
        self._build_timeslots()

    def _tree_panel(self, parent, cols: list[tuple]) -> ttk.Treeview:
        """Create a Treeview with scrollbar and return it."""
        frm = ttk.Frame(parent)
        frm.pack(fill="both", expand=True, padx=6, pady=6)

        tree = ttk.Treeview(
            frm,
            columns=[c[0] for c in cols],
            show="headings",
            height=16,
        )
        for col_id, width, label in cols:
            tree.heading(col_id, text=label)
            tree.column(col_id, width=width, anchor="center")

        sb = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        return tree

    # ── Lecturers ─────────────────────────────────────────────────────────────

    def _build_lecturers(self) -> None:
        self.lec_tree = self._tree_panel(
            self._lec_frame,
            [("id", 90, "ID"), ("name", 200, "Name"),
             ("avail", 70, "Avail slots"), ("max_day", 80, "Max/day")],
        )
        row = ttk.Frame(self._lec_frame)
        row.pack(pady=4)
        ttk.Button(row, text="Add",         command=self._add_lecturer).pack(side="left", padx=4)
        ttk.Button(row, text="Delete",       command=self._del_lecturer).pack(side="left")
        ttk.Button(row, text="Edit max/day", command=self._edit_max_per_day).pack(side="left", padx=4)

    def _add_lecturer(self) -> None:
        if self.cfg is None: return
        lid = simpledialog.askstring("Add Lecturer", "Lecturer ID (e.g. L03):", parent=self)
        if not lid: return
        if any(l.id == lid for l in self.cfg.lecturers):
            messagebox.showerror("Duplicate ID", f"Lecturer ID '{lid}' already exists.")
            return
        name = simpledialog.askstring("Add Lecturer", "Full name:", parent=self)
        if not name: return
        self.cfg.lecturers.append(Lecturer(id=lid, name=name))
        self._refresh_lecturers()
        self._on_change()

    def _del_lecturer(self) -> None:
        if self.cfg is None: return
        sel = self.lec_tree.selection()
        if not sel: return
        lid = self.lec_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete lecturer '{lid}'?\n"
                                   "Their row will be removed from the Availability grid.\n"
                                   "Projects supervised by them will lose their supervisor."):
            return
        self.cfg.lecturers = [l for l in self.cfg.lecturers if l.id != lid]
        for p in self.cfg.projects:
            if p.supervisor_lecturer_id == lid:
                p.supervisor_lecturer_id = ""
        self._refresh_lecturers()
        self._refresh_projects()
        self._on_change()   # triggers App._mark_dirty and availability grid rebuild

    def _edit_max_per_day(self) -> None:
        if self.cfg is None: return
        sel = self.lec_tree.selection()
        if not sel:
            messagebox.showinfo("Select first", "Select a lecturer first.")
            return
        lid = self.lec_tree.item(sel[0], "values")[0]
        lec = self.cfg.get_lecturer(lid)
        if lec is None: return
        val = simpledialog.askstring(
            "Max per day",
            f"Max assessments per day for {lec.name}\n(leave blank = no limit):",
            parent=self,
            initialvalue="" if lec.max_per_day is None else str(lec.max_per_day),
        )
        if val is None: return
        lec.max_per_day = int(val) if val.strip().isdigit() else None
        self._refresh_lecturers()

    def _refresh_lecturers(self) -> None:
        self.lec_tree.delete(*self.lec_tree.get_children())
        if self.cfg is None: return
        for l in self.cfg.lecturers:
            self.lec_tree.insert("", "end", values=(
                l.id, l.name,
                len(l.available_slot_ids),
                l.max_per_day if l.max_per_day is not None else "—",
            ))

    # ── Students ──────────────────────────────────────────────────────────────

    def _build_students(self) -> None:
        self.stu_tree = self._tree_panel(
            self._stu_frame,
            [("id", 90, "ID"), ("name", 180, "Name"), ("project", 160, "Project")],
        )
        row = ttk.Frame(self._stu_frame)
        row.pack(pady=4)
        ttk.Button(row, text="Add",    command=self._add_student).pack(side="left", padx=4)
        ttk.Button(row, text="Delete", command=self._del_student).pack(side="left")

    def _add_student(self) -> None:
        if self.cfg is None: return
        if not self.cfg.projects:
            messagebox.showinfo("No projects", "Add at least one project first.")
            return
        sid = simpledialog.askstring("Add Student", "Student ID (e.g. S04):", parent=self)
        if not sid: return
        if any(s.id == sid for s in self.cfg.students):
            messagebox.showerror("Duplicate ID", f"Student ID '{sid}' already exists.")
            return
        name = simpledialog.askstring("Add Student", "Full name:", parent=self)
        if not name: return
        proj_id = self._pick_project("Assign to project")
        if proj_id is None: return
        student = Student(id=sid, name=name)
        self.cfg.students.append(student)
        proj = self.cfg.get_project(proj_id)
        if proj:
            proj.student_ids.append(sid)
        self._refresh_students()
        self._refresh_projects()
        self._on_change()

    def _del_student(self) -> None:
        if self.cfg is None: return
        sel = self.stu_tree.selection()
        if not sel: return
        sid = self.stu_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete student '{sid}'?"): return
        self.cfg.students = [s for s in self.cfg.students if s.id != sid]
        for p in self.cfg.projects:
            if sid in p.student_ids:
                p.student_ids.remove(sid)
        self._refresh_students()
        self._refresh_projects()
        self._on_change()

    def _refresh_students(self) -> None:
        self.stu_tree.delete(*self.stu_tree.get_children())
        if self.cfg is None: return
        stu_to_proj: dict[str, str] = {}
        for p in self.cfg.projects:
            for sid in p.student_ids:
                stu_to_proj[sid] = p.title
        for s in self.cfg.students:
            self.stu_tree.insert("", "end", values=(
                s.id, s.name, stu_to_proj.get(s.id, "—"),
            ))

    # ── Projects ──────────────────────────────────────────────────────────────

    def _build_projects(self) -> None:
        self.proj_tree = self._tree_panel(
            self._proj_frame,
            [("id", 80, "ID"), ("title", 200, "Title"),
             ("sup", 110, "Supervisor"), ("students", 70, "Students")],
        )
        row = ttk.Frame(self._proj_frame)
        row.pack(pady=4)
        ttk.Button(row, text="Add",            command=self._add_project).pack(side="left", padx=4)
        ttk.Button(row, text="Delete",          command=self._del_project).pack(side="left")
        ttk.Button(row, text="Set supervisor…", command=self._set_supervisor).pack(side="left", padx=4)

    def _add_project(self) -> None:
        if self.cfg is None: return
        pid = simpledialog.askstring("Add Project", "Project ID (e.g. P04):", parent=self)
        if not pid: return
        if any(p.id == pid for p in self.cfg.projects):
            messagebox.showerror("Duplicate ID", f"Project ID '{pid}' already exists.")
            return
        title = simpledialog.askstring("Add Project", "Project title:", parent=self)
        if not title: return
        self.cfg.projects.append(Project(id=pid, title=title))
        self._refresh_projects()
        self._on_change()

    def _del_project(self) -> None:
        if self.cfg is None: return
        sel = self.proj_tree.selection()
        if not sel: return
        pid = self.proj_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete project '{pid}'?"): return
        self.cfg.projects = [p for p in self.cfg.projects if p.id != pid]
        self._refresh_projects()
        self._refresh_students()
        self._on_change()

    def _set_supervisor(self) -> None:
        if self.cfg is None: return
        sel = self.proj_tree.selection()
        if not sel:
            messagebox.showinfo("Select first", "Select a project first.")
            return
        pid = self.proj_tree.item(sel[0], "values")[0]
        proj = self.cfg.get_project(pid)
        if proj is None: return
        lid = self._pick_lecturer(f"Supervisor for '{proj.title}'")
        if lid is None: return
        proj.supervisor_lecturer_id = lid
        self._refresh_projects()
        self._on_change()

    def _refresh_projects(self) -> None:
        self.proj_tree.delete(*self.proj_tree.get_children())
        if self.cfg is None: return
        for p in self.cfg.projects:
            self.proj_tree.insert("", "end", values=(
                p.id, p.title,
                p.supervisor_lecturer_id or "—",
                len(p.student_ids),
            ))

    # ── Time Slots ────────────────────────────────────────────────────────────

    def _build_timeslots(self) -> None:
        self.slot_tree = self._tree_panel(
            self._slot_frame,
            [("id", 100, "ID"), ("date", 110, "Date"),
             ("start", 70, "Start"), ("end", 70, "End"), ("label", 140, "Label")],
        )
        row = ttk.Frame(self._slot_frame)
        row.pack(pady=4)
        ttk.Button(row, text="Add slot",        command=self._add_slot).pack(side="left", padx=4)
        ttk.Button(row, text="Delete slot",     command=self._del_slot).pack(side="left")
        ttk.Button(row, text="Generate batch…", command=self._generate_slots).pack(side="left", padx=4)

        # format hints below the buttons
        hint_row = ttk.Frame(self._slot_frame)
        hint_row.pack(anchor="w", padx=8, pady=(0, 4))
        ttk.Label(
            hint_row,
            text="Date format: YYYY-MM-DD  |  Time format: HH:MM  |  "
                 "Use 'Generate batch' to create a full day of slots at once.",
            font=("TkDefaultFont", 8),
            foreground="#888",
        ).pack(anchor="w")

    def _add_slot(self) -> None:
        if self.cfg is None: return
        sid = simpledialog.askstring("Add Slot", "Slot ID (e.g. TS05):", parent=self)
        if not sid: return
        if any(s.id == sid for s in self.cfg.timeslots):
            messagebox.showerror("Duplicate ID", f"Slot ID '{sid}' already exists.")
            return
        date  = simpledialog.askstring("Add Slot", "Date (YYYY-MM-DD):", parent=self)
        if not date: return
        start = simpledialog.askstring("Add Slot", "Start time (HH:MM):", parent=self)
        if not start: return
        end   = simpledialog.askstring("Add Slot", "End time (HH:MM):", parent=self)
        if not end: return

        # ── validate formats ──────────────────────────────────────────────────
        from datetime import datetime
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", f"'{date}' is not a valid date.\nUse YYYY-MM-DD (e.g. 2026-03-10).")
            return
        try:
            t_start = datetime.strptime(start, "%H:%M")
            t_end   = datetime.strptime(end,   "%H:%M")
        except ValueError:
            messagebox.showerror("Invalid time", "Start and end times must be in HH:MM format (e.g. 09:00).")
            return
        if t_end <= t_start:
            messagebox.showerror("Invalid time range", f"End time ({end}) must be after start time ({start}).")
            return
        # ─────────────────────────────────────────────────────────────────────

        label = simpledialog.askstring("Add Slot", "Display label (optional):", parent=self) or ""
        self.cfg.timeslots.append(TimeSlot(id=sid, date=date, start=start, end=end, label=label))
        self._refresh_timeslots()
        self._on_change()

    def _del_slot(self) -> None:
        if self.cfg is None: return
        sel = self.slot_tree.selection()
        if not sel: return
        sid = self.slot_tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Confirm", f"Delete slot '{sid}'?\n"
                                   "It will be removed from all lecturer availability lists."): return
        self.cfg.timeslots = [s for s in self.cfg.timeslots if s.id != sid]
        for l in self.cfg.lecturers:
            if sid in l.available_slot_ids:
                l.available_slot_ids.remove(sid)
        self.cfg.constraints.lunch_slot_ids = [
            s for s in self.cfg.constraints.lunch_slot_ids if s != sid
        ]
        self._refresh_timeslots()
        self._on_change()

    def _generate_slots(self) -> None:
        """
        Batch-generate timeslots for a given date, start time, end time and
        duration. This avoids the need to hand-edit the JSON for common cases.
        """
        if self.cfg is None: return
        win = tk.Toplevel(self)
        win.title("Generate time slots")
        win.resizable(False, False)
        win.grab_set()

        fields: dict[str, tk.StringVar] = {}
        defaults = [
            ("date",     "Date (YYYY-MM-DD):",    "2026-03-10"),
            ("day_start","Day start (HH:MM):",     "09:00"),
            ("day_end",  "Day end (HH:MM):",       "17:00"),
            ("duration", "Slot duration (mins):",  "30"),
            ("prefix",   "ID prefix:",             "TS"),
        ]
        for i, (key, label, default) in enumerate(defaults):
            ttk.Label(win, text=label).grid(row=i, column=0, sticky="w", padx=12, pady=4)
            var = tk.StringVar(value=default)
            ttk.Entry(win, textvariable=var, width=18).grid(row=i, column=1, padx=8, pady=4)
            fields[key] = var

        def do_generate() -> None:
            try:
                from datetime import datetime, timedelta
                date     = fields["date"].get().strip()
                day_start = datetime.strptime(fields["day_start"].get().strip(), "%H:%M")
                day_end   = datetime.strptime(fields["day_end"].get().strip(),   "%H:%M")
                dur_mins  = int(fields["duration"].get().strip())
                prefix    = fields["prefix"].get().strip() or "TS"
                if dur_mins <= 0:
                    raise ValueError("Duration must be positive")
            except ValueError as e:
                messagebox.showerror("Invalid input", str(e), parent=win)
                return

            existing_ids = {s.id for s in self.cfg.timeslots}
            current      = day_start
            delta        = timedelta(minutes=dur_mins)
            counter      = len(self.cfg.timeslots) + 1
            added        = 0

            while current + delta <= day_end:
                slot_id = f"{prefix}{counter:03d}"
                while slot_id in existing_ids:
                    counter += 1
                    slot_id = f"{prefix}{counter:03d}"
                end_t = current + delta
                self.cfg.timeslots.append(TimeSlot(
                    id    = slot_id,
                    date  = date,
                    start = current.strftime("%H:%M"),
                    end   = end_t.strftime("%H:%M"),
                    label = f"{date} {current.strftime('%H:%M')}",
                ))
                existing_ids.add(slot_id)
                current += delta
                counter += 1
                added   += 1

            self._refresh_timeslots()
            self._on_change()
            win.destroy()
            messagebox.showinfo("Done", f"Generated {added} slot(s).")

        btn_row = ttk.Frame(win)
        btn_row.grid(row=len(defaults), column=0, columnspan=2, pady=10)
        ttk.Button(btn_row, text="Generate", command=do_generate).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel",   command=win.destroy).pack(side="left")
        win.wait_window()

    def _refresh_timeslots(self) -> None:
        self.slot_tree.delete(*self.slot_tree.get_children())
        if self.cfg is None: return
        for s in self.cfg.timeslots:
            self.slot_tree.insert("", "end", values=(
                s.id, s.date, s.start, s.end, s.label or "",
            ))

    # ── helper modals ─────────────────────────────────────────────────────────

    def _pick_project(self, title: str) -> Optional[str]:
        if not self.cfg or not self.cfg.projects: return None
        return self._radio_pick(title,
            [(p.id, f"{p.id}  {p.title}") for p in self.cfg.projects])

    def _pick_lecturer(self, title: str) -> Optional[str]:
        if not self.cfg or not self.cfg.lecturers:
            messagebox.showinfo("No lecturers", "Add lecturers first.")
            return None
        return self._radio_pick(title,
            [(l.id, f"{l.id}  {l.name}") for l in self.cfg.lecturers])

    def _radio_pick(self, title: str, options: list[tuple[str, str]]) -> Optional[str]:
        """Generic modal that shows radio buttons and returns the chosen value."""
        win = tk.Toplevel(self)
        win.title(title)
        win.resizable(False, False)
        win.grab_set()

        var = tk.StringVar(value=options[0][0])
        for value, label in options:
            ttk.Radiobutton(win, text=label, variable=var, value=value).pack(
                anchor="w", padx=16, pady=2
            )

        result: list[Optional[str]] = [None]

        def ok():
            result[0] = var.get()
            win.destroy()

        btn_row = ttk.Frame(win)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="OK",     command=ok).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Cancel", command=win.destroy).pack(side="left")
        win.wait_window()
        return result[0]

    # ── public API ────────────────────────────────────────────────────────────

    def refresh(self, cfg: Config) -> None:
        self.cfg = cfg
        self._refresh_lecturers()
        self._refresh_students()
        self._refresh_projects()
        self._refresh_timeslots()

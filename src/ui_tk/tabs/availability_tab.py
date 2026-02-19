"""
Availability Tab — lecturer × timeslot grid.

Drawn on a tk.Canvas so that large matrices (many lecturers or many slots)
do not hit tkinter's widget limit.  Scrollbars are added for both axes.

canvas.canvasx(event.x) converts a screen x-coordinate to the canvas
coordinate system, which is essential when the canvas is scrolled.

Reference: Python docs — tkinter Canvas
https://docs.python.org/3/library/tkinter.html#canvas-objects
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from schedule_app.models import Config


class AvailabilityTab(ttk.Frame):

    CELL_W    = 96
    CELL_H    = 28
    HEADER_H  = 40
    SIDEBAR_W = 180
    C_AVAIL   = "#b7ecb7"   # green
    C_EMPTY   = "#f5f5f5"   # light grey

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.cfg: Optional[Config] = None
        self._state: dict[tuple[int, int], bool] = {}
        self._rects: dict[tuple[int, int], int]  = {}
        self._build()

    def _build(self) -> None:
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        sb_x = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        sb_y = ttk.Scrollbar(self, orient="vertical",   command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sb_x.set, yscrollcommand=sb_y.set)

        sb_y.pack(side="right",  fill="y")
        sb_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._on_click)

    def refresh(self, cfg: Config) -> None:
        self.cfg = cfg
        self.canvas.delete("all")
        self._state.clear()
        self._rects.clear()

        if not cfg.lecturers or not cfg.timeslots:
            self.canvas.create_text(
                10, 10, anchor="nw",
                text="Add lecturers and timeslots first (Entities tab).",
                fill="gray",
            )
            return

        # Column headers
        self.canvas.create_text(
            6, self.HEADER_H // 2, anchor="w",
            text="Lecturer \\ Slot",
            font=("TkDefaultFont", 9, "bold"),
        )
        for j, slot in enumerate(cfg.timeslots):
            cx = self.SIDEBAR_W + j * self.CELL_W + self.CELL_W // 2
            self.canvas.create_text(
                cx, self.HEADER_H // 2, anchor="center",
                text=slot.label or slot.id,
                width=self.CELL_W - 6,
                font=("TkDefaultFont", 8),
            )

        # Row headers and cells
        for i, lec in enumerate(cfg.lecturers):
            row_y  = self.HEADER_H + i * self.CELL_H
            mid_y  = row_y + self.CELL_H // 2
            avail  = set(lec.available_slot_ids)
            self.canvas.create_text(
                6, mid_y, anchor="w",
                text=f"{lec.id}  {lec.name}",
                font=("TkDefaultFont", 9),
            )
            for j, slot in enumerate(cfg.timeslots):
                is_avail        = slot.id in avail
                self._state[i, j] = is_avail
                x0 = self.SIDEBAR_W + j * self.CELL_W
                y0 = row_y
                x1 = x0 + self.CELL_W
                y1 = y0 + self.CELL_H
                rid = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=self.C_AVAIL if is_avail else self.C_EMPTY,
                    outline="#cccccc",
                )
                self._rects[i, j] = rid

        total_w = self.SIDEBAR_W + len(cfg.timeslots)  * self.CELL_W
        total_h = self.HEADER_H  + len(cfg.lecturers)  * self.CELL_H
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

    def _on_click(self, event: tk.Event) -> None:
        if self.cfg is None:
            return
        # Convert widget coords → canvas coords to handle scrolling correctly
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        if cx < self.SIDEBAR_W or cy < self.HEADER_H:
            return
        j = int((cx - self.SIDEBAR_W) // self.CELL_W)
        i = int((cy - self.HEADER_H)  // self.CELL_H)
        if i >= len(self.cfg.lecturers) or j >= len(self.cfg.timeslots):
            return
        new = not self._state.get((i, j), False)
        self._state[i, j] = new
        self.canvas.itemconfig(
            self._rects[i, j],
            fill=self.C_AVAIL if new else self.C_EMPTY,
        )

    def flush_to_config(self) -> None:
        """Write grid state back to cfg.lecturers[].available_slot_ids."""
        if self.cfg is None:
            return
        for i, lec in enumerate(self.cfg.lecturers):
            lec.available_slot_ids = [
                self.cfg.timeslots[j].id
                for j in range(len(self.cfg.timeslots))
                if self._state.get((i, j), False)
            ]
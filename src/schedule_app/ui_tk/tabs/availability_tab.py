"""
Availability Tab — canvas-based grid showing lecturer × timeslot availability.

Clicking a cell toggles a lecturer's availability for that slot.
Canvas-based rendering avoids tkinter's widget count limits for large matrices.

Canvas coordinate note:
  After scrolling, canvas.canvasx(x) and canvas.canvasy(y) must be used to
  convert mouse event coordinates to canvas coordinates.
  Reference: https://docs.python.org/3/library/tkinter.html#canvas-objects

Mousewheel scrolling is supported on all three platforms.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from schedule_app.models import Config

CELL_W = 56
CELL_H = 28
HDR_W  = 160
HDR_H  = 36


class AvailabilityTab(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.cfg: Optional[Config] = None
        self._grid: dict[tuple[int, int], bool] = {}   # (l_idx, t_idx) → available
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self,
            text="Click a cell to toggle availability. Green = available.",
            font=("TkDefaultFont", 9),
        ).pack(anchor="w", padx=8, pady=4)

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=6, pady=4)

        self.canvas = tk.Canvas(container, bg="white", cursor="crosshair")
        vsb = ttk.Scrollbar(container, orient="vertical",   command=self.canvas.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<Button-1>",  self._on_click)
        # Mousewheel — platform differences require three bindings
        self.canvas.bind("<MouseWheel>",       self._on_mousewheel_y)
        self.canvas.bind("<Shift-MouseWheel>", self._on_mousewheel_x)
        self.canvas.bind("<Button-4>",  lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>",  lambda e: self.canvas.yview_scroll( 1, "units"))

    # ── public API ────────────────────────────────────────────────────────────

    def refresh(self, cfg: Config) -> None:
        self.cfg = cfg
        # Initialise grid — default to whatever the model says
        self._grid = {}
        avail_sets = [set(l.available_slot_ids) for l in cfg.lecturers]
        for l_i in range(len(cfg.lecturers)):
            for t_i, slot in enumerate(cfg.timeslots):
                self._grid[(l_i, t_i)] = slot.id in avail_sets[l_i]
        self._draw()

    def flush_to_config(self) -> None:
        if self.cfg is None: return
        for l_i, lec in enumerate(self.cfg.lecturers):
            lec.available_slot_ids = [
                self.cfg.timeslots[t_i].id
                for t_i in range(len(self.cfg.timeslots))
                if self._grid.get((l_i, t_i), False)
            ]

    # ── drawing ───────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        if self.cfg is None: return
        self.canvas.delete("all")

        L = len(self.cfg.lecturers)
        T = len(self.cfg.timeslots)
        W = HDR_W + T * CELL_W
        H = HDR_H + L * CELL_H

        self.canvas.configure(scrollregion=(0, 0, W, H))

        # Column headers (timeslots)
        for t_i, slot in enumerate(self.cfg.timeslots):
            x0 = HDR_W + t_i * CELL_W
            self.canvas.create_rectangle(x0, 0, x0 + CELL_W, HDR_H,
                                         fill="#d0d8e8", outline="#aaa")
            label = slot.label or f"{slot.start}"
            self.canvas.create_text(x0 + CELL_W // 2, HDR_H // 2,
                                    text=label, font=("TkDefaultFont", 7))

        # Row headers (lecturers) + cells
        for l_i, lec in enumerate(self.cfg.lecturers):
            y0 = HDR_H + l_i * CELL_H
            self.canvas.create_rectangle(0, y0, HDR_W, y0 + CELL_H,
                                         fill="#e8e8e8", outline="#aaa")
            self.canvas.create_text(HDR_W // 2, y0 + CELL_H // 2,
                                    text=f"{lec.id}  {lec.name}",
                                    font=("TkDefaultFont", 8), anchor="center")
            for t_i in range(T):
                x0    = HDR_W + t_i * CELL_W
                avail = self._grid.get((l_i, t_i), False)
                fill  = "#7ec87e" if avail else "#d8d8d8"
                self.canvas.create_rectangle(x0, y0, x0 + CELL_W, y0 + CELL_H,
                                             fill=fill, outline="#bbb",
                                             tags=(f"cell_{l_i}_{t_i}",))

    # ── interaction ───────────────────────────────────────────────────────────

    def _on_click(self, event: tk.Event) -> None:
        if self.cfg is None: return
        # Convert screen coords to canvas coords (accounts for scroll position)
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        if cx < HDR_W or cy < HDR_H: return

        t_i = int((cx - HDR_W) // CELL_W)
        l_i = int((cy - HDR_H) // CELL_H)
        T   = len(self.cfg.timeslots)
        L   = len(self.cfg.lecturers)
        if t_i < 0 or t_i >= T or l_i < 0 or l_i >= L: return

        key                = (l_i, t_i)
        self._grid[key]    = not self._grid.get(key, False)
        fill               = "#7ec87e" if self._grid[key] else "#d8d8d8"
        for item in self.canvas.find_withtag(f"cell_{l_i}_{t_i}"):
            self.canvas.itemconfig(item, fill=fill)

    def _on_mousewheel_y(self, event: tk.Event) -> None:
        delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")

    def _on_mousewheel_x(self, event: tk.Event) -> None:
        delta = -1 if event.delta > 0 else 1
        self.canvas.xview_scroll(delta, "units")

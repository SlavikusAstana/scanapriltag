"""Simple hover tooltips for tkinter/ttk widgets."""

from __future__ import annotations

import tkinter as tk
from typing import Callable


class ToolTip:
    """Show *text* (or dynamic text from *get_text*) after a short hover delay."""

    def __init__(
        self,
        widget: tk.Misc,
        text: str = "",
        *,
        get_text: Callable[[], str] | None = None,
        delay_ms: int = 500,
        wraplength: int = 420,
    ) -> None:
        self.widget = widget
        self._static = text
        self._get_text = get_text
        self.delay_ms = delay_ms
        self.wraplength = wraplength
        self._tip: tk.Toplevel | None = None
        self._after_id: str | None = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _text(self) -> str:
        if self._get_text is not None:
            return self._get_text()
        return self._static

    def _on_enter(self, _event=None) -> None:
        self._schedule()

    def _schedule(self) -> None:
        self._cancel_schedule()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel_schedule(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        self._after_id = None
        txt = self._text().strip()
        if not txt:
            return
        self._hide()
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=txt,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=self.wraplength,
            font=("Segoe UI", 9),
        )
        label.pack()

    def _on_leave(self, _event=None) -> None:
        self._cancel_schedule()
        self._hide()

    def _hide(self) -> None:
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None

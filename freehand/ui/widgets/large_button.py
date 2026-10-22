"""Very large, high-contrast choice buttons for motor accessibility."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from freehand.ui.theme import COLORS, RADIUS, make_font


class LargeChoiceButton(ctk.CTkButton):
    """Full-width / tall selectable area with clear idle / hover / disabled states."""

    def __init__(
        self,
        master,
        text: str,
        command: Optional[Callable] = None,
        *,
        subtitle: str = "",
        height: int = 108,
        enabled: bool = True,
        **kwargs,
    ) -> None:
        self._subtitle = subtitle
        self._enabled_flag = enabled

        super().__init__(
            master,
            text=self._compose_text(text, subtitle),
            command=command,
            height=height,
            corner_radius=RADIUS["lg"],
            fg_color=COLORS["surface"],
            hover_color=COLORS["surface_hover"],
            text_color=COLORS["text"],
            border_width=2,
            border_color=COLORS["border"],
            font=make_font(26, "semibold"),
            anchor="center",
            **kwargs,
        )
        self.set_enabled(enabled)

    @staticmethod
    def _compose_text(title: str, subtitle: str) -> str:
        if subtitle:
            return f"{title}\n{subtitle}"
        return title

    def set_enabled(self, enabled: bool) -> None:
        self._enabled_flag = enabled
        if enabled:
            self.configure(
                state="normal",
                fg_color=COLORS["surface"],
                text_color=COLORS["text"],
                border_color=COLORS["accent_dim"],
                hover_color=COLORS["surface_hover"],
            )
        else:
            self.configure(
                state="disabled",
                fg_color=COLORS["bg_soft"],
                text_color=COLORS["text_dim"],
                border_color=COLORS["border"],
            )

    def set_selected(self, selected: bool) -> None:
        if not self._enabled_flag:
            return
        if selected:
            self.configure(
                fg_color=COLORS["accent_soft"],
                border_color=COLORS["accent"],
                text_color=COLORS["text"],
            )
        else:
            self.configure(
                fg_color=COLORS["surface"],
                border_color=COLORS["accent_dim"],
                text_color=COLORS["text"],
            )

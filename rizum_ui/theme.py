"""Design tokens for the Rizum Painter UI kit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str = "Rizum Dark"
    font_size: int = 11
    radius_window: int = 10
    radius: int = 8
    radius_small: int = 6
    radius_button: int = 16
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 20
    bg: str = "#111111"
    surface: str = "#1b1b1b"
    surface_raised: str = "#222222"
    surface_control: str = "#343434"
    surface_hover: str = "rgba(255, 255, 255, 13)"
    surface_child_hover: str = "rgba(255, 255, 255, 20)"
    surface_sunken: str = "#222222"
    border: str = "#414141"
    border_soft: str = "rgba(255, 255, 255, 0)"
    border_hover: str = "#414141"
    text: str = "#e0e0e0"
    text_muted: str = "#9e9e9e"
    text_faint: str = "#666666"
    accent: str = "#ffffff"
    accent_hover: str = "#e0e0e0"
    accent_pressed: str = "#b8b8b8"
    accent_text: str = "#1b1b1b"
    blue: str = "#1473e6"
    warning: str = "#d69a38"
    danger: str = "#ff453a"
    success: str = "#37c98b"
    checkbox: str = "#ffffff"
    checkbox_checked: str = "#ffffff"
    checkbox_checked_hover: str = "#e0e0e0"
    checkbox_mark: str = "#1b1b1b"
    shadow: str = "rgba(0, 0, 0, 110)"
    duration_fast: int = 120
    duration_normal: int = 300


default_theme = Theme()

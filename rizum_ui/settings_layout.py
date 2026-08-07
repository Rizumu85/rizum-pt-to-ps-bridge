"""Canonical compact layout metrics for Painter settings panels."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScaledSettingsMetric:
    """A design-pixel value and its approved compact floor."""

    design: int
    minimum: int

    def resolve(self, dialog) -> int:
        return dialog.settingsMetric(self.design, self.minimum)


@dataclass(frozen=True)
class PainterSettingsLayoutSpec:
    """Spacing and sizing approved against the live View Roll dialog."""

    dialog_width: ScaledSettingsMetric = ScaledSettingsMetric(300, 240)
    body_margin_x: ScaledSettingsMetric = ScaledSettingsMetric(20, 15)
    body_margin_top: ScaledSettingsMetric = ScaledSettingsMetric(12, 9)
    body_margin_bottom: ScaledSettingsMetric = ScaledSettingsMetric(20, 15)
    body_spacing: ScaledSettingsMetric = ScaledSettingsMetric(2, 2)
    first_section_height: ScaledSettingsMetric = ScaledSettingsMetric(26, 20)
    section_height: ScaledSettingsMetric = ScaledSettingsMetric(36, 27)
    row_height: ScaledSettingsMetric = ScaledSettingsMetric(40, 30)
    detail_row_height: ScaledSettingsMetric = ScaledSettingsMetric(46, 35)
    row_padding_y: ScaledSettingsMetric = ScaledSettingsMetric(5, 4)
    control_height: ScaledSettingsMetric = ScaledSettingsMetric(30, 23)
    stepper_height: ScaledSettingsMetric = ScaledSettingsMetric(32, 24)
    text_spacing: ScaledSettingsMetric = ScaledSettingsMetric(2, 1)
    footer_margin_x: ScaledSettingsMetric = ScaledSettingsMetric(20, 15)
    footer_top: ScaledSettingsMetric = ScaledSettingsMetric(8, 6)
    footer_gap: ScaledSettingsMetric = ScaledSettingsMetric(6, 5)
    footer_bottom: ScaledSettingsMetric = ScaledSettingsMetric(16, 12)
    footer_row_height: ScaledSettingsMetric = ScaledSettingsMetric(32, 24)
    footer_button_height: ScaledSettingsMetric = ScaledSettingsMetric(28, 21)
    row_spacing: int = 8
    footer_button_spacing: int = 8


PAINTER_SETTINGS_LAYOUT = PainterSettingsLayoutSpec()


__all__ = [
    "PAINTER_SETTINGS_LAYOUT",
    "PainterSettingsLayoutSpec",
    "ScaledSettingsMetric",
]

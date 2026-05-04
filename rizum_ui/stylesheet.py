"""Qt stylesheet generation and application helpers."""

from __future__ import annotations

from .theme import Theme, default_theme


def build_stylesheet(theme: Theme = default_theme, mode: str = "overlay") -> str:
    """Return a Painter-friendly Qt stylesheet.

    `overlay` styles only Rizum components and explicit variants so Painter's
    host style remains visible. `full` is useful for standalone previews or
    experiments where the whole Qt surface should be controlled.
    """
    radius = theme.radius
    radius_small = theme.radius_small
    radius_button = theme.radius_button
    overlay = f"""
QWidget#RizumSurface {{
    background: {theme.bg};
    color: {theme.text};
}}

QFrame#RizumCard {{
    background: {theme.surface};
    border: 1px solid transparent;
    border-radius: {radius}px;
}}

QFrame#RizumCard:hover {{
    border-color: transparent;
}}

QFrame#RizumDialogCard {{
    background: {theme.surface};
    border: 1px solid {theme.border_hover};
    border-radius: {theme.radius_window}px;
}}

QFrame#RizumInsetSeparator {{
    background: {theme.border_hover};
    border: 0;
}}

QLabel#RizumDialogTitle {{
    color: {theme.text};
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}}

QLabel#RizumSectionTitle {{
    color: {theme.text};
    font-size: 13pt;
    font-weight: 700;
    background: transparent;
}}

QLabel#RizumFieldLabel {{
    color: {theme.text_muted};
    font-size: 13px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}

QLabel#RizumFieldLabel:hover {{
    background: transparent;
    border: 0;
}}

QLabel[muted="true"] {{
    color: {theme.text_muted};
    background: transparent;
}}

QPushButton[variant="primary"] {{
    min-height: 32px;
    padding: 5px 22px;
    color: {theme.accent_text};
    background: {theme.accent};
    border: 1px solid {theme.accent};
    border-radius: {radius_button}px;
    font-weight: 600;
}}

QPushButton[variant="primary"]:hover {{
    background: {theme.accent_hover};
    border-color: transparent;
}}

QPushButton[variant="primary"]:pressed {{
    background: {theme.accent_pressed};
    border-color: transparent;
}}

QPushButton[variant="ghost"] {{
    min-height: 32px;
    padding: 5px 12px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: {radius_small}px;
    color: {theme.text_muted};
}}

QPushButton[variant="ghost"]:hover {{
    background: #303034;
    border-color: transparent;
    color: {theme.text};
}}

QPushButton[variant="ghost"]:pressed {{
    background: #242426;
    border-color: transparent;
    color: {theme.text};
}}

QPushButton[variant="icon"] {{
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: {theme.text_muted};
}}

QPushButton[variant="icon"]:hover {{
    background: #303034;
    color: {theme.text};
}}

QPushButton[variant="icon"]:pressed {{
    background: #242426;
    color: {theme.text};
}}

QPushButton[variant="dialog-secondary"] {{
    min-height: 24px;
    max-height: 24px;
    padding: 0 18px;
    color: {theme.text};
    background: {theme.surface_control};
    border: 1px solid transparent;
    border-radius: 13px;
    font-size: 12px;
    font-weight: 400;
}}

QPushButton[variant="dialog-secondary"]:hover {{
    background: #3b3b3b;
}}

QPushButton[variant="dialog-secondary"]:pressed {{
    background: #2b2b2b;
}}

QPushButton[variant="dialog-primary"] {{
    min-height: 24px;
    max-height: 24px;
    padding: 0 18px;
    color: {theme.accent_text};
    background: {theme.accent};
    border: 1px solid transparent;
    border-radius: 13px;
    font-size: 12px;
    font-weight: 400;
}}

QPushButton[variant="dialog-primary"]:hover {{
    background: {theme.accent_hover};
}}

QPushButton[variant="dialog-primary"]:pressed {{
    background: {theme.accent_pressed};
}}

QWidget#RizumActionRow {{
    background: transparent;
}}

QWidget#RizumTransparent {{
    background: transparent;
}}

QWidget#RizumInlineCheckbox {{
    background: transparent;
    border-radius: {radius_small}px;
}}

QLabel#RizumHintLabel {{
    color: {theme.text_muted};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}

QPushButton[variant="icon"][compact="true"] {{
    min-width: 22px;
    max-width: 22px;
    min-height: 22px;
    max-height: 22px;
}}

QLabel#RizumHintLabel:hover {{
    background: transparent;
    border: 0;
}}

QWidget#RizumInlineCheckbox:hover {{
    background: {theme.surface_hover};
}}

QFrame#RizumMockInput {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {radius_small}px;
}}

QFrame#RizumMockInput:hover {{
    background: {theme.surface_hover};
    border-color: transparent;
}}

QLabel#RizumMockText {{
    color: {theme.text};
    font-size: 13px;
    background: transparent;
    border: 0;
}}

QLabel#RizumMockText:hover {{
    background: transparent;
    border: 0;
}}

QWidget#RizumMockIcon, QWidget#RizumMockIcon:hover,
QWidget#RizumChevronIcon, QWidget#RizumChevronIcon:hover,
QLabel#RizumSvgLabel, QLabel#RizumSvgLabel:hover {{
    background: transparent;
    border: 0;
}}

QFrame#RizumCollapsibleGroup {{
    background: transparent;
    border: 0;
    border-radius: 8px;
}}

QFrame#RizumCollapsibleGroup:hover {{
    background: rgba(255, 255, 255, 0.04);
    border: 0;
}}

QFrame#RizumCollapsibleGroup[hovered="true"] {{
    background: rgba(255, 255, 255, 0.04);
    border: 0;
}}

QFrame#RizumCollapsibleGroup[variant="drag"][dragging="true"] {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid transparent;
}}

QFrame#RizumCollapsibleHeader,
QFrame#RizumCollapsibleContent,
QWidget#RizumCollapsibleContentInner,
QWidget#RizumCollapsibleChevron {{
    background: transparent;
    border: 0;
}}

QFrame#RizumCollapsibleHeader:hover {{
    background: transparent;
    border: 0;
}}

QLabel#RizumCollapsibleTitle {{
    color: {theme.text};
    font-size: 13px;
    font-weight: 600;
    background: transparent;
    border: 0;
}}

QLabel#RizumCollapsibleSubtitle {{
    color: {theme.text_faint};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}

QFrame#RizumCollapsibleGroup[variant="drag"] QLabel#RizumCollapsibleTitle,
QFrame#RizumCollapsibleGroup[variant="drag"] QLabel#RizumCollapsibleSubtitle {{
    font-weight: 400;
}}

QLabel#RizumCollapsibleTitle:hover,
QLabel#RizumCollapsibleSubtitle:hover {{
    background: transparent;
    border: 0;
}}

QFrame#RizumDragTreeItemHost {{
    background: transparent;
    border: 0;
}}

QFrame#RizumDragTreeItem {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}}

QFrame#RizumDragTreeItem:hover {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid transparent;
}}

QFrame#RizumDragTreeItem[hovered="true"] {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid transparent;
}}

QFrame#RizumDragTreeItem[dragging="true"] {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid transparent;
}}

QFrame#RizumDragTreeItem[dragging="true"] QLabel,
QFrame#RizumDragTreeItem[dragging="true"] QLabel#RizumSvgLabel {{
    color: rgba(224, 224, 224, 0.2);
}}

QFrame#RizumDragTreeItem[added="true"] {{
    background: rgba(255, 255, 255, 0.12);
}}

QLabel#RizumDragItemName,
QLabel#RizumDragItemName:hover,
QLabel#RizumDragItemName:focus {{
    color: {theme.text};
    font-size: 13px;
    font-weight: 400;
    background: transparent;
    border: 0;
    outline: 0;
}}

QPushButton#RizumRemoveButton {{
    min-width: 24px;
    max-width: 24px;
    min-height: 24px;
    max-height: 24px;
    color: transparent;
    background: transparent;
    border: 0;
    border-radius: 5px;
    padding: 0;
    font-size: 13px;
    font-weight: 400;
    text-align: center;
}}

QFrame#RizumDragTreeItem:hover QPushButton#RizumRemoveButton {{
    color: transparent;
}}

QFrame#RizumDragTreeItem[hovered="true"] QPushButton#RizumRemoveButton {{
    color: transparent;
}}

QPushButton#RizumRemoveButton:hover {{
    color: {theme.danger};
    background: rgba(255, 69, 58, 44);
    border: 0;
}}

QWidget#RizumControlSlot {{
    background: transparent;
    border: 0;
}}

QFrame#RizumMockCheckbox {{
    background: transparent;
    border: 1.5px solid #ffffff;
    border-radius: 3px;
}}

QFrame#RizumMockCheckbox[checked="true"] {{
    background: #ffffff;
    border: 1.5px solid #ffffff;
}}

QFrame#RizumMockCheckbox[checked="false"] {{
    background: transparent;
    border: 1.5px solid #ffffff;
}}

QMenu#RizumPopupMenu {{
    background: {theme.surface};
    color: {theme.text};
    border: 1px solid {theme.border_hover};
    border-radius: {radius_small}px;
    padding: 4px;
    font-size: 12px;
}}

QMenu#RizumPopupMenu::item {{
    padding: 6px 22px 6px 8px;
    border-radius: 4px;
}}

QMenu#RizumPopupMenu::item:selected {{
    background: {theme.surface_hover};
    color: {theme.text};
}}
"""
    if mode == "overlay":
        return overlay

    return f"""
QWidget {{
    background: {theme.bg};
    color: {theme.text};
    selection-background-color: {theme.accent};
    selection-color: {theme.accent_text};
}}

QDialog, QWidget#RizumSurface {{
    background: {theme.bg};
}}

QFrame#RizumCard {{
    background: {theme.surface};
    border: 1px solid {theme.border_soft};
    border-radius: {radius}px;
}}

QLabel {{
    color: {theme.text};
    background: transparent;
    border: 0;
}}

QLabel:hover,
QLabel:focus {{
    background: transparent;
    border: 0;
    outline: 0;
}}

QLabel[muted="true"] {{
    color: {theme.text_muted};
}}

QLabel#RizumFieldLabel {{
    color: {theme.text_muted};
    font-size: {max(theme.font_size - 1, 8)}pt;
}}

QPushButton {{
    min-height: 32px;
    padding: 5px 18px;
    border: 1px solid transparent;
    border-radius: {radius_button}px;
    background: {theme.surface_control};
    color: {theme.text};
}}

QPushButton:hover {{
    border-color: {theme.border_hover};
    background: #3b3b3b;
}}

QPushButton:pressed {{
    background: #2b2b2b;
    border-color: transparent;
}}

QPushButton:disabled {{
    color: {theme.text_faint};
    background: #242424;
    border-color: {theme.border_soft};
}}

QPushButton[variant="primary"] {{
    color: #07110d;
    background: {theme.accent};
    border-color: {theme.accent};
    font-weight: 600;
}}

QPushButton[variant="primary"]:hover {{
    background: {theme.accent_hover};
    border-color: transparent;
}}

QPushButton[variant="primary"]:pressed {{
    background: {theme.accent_pressed};
    border-color: transparent;
}}

QPushButton[variant="ghost"] {{
    background: transparent;
    border-color: transparent;
}}

QPushButton[variant="ghost"]:hover {{
    background: #303034;
    border-color: transparent;
    color: {theme.text};
}}

QPushButton[variant="ghost"]:pressed {{
    background: #242426;
    border-color: transparent;
    color: {theme.text};
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    min-height: 32px;
    padding: 4px 10px;
    border: 1px solid transparent;
    border-radius: {radius_small}px;
    background: {theme.surface_raised};
    color: {theme.text};
}}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 20px;
    background: transparent;
    border: 0;
}}

QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {theme.border_hover};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {theme.border_hover};
}}

QComboBox::drop-down {{
    width: 22px;
    border: 0;
}}

QCheckBox {{
    spacing: 10px;
    color: {theme.text_muted};
    background: transparent;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 0;
    background: {theme.surface_control};
}}

QCheckBox::indicator:checked {{
    background: {theme.checkbox_checked};
}}

QCheckBox::indicator:checked:pressed {{
    background: {theme.checkbox_checked_hover};
}}

QCheckBox::indicator:hover {{
    background: #454545;
}}

QCheckBox::indicator:checked:hover {{
    background: {theme.checkbox_checked_hover};
}}

QTreeWidget, QListWidget, QTableWidget {{
    background: {theme.surface};
    border: 1px solid transparent;
    border-radius: {radius_small}px;
    alternate-background-color: #202020;
}}

QTreeWidget::item, QListWidget::item {{
    min-height: 30px;
    padding: 4px 10px;
    border-radius: {radius_small}px;
}}

QTreeWidget::item:selected, QListWidget::item:selected {{
    color: {theme.text};
    background: rgba(255, 255, 255, 20);
}}

QTreeWidget:hover, QListWidget:hover, QTableWidget:hover {{
    border-color: {theme.border_hover};
}}

QProgressBar {{
    min-height: 12px;
    border: 0;
    border-radius: 4px;
    background: {theme.surface_sunken};
    text-align: center;
}}

QProgressBar::chunk {{
    border-radius: 0;
    background: {theme.blue};
}}

QScrollBar:vertical, QScrollBar:horizontal {{
    background: transparent;
    border: 0;
    width: 10px;
    height: 10px;
}}

QScrollBar::handle {{
    background: #3c424a;
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:hover {{
    background: #4a525d;
}}

QToolTip {{
    color: {theme.text};
    background: {theme.surface};
    border: 1px solid #414141;
    border-radius: 5px;
    padding: 1px 6px;
    margin: 0;
    font-size: 12px;
    font-weight: 400;
}}
""" + overlay


def apply_theme(widget_or_app, theme: Theme = default_theme, mode: str = "overlay") -> str:
    """Apply the generated stylesheet and return it for debugging."""
    stylesheet = build_stylesheet(theme, mode=mode)
    widget_or_app.setStyleSheet(stylesheet)
    return stylesheet

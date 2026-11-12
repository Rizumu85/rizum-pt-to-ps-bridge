"""Compact feedback dialogs shared by the Painter dock and Bridge."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .localization import text
from .ui_kit import (
    PAINTER_DIALOG_STYLE,
    PAINTER_SETTINGS_LAYOUT,
    PainterSettingsDialog,
    SecondaryActionButton,
    apply_theme,
    default_theme,
    make_inset_separator,
)


def _make_dialog_action(text, primary=False):
    theme = PAINTER_DIALOG_STYLE
    if primary:
        colors = (
            theme["accent"],
            theme["accent_hover"],
            theme["accent_pressed"],
            theme["accent_text"],
        )
    else:
        colors = (
            theme["control"],
            theme["control_hover"],
            theme["control_pressed"],
            theme["text"],
        )
    return SecondaryActionButton(
        text,
        *colors,
        default_theme.radius_small,
    )


class CompactDialogShell:
    """Shared native-chrome shell for compact bridge feedback dialogs."""

    def __init__(
        self,
        QtWidgets,
        parent,
        title,
        object_name,
        *,
        width=320,
        body_spacing=10,
    ):
        self.QtWidgets = QtWidgets
        self.dialog = PainterSettingsDialog(parent)
        self.dialog.setObjectName(object_name)
        self.dialog.setWindowTitle(title)
        self.dialog.setModal(True)
        self.dialog.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._width = int(width)
        self._body_spacing = int(body_spacing)
        self._buttons = []
        self._scale_callbacks = []

        surface_layout = self.dialog.settingsSurfaceLayout()
        self.body = QtWidgets.QWidget()
        self.body.setObjectName("RizumCompactDialogBody")
        self.body_layout = QtWidgets.QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        surface_layout.addWidget(self.body)

        self.footer_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            thickness=1,
        )
        self.footer_separator.setObjectName("RizumCompactDialogFooterDivider")
        surface_layout.addWidget(self.footer_separator)

        self.footer = QtWidgets.QWidget()
        self.footer.setObjectName("RizumCompactDialogFooter")
        self.footer_outer = QtWidgets.QVBoxLayout(self.footer)
        self.footer_outer.setContentsMargins(0, 0, 0, 0)
        self.footer_outer.setSpacing(0)
        self.footer_row = QtWidgets.QWidget()
        self.footer_row.setObjectName("RizumCompactDialogFooterRow")
        self.footer_layout = QtWidgets.QHBoxLayout(self.footer_row)
        self.footer_layout.setContentsMargins(0, 0, 0, 0)
        self.footer_layout.setSpacing(
            PAINTER_SETTINGS_LAYOUT.footer_button_spacing
        )
        self.footer_outer.addWidget(self.footer_row)
        surface_layout.addWidget(self.footer)

    def add_action(self, text, *, primary=False, minimum=68, maximum=112):
        button = _make_dialog_action(text, primary=primary)
        self._buttons.append((button, int(minimum), int(maximum)))
        return button

    def add_scale_callback(self, callback):
        self._scale_callbacks.append(callback)

    def finalize(self):
        apply_theme(self.dialog, mode="overlay")
        self.dialog.syncSettingsUiScale()
        self.dialog.settingsUiScaleChanged.connect(self._apply_ui_scale)
        self._apply_ui_scale(self.dialog.settingsUiScale())
        self.dialog._rizum_compact_shell = self
        return self.dialog

    def _metric(self, pixels, minimum=None):
        return self.dialog.settingsMetric(pixels, minimum)

    def _apply_ui_scale(self, _scale):
        body_margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        self.body_layout.setContentsMargins(
            body_margin,
            PAINTER_SETTINGS_LAYOUT.body_margin_top.resolve(self.dialog),
            body_margin,
            PAINTER_SETTINGS_LAYOUT.body_margin_bottom.resolve(self.dialog),
        )
        self.body_layout.setSpacing(self._metric(self._body_spacing))

        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(
            self.dialog
        )
        footer_top = PAINTER_SETTINGS_LAYOUT.footer_top.resolve(self.dialog)
        footer_gap = PAINTER_SETTINGS_LAYOUT.footer_gap.resolve(self.dialog)
        footer_bottom = PAINTER_SETTINGS_LAYOUT.footer_bottom.resolve(self.dialog)
        footer_row_height = PAINTER_SETTINGS_LAYOUT.footer_row_height.resolve(
            self.dialog
        )
        self.footer_outer.setContentsMargins(
            0,
            footer_top + footer_gap,
            0,
            footer_bottom,
        )
        self.footer_row.setFixedHeight(footer_row_height)
        self.footer.setFixedHeight(
            footer_top + footer_gap + footer_row_height + footer_bottom
        )
        self.footer_layout.setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        self.footer_separator.layout().setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )

        button_height = PAINTER_SETTINGS_LAYOUT.footer_button_height.resolve(
            self.dialog
        )
        scale = self.dialog.settingsUiScale()
        for button, minimum, maximum in self._buttons:
            button.setCompactHeight(button_height)
            button.setFixedWidth(
                max(
                    self._metric(minimum),
                    min(
                        int(round(maximum * scale)),
                        button.sizeHint().width() + self._metric(8, 6),
                    ),
                )
            )

        for callback in self._scale_callbacks:
            callback(scale)

        width = self._metric(self._width)
        self.dialog.setFixedWidth(width)
        self._restyle()
        layout = self.dialog.layout()
        layout.invalidate()
        self.dialog.settingsSurfaceLayout().invalidate()
        # Word-wrapped labels know their height only for a given width; sizing
        # from the plain size hint clipped the last line of longer messages.
        height = layout.heightForWidth(width) if layout.hasHeightForWidth() else -1
        if height > 0:
            self.dialog.setFixedHeight(max(height, layout.minimumSize().height()))
        else:
            self.dialog.adjustSize()

    def _restyle(self):
        theme = PAINTER_DIALOG_STYLE
        self.dialog._update_surface_stylesheet()
        surface = self.dialog.settingsSurface()
        surface.setStyleSheet(
            surface.styleSheet()
            + f"""
QFrame#RizumPainterSettingsSurface {{
    background: {theme["surface"]};
}}
QWidget#RizumCompactDialogBody,
QWidget#RizumCompactDialogFooter,
QWidget#RizumCompactDialogFooterRow,
QWidget#RizumCompactDialogFooterDivider {{
    background: transparent;
    border: 0;
}}
QWidget#RizumCompactDialogFooterDivider QFrame#RizumInsetSeparator {{
    background: #3a3b3e;
}}
"""
        )


def build_modal_message(QtWidgets, parent, title, message):
    shell = CompactDialogShell(
        QtWidgets,
        parent,
        title,
        "RizumFeedbackDialog",
        width=300,
        body_spacing=0,
    )
    message_label = QtWidgets.QLabel(message)
    message_label.setObjectName("RizumSettingsItemMeta")
    message_label.setWordWrap(True)
    message_label.setMinimumHeight(42)
    shell.body_layout.addWidget(message_label)
    shell.add_scale_callback(
        lambda _scale: message_label.setMinimumHeight(shell._metric(42, 32))
    )

    shell.footer_layout.addStretch(1)
    ok_button = shell.add_action(
        text("ok"),
        primary=True,
        minimum=68,
        maximum=96,
    )
    ok_button.clicked.connect(shell.dialog.accept)
    shell.footer_layout.addWidget(ok_button)

    dialog = shell.finalize()
    dialog._rizum_message_label = message_label
    dialog._rizum_ok_button = ok_button
    return dialog


def run_modal(dialog):
    """Show a modal dialog and delete it once it is answered."""
    # A dialog is a child of the dock widget: left alone after exec(), every
    # one ever opened stayed there hidden until the plugin closed.
    result = dialog.exec()
    dialog.deleteLater()
    return result


def show_modal_message(QtWidgets, parent, title, message):
    return run_modal(build_modal_message(QtWidgets, parent, title, message))


def build_modal_question(QtWidgets, parent, title, message, confirm_text):
    """A message with Cancel and one confirming action; accepted means confirmed."""
    shell = CompactDialogShell(
        QtWidgets,
        parent,
        title,
        "RizumFeedbackDialog",
        width=320,
        body_spacing=0,
    )
    message_label = QtWidgets.QLabel(message)
    message_label.setObjectName("RizumSettingsItemMeta")
    message_label.setWordWrap(True)
    shell.body_layout.addWidget(message_label)

    shell.footer_layout.addStretch(1)
    cancel_button = shell.add_action(text("cancel"), minimum=68, maximum=104)
    cancel_button.clicked.connect(shell.dialog.reject)
    shell.footer_layout.addWidget(cancel_button)
    confirm_button = shell.add_action(confirm_text, primary=True, minimum=68, maximum=128)
    confirm_button.clicked.connect(shell.dialog.accept)
    shell.footer_layout.addWidget(confirm_button)

    dialog = shell.finalize()
    dialog._rizum_message_label = message_label
    dialog._rizum_confirm_button = confirm_button
    dialog._rizum_cancel_button = cancel_button
    return dialog


def ask_modal_question(QtWidgets, parent, title, message, confirm_text):
    dialog = build_modal_question(QtWidgets, parent, title, message, confirm_text)
    return run_modal(dialog) == QtWidgets.QDialog.DialogCode.Accepted


class ProgressTrack(QtWidgets.QWidget):
    """A thin progress line drawn like the desktop mapper's.

    QProgressBar's style-sheet chunks render as separate segments on Windows,
    so the track is painted: a solid fill for a count, and a light sweeping
    across for work without one.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._minimum = 0
        self._maximum = 0
        self._value = 0
        self._sweep = QtCore.QVariantAnimation(self)
        self._sweep.setStartValue(0.0)
        self._sweep.setEndValue(1.0)
        self._sweep.setDuration(1100)
        self._sweep.setLoopCount(-1)
        self._sweep.valueChanged.connect(self.update)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def minimum(self):
        return self._minimum

    def maximum(self):
        return self._maximum

    def value(self):
        return self._value

    def setRange(self, minimum, maximum):
        self._minimum = int(minimum)
        self._maximum = int(maximum)
        self._sync_sweep()
        self.update()

    def setValue(self, value):
        self._value = int(value)
        self.update()

    def _indeterminate(self):
        return self._maximum <= self._minimum

    def _sync_sweep(self):
        # The sweep runs only while it can be seen, so a hidden dialog keeps
        # no timer alive.
        running = self._sweep.state() == QtCore.QAbstractAnimation.State.Running
        wanted = self._indeterminate() and self.isVisible()
        if wanted and not running:
            self._sweep.start()
        elif not wanted and running:
            self._sweep.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_sweep()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._sync_sweep()

    def paintEvent(self, _event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        bounds = QtCore.QRectF(self.rect())
        radius = bounds.height() / 2
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(bounds, radius, radius)
        painter.setClipPath(clip)
        painter.fillRect(bounds, QtGui.QColor(PAINTER_DIALOG_STYLE["control"]))
        fill = QtGui.QColor(PAINTER_DIALOG_STYLE["accent"])
        if self._indeterminate():
            segment = max(48.0, bounds.width() * 0.28)
            left = -segment + (bounds.width() + segment) * float(self._sweep.currentValue() or 0.0)
            painter.fillRect(QtCore.QRectF(left, 0, segment, bounds.height()), fill)
        else:
            span = self._maximum - self._minimum
            fraction = max(0.0, min(1.0, (self._value - self._minimum) / span))
            painter.fillRect(QtCore.QRectF(0, 0, bounds.width() * fraction, bounds.height()), fill)
        painter.end()


class CompactProgressDialog:
    """The mapper's Apply card as a Painter dialog, for Export and Photoshop jobs.

    The user asked that Export read exactly as Bridge does: the step's title
    with its number beside it, what is being worked on, a thin line, and the
    real count under it next to Cancel. A count is never a percentage of the
    whole export: steps have different units and each counts its own work.
    """

    def __init__(self, panel, title, heading, *, cancellable=True, modal=True):
        self.QtCore = panel.QtCore
        self.QtWidgets = panel.QtWidgets
        self._cancellable = cancellable
        self._cancelled = False
        self._finishing = False
        self._minimum = 0
        self._maximum = 0

        self.shell = CompactDialogShell(
            self.QtWidgets,
            panel.widget,
            title,
            "RizumProgressDialog",
            width=340,
            body_spacing=12,
        )
        heading_row = self.QtWidgets.QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        self.heading_label = self.QtWidgets.QLabel(heading)
        self.heading_label.setObjectName("RizumSettingsItemName")
        self.step_label = self.QtWidgets.QLabel("")
        self.step_label.setObjectName("RizumSettingsItemMeta")
        heading_row.addWidget(self.heading_label, 1)
        heading_row.addWidget(self.step_label)
        self.shell.body_layout.addLayout(heading_row)

        self.message_label = self.QtWidgets.QLabel("")
        self.message_label.setObjectName("RizumSettingsItemMeta")
        self.message_label.setWordWrap(True)
        self.shell.body_layout.addWidget(self.message_label)

        self.progress_bar = ProgressTrack()
        self.progress_bar.setRange(0, 0)
        self.shell.body_layout.addWidget(self.progress_bar)

        action_row = self.QtWidgets.QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        self.count_label = self.QtWidgets.QLabel("")
        self.count_label.setObjectName("RizumSettingsItemMeta")
        action_row.addWidget(self.count_label, 1)
        self.cancel_button = None
        if cancellable:
            self.cancel_button = self.shell.add_action(
                text("cancel"),
                minimum=72,
                maximum=104,
            )
            self.cancel_button.clicked.connect(self._request_cancel)
            action_row.addWidget(self.cancel_button)
        self.shell.body_layout.addLayout(action_row)
        # The card has no footer: Cancel sits on the count's line, as in the mapper.
        self.shell.footer_separator.hide()
        self.shell.footer.hide()
        self.shell.add_scale_callback(self._apply_ui_scale)
        self.dialog = self.shell.finalize()
        self.dialog.rejected.connect(self._window_rejected)
        modality = self.QtCore.Qt.WindowModality
        self.dialog.setWindowModality(modality.ApplicationModal if modal else modality.NonModal)
        self.dialog._rizum_progress_controller = self

    def _apply_ui_scale(self, _scale):
        self.progress_bar.setFixedHeight(self.shell._metric(4, 3))
        # Both lines keep their height while they are empty, so the dialog
        # does not jump when a message or a count starts or ends.
        for label in (self.message_label, self.count_label):
            label.setMinimumHeight(label.fontMetrics().height())

    def _request_cancel(self):
        if self._cancelled or not self._cancellable:
            return
        self._cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText(text("cancelling"))

    def _window_rejected(self):
        if not self._finishing:
            self._request_cancel()

    def show(self):
        self.dialog.show()

    def close(self):
        self._finishing = True
        self.dialog.close()
        self.dialog.deleteLater()

    def setHeading(self, heading, step=""):
        """Name the step being worked on; ``step`` is its "Step 2 of 3"."""
        self.heading_label.setText(str(heading))
        self.step_label.setText(str(step))

    def setRange(self, minimum, maximum):
        self._minimum = int(minimum)
        self._maximum = int(maximum)
        self.progress_bar.setRange(self._minimum, self._maximum)
        self._update_count(self.progress_bar.value())

    def setValue(self, value):
        self.progress_bar.setValue(int(value))
        self._update_count(value)

    def _update_count(self, value):
        if self._maximum <= self._minimum:
            self.count_label.clear()
            return
        done = max(self._minimum, min(self._maximum, int(value))) - self._minimum
        self.count_label.setText(f"{done} / {self._maximum - self._minimum}")

    def setLabelText(self, text):
        self.message_label.setText(str(text))

    def wasCanceled(self):
        return self._cancelled

"""Painter Settings dialog."""

from __future__ import annotations

from .ui_kit import (
    PLUGIN_VERSION,
    PAINTER_DIALOG_STYLE,
    PAINTER_SETTINGS_LAYOUT,
    PainterSettingsDialog,
    SecondaryActionButton,
    apply_theme,
    default_theme,
    make_combo_input,
    make_compact_stepper,
    make_icon_button,
    make_inset_separator,
)


def _section_label(QtWidgets, text):
    label = QtWidgets.QLabel(text)
    label.setObjectName("RizumSettingsSection")
    label.setFixedHeight(22)
    return label


def _settings_row(QtWidgets, label_text, meta_text, control):
    row = QtWidgets.QWidget()
    row.setObjectName("RizumSettingsRow")
    row.setFixedHeight(42 if meta_text else 36)
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(8, 0, 8, 0)
    layout.setSpacing(12)

    text_block = QtWidgets.QWidget()
    text_layout = QtWidgets.QVBoxLayout(text_block)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(1)
    label = QtWidgets.QLabel(label_text)
    label.setObjectName("RizumDialogTitle")
    text_layout.addWidget(label)
    if meta_text:
        meta = QtWidgets.QLabel(meta_text)
        meta.setObjectName("RizumSettingsMeta")
        text_layout.addWidget(meta)
    layout.addWidget(text_block, 1)
    layout.addWidget(control, 0)
    return row


def _settings_label(QtWidgets, text, object_name):
    label = QtWidgets.QLabel(text)
    label.setObjectName(object_name)
    return label


def _settings_section(QtWidgets, text, first=False):
    label = _settings_label(QtWidgets, text.upper(), "RizumSettingsSection")
    metric = (
        PAINTER_SETTINGS_LAYOUT.first_section_height
        if first
        else PAINTER_SETTINGS_LAYOUT.section_height
    )
    label._rizum_layout_metric = metric
    label.setFixedHeight(metric.design)
    return label


def _settings_frame_row(QtWidgets, height=40):
    row = QtWidgets.QFrame()
    row.setObjectName("RizumSettingsRow")
    row._rizum_base_height = height
    row.setFixedHeight(height)
    layout = QtWidgets.QHBoxLayout(row)
    layout.setContentsMargins(
        0,
        PAINTER_SETTINGS_LAYOUT.row_padding_y.design,
        0,
        PAINTER_SETTINGS_LAYOUT.row_padding_y.design,
    )
    layout.setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)
    return row, layout


def _settings_text_block(QtWidgets, name, meta=""):
    widget = QtWidgets.QWidget()
    widget.setObjectName("RizumSettingsTexts")
    layout = QtWidgets.QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    layout.addWidget(_settings_label(QtWidgets, name, "RizumSettingsItemName"))
    if meta:
        layout.addWidget(_settings_label(QtWidgets, meta, "RizumSettingsItemMeta"))
    return widget


def _make_settings_toggle(QtCore, QtGui, QtWidgets, checked=False):
    class _SettingsToggle(QtWidgets.QAbstractButton):
        BASE_WIDTH = 36
        BASE_HEIGHT = 20
        MIN_HEIGHT = 15

        def __init__(self):
            super().__init__()
            self.setObjectName("RizumSettingsToggle")
            self.setCheckable(True)
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self.setStyleSheet("background: transparent; border: 0;")
            self._compact_height = self.BASE_HEIGHT
            self._knob_margin = 3.0
            self._knob_size = 14.0
            self._offset = 0.0
            self._animation = None
            self.toggled.connect(self._animate_to_state)
            self.setCompactHeight(self.BASE_HEIGHT)
            self.setChecked(bool(checked))

        def _knob_travel(self):
            return max(
                0.0,
                float(self.width()) - self._knob_size - self._knob_margin * 2,
            )

        def setCompactHeight(self, height):
            if self._animation is not None:
                self._animation.stop()
                self._animation = None
            self._compact_height = max(self.MIN_HEIGHT, int(round(height)))
            scale = self._compact_height / float(self.BASE_HEIGHT)
            self._knob_margin = 3.0 * scale
            self._knob_size = 14.0 * scale
            self.setFixedSize(
                max(27, int(round(self.BASE_WIDTH * scale))),
                self._compact_height,
            )
            self._offset = self._knob_travel() if self.isChecked() else 0.0
            self.updateGeometry()
            self.update()

        def getOffset(self):
            return self._offset

        def setOffset(self, value):
            self._offset = float(value)
            self.update()

        offset = QtCore.Property(float, getOffset, setOffset)

        def _animate_to_state(self, enabled):
            if self._animation is not None:
                self._animation.stop()
            animation = QtCore.QPropertyAnimation(self, b"offset", self)
            animation.setDuration(180)
            animation.setStartValue(self._offset)
            animation.setEndValue(self._knob_travel() if enabled else 0.0)
            animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._animation = animation
            animation.start()

        def paintEvent(self, event):
            del event
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            track = QtCore.QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(
                QtGui.QColor(PAINTER_DIALOG_STYLE["accent"])
                if self.isChecked()
                else QtGui.QColor(PAINTER_DIALOG_STYLE["control"])
            )
            painter.drawRoundedRect(track, track.height() / 2.0, track.height() / 2.0)
            painter.setBrush(QtGui.QColor(PAINTER_DIALOG_STYLE["muted"]))
            painter.drawEllipse(
                QtCore.QRectF(
                    self._knob_margin + self._offset,
                    self._knob_margin,
                    self._knob_size,
                    self._knob_size,
                )
            )
            painter.end()

    return _SettingsToggle()


def _make_settings_reveal_row(QtCore, QtWidgets, content, expanded_height):
    class _SettingsRevealRow(QtWidgets.QFrame):
        def __init__(self):
            super().__init__()
            self.setObjectName("RizumSettingsRevealRow")
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self.setStyleSheet("background: transparent; border: 0;")
            self._expanded_height = int(expanded_height)
            self._gap = PAINTER_SETTINGS_LAYOUT.body_spacing.design
            self._progress = 1.0
            self._gap_layout = None
            self._geometry_callback = None
            self._animation = None
            reveal_layout = QtWidgets.QVBoxLayout(self)
            reveal_layout.setContentsMargins(0, 0, 0, 0)
            reveal_layout.setSpacing(0)
            reveal_layout.addWidget(content)
            self.setFixedHeight(self._expanded_height)

        def setExpandedHeight(self, height):
            self._expanded_height = max(0, int(round(height)))
            self._sync_geometry()

        def expandedHeight(self):
            return self._expanded_height

        def setGapLayout(self, layout):
            self._gap_layout = layout
            self._sync_geometry()

        def setGap(self, gap):
            self._gap = max(0, int(round(gap)))
            self._sync_geometry()

        def setGeometryCallback(self, callback):
            self._geometry_callback = callback

        def _sync_geometry(self):
            progress = max(0.0, min(1.0, self._progress))
            self.setFixedHeight(round(self._expanded_height * progress))
            if self._gap_layout is not None:
                self._gap_layout.setSpacing(round(self._gap * progress))
            if self._geometry_callback is not None:
                self._geometry_callback(progress)

        def getRevealProgress(self):
            return self._progress

        def setRevealProgress(self, value):
            self._progress = float(value)
            self._sync_geometry()

        revealProgress = QtCore.Property(
            float,
            getRevealProgress,
            setRevealProgress,
        )

        def setExpanded(self, expanded, animate=True):
            target = 1.0 if expanded else 0.0
            self.setAttribute(
                QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents,
                not expanded,
            )
            if self._animation is not None:
                self._animation.stop()
            if not animate:
                self.setRevealProgress(target)
                return
            animation = QtCore.QPropertyAnimation(self, b"revealProgress", self)
            animation.setDuration(
                max(100, round(180 * abs(target - self._progress)))
            )
            animation.setStartValue(self._progress)
            animation.setEndValue(target)
            animation.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            self._animation = animation
            animation.start()

    return _SettingsRevealRow()


class SettingsDialog:
    """Global Painter-side bridge settings."""

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtGui = panel.QtGui
        self.QtWidgets = panel.QtWidgets

        self.dialog = PainterSettingsDialog(panel.widget)
        self.dialog.setObjectName("RizumSettingsDialog")
        self.dialog.setWindowTitle("Settings")
        self.dialog.setModal(True)
        self.dialog.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Fixed,
            self.QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._settings_sections = []
        self._settings_rows = []
        self._text_blocks = []
        self._base_height = None
        self._design_height = None
        self._loading_values = False

        surface_layout = self.dialog.settingsSurfaceLayout()

        body = self.QtWidgets.QWidget()
        body.setObjectName("RizumSettingsBody")
        body_layout = self.QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(
            PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
            PAINTER_SETTINGS_LAYOUT.body_margin_top.design,
            PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
            PAINTER_SETTINGS_LAYOUT.body_margin_bottom.design,
        )
        body_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.body_spacing.design)
        self._settings_body = body
        self._body_layout = body_layout

        export_section = _settings_section(self.QtWidgets, "Export", first=True)
        self._settings_sections.append(export_section)
        body_layout.addWidget(export_section)

        padding_stack = self.QtWidgets.QWidget()
        padding_stack.setObjectName("RizumSettingsPaddingStack")
        padding_stack_layout = self.QtWidgets.QVBoxLayout(padding_stack)
        padding_stack_layout.setContentsMargins(0, 0, 0, 0)
        padding_stack_layout.setSpacing(0)

        self.infinite_padding = _make_settings_toggle(self.QtCore, self.QtGui, self.QtWidgets)
        padding_row, padding_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(padding_row)
        padding_texts = self._make_text_block("Padding", "Infinite")
        self.padding_meta = padding_texts.findChild(self.QtWidgets.QLabel, "RizumSettingsItemMeta")
        padding_layout.addWidget(padding_texts)
        padding_layout.addStretch(1)
        padding_layout.addWidget(self.infinite_padding)
        padding_stack_layout.addWidget(padding_row)

        dilation_row, dilation_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(dilation_row)
        dilation_layout.addWidget(self._make_text_block("Dilation", "px"))
        dilation_layout.addStretch(1)
        self.dilation_stepper = make_compact_stepper(8, minimum=0, maximum=999, step=1)
        dilation_layout.addWidget(self.dilation_stepper)
        self.dilation_reveal = _make_settings_reveal_row(
            self.QtCore,
            self.QtWidgets,
            dilation_row,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self.dilation_reveal.setGapLayout(padding_stack_layout)
        self.dilation_reveal.setGeometryCallback(self._sync_dialog_height)
        padding_stack_layout.addWidget(self.dilation_reveal)
        body_layout.addWidget(padding_stack)

        self.bit_depth = make_combo_input([("Texture Set", None), ("8-bit", 8), ("16-bit", 16)])
        self.bit_depth.setFitToContents(False)
        self.bit_depth.setFixedWidth(126)
        bit_depth_row, bit_depth_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.row_height.design,
        )
        self._settings_rows.append(bit_depth_row)
        bit_depth_layout.addWidget(_settings_label(self.QtWidgets, "Bit depth", "RizumSettingsItemName"))
        bit_depth_layout.addStretch(1)
        bit_depth_layout.addWidget(self.bit_depth)
        body_layout.addWidget(bit_depth_row)

        self.export_uv_map = _make_settings_toggle(
            self.QtCore,
            self.QtGui,
            self.QtWidgets,
        )
        uv_map_row, uv_map_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.detail_row_height.design,
        )
        self._settings_rows.append(uv_map_row)
        self.uv_map_texts = self._make_text_block(
            "UV map",
            "Add wireframe as the top Photoshop layer",
        )
        uv_map_layout.addWidget(self.uv_map_texts)
        uv_map_layout.addStretch(1)
        uv_map_layout.addWidget(self.export_uv_map)
        body_layout.addWidget(uv_map_row)

        photoshop_section = _settings_section(self.QtWidgets, "Photoshop")
        self._settings_sections.append(photoshop_section)
        body_layout.addWidget(photoshop_section)
        path_row, path_row_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.row_height.design,
        )
        self._settings_rows.append(path_row)
        self.path_field = self.QtWidgets.QFrame()
        self.path_field.setObjectName("RizumSettingsMockSelect")
        self.path_field.setFixedHeight(PAINTER_SETTINGS_LAYOUT.control_height.design)
        path_layout = self.QtWidgets.QHBoxLayout(self.path_field)
        path_layout.setContentsMargins(8, 0, 8, 0)
        path_layout.setSpacing(6)
        self.photoshop_path = self.QtWidgets.QLineEdit()
        self.photoshop_path.setObjectName("RizumSettingsPathInput")
        self.photoshop_path.setPlaceholderText("Photoshop.exe")
        self.photoshop_path.setFrame(False)
        self.photoshop_path.setClearButtonEnabled(False)
        self.photoshop_path.setCursorPosition(0)
        self.photoshop_path.setAlignment(self.panel.QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.photoshop_path.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.browse_button = make_icon_button("folder.svg", "Browse executable", size=14, compact=False)
        self.browse_button.setFixedSize(26, 26)
        self.browse_button.clicked.connect(self.browse_photoshop)
        path_layout.addWidget(self.photoshop_path, 1, self.panel.QtCore.Qt.AlignmentFlag.AlignVCenter)
        path_row_layout.addWidget(self.path_field, 1)
        path_row_layout.addWidget(self.browse_button)
        body_layout.addWidget(path_row)

        about_section = _settings_section(self.QtWidgets, "About")
        self._settings_sections.append(about_section)
        body_layout.addWidget(about_section)
        version_row, version_layout = _settings_frame_row(
            self.QtWidgets,
            PAINTER_SETTINGS_LAYOUT.row_height.design,
        )
        self._settings_rows.append(version_row)
        version_layout.addWidget(_settings_label(self.QtWidgets, "Version", "RizumSettingsItemName"))
        version_layout.addStretch(1)
        version_layout.addWidget(_settings_label(self.QtWidgets, PLUGIN_VERSION, "RizumSettingsItemMeta"))
        body_layout.addWidget(version_row)

        surface_layout.addWidget(body)
        self._footer_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            thickness=1,
        )
        self._footer_separator.setObjectName("RizumSettingsFooterDivider")
        surface_layout.addWidget(self._footer_separator)

        footer = self.QtWidgets.QWidget()
        footer.setObjectName("RizumSettingsFooter")
        footer_outer = self.QtWidgets.QVBoxLayout(footer)
        footer_outer.setContentsMargins(0, 0, 0, 0)
        footer_outer.setSpacing(0)
        footer_row = self.QtWidgets.QWidget()
        footer_row.setObjectName("RizumSettingsFooterRow")
        footer_layout = self.QtWidgets.QHBoxLayout(footer_row)
        footer_layout.setContentsMargins(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
        )
        footer_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.footer_button_spacing)
        self.footer_hint = _settings_label(
            self.QtWidgets,
            "Changes save automatically",
            "RizumSettingsFooterHint",
        )
        footer_layout.addWidget(self.footer_hint)
        footer_layout.addStretch(1)
        self.done_button = SecondaryActionButton(
            "Done",
            PAINTER_DIALOG_STYLE["accent"],
            PAINTER_DIALOG_STYLE["accent_hover"],
            PAINTER_DIALOG_STYLE["accent_pressed"],
            PAINTER_DIALOG_STYLE["accent_text"],
            default_theme.radius_small,
        )
        self.done_button.clicked.connect(self.save)
        footer_layout.addWidget(self.done_button)
        footer_outer.addWidget(footer_row)
        surface_layout.addWidget(footer)
        self._footer = footer
        self._footer_outer = footer_outer
        self._footer_row = footer_row
        self._footer_layout = footer_layout

        self._bind_toggle_row(padding_row, self.infinite_padding)
        self._bind_toggle_row(uv_map_row, self.export_uv_map)
        self.infinite_padding.toggled.connect(self._sync_padding_mode)
        self.infinite_padding.toggled.connect(self._save_live)
        self.dilation_stepper.valueChanged.connect(self._save_live)
        self.bit_depth.currentIndexChanged.connect(self._save_live)
        self.export_uv_map.toggled.connect(self._save_live)
        self.photoshop_path.editingFinished.connect(self._save_live)

        apply_theme(self.dialog, mode="overlay")
        self.dialog.syncSettingsUiScale()
        self.load_values()
        self.dialog.settingsUiScaleChanged.connect(self._apply_ui_scale)
        self._apply_ui_scale(self.dialog.settingsUiScale())

    def open(self):
        self.load_values()
        return self.dialog.exec()

    def _make_text_block(self, name, meta=""):
        block = _settings_text_block(self.QtWidgets, name, meta)
        block._rizum_name_label = block.findChild(
            self.QtWidgets.QLabel,
            "RizumSettingsItemName",
        )
        block._rizum_meta_label = block.findChild(
            self.QtWidgets.QLabel,
            "RizumSettingsItemMeta",
        )
        self._text_blocks.append(block)
        return block

    def _metric(self, pixels, minimum=None):
        return self.dialog.settingsMetric(pixels, minimum)

    def _text_font(self, pixel_size, weight):
        font = self.QtGui.QFont(self.dialog.font())
        font.setPixelSize(self._metric(pixel_size))
        font.setWeight(weight)
        return font

    def _bind_toggle_row(self, row, toggle):
        def press(event):
            if event.button() == self.QtCore.Qt.MouseButton.LeftButton:
                toggle.toggle()
                event.accept()
                return
            self.QtWidgets.QFrame.mousePressEvent(row, event)

        row.mousePressEvent = press

    def _current_extra_height(self):
        progress = max(
            0.0,
            min(1.0, self.dilation_reveal.getRevealProgress()),
        )
        return round(self.dilation_reveal.expandedHeight() * progress) + round(
            self._body_layout.spacing() * progress
        )

    def _sync_dialog_height(self, _progress=0.0):
        del _progress
        if self._base_height is None:
            return
        self.dialog.setFixedHeight(
            self._base_height + self._current_extra_height()
        )
        self.dialog.updateGeometry()

    def _required_width(self):
        metric = self._metric
        body_margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        footer_need = (
            self.footer_hint.sizeHint().width()
            + self.done_button.width()
            + PAINTER_SETTINGS_LAYOUT.footer_button_spacing
            + 2 * footer_margin
        )
        bit_depth_need = (
            self.bit_depth.width()
            + PAINTER_SETTINGS_LAYOUT.row_spacing
            + self._settings_rows[2].layout().itemAt(0).widget().sizeHint().width()
            + 2 * body_margin
        )
        uv_map_need = (
            self.uv_map_texts.sizeHint().width()
            + PAINTER_SETTINGS_LAYOUT.row_spacing
            + self.export_uv_map.width()
            + 2 * body_margin
        )
        return max(
            metric(338, 254),
            footer_need,
            bit_depth_need,
            uv_map_need,
        )

    def _apply_ui_scale(self, _scale):
        metric = self._metric
        body_margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        self._body_layout.setContentsMargins(
            body_margin,
            PAINTER_SETTINGS_LAYOUT.body_margin_top.resolve(self.dialog),
            body_margin,
            PAINTER_SETTINGS_LAYOUT.body_margin_bottom.resolve(self.dialog),
        )
        self._body_layout.setSpacing(
            PAINTER_SETTINGS_LAYOUT.body_spacing.resolve(self.dialog)
        )
        for label in self._settings_sections:
            label.setFixedHeight(label._rizum_layout_metric.resolve(self.dialog))
        row_padding = PAINTER_SETTINGS_LAYOUT.row_padding_y.resolve(self.dialog)
        for row in self._settings_rows:
            row.setFixedHeight(
                metric(
                    row._rizum_base_height,
                    round(row._rizum_base_height * 0.75),
                )
            )
            row.layout().setContentsMargins(0, row_padding, 0, row_padding)
            row.layout().setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)

        name_metrics = self.QtGui.QFontMetrics(
            self._text_font(13, self.QtGui.QFont.Weight.Medium)
        )
        meta_metrics = self.QtGui.QFontMetrics(
            self._text_font(11, self.QtGui.QFont.Weight.Medium)
        )
        text_spacing = PAINTER_SETTINGS_LAYOUT.text_spacing.resolve(self.dialog)
        for block in self._text_blocks:
            block.layout().setSpacing(text_spacing)
            block._rizum_name_label.setFixedHeight(name_metrics.height())
            if block._rizum_meta_label is not None:
                block._rizum_meta_label.setFixedHeight(meta_metrics.height())
                block.setFixedHeight(
                    name_metrics.height() + text_spacing + meta_metrics.height()
                )

        self.infinite_padding.setCompactHeight(metric(20))
        self.export_uv_map.setCompactHeight(metric(20))
        self.dilation_stepper.setCompactHeight(
            PAINTER_SETTINGS_LAYOUT.stepper_height.resolve(self.dialog)
        )
        control_height = PAINTER_SETTINGS_LAYOUT.control_height.resolve(self.dialog)
        self.bit_depth.setCompactHeight(control_height)
        self.bit_depth.setFitToContents(True)
        self.bit_depth.fitToContents()
        combo_margins = self.bit_depth.layout().contentsMargins()
        localized_width = max(
            self.bit_depth.width(),
            self.bit_depth._label.sizeHint().width()
            + combo_margins.left()
            + combo_margins.right()
            + self.bit_depth.layout().spacing()
            + self.bit_depth._arrow_size
            + metric(6, 5),
        )
        self.bit_depth.setFitToContents(False)
        self.bit_depth.setFixedWidth(max(metric(126, 95), localized_width))
        self.dilation_reveal.setExpandedHeight(
            PAINTER_SETTINGS_LAYOUT.detail_row_height.resolve(self.dialog)
        )
        self.dilation_reveal.setGap(self._body_layout.spacing())

        self.path_field.setFixedHeight(control_height)
        self.photoshop_path.setFixedHeight(max(15, control_height - metric(8, 6)))
        browse_size = metric(26)
        self.browse_button.setFixedSize(browse_size, browse_size)
        if hasattr(self.browse_button, "setPaintedIconSize"):
            self.browse_button.setPaintedIconSize(metric(14))
        if hasattr(self.browse_button, "setCompactTooltipScale"):
            self.browse_button.setCompactTooltipScale(
                self.dialog.settingsUiScale()
            )

        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        footer_top = PAINTER_SETTINGS_LAYOUT.footer_top.resolve(self.dialog)
        footer_gap = PAINTER_SETTINGS_LAYOUT.footer_gap.resolve(self.dialog)
        footer_bottom = PAINTER_SETTINGS_LAYOUT.footer_bottom.resolve(self.dialog)
        footer_row_height = PAINTER_SETTINGS_LAYOUT.footer_row_height.resolve(self.dialog)
        self._footer_outer.setContentsMargins(
            0,
            footer_top + footer_gap,
            0,
            footer_bottom,
        )
        self._footer_row.setFixedHeight(footer_row_height)
        self._footer.setFixedHeight(
            footer_top + footer_gap + footer_row_height + footer_bottom
        )
        self._footer_layout.setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        self._footer_separator.layout().setContentsMargins(
            footer_margin,
            0,
            footer_margin,
            0,
        )
        button_height = PAINTER_SETTINGS_LAYOUT.footer_button_height.resolve(self.dialog)
        self.done_button.setCompactHeight(button_height)
        self.done_button.setFixedWidth(
            max(metric(72, 54), self.done_button.sizeHint().width() + metric(8, 6))
        )
        self.dialog.setFixedWidth(self._required_width())
        self._restyle()
        self._remeasure_base_height()

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
QWidget#RizumSettingsBody,
QWidget#RizumSettingsFooter,
QWidget#RizumSettingsFooterRow,
QWidget#RizumSettingsPaddingStack,
QWidget#RizumSettingsTexts,
QWidget#RizumSettingsFooterDivider,
QFrame#RizumSettingsRevealRow {{
    background: transparent;
    border: 0;
}}
QLabel#RizumSettingsSection {{ color: {theme["faint"]}; }}
QLabel#RizumSettingsItemName {{ color: {theme["text"]}; }}
QLabel#RizumSettingsItemMeta,
QLabel#RizumSettingsFooterHint {{ color: {theme["muted"]}; }}
QFrame#RizumSettingsRow,
QFrame#RizumSettingsRow:hover {{
    background: transparent;
    border: 0;
}}
QWidget#RizumSettingsFooterDivider QFrame#RizumInsetSeparator {{
    background: #3a3b3e;
}}
QFrame#RizumSettingsMockSelect {{
    background: transparent;
    border: 0;
}}
QLineEdit#RizumSettingsPathInput {{
    color: {theme["muted"]};
    background: transparent;
    border: 0;
    padding: 0;
    selection-background-color: {theme["control_hover"]};
    selection-color: {theme["text"]};
}}
QLineEdit#RizumSettingsPathInput:hover,
QLineEdit#RizumSettingsPathInput:focus {{
    color: {theme["text"]};
    background: transparent;
    border: 0;
}}
QPushButton[variant="icon"] {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QPushButton[variant="icon"]:hover {{
    background: {theme["control_hover"]};
}}
QPushButton[variant="icon"]:pressed {{
    background: {theme["control_pressed"]};
}}
"""
        )
        self.dilation_stepper.setTheme(
            {
                "window_bg": theme["surface"],
                "text": theme["text"],
                "muted": theme["muted"],
                "control_hover": theme["control_hover"],
            }
        )
        self.browse_button.setProperty("iconColor", theme["muted"])
        self.browse_button.setProperty("iconHoverColor", theme["text"])
        self.browse_button.update()

    def _remeasure_base_height(self):
        self.dialog.setMinimumHeight(0)
        self.dialog.setMaximumHeight(16777215)
        self.dialog.layout().invalidate()
        self.dialog.settingsSurfaceLayout().invalidate()
        self.dialog.layout().activate()
        self.dialog.settingsSurfaceLayout().activate()
        measured = max(
            1,
            self.dialog.sizeHint().height() - self._current_extra_height(),
        )
        scale = self.dialog.settingsUiScale()
        if self._design_height is None:
            normalizer = scale if scale >= 1.0 else 1.0
            self._design_height = int(round(measured / normalizer))
        self._base_height = max(measured, int(round(self._design_height * scale)))
        self._sync_dialog_height()

    def load_values(self):
        self._loading_values = True
        try:
            settings = self.panel.user_settings
            self.photoshop_path.setText(settings.get("photoshop_path") or "")
            self.infinite_padding.setChecked(bool(settings.get("infinite_padding")))
            self.dilation_stepper.setValue(
                int(settings.get("dilation") or 8),
                emit=False,
            )
            self.export_uv_map.setChecked(bool(settings.get("export_uv_map")))
            self._sync_padding_mode(animate=False)

            bit_depth = settings.get("bit_depth")
            index = self.bit_depth.findData(bit_depth)
            self.bit_depth.setCurrentIndex(index if index >= 0 else 0)
        finally:
            self._loading_values = False

    def _sync_padding_mode(self, _enabled=None, animate=True):
        infinite = self.infinite_padding.isChecked()
        if self.padding_meta is not None:
            self.padding_meta.setText("Infinite" if infinite else "Custom")
        self.dilation_reveal.setExpanded(not infinite, animate=animate)
        self._sync_dialog_height()

    def browse_photoshop(self):
        path, _selected_filter = self.QtWidgets.QFileDialog.getOpenFileName(
            self.dialog,
            "Choose Photoshop executable",
            self.photoshop_path.text() or "",
            "Executable (*.exe);;All Files (*)",
        )
        if path:
            self.photoshop_path.setText(path)
            self._save_live()

    def _settings_values(self):
        return {
            "photoshop_path": self.photoshop_path.text().strip(),
            "infinite_padding": self.infinite_padding.isChecked(),
            "dilation": self.dilation_stepper.value(),
            "export_uv_map": self.export_uv_map.isChecked(),
            "bit_depth": self.bit_depth.currentData(),
        }

    def _save_live(self, *_args):
        if self._loading_values:
            return
        self.panel.save_user_settings(self._settings_values())

    def save(self):
        self._save_live()
        self.dialog.accept()

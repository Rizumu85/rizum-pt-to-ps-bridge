"""Painter Export dialog."""

from __future__ import annotations

from .exporter import list_export_targets
from .export_selection_memory import (
    ExportSelectionMemory,
    current_project_identity,
    target_selection_key,
)
from .ui_kit import (
    AnimatedSaveButton,
    PAINTER_DIALOG_STYLE,
    PAINTER_SETTINGS_LAYOUT,
    PainterSettingsDialog,
    SETTINGS_APP,
    SETTINGS_ORG,
    SecondaryActionButton,
    apply_theme,
    compact_action_bar_width,
    default_theme,
    install_compact_tooltip,
    make_collapsible_group,
    make_combo_input,
    make_compact_action_bar,
    make_compact_icon_toolbar,
    make_export_tree_item,
    make_icon_button,
    make_inset_separator,
    make_mock_checkbox,
    update_export_tree_item,
)
from .ui_dialogs import show_modal_message
from .settings_ui import PSD_SIZE_OPTIONS, RENDER_SCALE_OPTIONS


class ExportDialog:
    """Focused target/channel export dialog launched from the Painter dock."""

    DEFAULT_TREE_VIEWPORT_HEIGHT = 500
    MINIMUM_TREE_VIEWPORT_HEIGHT = 375

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtGui = panel.QtGui
        self.QtWidgets = panel.QtWidgets
        self.targets = []
        self.groups = []
        self._selection_memory = None
        self._updating_checks = False
        self._target_error = ""
        self._height_animation = None
        self._height_animation_token = 0

        self.dialog = PainterSettingsDialog(panel.widget)
        self.dialog.setObjectName("RizumExportDialog")
        self.dialog.setWindowTitle("Export")
        self.dialog.setModal(True)
        self.dialog.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Fixed,
            self.QtWidgets.QSizePolicy.Policy.Expanding,
        )
        surface_layout = self.dialog.settingsSurfaceLayout()

        self.scope_combo = make_combo_input([("Current Stack", "current"), ("All Stacks", "all")])
        self.scope_combo.setObjectName("RizumExportScopeInput")
        self.scope_combo.currentIndexChanged.connect(self._scope_changed)

        self.expand_button = make_icon_button("chevrons-down.svg", "Expand all")
        self.collapse_button = make_icon_button("chevrons-up.svg", "Collapse all")
        self.all_button = make_icon_button("circle-dot.svg", "Select all")
        self.none_button = make_icon_button("circle-slash.svg", "Select none")
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setProperty("accent", True)
        self.expand_button.clicked.connect(self.tree_expand_all)
        self.collapse_button.clicked.connect(self.tree_collapse_all)
        self.all_button.clicked.connect(lambda: self.set_all_checked(True))
        self.none_button.clicked.connect(lambda: self.set_all_checked(False))

        self.icon_bar = make_compact_icon_toolbar(
            self.expand_button,
            self.collapse_button,
            None,
            self.all_button,
            self.none_button,
        )
        self.top_controls = make_compact_action_bar(
            [self.scope_combo],
            self.icon_bar,
            object_name="RizumExportTopControls",
            height=PAINTER_SETTINGS_LAYOUT.row_height.design,
            margins=(
                PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
                0,
                PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
                0,
            ),
            spacing=PAINTER_SETTINGS_LAYOUT.row_spacing,
        )
        surface_layout.addWidget(self.top_controls)

        self.top_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.body_margin_x.design,
            thickness=1,
        )
        self.top_separator.setObjectName("RizumExportTopDivider")
        surface_layout.addWidget(self.top_separator)

        self.tree_scroll = self.QtWidgets.QScrollArea()
        self.tree_scroll.setObjectName("RizumExportTreeScroll")
        self.tree_scroll.setWidgetResizable(True)
        self.tree_scroll.setFrameShape(self.QtWidgets.QFrame.Shape.NoFrame)
        self.tree_scroll.setHorizontalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tree_scroll.setVerticalScrollBarPolicy(
            self.QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.tree_scroll.viewport().setAutoFillBackground(False)
        internal_scrollbar = self.tree_scroll.verticalScrollBar()
        internal_scrollbar.setObjectName("RizumExportInternalScrollbar")
        internal_scrollbar.setStyleSheet(
            "QScrollBar#RizumExportInternalScrollbar {"
            " min-width: 0; max-width: 0; width: 0;"
            " background: transparent; border: 0; }"
        )
        internal_scrollbar.setFixedWidth(0)
        internal_scrollbar.valueChanged.connect(
            self._refresh_tree_hover
        )

        # Painter can reclaim a native scrollbar lane even under AlwaysOn.
        # Keep scrolling internal, but render it through a fixed-width proxy.
        self.tree_scrollbar = self.QtWidgets.QScrollBar(
            self.QtCore.Qt.Orientation.Vertical
        )
        self.tree_scrollbar.setObjectName("RizumExportTreeScrollbar")
        self.tree_scrollbar.setFocusPolicy(
            self.QtCore.Qt.FocusPolicy.NoFocus
        )
        self.tree_scrollbar.valueChanged.connect(internal_scrollbar.setValue)
        internal_scrollbar.valueChanged.connect(self.tree_scrollbar.setValue)
        internal_scrollbar.rangeChanged.connect(self._sync_scrollbar_range)

        self.tree_container = self.QtWidgets.QWidget()
        self.tree_container.setObjectName("RizumExportTreeContainer")
        self.tree_container.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Expanding,
        )
        tree_container_layout = self.QtWidgets.QHBoxLayout(self.tree_container)
        tree_container_layout.setContentsMargins(0, 0, 0, 0)
        tree_container_layout.setSpacing(0)
        tree_container_layout.addWidget(self.tree_scroll, 1)
        tree_container_layout.addWidget(self.tree_scrollbar)

        self.tree = self.QtWidgets.QFrame()
        self.tree.setObjectName("RizumExportTree")
        self.tree.setMinimumWidth(0)
        self.tree.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.tree_layout = self.QtWidgets.QVBoxLayout(self.tree)
        self.tree_layout.setContentsMargins(12, 8, 12, 8)
        self.tree_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.body_spacing.design)
        self.status = self.QtWidgets.QLabel("")
        self.status.setObjectName("RizumExportEmptyState")
        self.status.setWordWrap(True)
        self.status.setAlignment(self.QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status.hide()
        self.tree_layout.addWidget(self.status)
        self.tree_layout.addStretch(1)
        self.tree_scroll.setWidget(self.tree)
        self.tree_scroll.setSizePolicy(
            self.QtWidgets.QSizePolicy.Policy.Expanding,
            self.QtWidgets.QSizePolicy.Policy.Expanding,
        )
        surface_layout.addWidget(self.tree_container, 1)


        self.footer_separator = make_inset_separator(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            thickness=1,
        )
        self.footer_separator.setObjectName("RizumExportFooterDivider")
        surface_layout.addWidget(self.footer_separator)

        # Size is chosen per export: these open on the Settings defaults and
        # apply to this export only, so a one-off 2K or 2x render needs no
        # trip to Settings and leaves the defaults alone.
        self.psd_size_combo = make_combo_input(PSD_SIZE_OPTIONS)
        self.psd_size_combo.setObjectName("RizumExportPsdSize")
        self.render_scale_combo = make_combo_input(RENDER_SCALE_OPTIONS)
        self.render_scale_combo.setObjectName("RizumExportRenderScale")
        # Short muted labels in the dialog's own colours: the combo's built-in
        # prefix used the kit's fixed greys, which read off against the
        # Painter dialog palette.
        self.psd_size_label = self.QtWidgets.QLabel("Size")
        self.psd_size_label.setObjectName("RizumExportOptionLabel")
        self.render_scale_label = self.QtWidgets.QLabel("Render")
        self.render_scale_label.setObjectName("RizumExportOptionLabel")
        for widget in (self.render_scale_label, self.render_scale_combo):
            widget.setToolTip(
                "Supersampling: Painter renders this many times the PSD size, "
                "smooths edges there, then scales down."
            )
        self.size_controls = make_compact_action_bar(
            [
                self.psd_size_label,
                self.psd_size_combo,
                self.render_scale_label,
                self.render_scale_combo,
            ],
            None,
            object_name="RizumExportSizeControls",
            height=PAINTER_SETTINGS_LAYOUT.row_height.design,
            margins=(
                PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
                0,
                PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
                0,
            ),
            spacing=PAINTER_SETTINGS_LAYOUT.row_spacing,
        )
        surface_layout.addWidget(self.size_controls)

        self.footer = self.QtWidgets.QWidget()
        self.footer.setObjectName("RizumExportFooter")
        self.footer_outer = self.QtWidgets.QVBoxLayout(self.footer)
        self.footer_outer.setContentsMargins(0, 0, 0, 0)
        self.footer_outer.setSpacing(0)
        self.footer_row = self.QtWidgets.QWidget()
        self.footer_row.setObjectName("RizumExportFooterRow")
        self.footer_layout = self.QtWidgets.QHBoxLayout(self.footer_row)
        self.footer_layout.setContentsMargins(
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
            PAINTER_SETTINGS_LAYOUT.footer_margin_x.design,
            0,
        )
        self.footer_layout.setSpacing(PAINTER_SETTINGS_LAYOUT.footer_button_spacing)
        theme = PAINTER_DIALOG_STYLE
        self.cancel_button = SecondaryActionButton(
            "Cancel",
            theme["control"],
            theme["control_hover"],
            theme["control_pressed"],
            theme["text"],
            default_theme.radius_small,
        )
        self.cancel_button.setObjectName("RizumExportCancel")
        self.run_button = AnimatedSaveButton("Export")
        self.run_button.setObjectName("RizumExportConfirm")
        self.cancel_button.clicked.connect(self.dialog.reject)
        self.run_button.clicked.connect(self.export_checked)
        self.footer_layout.addWidget(self.cancel_button)
        self.footer_layout.addStretch(1)
        self.footer_layout.addWidget(self.run_button)
        self.footer_outer.addWidget(self.footer_row)
        surface_layout.addWidget(self.footer)

        apply_theme(self.dialog, mode="overlay")
        self.dialog.syncSettingsUiScale()
        self.dialog.settingsUiScaleChanged.connect(self._apply_ui_scale)
        self._apply_ui_scale(self.dialog.settingsUiScale())

    def open(self):
        self._load_size_defaults()
        self.refresh_targets()
        self._position_for_default_expansion()
        # Windows recenters a parented modal as exec() begins, so repeat the
        # placement after the native window has completed its first show.
        self.QtCore.QTimer.singleShot(
            0,
            self._position_for_default_expansion,
        )
        return self.dialog.exec()

    def _load_size_defaults(self):
        settings = self.panel.user_settings
        for combo, value in (
            (self.psd_size_combo, settings.get("psd_size")),
            (self.render_scale_combo, settings.get("render_scale", 1)),
        ):
            index = combo.findData(value)
            combo.setCurrentIndex(index if index >= 0 else 0)

    def size_overrides(self):
        return {
            "psd_size": self.psd_size_combo.currentData(),
            "render_scale": self.render_scale_combo.currentData(),
        }

    def tree_expand_all(self):
        for group in self.groups:
            group["widget"].setExpanded(True)

    def tree_collapse_all(self):
        for group in self.groups:
            group["widget"].setExpanded(False)

    def _metric(self, pixels, minimum=None):
        return self.dialog.settingsMetric(pixels, minimum)

    def _selection_counter(self, selected, total):
        theme = PAINTER_DIALOG_STYLE
        return (
            f'<span style="color:{theme["text"]};">{selected}</span>'
            f'<span style="color:{theme["faint"]};"> / {total}</span>'
        )

    @staticmethod
    def _selection_tooltip(selected, total):
        return f"{selected} of {total} channels selected"

    def _footer_button_width(self, button, minimum=56, maximum=112):
        scale = self.dialog.settingsUiScale()
        width = button.sizeHint().width() + self._metric(16, 12)
        return max(
            self._metric(minimum),
            min(int(round(maximum * scale)), width),
        )

    def _required_width(self):
        margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        toolbar_width = compact_action_bar_width(
            [self.scope_combo],
            self.icon_bar,
            minimum=PAINTER_SETTINGS_LAYOUT.dialog_width.resolve(self.dialog),
            horizontal_margins=margin * 2,
            spacing=PAINTER_SETTINGS_LAYOUT.row_spacing,
            spacing_budget=PAINTER_SETTINGS_LAYOUT.row_spacing,
        )
        footer_width = (
            margin * 2
            + self.cancel_button.width()
            + self.run_button.width()
            + PAINTER_SETTINGS_LAYOUT.footer_button_spacing
        )
        return max(
            PAINTER_SETTINGS_LAYOUT.dialog_width.resolve(self.dialog),
            toolbar_width,
            footer_width,
        )

    def _expanded_tree_height(self):
        margins = self.tree_layout.contentsMargins()
        if not self.groups:
            return margins.top() + self._metric(72, 54) + margins.bottom()

        height = margins.top() + margins.bottom()
        for index, group in enumerate(self.groups):
            if index:
                height += self.tree_layout.spacing()
            height += group["widget"].height()
        return height

    def _first_group_prefix_height(self, group, maximum):
        widget = group["widget"]
        group_margins = widget.layout().contentsMargins()
        base = (
            group_margins.top()
            + widget._rizum_header.height()
            + group_margins.bottom()
        )
        if not widget.isExpanded() or base >= maximum:
            return min(base, maximum)

        height = base
        content_layout = widget._rizum_content_layout
        for index, child in enumerate(group["children"]):
            row_height = child["row"].height()
            addition = row_height + (content_layout.spacing() if index else 0)
            if height + addition > maximum:
                break
            height += addition
        return height

    def _quantized_tree_height(self, content_height, maximum):
        if content_height <= maximum or not self.groups:
            return content_height

        margins = self.tree_layout.contentsMargins()
        height = margins.top()
        complete_groups = 0
        truncated = False
        for group in self.groups:
            spacing = self.tree_layout.spacing() if complete_groups else 0
            candidate = (
                height
                + spacing
                + group["widget"].height()
                + margins.bottom()
            )
            if candidate > maximum:
                truncated = True
                if not complete_groups:
                    available = max(
                        0,
                        maximum - height - spacing - margins.bottom(),
                    )
                    height += spacing + self._first_group_prefix_height(
                        group,
                        available,
                    )
                break
            height += spacing + group["widget"].height()
            complete_groups += 1
        if truncated:
            # The tree's bottom margin exists only after its final group. When
            # more groups follow, ending on that hypothetical margin exposes
            # the first pixels of the next header inside the viewport.
            return max(1, height + self.tree_layout.spacing())
        return max(1, height + margins.bottom())

    def _sync_toolbar_gutter(self):
        margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        gutter = self._metric(10, 8)
        self.top_controls.layout().setContentsMargins(
            margin,
            0,
            margin + max(0, gutter),
            0,
        )

    def _refresh_tree_hover(self, *_args):
        for group in self.groups:
            for child in group["children"]:
                hover_filter = getattr(
                    child["row"],
                    "_rizum_hover_filter",
                    None,
                )
                if hover_filter is not None:
                    hover_filter.refresh_hovered()

    def _sync_scrollbar_range(self, minimum, maximum):
        internal = self.tree_scroll.verticalScrollBar()
        self.tree_scrollbar.setRange(minimum, maximum)
        self.tree_scrollbar.setPageStep(internal.pageStep())
        self.tree_scrollbar.setSingleStep(internal.singleStep())
        self.tree_scrollbar.setValue(internal.value())
        self._set_tree_scrollable(maximum > minimum)

    def _set_tree_scrollable(self, scrolling):
        scrolling = bool(scrolling)
        if self.tree_scrollbar.property("scrollable") == scrolling:
            return
        self.tree_scrollbar.setProperty("scrollable", scrolling)
        self.tree_scrollbar.style().unpolish(self.tree_scrollbar)
        self.tree_scrollbar.style().polish(self.tree_scrollbar)
        self.tree_scrollbar.update()

    def _sync_tree_content_height(self):
        self.tree_layout.activate()
        content_height = self._expanded_tree_height()
        self.tree.setFixedHeight(content_height)
        viewport_height = max(1, self.tree_scroll.viewport().height())
        scrolling = content_height > viewport_height
        self._set_tree_scrollable(scrolling)
        if not scrolling:
            self.tree_scroll.verticalScrollBar().setValue(0)

    def _dialog_height_for_viewport(self, viewport_height):
        return (
            self.top_controls.height()
            + self.top_separator.height()
            + int(round(viewport_height))
            + self.footer_separator.height()
            + self.size_controls.height()
            + self.footer.height()
        )

    def _position_for_default_expansion(self):
        parent_window = self.dialog.parentWidget()
        if parent_window is not None:
            parent_window = parent_window.window()
        parent_geometry = (
            parent_window.frameGeometry()
            if parent_window is not None and parent_window.isVisible()
            else None
        )
        screen = None
        if parent_geometry is not None:
            screen = self.QtGui.QGuiApplication.screenAt(
                parent_geometry.center()
            )
        screen = screen or self.dialog.screen()
        screen = screen or self.QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        anchor = parent_geometry or available
        frame_width = max(1, self.dialog.frameGeometry().width())
        reserve_height = min(
            available.height(),
            self._dialog_height_for_viewport(
                self._metric(
                    self.DEFAULT_TREE_VIEWPORT_HEIGHT,
                    self.MINIMUM_TREE_VIEWPORT_HEIGHT,
                )
            ),
        )
        x = anchor.center().x() - frame_width // 2
        x = max(
            available.left(),
            min(x, available.right() - frame_width + 1),
        )
        y = available.top() + max(
            0,
            (available.height() - reserve_height) // 2,
        )
        self.dialog.move(x, y)

    def _set_viewport_height(self, viewport_height):
        viewport_height = max(1, int(round(viewport_height)))
        self.dialog.resize(
            self.dialog.width(),
            self._dialog_height_for_viewport(viewport_height),
        )
        self.dialog.updateGeometry()

    def _stop_height_animation(self):
        animation = self._height_animation
        self._height_animation = None
        if animation is not None:
            self._height_animation_token += 1
            animation.stop()
            animation.deleteLater()

    def _animate_viewport_height(self, target_height):
        start_height = max(1, self.tree_scroll.height())
        target_height = max(1, int(round(target_height)))
        threshold = self._metric(32, 24)
        if (
            not self.dialog.isVisible()
            or abs(target_height - start_height) < threshold
        ):
            self._stop_height_animation()
            self._set_viewport_height(target_height)
            return

        self._stop_height_animation()
        self._height_animation_token += 1
        token = self._height_animation_token
        animation = self.QtCore.QVariantAnimation(self.dialog)
        animation.setDuration(165)
        animation.setStartValue(start_height)
        animation.setEndValue(target_height)
        animation.setEasingCurve(
            self.QtCore.QEasingCurve.Type.OutCubic
        )
        animation.valueChanged.connect(self._set_viewport_height)

        def finish():
            if token != self._height_animation_token:
                return
            self._set_viewport_height(target_height)
            self._height_animation = None
            animation.deleteLater()

        animation.finished.connect(finish)
        self._height_animation = animation
        animation.start()

    def _sync_tree_height(self, animate=False, reset_scroll=False):
        self.tree_layout.activate()
        content_height = self._expanded_tree_height()
        viewport_height = self._quantized_tree_height(
            content_height,
            self._metric(
                self.DEFAULT_TREE_VIEWPORT_HEIGHT,
                self.MINIMUM_TREE_VIEWPORT_HEIGHT,
            ),
        )
        self.tree.setFixedHeight(content_height)
        scrollbar = self.tree_scroll.verticalScrollBar()
        scrolling = content_height > viewport_height
        self._set_tree_scrollable(scrolling)
        if reset_scroll:
            scrollbar.setValue(0)
        self._sync_toolbar_gutter()
        if animate:
            self._animate_viewport_height(viewport_height)
        else:
            self._stop_height_animation()
            self._set_viewport_height(viewport_height)
        self.QtCore.QTimer.singleShot(0, self._refresh_tree_hover)

    def _apply_ui_scale(
        self,
        _scale,
        animate_height=False,
        reset_scroll=False,
    ):
        margin = PAINTER_SETTINGS_LAYOUT.body_margin_x.resolve(self.dialog)
        self.top_controls.setFixedHeight(
            PAINTER_SETTINGS_LAYOUT.row_height.resolve(self.dialog)
        )
        self.top_controls.layout().setContentsMargins(margin, 0, margin, 0)
        self.top_controls.layout().setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)
        self.scope_combo.setCompactHeight(
            PAINTER_SETTINGS_LAYOUT.control_height.resolve(self.dialog)
        )
        self.scope_combo.fitToContents()
        footer_margin_x = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        self.size_controls.setFixedHeight(
            PAINTER_SETTINGS_LAYOUT.row_height.resolve(self.dialog)
        )
        self.size_controls.layout().setContentsMargins(footer_margin_x, 0, footer_margin_x, 0)
        self.size_controls.layout().setSpacing(PAINTER_SETTINGS_LAYOUT.row_spacing)
        for combo in (self.psd_size_combo, self.render_scale_combo):
            combo.setCompactHeight(
                PAINTER_SETTINGS_LAYOUT.control_height.resolve(self.dialog)
            )
            combo.fitToContents()

        icon_frame = self._metric(22, 17)
        icon_size = self._metric(16, 12)
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setFixedSize(icon_frame, icon_frame)
            button.setPaintedIconSize(icon_size)
            if hasattr(button, "setCompactTooltipScale"):
                button.setCompactTooltipScale(self.dialog.settingsUiScale())
        for separator in self.icon_bar.findChildren(self.QtWidgets.QFrame):
            if separator.width() == 1:
                separator.setFixedHeight(self._metric(14, 11))

        tree_margin_x = self._metric(12, 9)
        tree_margin_y = self._metric(8, 6)
        self.tree_layout.setContentsMargins(
            tree_margin_x,
            tree_margin_y,
            tree_margin_x,
            tree_margin_y,
        )
        self.tree_layout.setSpacing(
            PAINTER_SETTINGS_LAYOUT.body_spacing.resolve(self.dialog)
        )
        checkbox_size = self._metric(14, 11)
        group_height = self._metric(36, 27)
        child_height = self._metric(32, 24)
        for group in self.groups:
            for checkbox in (
                group["parent"],
                *(child["checkbox"] for child in group["children"]),
            ):
                checkbox.setSize(checkbox_size)
            group["subtitle"].setFixedWidth(self._metric(42, 32))
            group["subtitle"].setCompactTooltipScale(
                self.dialog.settingsUiScale()
            )
            group["widget"].setCompactHeight(group_height)
            for child in group["children"]:
                child["row"].setRightInset(
                    self._metric(4, 3),
                    self._metric(4, 3),
                )
                update_export_tree_item(
                    child["row"],
                    minimum_height=child_height,
                )
            group["widget"].refreshLayout()

        footer_margin = PAINTER_SETTINGS_LAYOUT.footer_margin_x.resolve(self.dialog)
        footer_top = PAINTER_SETTINGS_LAYOUT.footer_top.resolve(self.dialog)
        footer_gap = PAINTER_SETTINGS_LAYOUT.footer_gap.resolve(self.dialog)
        footer_bottom = PAINTER_SETTINGS_LAYOUT.footer_bottom.resolve(self.dialog)
        footer_row_height = PAINTER_SETTINGS_LAYOUT.footer_row_height.resolve(self.dialog)
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
        self.top_separator.layout().setContentsMargins(margin, 0, margin, 0)
        button_height = PAINTER_SETTINGS_LAYOUT.footer_button_height.resolve(
            self.dialog
        )
        for button in (self.cancel_button, self.run_button):
            button.setCompactHeight(button_height)
            button.setFixedWidth(self._footer_button_width(button))

        self._restyle()
        # Painter's host stylesheet applies a 24 px icon-button minimum during
        # polish, so restore the shared compact frame after the local style lands.
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setFixedSize(icon_frame, icon_frame)
        self.icon_bar.layout().invalidate()
        self.icon_bar.layout().activate()
        scrollbar_gutter = self._metric(10, 8)
        self.tree_scroll.verticalScrollBar().setFixedWidth(0)
        self.tree_scrollbar.setFixedWidth(scrollbar_gutter)
        minimum_viewport_height = self._metric(72, 54)
        self.tree_container.setMinimumHeight(minimum_viewport_height)
        self.tree_scroll.setMinimumHeight(minimum_viewport_height)
        self.dialog.setMinimumHeight(
            self._dialog_height_for_viewport(minimum_viewport_height)
        )
        self.dialog.setMaximumHeight(16777215)
        self.dialog.setFixedWidth(self._required_width())
        self._sync_tree_height(
            animate=animate_height,
            reset_scroll=reset_scroll,
        )

    def _restyle(self):
        theme = PAINTER_DIALOG_STYLE
        self.dialog._update_surface_stylesheet()
        item_px = self._metric(13)
        meta_px = self._metric(11)
        surface = self.dialog.settingsSurface()
        surface.setStyleSheet(
            surface.styleSheet()
            + f"""
QFrame#RizumPainterSettingsSurface {{
    background: {theme["surface"]};
}}
QLabel#RizumExportOptionLabel {{
    color: {theme["muted"]};
    background: transparent;
    font-size: {item_px}px;
}}

QWidget#RizumExportTopControls,
QWidget#RizumExportSizeControls,
QWidget#RizumExportTreeContainer,
QScrollArea#RizumExportTreeScroll,
QScrollArea#RizumExportTreeScroll > QWidget > QWidget,
QFrame#RizumExportTree,
QWidget#RizumExportFooter,
QWidget#RizumExportFooterRow,
QWidget#RizumExportTopDivider,
QWidget#RizumExportFooterDivider,
QFrame#RizumCollapsibleHeader,
QFrame#RizumCollapsibleContent,
QWidget#RizumCollapsibleContentInner,
QFrame#RizumExportTreeItemHost {{
    background: transparent;
    border: 0;
}}
QScrollBar#RizumExportTreeScrollbar {{
    background: transparent;
    border: 0;
    margin: 0;
    width: {self._metric(10, 8)}px;
}}
QScrollBar#RizumExportTreeScrollbar::handle:vertical {{
    background: #515151;
    border: 0;
    border-radius: {max(3, self._metric(4, 3))}px;
    min-height: {self._metric(28, 21)}px;
    margin: {self._metric(2, 1)}px;
}}
QScrollBar#RizumExportTreeScrollbar::handle:vertical:hover {{
    background: #686868;
}}
QScrollBar#RizumExportTreeScrollbar::handle:vertical:pressed {{
    background: #777777;
}}
QScrollBar#RizumExportTreeScrollbar[scrollable="false"]::handle:vertical {{
    background: transparent;
}}
QScrollBar#RizumExportTreeScrollbar::add-line:vertical,
QScrollBar#RizumExportTreeScrollbar::sub-line:vertical {{
    background: transparent;
    border: 0;
    height: 0;
}}
QScrollBar#RizumExportTreeScrollbar::add-page:vertical,
QScrollBar#RizumExportTreeScrollbar::sub-page:vertical {{
    background: transparent;
}}
QWidget#RizumExportTopDivider QFrame#RizumInsetSeparator,
QWidget#RizumExportFooterDivider QFrame#RizumInsetSeparator {{
    background: #3a3b3e;
}}
QFrame#RizumExportScopeInput {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QFrame#RizumExportScopeInput:focus {{
    background: transparent;
}}
QFrame#RizumExportScopeInput:hover {{
    background: {default_theme.action_hover};
}}
QFrame#RizumCollapsibleGroup {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QFrame#RizumCollapsibleGroup:hover {{
    background: {theme["control_pressed"]};
    border: 0;
}}
QFrame#RizumExportTreeItem {{
    background: transparent;
    border: 0;
    border-radius: {default_theme.radius_small}px;
}}
QFrame#RizumExportTreeItem[hovered="true"][child="true"] {{
    background: {default_theme.action_hover};
}}
QFrame#RizumExportTreeItem[pressed="true"][child="true"] {{
    background: {default_theme.action_pressed};
}}
QLabel#RizumExportItemName,
QLabel#RizumCollapsibleTitle {{
    color: {theme["text"]};
    font-size: {item_px}px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}
QLabel#RizumExportMeta,
QLabel#RizumCollapsibleSubtitle,
QLabel#RizumExportEmptyState {{
    color: {theme["muted"]};
    font-size: {meta_px}px;
    font-weight: 500;
    background: transparent;
    border: 0;
}}
QLabel#RizumSvgLabel,
QLabel#RizumSvgLabel:hover {{
    background: transparent;
    border: 0;
}}
"""
        )
        for button in (
            self.expand_button,
            self.collapse_button,
            self.all_button,
            self.none_button,
        ):
            button.setProperty("iconColor", theme["muted"])
            button.setProperty("iconAccentColor", theme["muted"])
            button.setProperty("iconHoverColor", theme["text"])
            button.update()

    def refresh_targets(self):
        self._target_error = ""
        if not self.panel._project_is_open():
            self.targets = []
            self._target_error = "Open a Painter project to export."
            self.refresh_tree()
            return
        if not self.panel._project_is_ready():
            self.targets = []
            self._target_error = "Painter project is still loading or not editable."
            self.refresh_tree()
            return

        self._selection_memory = ExportSelectionMemory(
            self.QtCore,
            SETTINGS_ORG,
            SETTINGS_APP,
            current_project_identity(),
        )
        remembered_scope = self._selection_memory.scope()
        remembered_index = self.scope_combo.findData(remembered_scope)
        if remembered_index >= 0:
            previous_signal_state = self.scope_combo.blockSignals(True)
            self.scope_combo.setCurrentIndex(remembered_index)
            self.scope_combo.blockSignals(previous_signal_state)

        try:
            self.targets = list_export_targets(settings=self.panel._base_export_settings())
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.targets = []
            self._target_error = (
                f"Could not list export targets: {type(exc).__name__}: {exc}"
            )
        self.refresh_tree()

    def _clear_groups(self):
        for group in self.groups:
            self.tree_layout.removeWidget(group["widget"])
            group["widget"].deleteLater()
        self.groups.clear()

    def _show_tree_message(self, message):
        self.status.setText(message)
        self.status.setVisible(bool(message))

    def _scope_changed(self, *_args):
        if self._selection_memory is not None:
            self._selection_memory.remember_scope(
                self.scope_combo.currentData()
            )
            self._selection_memory.save()
        self.refresh_tree(
            animate_height=self.dialog.isVisible(),
            reset_scroll=True,
        )

    def refresh_tree(
        self,
        *_args,
        animate_height=False,
        reset_scroll=False,
    ):
        self._updating_checks = True
        self._clear_groups()

        visible_targets = [
            target
            for target in self._visible_targets()
            if target.get("channels")
        ]
        if not visible_targets:
            if self._target_error:
                message = self._target_error
            elif (
                self.scope_combo.currentText() == "Current Stack"
                and self._active_target_key() is None
            ):
                message = "Select a stack in Painter to export."
            elif self.scope_combo.currentText() == "Current Stack":
                message = "No exportable channels found for Current Stack."
            else:
                message = "No exportable channels were found."
            self._show_tree_message(message)
            self.run_button.setDirty(
                False,
                animate=self.dialog.isVisible(),
            )
            self._updating_checks = False
            self._apply_ui_scale(
                self.dialog.settingsUiScale(),
                animate_height=animate_height,
                reset_scroll=reset_scroll,
            )
            return

        select_current = self.scope_combo.currentText() == "Current Stack"
        self._show_tree_message("")

        for target in visible_targets:
            self._add_group(target, checked=select_current)

        self._updating_checks = False
        self._refresh_selection_state()
        self._apply_ui_scale(
            self.dialog.settingsUiScale(),
            animate_height=animate_height,
            reset_scroll=reset_scroll,
        )

    def _add_group(self, target, checked):
        parent_checkbox = make_mock_checkbox(False)
        group = {
            "target": target,
            "parent": parent_checkbox,
            "children": [],
        }
        labels = target.get("channel_labels", {})
        child_rows = []
        selection_key = target_selection_key(target)

        for channel in target.get("channels", []):
            remembered = checked
            if self._selection_memory is not None:
                remembered = self._selection_memory.checked(
                    selection_key,
                    channel,
                    checked,
                )
            checkbox = make_mock_checkbox(remembered)
            row = make_export_tree_item(
                labels.get(channel) or channel,
                checkbox,
                child=True,
            )
            child = {
                "channel": channel,
                "checkbox": checkbox,
                "row": row,
            }
            group["children"].append(child)
            child_rows.append(row)

            def row_press(event, cb=checkbox, owner=group):
                if event.button() == self.QtCore.Qt.MouseButton.LeftButton:
                    cb.toggle()
                    self._update_group(owner)
                    event.accept()

            row.mousePressEvent = row_press
            old_checkbox_press = checkbox.mousePressEvent

            def checkbox_press(
                event,
                owner=group,
                old=old_checkbox_press,
            ):
                old(event)
                if event.button() == self.QtCore.Qt.MouseButton.LeftButton:
                    self._update_group(owner)

            checkbox.mousePressEvent = checkbox_press

        old_parent_press = parent_checkbox.mousePressEvent

        def parent_press(event, owner=group, old=old_parent_press):
            old(event)
            if event.button() != self.QtCore.Qt.MouseButton.LeftButton:
                return
            next_checked = owner["parent"].isChecked()
            for child in owner["children"]:
                child["checkbox"].setChecked(next_checked)
            self._update_group(owner)

        parent_checkbox.mousePressEvent = parent_press
        total = len(group["children"])
        selected = sum(
            1
            for child in group["children"]
            if child["checkbox"].isChecked()
        )
        widget = make_collapsible_group(
            self._target_label(target),
            self._selection_counter(selected, total),
            children=child_rows,
            trailing_widget=parent_checkbox,
            expanded=True,
        )
        group["widget"] = widget
        subtitle = widget.findChild(
            self.QtWidgets.QLabel,
            "RizumCollapsibleSubtitle",
        )
        subtitle.setTextFormat(self.QtCore.Qt.TextFormat.RichText)
        tooltip = self._selection_tooltip(selected, total)
        install_compact_tooltip(subtitle, tooltip)
        subtitle.setAccessibleName(tooltip)
        group["subtitle"] = subtitle
        self.tree_layout.insertWidget(self.tree_layout.count() - 1, widget)
        self.groups.append(group)
        # Follow every animation frame so a collapsed tree cannot retain the
        # expanded content height as a blank scroll range.
        content = widget._rizum_content
        sync_group_height = content._height_changed

        def sync_export_tree_height(value, sync_group=sync_group_height):
            sync_group(value)
            self._sync_tree_content_height()

        content._height_changed = sync_export_tree_height
        self._update_group(group, refresh_total=False)

    def _update_group(self, group, refresh_total=True):
        selected = sum(
            1
            for child in group["children"]
            if child["checkbox"].isChecked()
        )
        total = len(group["children"])
        if not selected:
            group["parent"].setChecked(False)
        elif selected == total:
            group["parent"].setChecked(True)
        else:
            group["parent"].setIndeterminate(True)

        tooltip = self._selection_tooltip(selected, total)
        group["widget"].refreshLayout(
            subtitle_text=self._selection_counter(selected, total)
        )
        group["subtitle"].setCompactTooltipText(tooltip)
        group["subtitle"].setAccessibleName(tooltip)
        if refresh_total and not self._updating_checks:
            self._refresh_selection_state()

    def _visible_targets(self):
        if self.scope_combo.currentText() == "Current Stack":
            active_key = self._active_target_key()
            if active_key is None:
                return []
            texture_set_name, stack_name = active_key
            matches = [
                target
                for target in self.targets
                if target.get("texture_set") == texture_set_name
                and (target.get("stack") or "") == (stack_name or "")
            ]
            return matches
        return self.targets

    def _active_target_key(self):
        try:
            return self.panel.active_target_key()
        except Exception:
            return None

    def _target_label(self, target):
        texture_set = target.get("texture_set") or "(unknown texture set)"
        stack = target.get("stack") or "(default)"
        return stack if stack != "(default)" else texture_set

    def set_all_checked(self, checked):
        self._updating_checks = True
        for group in self.groups:
            for child in group["children"]:
                child["checkbox"].setChecked(checked)
            self._update_group(group, refresh_total=False)
        self._updating_checks = False
        self._refresh_selection_state()

    def _refresh_selection_state(self):
        if not self._updating_checks:
            self._remember_visible_selections()
        selected_total = sum(
            1
            for group in self.groups
            for child in group["children"]
            if child["checkbox"].isChecked()
        )
        self.run_button.setDirty(
            selected_total > 0,
            animate=self.dialog.isVisible(),
        )

    def _remember_visible_selections(self):
        if self._selection_memory is None:
            return
        # Keep choices project-scoped because production files commonly reuse
        # texture-set names while requiring different export channel subsets.
        for group in self.groups:
            self._selection_memory.remember_target(
                target_selection_key(group["target"]),
                {
                    child["channel"]: child["checkbox"].isChecked()
                    for child in group["children"]
                },
            )
        self._selection_memory.save()

    def selected_exports(self):
        selections = []
        for group in self.groups:
            channels = [
                child["channel"]
                for child in group["children"]
                if child["checkbox"].isChecked()
            ]
            if channels:
                selections.append((group["target"], channels))
        return selections

    def export_checked(self):
        selections = self.selected_exports()
        if not selections:
            self.run_button.setDirty(
                False,
                animate=self.dialog.isVisible(),
            )
            return
        # Every export continues into Photoshop, so a missing Photoshop is
        # reported before Painter spends time writing layer PNGs.
        if self.panel.photoshop_executable() is None:
            show_modal_message(
                self.QtWidgets,
                self.dialog,
                "Photoshop",
                "Photoshop was not found. Set Photoshop.exe in Settings before exporting.",
            )
            return

        result = self.panel._run_export_selections(
            "export dialog selection",
            selections,
            self.size_overrides(),
        )
        if not result["ok"]:
            show_modal_message(
                self.QtWidgets,
                self.dialog,
                "Export failed",
                result["message"],
            )
            return

        # The plugin is an automation bridge: every export continues straight
        # into the Photoshop build, so there is no manual handoff to choose.
        try:
            launched, message = self.panel.start_photoshop_build(
                result["export_list"], result["output_dir"]
            )
        except Exception as exc:  # noqa: BLE001 - surface launch preparation errors.
            launched, message = False, f"Could not prepare the Photoshop build script: {exc}"
        if not launched:
            show_modal_message(self.QtWidgets, self.dialog, "Photoshop", message)
            return
        self.dialog.accept()

"""Painter UI registration for Rizum PT-to-PS Bridge."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .exporter import (
    ExportCancelled,
    default_output_dir,
    list_export_targets,
    write_build_bundles,
)

LAST_EXPORT_FILENAME = "_last_export.json"
SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
_ACTIVE_PANEL = None


class SettingsDialog:
    """Global Painter-side bridge settings."""

    def __init__(self, panel):
        self.panel = panel
        self.QtWidgets = panel.QtWidgets

        self.dialog = self.QtWidgets.QDialog(panel.widget)
        self.dialog.setWindowTitle("Settings")
        self.dialog.setModal(True)
        self.dialog.resize(360, 260)

        layout = self.QtWidgets.QVBoxLayout(self.dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        form = self.QtWidgets.QFormLayout()
        form.setLabelAlignment(panel.QtCore.Qt.AlignmentFlag.AlignLeft)

        path_row = self.QtWidgets.QHBoxLayout()
        self.photoshop_path = self.QtWidgets.QLineEdit()
        self.photoshop_path.setPlaceholderText("Photoshop.exe")
        self.browse_button = self.QtWidgets.QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_photoshop)
        path_row.addWidget(self.photoshop_path, 1)
        path_row.addWidget(self.browse_button)
        form.addRow("Photoshop", path_row)

        self.infinite_padding = self.QtWidgets.QCheckBox("Infinite padding")
        form.addRow("Padding", self.infinite_padding)

        self.bit_depth = self.QtWidgets.QComboBox()
        self.bit_depth.addItem("Texture Set", None)
        self.bit_depth.addItem("8-bit", 8)
        self.bit_depth.addItem("16-bit", 16)
        form.addRow("Bit depth", self.bit_depth)

        layout.addLayout(form)
        layout.addStretch(1)

        footer = self.QtWidgets.QHBoxLayout()
        self.cancel_button = self.QtWidgets.QPushButton("Cancel")
        self.done_button = self.QtWidgets.QPushButton("Done")
        self.cancel_button.clicked.connect(self.dialog.reject)
        self.done_button.clicked.connect(self.save)
        footer.addWidget(self.cancel_button)
        footer.addStretch(1)
        footer.addWidget(self.done_button)
        layout.addLayout(footer)

        self.dialog.setStyleSheet(
            """
            QDialog { background: #1f1f21; color: #f1f1f1; }
            QLineEdit, QComboBox { min-height: 28px; padding: 2px 8px; border-radius: 6px; background: #2a2a2d; color: #f1f1f1; }
            QPushButton { min-height: 28px; padding: 4px 14px; border-radius: 14px; background: #333336; color: #f1f1f1; }
            QPushButton:hover { background: #404044; }
            QCheckBox, QLabel { color: #d8d8d8; }
            """
        )

        self.load_values()

    def open(self):
        self.load_values()
        return self.dialog.exec()

    def load_values(self):
        settings = self.panel.user_settings
        self.photoshop_path.setText(settings.get("photoshop_path") or "")
        self.infinite_padding.setChecked(bool(settings.get("infinite_padding")))

        bit_depth = settings.get("bit_depth")
        index = self.bit_depth.findData(bit_depth)
        self.bit_depth.setCurrentIndex(index if index >= 0 else 0)

    def browse_photoshop(self):
        path, _selected_filter = self.QtWidgets.QFileDialog.getOpenFileName(
            self.dialog,
            "Choose Photoshop executable",
            self.photoshop_path.text() or "",
            "Executable (*.exe);;All Files (*)",
        )
        if path:
            self.photoshop_path.setText(path)

    def save(self):
        self.panel.save_user_settings(
            {
                "photoshop_path": self.photoshop_path.text().strip(),
                "infinite_padding": self.infinite_padding.isChecked(),
                "bit_depth": self.bit_depth.currentData(),
            }
        )
        self.dialog.accept()


class ExportDialog:
    """Focused target/channel export dialog launched from the Painter dock."""

    def __init__(self, panel):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtWidgets = panel.QtWidgets
        self.targets = []
        self._updating_checks = False

        self.dialog = self.QtWidgets.QDialog(panel.widget)
        self.dialog.setWindowTitle("Export")
        self.dialog.setModal(True)
        self.dialog.resize(460, 760)

        layout = self.QtWidgets.QVBoxLayout(self.dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = self.QtWidgets.QHBoxLayout()
        self.scope_combo = self.QtWidgets.QComboBox()
        self.scope_combo.addItem("Current Stack")
        self.scope_combo.addItem("All Stacks")
        self.scope_combo.currentIndexChanged.connect(self.refresh_tree)
        header.addWidget(self.scope_combo, 1)

        self.all_button = self.QtWidgets.QPushButton("All")
        self.none_button = self.QtWidgets.QPushButton("None")
        self.all_button.clicked.connect(lambda: self.set_all_checked(True))
        self.none_button.clicked.connect(lambda: self.set_all_checked(False))
        header.addWidget(self.all_button)
        header.addWidget(self.none_button)
        layout.addLayout(header)

        self.tree = self.QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree, 1)

        self.export_pngs = self.QtWidgets.QCheckBox("Export PNGs")
        self.export_pngs.setChecked(True)
        layout.addWidget(self.export_pngs)

        self.status = self.QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.output = self.QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(90)
        layout.addWidget(self.output)

        footer = self.QtWidgets.QHBoxLayout()
        self.cancel_button = self.QtWidgets.QPushButton("Cancel")
        self.run_button = self.QtWidgets.QPushButton("Export")
        self.cancel_button.clicked.connect(self.dialog.reject)
        self.run_button.clicked.connect(self.export_checked)
        footer.addWidget(self.cancel_button)
        footer.addStretch(1)
        footer.addWidget(self.run_button)
        layout.addLayout(footer)

        self.dialog.setStyleSheet(
            """
            QDialog { background: #1f1f21; color: #f1f1f1; }
            QTreeWidget { background: #1f1f21; border: 1px solid #343438; border-radius: 8px; padding: 4px; }
            QTreeWidget::item { min-height: 28px; }
            QPlainTextEdit { background: #161618; border: 1px solid #343438; border-radius: 6px; color: #e8e8e8; }
            QPushButton { min-height: 28px; padding: 4px 14px; border-radius: 14px; background: #333336; color: #f1f1f1; }
            QPushButton:hover { background: #404044; }
            QComboBox { min-height: 28px; padding: 2px 8px; border-radius: 6px; background: #2a2a2d; color: #f1f1f1; }
            QCheckBox { color: #d8d8d8; }
            QLabel { color: #bdbdc2; }
            """
        )

    def open(self):
        self.refresh_targets()
        return self.dialog.exec()

    def _enum(self, group, name):
        container = getattr(self.QtCore.Qt, group, self.QtCore.Qt)
        return getattr(container, name)

    def _checked(self):
        return self._enum("CheckState", "Checked")

    def _unchecked(self):
        return self._enum("CheckState", "Unchecked")

    def _partial(self):
        return self._enum("CheckState", "PartiallyChecked")

    def _user_role(self):
        return self._enum("ItemDataRole", "UserRole")

    def _checkable_flags(self):
        return (
            self._enum("ItemFlag", "ItemIsEnabled")
            | self._enum("ItemFlag", "ItemIsSelectable")
            | self._enum("ItemFlag", "ItemIsUserCheckable")
        )

    def refresh_targets(self):
        if not self.panel._project_is_open():
            self.targets = []
            self.refresh_tree()
            self.status.setText("Open a Painter project to export.")
            return
        if not self.panel._project_is_ready():
            self.targets = []
            self.refresh_tree()
            self.status.setText("Painter project is still loading or not editable.")
            return

        try:
            self.targets = list_export_targets(settings=self.panel._base_export_settings())
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.targets = []
            self.status.setText(f"Could not list export targets: {type(exc).__name__}: {exc}")
        self.refresh_tree()

    def refresh_tree(self):
        self._updating_checks = True
        self.tree.clear()

        visible_targets = self._visible_targets()
        if not visible_targets:
            if self.scope_combo.currentText() == "Current Stack":
                self.status.setText("No exportable channels found for Current Stack.")
            else:
                self.status.setText("No exportable channels were found.")
            self.run_button.setEnabled(False)
            self._updating_checks = False
            return

        self.run_button.setEnabled(True)
        if self.scope_combo.currentText() == "Current Stack" and self._active_target_key() is None:
            self.status.setText("Showing the first available stack for Current Stack.")
        else:
            self.status.setText("")

        for target in visible_targets:
            item = self.QtWidgets.QTreeWidgetItem([self._target_label(target)])
            item.setFlags(self._checkable_flags())
            item.setCheckState(0, self._unchecked())
            item.setData(
                0,
                self._user_role(),
                {"kind": "target", "target": target},
            )
            self.tree.addTopLevelItem(item)

            labels = target.get("channel_labels", {})
            for channel in target.get("channels", []):
                child = self.QtWidgets.QTreeWidgetItem([labels.get(channel) or channel])
                child.setFlags(self._checkable_flags())
                child.setCheckState(0, self._unchecked())
                child.setData(
                    0,
                    self._user_role(),
                    {"kind": "channel", "channel": channel},
                )
                item.addChild(child)
            item.setExpanded(True)

        self._updating_checks = False

    def _visible_targets(self):
        if self.scope_combo.currentText() == "Current Stack":
            active_key = self._active_target_key()
            if active_key is None:
                return self.targets[:1]
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
        channels = target.get("channels") or []
        channel_word = "channel" if len(channels) == 1 else "channels"
        return f"{texture_set} / {stack} / {len(channels)} {channel_word}"

    def set_all_checked(self, checked):
        state = self._checked() if checked else self._unchecked()
        self._updating_checks = True
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            item.setCheckState(0, state)
            for child_index in range(item.childCount()):
                item.child(child_index).setCheckState(0, state)
        self._updating_checks = False

    def _on_item_changed(self, item, column):
        if self._updating_checks or column != 0:
            return

        data = item.data(0, self._user_role()) or {}
        if data.get("kind") == "target":
            self._updating_checks = True
            state = item.checkState(0)
            for child_index in range(item.childCount()):
                item.child(child_index).setCheckState(0, state)
            self._updating_checks = False
            return

        parent = item.parent()
        if parent is None:
            return

        checked_count = 0
        partial_count = 0
        for child_index in range(parent.childCount()):
            state = parent.child(child_index).checkState(0)
            if state == self._checked():
                checked_count += 1
            elif state == self._partial():
                partial_count += 1

        self._updating_checks = True
        if checked_count == parent.childCount():
            parent.setCheckState(0, self._checked())
        elif checked_count or partial_count:
            parent.setCheckState(0, self._partial())
        else:
            parent.setCheckState(0, self._unchecked())
        self._updating_checks = False

    def selected_exports(self):
        selections = []
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            data = item.data(0, self._user_role()) or {}
            target = data.get("target")
            if not target:
                continue

            channels = []
            for child_index in range(item.childCount()):
                child = item.child(child_index)
                if child.checkState(0) != self._checked():
                    continue
                child_data = child.data(0, self._user_role()) or {}
                channel = child_data.get("channel")
                if channel:
                    channels.append(channel)
            if channels:
                selections.append((target, channels))
        return selections

    def export_checked(self):
        selections = self.selected_exports()
        if not selections:
            self.status.setText("Choose at least one channel to export.")
            return

        self.output.clear()
        self.output.setPlainText(
            self.panel._run_export_selections(
                "export dialog selection",
                selections,
                export_pngs=self.export_pngs.isChecked(),
            )
        )


class SmokeTestPanel:
    """Painter dock panel for the PT Bridge workflow."""

    def __init__(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        self.QtCore = QtCore
        self.QtGui = QtGui
        self.QtWidgets = QtWidgets
        self._running = False
        self.targets = []
        self.last_paths = []
        self.last_export_list_path = None
        self.last_output_dir = None
        self.user_settings = self._load_user_settings()
        self.widget = QtWidgets.QWidget()
        self.widget.setObjectName("RizumPtToPsSmokeTestPanel")
        self.widget.setWindowTitle("PT Bridge")

        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.export_pngs = QtWidgets.QCheckBox("Export PNGs")
        self.export_pngs.setChecked(True)

        self.refresh_targets_button = QtWidgets.QPushButton("Refresh Targets")
        self.refresh_targets_button.clicked.connect(self.refresh_targets)

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.setEnabled(False)
        self.target_combo.currentIndexChanged.connect(self.refresh_channel_combo)

        self.channel_combo = QtWidgets.QComboBox()
        self.channel_combo.setEnabled(False)

        self.run_selected_button = QtWidgets.QPushButton("Export Selected Target")
        self.run_selected_button.clicked.connect(self.export_selected_target)

        self.run_stack_button = QtWidgets.QPushButton("Export Selected Stack")
        self.run_stack_button.clicked.connect(self.export_selected_stack)

        self.run_channel_button = QtWidgets.QPushButton("Export Selected Channel")
        self.run_channel_button.clicked.connect(self.export_selected_channel)

        self.run_all_button = QtWidgets.QPushButton("Export All Targets")
        self.run_all_button.clicked.connect(self.export_all_targets)

        self.copy_request_button = QtWidgets.QPushButton("Copy Last Request Path")
        self.copy_request_button.setEnabled(False)
        self.copy_request_button.clicked.connect(self.copy_last_request_path)

        self.copy_export_list_button = QtWidgets.QPushButton("Copy Last Export List Path")
        self.copy_export_list_button.setEnabled(False)
        self.copy_export_list_button.clicked.connect(self.copy_last_export_list_path)

        self.open_output_button = QtWidgets.QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_folder)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)

        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(120)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(8)

        self.dock_export_button = QtWidgets.QPushButton("Export")
        self.dock_export_button.clicked.connect(self.open_export_dialog)
        action_row.addWidget(self.dock_export_button, 1)

        self.dock_bridge_button = QtWidgets.QPushButton("Bridge")
        self.dock_bridge_button.setEnabled(False)
        self.dock_bridge_button.setToolTip("Bridge mapping will be implemented later.")
        action_row.addWidget(self.dock_bridge_button, 1)

        self.dock_settings_button = QtWidgets.QPushButton("Settings")
        self.dock_settings_button.clicked.connect(self.open_settings_dialog)
        action_row.addWidget(self.dock_settings_button, 1)

        layout.addLayout(action_row)

        self.no_project_label = QtWidgets.QLabel("Open a Painter project to export.")
        self.no_project_label.setWordWrap(True)
        self.no_project_label.setVisible(not self._project_is_open())
        layout.addWidget(self.no_project_label)

        layout.addStretch(1)

    def close(self):
        """Stop owned Qt helpers before Painter removes the dock."""
        pass

    def _project_is_open(self):
        try:
            import substance_painter.project

            return substance_painter.project.is_open()
        except Exception:
            return False

    def _project_is_ready(self):
        try:
            import substance_painter.project

            return (
                substance_painter.project.is_open()
                and substance_painter.project.is_in_edition_state()
            )
        except Exception:
            return False

    def active_target_key(self):
        import substance_painter.textureset

        stack = substance_painter.textureset.get_active_stack()
        texture_set = stack.material()
        return (_call_or_attr(texture_set, "name"), _call_or_attr(stack, "name") or "")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.open()

    def _load_user_settings(self):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        bit_depth = _optional_int(store.value("bit_depth", None))
        return {
            "photoshop_path": store.value("photoshop_path", "", str) or "",
            "infinite_padding": _to_bool(store.value("infinite_padding", False)),
            "bit_depth": bit_depth,
        }

    def save_user_settings(self, values):
        store = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        store.setValue("photoshop_path", values.get("photoshop_path") or "")
        store.setValue("infinite_padding", bool(values.get("infinite_padding")))
        bit_depth = values.get("bit_depth")
        if bit_depth:
            store.setValue("bit_depth", int(bit_depth))
        else:
            store.remove("bit_depth")
        store.sync()
        self.user_settings = self._load_user_settings()
        self.status.setText("Settings saved.")

    def open_export_dialog(self):
        self.no_project_label.setVisible(not self._project_is_open())
        if not self._project_is_open():
            return

        dialog = ExportDialog(self)
        dialog.open()

    def refresh_targets(self):
        if not self._project_is_open():
            self.status.setText("Open a Painter project to refresh export targets.")
            return

        self.status.setText("Refreshing export targets...")
        self.QtWidgets.QApplication.processEvents()

        try:
            self.targets = list_export_targets()
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.targets = []
            self.target_combo.clear()
            self.channel_combo.clear()
            self.target_combo.setEnabled(False)
            self.channel_combo.setEnabled(False)
            self.status.setText("Target refresh failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
            return

        self.target_combo.clear()
        for target in self.targets:
            stack_label = target["stack"] or "(default)"
            tile_label = f"{target['uv_tile_count']} tile(s)"
            self.target_combo.addItem(
                f"{target['texture_set']} / {stack_label} / {tile_label}",
                target,
            )

        enabled = bool(self.targets)
        self.target_combo.setEnabled(enabled)
        self.channel_combo.setEnabled(enabled)
        self.refresh_channel_combo()
        self.status.setText(f"Found {len(self.targets)} export target(s).")
        self.output.setPlainText(self._format_targets(self.targets))

    def refresh_channel_combo(self):
        self.channel_combo.clear()
        target = self._selected_target()
        if not target:
            return

        channels = target.get("channels", [])
        channel_labels = target.get("channel_labels", {})
        preferred = "BaseColor" if "BaseColor" in channels else None
        for channel in channels:
            label = channel_labels.get(channel) or channel
            display = label if label == channel else f"{label} ({channel})"
            self.channel_combo.addItem(display, channel)
        if preferred:
            index = self.channel_combo.findData(preferred)
            if index >= 0:
                self.channel_combo.setCurrentIndex(index)

    def export_selected_target(self):
        target = self._selected_target()
        channel = self._selected_channel()
        if not target or not channel:
            self.status.setText("Click Refresh Targets, then choose a target/channel.")
            return

        settings = {
            **self._base_export_settings(),
            "texture_sets": [target["texture_set"]],
            "stacks": [target["stack"]],
            "channels": [channel],
        }
        self._run_export("selected target", settings)

    def export_selected_stack(self):
        target = self._selected_target()
        if not target:
            self.status.setText("Click Refresh Targets, then choose a target.")
            return

        channels = list(target.get("channels") or [])
        if not channels:
            self.status.setText("The selected stack has no exportable channels.")
            return

        stack_label = target["stack"] or "(default)"
        settings = {
            **self._base_export_settings(),
            "texture_sets": [target["texture_set"]],
            "stacks": [target["stack"]],
            "channels": channels,
        }
        self._run_export(
            f"{target['texture_set']} / {stack_label} stack",
            settings,
        )

    def export_selected_channel(self):
        channel = self._selected_channel()
        if not channel:
            self.status.setText("Click Refresh Targets, then choose a channel.")
            return

        settings = {
            **self._base_export_settings(),
            "channels": [channel],
        }
        self._run_export(f"{channel} channel", settings)

    def export_all_targets(self):
        self._run_export("all targets", self._base_export_settings())

    def _run_export(self, label, settings):
        if not self._project_is_open():
            self.status.setText("Open a Painter project before exporting.")
            return
        if not self._project_is_ready():
            self.status.setText("Painter project is still loading or not editable.")
            return

        export_pngs = self.export_pngs.isChecked()
        self._running = True
        self._set_action_buttons_enabled(False)
        self.status.setText(f"Exporting {label}...")
        self.QtWidgets.QApplication.processEvents()
        progress = self._create_export_progress(label)

        try:
            output_dir = default_output_dir(settings)
            paths = write_build_bundles(
                output_dir,
                settings=settings,
                export_pngs=export_pngs,
                progress_callback=lambda event: self._update_export_progress(
                    progress,
                    event,
                ),
            )
        except ExportCancelled:
            self.status.setText("Export cancelled.")
            self.output.setPlainText("Export was cancelled before completion.")
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.status.setText("Export failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
        else:
            self.last_paths = paths
            self.last_output_dir = Path(output_dir)
            self.last_export_list_path = self._write_last_export_list(
                label,
                paths,
                self.last_output_dir,
                settings,
                export_pngs,
            )
            self.copy_request_button.setEnabled(bool(paths))
            self.copy_export_list_button.setEnabled(self.last_export_list_path is not None)
            self.open_output_button.setEnabled(True)
            mode = "JSON + PNG" if export_pngs else "JSON-only"
            self.status.setText(f"Export completed ({mode}).")
            lines = [
                f"Wrote {len(paths)} build request(s):",
                f"Output folder: {self.last_output_dir}",
                f"Last export list: {self.last_export_list_path}",
            ]
            lines.extend(str(path) for path in paths)
            self.output.setPlainText("\n".join(lines))
        finally:
            progress.close()
            self._running = False
            self._set_action_buttons_enabled(True)

    def _run_export_selections(self, label, selections, export_pngs):
        if not self._project_is_open():
            return "Open a Painter project before exporting."
        if not self._project_is_ready():
            return "Painter project is still loading or not editable."
        if not selections:
            return "No channels were selected."

        base_settings = self._base_export_settings()
        output_dir = default_output_dir(base_settings)
        all_paths = []
        texture_sets = []
        stacks = []
        channels = []

        self._running = True
        self._set_action_buttons_enabled(False)
        self.status.setText(f"Exporting {label}...")
        self.QtWidgets.QApplication.processEvents()
        progress = self._create_export_progress(label)

        try:
            for target, selected_channels in selections:
                texture_set = target["texture_set"]
                stack = target["stack"]
                stack_label = stack or "(default)"
                settings = {
                    **base_settings,
                    "texture_sets": [texture_set],
                    "stacks": [stack],
                    "channels": list(selected_channels),
                }
                texture_sets.append(texture_set)
                stacks.append(stack)
                channels.extend(selected_channels)
                self.status.setText(f"Exporting {texture_set} / {stack_label}...")
                all_paths.extend(
                    write_build_bundles(
                        output_dir,
                        settings=settings,
                        export_pngs=export_pngs,
                        progress_callback=lambda event: self._update_export_progress(
                            progress,
                            event,
                        ),
                    )
                )
        except ExportCancelled:
            return "Export was cancelled before completion."
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            return f"{type(exc).__name__}: {exc}"
        finally:
            progress.close()
            self._running = False
            self._set_action_buttons_enabled(True)

        combined_settings = {
            **base_settings,
            "texture_sets": sorted(set(texture_sets)),
            "stacks": _unique_preserving_order(stacks),
            "channels": sorted(set(channels)),
        }
        self.last_paths = all_paths
        self.last_output_dir = Path(output_dir)
        self.last_export_list_path = self._write_last_export_list(
            label,
            all_paths,
            self.last_output_dir,
            combined_settings,
            export_pngs,
        )
        self.copy_request_button.setEnabled(bool(all_paths))
        self.copy_export_list_button.setEnabled(self.last_export_list_path is not None)
        self.open_output_button.setEnabled(True)

        mode = "JSON + PNG" if export_pngs else "JSON-only"
        self.status.setText(f"Export completed ({mode}).")
        lines = [
            f"Wrote {len(all_paths)} build request(s):",
            f"Output folder: {self.last_output_dir}",
            f"Last export list: {self.last_export_list_path}",
        ]
        lines.extend(str(path) for path in all_paths)
        return "\n".join(lines)

    def copy_last_request_path(self):
        if not self.last_paths:
            self.status.setText("No exported build request path to copy yet.")
            return

        self.QtWidgets.QApplication.clipboard().setText(str(self.last_paths[-1]))
        self.status.setText("Copied last build_request.json path.")

    def copy_last_export_list_path(self):
        if self.last_export_list_path is None:
            self.status.setText("No last export list path to copy yet.")
            return

        self.QtWidgets.QApplication.clipboard().setText(str(self.last_export_list_path))
        self.status.setText("Copied last export list path.")

    def open_output_folder(self):
        if self.last_output_dir is None:
            self.status.setText("No output folder to open yet.")
            return

        path = str(self.last_output_dir)
        url = self.QtCore.QUrl.fromLocalFile(path)
        if self.QtGui.QDesktopServices.openUrl(url):
            self.status.setText("Opened output folder.")
        else:
            self.status.setText(f"Could not open output folder: {path}")

    def _selected_target(self):
        index = self.target_combo.currentIndex()
        if index < 0:
            return None
        return self.target_combo.itemData(index)

    def _selected_channel(self):
        index = self.channel_combo.currentIndex()
        if index < 0:
            return None
        return self.channel_combo.itemData(index) or self.channel_combo.currentText()

    def _base_export_settings(self):
        settings = {
            "normal_map_format": "OpenGL",
            "infinite_padding": bool(self.user_settings.get("infinite_padding")),
            "keep_alpha": True,
        }
        bit_depth = self.user_settings.get("bit_depth")
        if bit_depth:
            settings["bit_depth"] = int(bit_depth)
        return settings

    def _write_last_export_list(self, label, paths, output_dir, settings, export_pngs):
        list_path = output_dir / LAST_EXPORT_FILENAME
        payload = {
            "schema_version": 1,
            "request_type": "build_list",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "label": label,
            "export_pngs": bool(export_pngs),
            "output_dir": str(output_dir),
            "settings": {
                "texture_sets": settings.get("texture_sets"),
                "stacks": settings.get("stacks"),
                "channels": settings.get("channels"),
            },
            "build_requests": [
                {
                    "path": str(path),
                    "relative_path": str(path.relative_to(output_dir))
                    if _is_relative_to(path, output_dir)
                    else str(path),
                }
                for path in paths
            ],
        }
        list_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return list_path

    def _set_action_buttons_enabled(self, enabled):
        self.dock_export_button.setEnabled(enabled)
        self.dock_settings_button.setEnabled(enabled)
        self.refresh_targets_button.setEnabled(enabled)
        self.run_selected_button.setEnabled(enabled)
        self.run_stack_button.setEnabled(enabled)
        self.run_channel_button.setEnabled(enabled)
        self.run_all_button.setEnabled(enabled)
        if enabled:
            self.copy_request_button.setEnabled(bool(self.last_paths))
            self.copy_export_list_button.setEnabled(self.last_export_list_path is not None)
            self.open_output_button.setEnabled(self.last_output_dir is not None)
        else:
            self.copy_request_button.setEnabled(False)
            self.copy_export_list_button.setEnabled(False)
            self.open_output_button.setEnabled(False)

    def _create_export_progress(self, label):
        progress = self.QtWidgets.QProgressDialog(
            f"Exporting {label}...",
            "Cancel",
            0,
            0,
            self.widget,
        )
        progress.setWindowTitle("Rizum PT-to-PS Export")
        modality = getattr(self.QtCore.Qt, "ApplicationModal", None)
        if modality is None:
            modality = self.QtCore.Qt.WindowModality.ApplicationModal
        progress.setWindowModality(modality)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setMinimumDuration(0)
        progress.show()
        self.QtWidgets.QApplication.processEvents()
        return progress

    def _update_export_progress(self, progress, event):
        total = int(event.get("total") or 0)
        value = int(event.get("value") or 0)
        text = event.get("text") or "Exporting..."
        if total > 0:
            progress.setRange(0, total)
            progress.setValue(max(0, min(value, total)))
        else:
            progress.setRange(0, 0)
        progress.setLabelText(text)
        self.status.setText(text)
        self.QtWidgets.QApplication.processEvents()
        return not progress.wasCanceled()

    def _format_targets(self, targets):
        lines = ["Available export targets.", ""]
        if not targets:
            lines.append("No texture set targets were found.")
            return "\n".join(lines)

        for index, target in enumerate(targets, start=1):
            stack = target["stack"] or "(default)"
            channel_labels = target.get("channel_labels", {})
            channels = ", ".join(
                channel_labels.get(channel) or channel for channel in target["channels"]
            ) or "(none)"
            lines.append(
                f"[{index}] {target['texture_set']} / {stack} / "
                f"{target['uv_tile_count']} tile(s)"
            )
            lines.append(f"    Channels: {channels}")
        return "\n".join(lines)


def _is_relative_to(path, parent):
    try:
        Path(path).relative_to(parent)
        return True
    except ValueError:
        return False


def _unique_preserving_order(values):
    seen = set()
    unique = []
    for value in values:
        marker = "" if value is None else value
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(value)
    return unique


def _call_or_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    return value() if callable(value) else value


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _optional_int(value):
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def register():
    """Register Painter UI elements and return handles for cleanup."""
    import substance_painter as sp

    global _ACTIVE_PANEL
    panel = SmokeTestPanel()
    _ACTIVE_PANEL = panel
    dock = sp.ui.add_dock_widget(panel.widget)
    dock.setWindowTitle("PT Bridge")
    dock.show()
    dock.raise_()
    sp.logging.info("Rizum PT-to-PS Painter plugin loaded")
    return [dock]


def unregister(handles):
    """Remove Painter UI elements registered by this plugin."""
    import substance_painter as sp

    global _ACTIVE_PANEL
    if _ACTIVE_PANEL is not None:
        _ACTIVE_PANEL.close()
        _ACTIVE_PANEL = None

    for handle in handles:
        sp.ui.delete_ui_element(handle)
    handles.clear()
    sp.logging.info("Rizum PT-to-PS Painter plugin unloaded")

from __future__ import annotations

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from sp_plugin.rizum_sp_to_ps import ui, ui_dialogs, ui_kit
from sp_plugin.rizum_sp_to_ps.export_ui import ExportDialog
from sp_plugin.rizum_sp_to_ps.ui import BridgePanel


class _Panel:
    QtCore = QtCore
    QtGui = QtGui
    QtWidgets = QtWidgets

    def __init__(self):
        self.widget = QtWidgets.QWidget()
        self.user_settings = {}

    def active_target_key(self):
        return None

    def open_output_folder(self):
        pass

    def copy_last_export_list_path(self):
        pass


class FeedbackDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setProperty("rizumUiFontScale", 1.1)

    def setUp(self):
        self.panel = _Panel()

    def tearDown(self):
        for widget in self.app.topLevelWidgets():
            if widget.objectName().startswith("Rizum"):
                widget.close()
                widget.deleteLater()
        self.panel.widget.deleteLater()
        self.app.processEvents()

    def test_message_dialog_uses_the_shared_native_chrome_shell(self):
        dialog = ui_dialogs.build_modal_message(
            QtWidgets,
            self.panel.widget,
            "Export failed",
            "Painter could not export this project.",
        )

        self.assertIsInstance(dialog, ui_kit.PainterSettingsDialog)
        self.assertEqual(dialog.windowTitle(), "Export failed")
        self.assertEqual(
            dialog.findChildren(QtWidgets.QLabel, "RizumDialogTitle"),
            [],
        )
        self.assertIsInstance(
            dialog._rizum_ok_button,
            ui_kit.SecondaryActionButton,
        )
        self.assertEqual(
            dialog._rizum_message_label.text(),
            "Painter could not export this project.",
        )

    def test_export_handoff_uses_shared_fields_and_actions(self):
        export = ExportDialog(self.panel)
        dialog = export._build_export_handoff(
            {
                "count": 2,
                "output_dir": Path("C:/Exports/PT Bridge"),
            }
        )

        self.assertIsInstance(dialog, ui_kit.PainterSettingsDialog)
        self.assertEqual(dialog.windowTitle(), "Export complete")
        self.assertEqual(
            dialog.findChildren(QtWidgets.QLabel, "RizumDialogTitle"),
            [],
        )
        self.assertEqual(
            dialog._rizum_path_field.objectName(),
            "RizumExportHandoffPath",
        )
        for button in (
            dialog._rizum_open_button,
            dialog._rizum_copy_button,
            dialog._rizum_done_button,
        ):
            self.assertIsInstance(button, ui_kit.SecondaryActionButton)

    def test_export_progress_uses_the_compact_dialog_contract(self):
        panel = BridgePanel.__new__(BridgePanel)
        panel.QtCore = QtCore
        panel.QtWidgets = QtWidgets
        panel.widget = self.panel.widget

        progress = panel._create_export_progress("selected channels")
        progress.setRange(0, 4)
        progress.setValue(1)
        progress.setLabelText("Exporting Base Color...")
        self.app.processEvents()

        self.assertIsInstance(progress.dialog, ui_kit.PainterSettingsDialog)
        self.assertNotIsInstance(progress.dialog, QtWidgets.QProgressDialog)
        self.assertEqual(progress.percent_label.text(), "25%")
        self.assertEqual(progress.status_label.text(), "Exporting Base Color...")
        self.assertGreaterEqual(progress.progress_bar.height(), 3)

        progress.cancel_button.click()
        self.assertTrue(progress.wasCanceled())
        self.assertFalse(progress.cancel_button.isEnabled())
        progress.close()


if __name__ == "__main__":
    unittest.main()

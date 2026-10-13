from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from sp_plugin.rizum_sp_to_ps import ui_dialogs, ui_kit
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

    def test_export_progress_uses_the_compact_dialog_contract(self):
        panel = BridgePanel.__new__(BridgePanel)
        panel.QtCore = QtCore
        panel.QtWidgets = QtWidgets
        panel.widget = self.panel.widget

        progress = panel._create_export_progress()
        update = lambda event, **steps: panel._update_export_progress(progress, event, **steps)
        self.assertTrue(update(
            {"stage": "render", "value": 1, "total": 4, "detail": "Layer \u201cPaint\u201d", "context": ""},
            first_step=1, step_total=2,
        ))

        self.assertIsInstance(progress.dialog, ui_kit.PainterSettingsDialog)
        self.assertNotIsInstance(progress.dialog, QtWidgets.QProgressDialog)
        # The mapper's Apply card: the step and its number, what is worked
        # on, and the step's own count instead of a share of the whole export.
        self.assertEqual(progress.heading_label.text(), "Rendering Painter layers")
        self.assertEqual(progress.step_label.text(), "Step 1 of 2")
        self.assertEqual(progress.message_label.text(), "Layer \u201cPaint\u201d")
        self.assertEqual(progress.count_label.text(), "1 / 4")
        self.assertGreaterEqual(progress.progress_bar.height(), 3)

        update({"stage": "match", "value": 0, "total": 1, "detail": "M_body / Base Color"}, first_step=1, step_total=2)
        self.assertEqual(progress.heading_label.text(), "Matching Painter's look")
        self.assertEqual(progress.step_label.text(), "Step 2 of 2")
        self.assertEqual(progress.count_label.text(), "0 / 1")

        progress.cancel_button.click()
        self.assertTrue(progress.wasCanceled())
        self.assertFalse(progress.cancel_button.isEnabled())
        self.assertFalse(update({"stage": "match", "value": 1, "total": 1, "detail": ""}))
        progress.close()

    def test_one_step_export_is_not_numbered_and_names_its_texture_set_among_several(self):
        panel = BridgePanel.__new__(BridgePanel)
        panel.QtCore = QtCore
        panel.QtWidgets = QtWidgets
        panel.widget = self.panel.widget
        progress = panel._create_export_progress()

        event = {"stage": "render", "value": 0, "total": 3, "detail": "Layer \u201cPaint\u201d", "context": ""}
        panel._update_export_progress(progress, event)
        self.assertEqual(progress.step_label.text(), "")
        self.assertEqual(progress.message_label.text(), "Layer \u201cPaint\u201d")

        panel._update_export_progress(progress, event, first_step=3, step_total=4, target="M_dress2")
        self.assertEqual(progress.step_label.text(), "Step 3 of 4")
        self.assertEqual(progress.message_label.text(), "M_dress2 \u00b7 Layer \u201cPaint\u201d")
        progress.close()


    def test_long_message_is_not_clipped(self):
        message = (
            "Imported 3 Photoshop layer(s) into Painter.\n\n"
            "Tint: Photoshop blend mode 'linear light' has no direct Painter "
            "equivalent; Normal was kept."
        )
        dialog = ui_dialogs.build_modal_message(QtWidgets, self.panel.widget, "Bridge complete", message)
        dialog.show()
        self.app.processEvents()
        label = dialog._rizum_message_label
        self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()))
        dialog.close()


if __name__ == "__main__":
    unittest.main()

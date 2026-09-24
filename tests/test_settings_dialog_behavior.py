from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from sp_plugin.rizum_sp_to_ps import ui, ui_dialogs, ui_kit
from sp_plugin.rizum_sp_to_ps.settings_ui import SettingsDialog
from sp_plugin.rizum_sp_to_ps.ui import BridgePanel


class _Panel:
    QtCore = QtCore
    QtGui = QtGui
    QtWidgets = QtWidgets

    def __init__(self):
        self.widget = QtWidgets.QWidget()
        self.user_settings = {
            "photoshop_path": "",
            "infinite_padding": False,
            "dilation": 8,
            "bit_depth": None,
        }
        self.saved = []

    def save_user_settings(self, values):
        self.user_settings = dict(values)
        self.saved.append(dict(values))

    def photoshop_executable(self):
        return Path("C:/Adobe/Adobe Photoshop 2025/Photoshop.exe")


class _SettingsStore:
    def __init__(self):
        self.values = {}
        self.synced = False

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def sync(self):
        self.synced = True


class SettingsDialogBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.panel = _Panel()
        self.settings = SettingsDialog(self.panel)

    def tearDown(self):
        self.settings.dialog.close()
        self.settings.dialog.deleteLater()
        self.panel.widget.deleteLater()
        self.app.processEvents()

    def test_controls_save_live_without_saving_during_initial_load(self):
        self.assertEqual(self.panel.saved, [])

        self.settings.infinite_padding.setChecked(True)
        self.app.processEvents()

        self.assertTrue(self.panel.saved)
        self.assertTrue(self.panel.saved[-1]["infinite_padding"])

    def test_done_closes_without_showing_a_saved_message_dialog(self):
        self.settings.dialog.show()
        self.app.processEvents()

        with mock.patch.object(ui_kit.PainterSettingsDialog, "exec") as modal:
            QtTest.QTest.mouseClick(
                self.settings.done_button,
                QtCore.Qt.MouseButton.LeftButton,
            )

        modal.assert_not_called()
        self.assertEqual(
            self.settings.dialog.result(),
            QtWidgets.QDialog.DialogCode.Accepted,
        )

    def test_panel_persistence_has_no_secondary_confirmation_dialog(self):
        panel = BridgePanel.__new__(BridgePanel)
        panel.QtCore = QtCore
        panel.QtWidgets = QtWidgets
        panel.widget = QtWidgets.QWidget()
        panel._load_user_settings = lambda: {"dilation": 12}
        store = _SettingsStore()
        self.addCleanup(panel.widget.deleteLater)

        with (
            mock.patch.object(QtCore, "QSettings", return_value=store),
            mock.patch.object(ui_kit.PainterSettingsDialog, "exec") as modal,
        ):
            panel.save_user_settings(
                {
                    "photoshop_path": "",
                    "infinite_padding": False,
                    "dilation": 12,
                    "bit_depth": None,
                }
            )

        modal.assert_not_called()
        self.assertTrue(store.synced)


    def test_empty_photoshop_path_shows_the_auto_detected_install(self):
        self.assertIn("Auto-detected", self.settings.photoshop_path.placeholderText())
        self.assertIn("Adobe Photoshop 2025", self.settings.photoshop_path.placeholderText())

    def test_padding_switch_is_labelled_as_infinite_padding(self):
        self.settings.infinite_padding.setChecked(False)
        self.app.processEvents()
        self.assertEqual(self.settings.padding_meta.text(), "Off · uses dilation below")

if __name__ == "__main__":
    unittest.main()

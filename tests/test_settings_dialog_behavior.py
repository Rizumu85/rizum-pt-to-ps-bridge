from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from sp_plugin.rizum_sp_to_ps import ui_kit
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

    def value(self, key, default=None, _type=None):
        return self.values.get(key, default)

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

    def test_smoothing_previews_while_dragging_and_saves_on_release(self):
        slider = self.settings.smoothing_slider
        self.assertEqual(slider.value(), 100)
        middle = QtCore.QPoint(slider.width() // 2, slider.height() // 2)
        QtTest.QTest.mousePress(slider, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(1, middle.y()))
        self.assertIn("Off", self.settings.smoothing_meta.text())
        QtTest.QTest.mouseMove(slider, middle)
        self.assertEqual(self.panel.saved, [])
        QtTest.QTest.mouseRelease(slider, QtCore.Qt.MouseButton.LeftButton, pos=middle)
        self.assertEqual(self.panel.saved[-1]["edge_smoothing"], slider.value())
        self.assertTrue(40 <= slider.value() <= 60)

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

    def test_settings_come_back_as_the_user_set_them(self):
        # Dilation 0 came back as 8, and Blend modes was never stored.
        panel = BridgePanel.__new__(BridgePanel)
        panel.QtCore = QtCore
        with mock.patch.object(QtCore, "QSettings", return_value=_SettingsStore()):
            self.assertEqual(panel._load_user_settings()["dilation"], 8)
            panel.save_user_settings({"dilation": 0, "blend_modes": "keep_blend_modes"})

        self.assertEqual(panel.user_settings["dilation"], 0)
        self.assertEqual(panel.user_settings["blend_modes"], "keep_blend_modes")
        self.assertEqual(panel._base_export_settings()["dilation"], 0)
        self.assertEqual(panel._base_export_settings()["blend_modes"], "keep_blend_modes")

        self.panel.user_settings["dilation"] = 0
        self.settings.load_values()
        self.assertEqual(self.settings.dilation_stepper.value(), 0)

    def test_empty_photoshop_path_shows_the_auto_detected_install(self):
        self.assertIn("Auto-detected", self.settings.photoshop_path.placeholderText())
        self.assertIn("Adobe Photoshop 2025", self.settings.photoshop_path.placeholderText())

    def test_padding_switch_is_labelled_as_infinite_padding(self):
        self.settings.infinite_padding.setChecked(False)
        self.app.processEvents()
        self.assertEqual(self.settings.padding_meta.text(), "Off · uses dilation below")

class FirstUseSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def panel_with(self, stored):
        class Store:
            def __init__(self, *_args):
                pass

            def value(self, key, default=None):
                return stored.get(key, default)

            def setValue(self, key, value):
                stored[key] = value

            def allKeys(self):
                return list(stored)

        panel = BridgePanel.__new__(BridgePanel)
        panel.QtCore = mock.Mock(QSettings=Store)
        return panel

    def test_a_new_user_sees_settings_once_before_the_first_export_or_bridge(self):
        stored = {}
        panel = self.panel_with(stored)
        with mock.patch("sp_plugin.rizum_sp_to_ps.ui.SettingsDialog") as dialog:
            panel.confirm_settings_once()
            panel.confirm_settings_once()
        dialog.assert_called_once_with(panel, first_use=True)
        dialog.return_value.open.assert_called_once()

    def test_someone_who_used_the_plugin_before_is_not_asked(self):
        panel = self.panel_with({"photoshop_path": "C:/Photoshop.exe"})
        with mock.patch("sp_plugin.rizum_sp_to_ps.ui.SettingsDialog") as dialog:
            panel.confirm_settings_once()
        dialog.assert_not_called()

    def test_the_first_use_dialog_says_why_it_opened_and_continues(self):
        from sp_plugin.rizum_sp_to_ps.localization import text

        settings = SettingsDialog(_Panel(), first_use=True)
        self.assertEqual(settings.footer_hint.text(), text("settings_first_use"))
        self.assertEqual(settings.done_button.text(), text("continue"))
        settings.dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()

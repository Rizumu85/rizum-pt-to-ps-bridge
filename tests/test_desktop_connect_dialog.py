import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6 import QtCore, QtWidgets

from sp_plugin.rizum_sp_to_ps.desktop_bridge import DesktopBridgeController


class DesktopConnectDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QtCore.QSettings(
            str(Path(self.directory.name) / "settings.ini"), QtCore.QSettings.Format.IniFormat
        )
        self.widget = QtWidgets.QWidget()
        self.panel = SimpleNamespace(
            QtCore=SimpleNamespace(QSettings=lambda *_: self.settings),
            QtWidgets=QtWidgets, widget=self.widget,
            dock_bridge_button=QtWidgets.QPushButton(self.widget),
            status=QtWidgets.QLabel(self.widget),
        )
        self.controller = DesktopBridgeController(self.panel, Mock())
        self.controller._launch_desktop = Mock()
        self.controller._start_photoshop_document_export = Mock()

    def tearDown(self):
        if not self.controller._closing:
            self.controller.close()
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def test_cancel_reopens_bridge_and_releases_picker(self):
        self.controller._connect_photoshop()
        dialog = self.controller._source_dialog
        self.assertTrue(dialog.isVisible())
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        dialog.reject()
        self.assertIsNone(self.controller._source_dialog)
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertTrue(self.panel.dock_bridge_button.isEnabled())

    def test_accept_psd_starts_export(self):
        source = Path(self.directory.name) / "external.psd"
        source.touch()
        self.controller._connect_photoshop()
        dialog = self.controller._source_dialog
        dialog.selectFile(str(source))
        dialog.accept()
        self.controller._start_photoshop_document_export.assert_called_once_with(source)
        self.assertIsNone(self.controller._source_dialog)

    def test_unload_closes_picker_without_relaunch(self):
        self.controller._connect_photoshop()
        self.controller.close()
        self.assertIsNone(self.controller._source_dialog)
        self.controller._launch_desktop.assert_not_called()

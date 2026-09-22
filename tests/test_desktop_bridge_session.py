import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from sp_plugin.rizum_sp_to_ps.desktop_bridge import (
    MANIFEST_PATH_KEY,
    DesktopBridgeController,
    _desktop_request_type,
    _photoshop_document_session_dir,
    _photoshop_export_error_summary,
)


class _Signal:
    def connect(self, _callback):
        pass


class _Button:
    def __init__(self):
        self.clicked = _Signal()

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setToolTip(self, _tooltip):
        pass


class _Settings:
    values = {}

    def __init__(self, _organization, _application):
        pass

    def value(self, key, default, _value_type):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def sync(self):
        pass


class _QtCore:
    QSettings = _Settings


class _Panel:
    QtCore = _QtCore
    QtWidgets = object()
    widget = object()
    dock_bridge_button = _Button()


class DesktopBridgeSessionTests(unittest.TestCase):
    def setUp(self):
        _Settings.values = {}
        self.controller = DesktopBridgeController(_Panel(), lambda *_args: None)

    def test_window_close_without_transfer_releases_bridge_action(self):
        process = SimpleNamespace(
            readAllStandardError=lambda: b"",
            readAllStandardOutput=lambda: b"",
            deleteLater=Mock(),
        )
        self.controller.panel.status = SimpleNamespace(setText=Mock())
        self.controller._process = process
        self.controller.button.setEnabled(False)

        self.controller._desktop_finished(0, None)

        self.assertIsNone(self.controller._process)
        self.assertTrue(self.controller.button.enabled)
        process.deleteLater.assert_called_once()
        self.controller.panel.status.setText.assert_called_once_with(
            "Bridge mapping cancelled."
        )

    def test_remembers_exact_manifest_until_it_becomes_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "photoshop_selection.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "request_type": "photoshop_selection",
                        "layers": [{"png": "layer.png"}],
                    }
                ),
                encoding="utf-8",
            )

            self.controller._remember_photoshop_manifest(manifest)
            self.assertEqual(self.controller._recent_photoshop_manifest(), manifest)

            manifest.unlink()
            self.assertIsNone(self.controller._recent_photoshop_manifest())
            self.assertNotIn(MANIFEST_PATH_KEY, _Settings.values)

    def test_connect_handoff_releases_process_before_queuing_picker(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "desktop_transfer.json"
            request.write_text(json.dumps({"request_type": "desktop_connect_photoshop"}), encoding="utf-8")
            process = SimpleNamespace(
                readAllStandardError=lambda: b"",
                readAllStandardOutput=lambda: b"[PT Bridge] connect_request_written",
                deleteLater=Mock(),
            )
            schedule = Mock()
            self.controller.QtCore = SimpleNamespace(QTimer=SimpleNamespace(singleShot=schedule))
            self.controller._process = process
            self.controller._transfer_path = request
            self.controller._trace_path = Path(directory) / "desktop_session.log"
            self.controller._desktop_finished(0, None)
            self.assertIsNone(self.controller._process)
            self.assertFalse(self.controller.button.enabled)
            process.deleteLater.assert_called_once()
            schedule.assert_called_once_with(0, self.controller._open_photoshop_picker)
            self.assertIn("connect_request_written", self.controller._trace_path.read_text())

    def test_exit_after_unload_does_not_touch_deleted_widgets(self):
        self.controller._closing = True
        self.controller.button = SimpleNamespace(setEnabled=Mock(side_effect=RuntimeError("deleted")))
        self.controller._desktop_finished(0, None)
        self.controller.button.setEnabled.assert_not_called()

    def test_picker_exception_restores_bridge_action_and_reports_error(self):
        self.controller.panel.status = SimpleNamespace(setText=Mock())
        self.controller._connect_photoshop = Mock(side_effect=RuntimeError("Picker unavailable"))
        self.controller._show_message_callback = Mock()
        self.controller.button.setEnabled(False)
        self.controller._open_photoshop_picker()
        self.assertTrue(self.controller.button.enabled)
        self.assertEqual(self.controller._show_message_callback.call_args.args[-1], "Picker unavailable")

    def test_reads_desktop_connect_request(self):
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "desktop_transfer.json"
            request.write_text(
                json.dumps({"request_type": "desktop_connect_photoshop"}),
                encoding="utf-8",
            )
            self.assertEqual(
                _desktop_request_type(request),
                "desktop_connect_photoshop",
            )

    def test_photoshop_document_session_is_stable_and_path_specific(self):
        root = Path("C:/bridge")
        first = _photoshop_document_session_dir(root, Path("C:/art/Hero Dress.psd"))
        same = _photoshop_document_session_dir(root, Path("C:/art/Hero Dress.psd"))
        other = _photoshop_document_session_dir(root, Path("D:/art/Hero Dress.psd"))

        self.assertEqual(first, same)
        self.assertNotEqual(first, other)
        self.assertTrue(first.name.startswith("Hero_Dress-"))

    def test_photoshop_export_errors_are_bounded_for_the_dialog(self):
        payload = {
            "errors": [
                {"layer": f"Layer {index}", "error": "Could not render"}
                for index in range(10)
            ]
        }

        message = _photoshop_export_error_summary(payload)

        self.assertIn("Layer 0: Could not render", message)
        self.assertIn("...and 2 more error(s).", message)


if __name__ == "__main__":
    unittest.main()

import codecs
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from sp_plugin.rizum_sp_to_ps.desktop_bridge import (
    DesktopBridgeController,
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
    def test_progress_is_written_to_the_mapper(self):
        process = SimpleNamespace(write=Mock())
        self.controller._process = process
        self.controller._apply_progress({"message": "Inserting", "completed": 1, "total": 3})
        reply = json.loads(process.write.call_args.args[0])
        self.assertEqual(reply, {"type": "apply_progress", "message": "Inserting", "completed": 1, "total": 3})

    def setUp(self):
        _Settings.values = {}
        self.controller = DesktopBridgeController(_Panel(), lambda *_args: None)

    def test_window_close_without_transfer_releases_bridge_action(self):
        process = SimpleNamespace()
        self.controller._process = process
        self.controller.button.setEnabled(False)

        self.controller._desktop_finished(process, 0, "")

        self.assertIsNone(self.controller._process)
        self.assertTrue(self.controller.button.enabled)

    def test_a_closed_sessions_late_exit_leaves_the_current_mapper_alone(self):
        current = SimpleNamespace()
        self.controller._process = current
        self.controller._desktop_finished(SimpleNamespace(), 0, "")
        self.assertIs(self.controller._process, current)

    def test_marked_stdout_request_queues_picker_and_traces_other_output(self):
        with tempfile.TemporaryDirectory() as directory:
            chunks = [
                b'[PT Bridge] connect_clicked\n@ptbridge {"type":"connect',
                b'_photoshop"}\n',
            ]
            process = SimpleNamespace()
            schedule = Mock()
            self.controller.QtCore = SimpleNamespace(QTimer=SimpleNamespace(singleShot=schedule))
            self.controller._process = process
            self.controller._stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            self.controller._trace_path = Path(directory) / "desktop_session.log"
            self.controller._desktop_output(process, chunks.pop(0))
            schedule.assert_not_called()
            self.controller._desktop_output(process, chunks.pop(0))
            schedule.assert_called_once_with(0, self.controller._open_photoshop_picker)
            trace = self.controller._trace_path.read_text()
            self.assertIn("connect_clicked", trace)
            self.assertNotIn("@ptbridge", trace)

    def test_exit_after_unload_does_not_touch_deleted_widgets(self):
        self.controller._closing = True
        self.controller.button = SimpleNamespace(setEnabled=Mock(side_effect=RuntimeError("deleted")))
        self.controller._desktop_finished(self.controller._process, 0, "")
        self.controller.button.setEnabled.assert_not_called()

    def test_picker_exception_is_reported_to_the_open_mapper(self):
        self.controller._connect_photoshop = Mock(side_effect=RuntimeError("Picker unavailable"))
        process = SimpleNamespace(write=Mock())
        self.controller._process = process
        self.controller._open_photoshop_picker()
        reply = json.loads(process.write.call_args.args[0].decode("utf-8"))
        self.assertEqual(reply, {"type": "photoshop_connect_failed", "message": "Picker unavailable"})
        self.assertFalse(self.controller._picking)

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

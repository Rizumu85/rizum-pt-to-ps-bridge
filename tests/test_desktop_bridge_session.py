import json
import tempfile
import unittest
from pathlib import Path

from sp_plugin.rizum_sp_to_ps.desktop_bridge import (
    MANIFEST_PATH_KEY,
    DesktopBridgeController,
    _desktop_request_type,
)


class _Signal:
    def connect(self, _callback):
        pass


class _Button:
    def __init__(self):
        self.clicked = _Signal()

    def setEnabled(self, _enabled):
        pass

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


if __name__ == "__main__":
    unittest.main()

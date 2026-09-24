import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_desktop_mapper_ships_the_plugin_version(self):
        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        desktop = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(desktop["version"], plugin["version"])

    def test_settings_show_the_plugin_version(self):
        from sp_plugin.rizum_sp_to_ps.ui_kit import PLUGIN_VERSION

        plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(PLUGIN_VERSION, plugin["version"])


if __name__ == "__main__":
    unittest.main()

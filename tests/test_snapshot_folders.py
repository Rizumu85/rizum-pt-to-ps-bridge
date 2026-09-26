import unittest
from types import SimpleNamespace

from sp_plugin.rizum_sp_to_ps import exporter


class _Group:
    """A Painter group node as the layerstack API exposes it."""

    uid = 42

    def __init__(self, collapsed):
        self._collapsed = collapsed

    def get_name(self):
        return "Working"

    def get_type(self):
        return SimpleNamespace(name="GroupLayer")

    def is_visible(self):
        return True

    def is_collapsed(self):
        return self._collapsed

    def sub_layers(self):
        return []


class SnapshotFolderTests(unittest.TestCase):
    def test_a_group_records_whether_painter_shows_it_folded(self):
        self.assertTrue(exporter._node_record(_Group(True), {}, {})["collapsed"])
        self.assertFalse(exporter._node_record(_Group(False), {}, {})["collapsed"])


if __name__ == "__main__":
    unittest.main()

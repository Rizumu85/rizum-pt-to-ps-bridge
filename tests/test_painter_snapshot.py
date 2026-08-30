from __future__ import annotations

import unittest
from unittest.mock import patch

from sp_plugin.rizum_sp_to_ps.exporter import _build_painter_snapshot


class _Named:
    def __init__(self, name):
        self.name = name


class _Resolution:
    width = 2048
    height = 2048


class _UvTile:
    def __init__(self, u, name):
        self.u = u
        self.v = 0
        self.name = name

    def get_resolution(self):
        return _Resolution()


class _Channel:
    def __init__(self, is_color):
        self.is_color = is_color
        self.format = _Named("sRGB8" if is_color else "L8")
        self.bit_depth = 8


class _Layer:
    uid = 0x2A
    active_channels = set()

    def get_name(self):
        return "Paint"

    def get_type(self):
        return _Named("PaintLayer")

    def is_visible(self):
        return True

    def has_blending(self):
        return False


class _Stack:
    name = ""

    def __init__(self):
        self.all_channels = {
            _Named("BaseColor"): _Channel(True),
            _Named("Normal"): _Channel(False),
        }


class _TextureSet:
    name = "M_body"
    original_name = "M_body"
    has_uv_tiles = True

    def __init__(self):
        self.all_stacks = [_Stack()]
        self.all_uv_tiles = [_UvTile(0, "1001"), _UvTile(1, "1002")]


class _TextureSets:
    all_texture_sets = [_TextureSet()]


class _LayerStack:
    @staticmethod
    def get_root_layer_nodes(_stack):
        return [_Layer()]


class _Project:
    name = "Character"
    file_path = "C:/project/character.spp"
    last_imported_mesh_path = "C:/project/character.fbx"

    @staticmethod
    def get_uuid():
        return "project-uuid"


class PainterSnapshotTests(unittest.TestCase):
    @patch(
        "sp_plugin.rizum_sp_to_ps.exporter._used_channel_identifier_set",
        return_value=None,
    )
    def test_snapshot_keeps_one_layer_tree_per_stack_channel(self, _used_channels):
        snapshot = _build_painter_snapshot(
            {
                "textureset": _TextureSets(),
                "layerstack": _LayerStack(),
                "project": _Project(),
            },
            {},
        )

        self.assertEqual(snapshot["request_type"], "painter_snapshot")
        self.assertEqual(snapshot["project"]["uuid"], "project-uuid")
        self.assertEqual(
            [context["channel"] for context in snapshot["contexts"]],
            ["BaseColor", "Normal"],
        )
        self.assertEqual(len(snapshot["contexts"][0]["uv_tiles"]), 2)
        self.assertEqual(snapshot["contexts"][0]["layers"][0]["uid_hex"], "2a")
        self.assertEqual(len(snapshot["contexts"]), 2)


if __name__ == "__main__":
    unittest.main()

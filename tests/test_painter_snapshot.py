from __future__ import annotations

import unittest
from unittest.mock import patch

from sp_plugin.rizum_sp_to_ps.exporter import _build_painter_snapshot, _channel_content, _snapshot_opacities


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
    active_channels = {_Named("BaseColor"), _Named("Normal")}

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

    def material(self):
        return _TextureSet()

    def __init__(self):
        self.all_channels = {
            _Named("BaseColor"): _Channel(True),
            _Named("Normal"): _Channel(False),
        }


class _CallableName(str):
    def __call__(self):
        raise AssertionError("TextureSet.name must be read as a property")


class _TextureSet:
    name = _CallableName("M_body")
    original_name = "M_body"
    has_uv_tiles = True

    def __init__(self):
        self.all_stacks = [_Stack()]
        self.all_uv_tiles = [_UvTile(0, "1001"), _UvTile(1, "1002")]


class _TextureSets:
    all_texture_sets = [_TextureSet()]

    @staticmethod
    def get_active_stack():
        return _Stack()


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
    def test_snapshot_opacity_is_channel_specific_percent_even_below_one_percent(self):
        nodes = [{"opacity": {"BaseColor": 0.01, "Normal": 0.65}, "children": [
            {"opacity": {"BaseColor": 0.005}}, {"opacity": None},
        ]}]
        _snapshot_opacities(nodes, "BaseColor")
        self.assertEqual(nodes[0]["opacity"], 1)
        self.assertEqual(nodes[0]["children"][0]["opacity"], 0.5)
        self.assertEqual(nodes[0]["children"][1]["opacity"], 100)

    def test_snapshot_lists_only_layers_the_channel_shows(self):
        nodes = [
            {"name": "Color fill", "active_channels": ["BaseColor"]},
            {"name": "Height fill", "active_channels": ["Height"]},
            {"name": "Paint"},
            {"name": "Height folder", "children": [{"name": "Bump", "active_channels": ["Height"]}]},
            {"name": "Mixed folder", "children": [
                {"name": "Bump", "active_channels": ["Height"]}, {"name": "Tint", "active_channels": ["BaseColor"]},
            ]},
            {"name": "Empty folder", "children": []},
        ]
        kept = _channel_content(nodes, "BaseColor")
        self.assertEqual([node["name"] for node in kept], ["Color fill", "Paint", "Mixed folder", "Empty folder"])
        self.assertEqual([node["name"] for node in kept[2]["children"]], ["Tint"])

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
        # The mapper's pre-Apply blend warning reads the same table Apply uses.
        self.assertIn("multiply", snapshot["photoshop_blend_modes"])
        self.assertNotIn("hardmix", snapshot["photoshop_blend_modes"])
        self.assertEqual(snapshot["active_context"], {"texture_set": "M_body", "stack": ""})
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

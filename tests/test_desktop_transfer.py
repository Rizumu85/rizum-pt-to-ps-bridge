import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from sp_plugin.rizum_sp_to_ps.desktop_transfer import (
    DesktopTransferError,
    apply_transfer_plan,
    load_transfer_plan,
)


class _NamedValue:
    def __init__(self, name):
        self.name = name


class _Stack:
    def __init__(self, channel):
        self._channel = channel

    def material(self):
        return SimpleNamespace(name=lambda: "M_body")

    def name(self):
        return ""

    def all_channels(self):
        return {self._channel: object()}


class _TargetNode:
    def __init__(self, stack):
        self._stack = stack

    def get_stack(self):
        return self._stack


class _FillNode:
    def __init__(self):
        self.name = ""
        self.active_channels = set()
        self.sources = []
        self.visible = None
        self.opacity = None
        self.blending_mode = None
        self.mask_background = None

    def set_name(self, value):
        self.name = value

    def set_source(self, channel, source):
        self.sources.append((channel, source))

    def set_visible(self, value):
        self.visible = value

    def set_opacity(self, value, channel):
        self.opacity = (value, channel)

    def set_blending_mode(self, mode, channel):
        self.blending_mode = (mode, channel)

    def add_mask(self, background):
        self.mask_background = background


class _ScopedModification:
    names = []

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.names.append(self.name)

    def __exit__(self, _type, _value, _traceback):
        return False


class _LayerStack:
    def __init__(self, target):
        self.target = target
        self.fills = []
        self.ScopedModification = _ScopedModification
        self.InsertPosition = SimpleNamespace(
            below_node=lambda node: ("below", node),
            inside_node=lambda node, stack: ("inside", node, stack),
        )
        self.NodeStack = SimpleNamespace(Content="content", Mask="mask")
        self.MaskBackground = SimpleNamespace(Black="black")
        self.BlendingMode = SimpleNamespace(Normal="normal", Overlay="overlay")

    def get_node_by_uid(self, uid):
        if uid != 0x1A:
            raise ValueError(uid)
        return self.target

    def insert_fill(self, _position):
        fill = _FillNode()
        self.fills.append(fill)
        return fill


class _Resource:
    class Usage:
        TEXTURE = "texture"

    def __init__(self):
        self.imported = []

    def import_project_resource(self, path, usage):
        self.imported.append((path, usage))
        return SimpleNamespace(identifier=lambda: f"resource:{Path(path).name}")


class DesktopTransferTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.layer_png = self.root / "paint.png"
        self.mask_png = self.root / "paint_mask.png"
        self.layer_png.write_bytes(b"png")
        self.mask_png.write_bytes(b"mask")
        self.manifest = self.root / "desktop_transfer.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "request_type": "desktop_transfer",
                    "target": {
                        "host": "substance_painter",
                        "document": {
                            "uuid": "project-1",
                            "path": "C:/projects/example.spp",
                        },
                        "context": {
                            "texture_set": "M_body",
                            "stack": "",
                            "channel": "BaseColor",
                        },
                    },
                    "transfers": [
                        {
                            "order": 0,
                            "insertion": "after",
                            "source": {
                                "host": "photoshop",
                                "kind": "pixel",
                                "path": "Retouch/Paint edit",
                                "png": str(self.layer_png),
                                "mask_png": str(self.mask_png),
                                "blend_mode": "overlay",
                                "opacity": 65,
                                "visible": False,
                            },
                            "target": {
                                "host": "substance_painter",
                                "id": "1a",
                                "kind": "PaintLayer",
                                "path": "Working",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def test_plan_preserves_painter_address_and_photoshop_layer_state(self):
        plan = load_transfer_plan(self.manifest)

        self.assertEqual(plan.texture_set, "M_body")
        self.assertEqual(plan.channel, "BaseColor")
        self.assertEqual(plan.items[0].target_uid, 0x1A)
        self.assertEqual(plan.items[0].name, "Paint edit")
        self.assertEqual(plan.items[0].blend_mode, "overlay")
        self.assertEqual(plan.items[0].opacity, 65)
        self.assertFalse(plan.items[0].visible)

    def test_apply_creates_one_channel_fill_and_a_bitmap_mask(self):
        plan = load_transfer_plan(self.manifest)
        channel = _NamedValue("BaseColor")
        stack = _Stack(channel)
        layerstack = _LayerStack(_TargetNode(stack))
        resource = _Resource()
        painter = SimpleNamespace(
            project=SimpleNamespace(
                is_open=lambda: True,
                is_in_edition_state=lambda: True,
                get_uuid=lambda: "project-1",
                file_path=lambda: "C:/projects/example.spp",
            ),
            layerstack=layerstack,
            resource=resource,
        )

        result = apply_transfer_plan(plan, painter)

        self.assertEqual(result.count, 1)
        self.assertEqual(len(layerstack.fills), 2)
        layer, mask = layerstack.fills
        self.assertEqual(layer.name, "Paint edit")
        self.assertEqual(layer.active_channels, {channel})
        self.assertEqual(layer.sources, [(channel, "resource:paint.png")])
        self.assertEqual(layer.opacity, (0.65, channel))
        self.assertEqual(layer.blending_mode, ("overlay", channel))
        self.assertFalse(layer.visible)
        self.assertEqual(layer.mask_background, "black")
        self.assertEqual(mask.sources, [(None, "resource:paint_mask.png")])
        self.assertEqual(
            _ScopedModification.names[-1],
            "PT Bridge: import Photoshop layers",
        )

    def test_missing_source_png_is_rejected_before_painter_import(self):
        self.layer_png.unlink()

        with self.assertRaisesRegex(DesktopTransferError, "does not exist"):
            load_transfer_plan(self.manifest)


if __name__ == "__main__":
    unittest.main()

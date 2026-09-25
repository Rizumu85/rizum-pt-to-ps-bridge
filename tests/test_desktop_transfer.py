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
        return SimpleNamespace(name="M_body")

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
        self.groups = []
        self.ScopedModification = _ScopedModification
        self.InsertPosition = SimpleNamespace(
            above_node=lambda node: ("above", node),
            below_node=lambda node: ("below", node),
            inside_node=lambda node, stack: ("inside", node, stack),
        )
        self.NodeStack = SimpleNamespace(Content="content", Mask="mask", Substack="substack")
        self.MaskBackground = SimpleNamespace(Black="black")
        self.BlendingMode = SimpleNamespace(Normal="normal", Overlay="overlay", PassThrough="passthrough")

    def get_node_by_uid(self, uid):
        if uid != 0x1A:
            raise ValueError(uid)
        return self.target

    def insert_fill(self, position):
        fill = _FillNode()
        fill.position = position
        self.fills.append(fill)
        return fill

    def insert_group(self, position):
        group = _FillNode()
        group.position = position
        self.groups.append(group)
        return group


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
                    "schema_version": 3,
                    "request_type": "desktop_transfer",
                    "photoshop": {
                        "document": {
                            "id": 42,
                            "name": "example.psd",
                            "path": "C:/projects/example.psd",
                        },
                        "context": {},
                    },
                    "painter": {
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
                            "direction": "photoshop_to_painter",
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
        self.assertEqual(plan.painter_imports[0].target_uid, 0x1A)
        layer = plan.painter_imports[0].layer
        self.assertEqual(layer.name, "Paint edit")
        self.assertEqual(layer.blend_mode, "overlay")
        self.assertEqual(layer.opacity, 65)
        self.assertFalse(layer.visible)
        self.assertEqual(plan.photoshop_exports, ())

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

    def test_before_inserts_above_the_target_so_a_list_top_is_reachable(self):
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["transfers"][0]["insertion"] = "before"
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        target = _TargetNode(_Stack(_NamedValue("BaseColor")))
        layerstack = _LayerStack(target)
        painter = SimpleNamespace(
            project=SimpleNamespace(
                is_open=lambda: True,
                is_in_edition_state=lambda: True,
                get_uuid=lambda: "project-1",
            ),
            layerstack=layerstack,
            resource=_Resource(),
        )

        apply_transfer_plan(load_transfer_plan(self.manifest), painter)

        self.assertEqual(layerstack.fills[0].position, ("above", target))

    def test_inside_an_empty_folder_inserts_into_its_substack(self):
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["transfers"][0]["insertion"] = "inside"
        payload["transfers"][0]["target"]["kind"] = "GroupLayer"
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        target = _TargetNode(_Stack(_NamedValue("BaseColor")))
        target.sub_layers = lambda: []
        layerstack = _LayerStack(target)
        painter = SimpleNamespace(
            project=SimpleNamespace(
                is_open=lambda: True,
                is_in_edition_state=lambda: True,
                get_uuid=lambda: "project-1",
            ),
            layerstack=layerstack,
            resource=_Resource(),
        )

        apply_transfer_plan(load_transfer_plan(self.manifest), painter)

        self.assertEqual(layerstack.fills[0].position, ("inside", target, "substack"))

    def test_plan_preserves_painter_to_photoshop_direction_and_native_ids(self):
        reverse_manifest = self.root / "reverse_transfer.json"
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["transfers"] = [
            {
                "order": 0,
                "direction": "painter_to_photoshop",
                "insertion": "after",
                "source": {
                    "host": "substance_painter",
                    "id": "2b",
                    "kind": "FillLayer",
                    "path": "Working/Recolor",
                    "blend_mode": "COLOR",
                    "opacity": 72,
                    "visible": True,
                },
                "target": {
                    "host": "photoshop",
                    "id": "101",
                    "kind": "pixel",
                    "path": "Retouch",
                },
            }
        ]
        reverse_manifest.write_text(json.dumps(payload), encoding="utf-8")

        plan = load_transfer_plan(reverse_manifest)

        self.assertEqual(plan.painter_imports, ())
        self.assertEqual(plan.photoshop_exports[0].source_uid, 0x2B)
        self.assertEqual(plan.photoshop_exports[0].target_layer_id, 101)
        self.assertEqual(plan.photoshop_exports[0].name, "Recolor")

    def test_photoshop_target_without_layer_id_is_addressed_by_position(self):
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        payload["transfers"] = [{
            "order": 0, "direction": "painter_to_photoshop", "insertion": "after",
            "source": {"host": "substance_painter", "id": "2b", "kind": "FillLayer", "path": "Recolor"},
            "target": {"host": "photoshop", "id": None, "kind": "layer", "path": "Paint/Base", "index_path": [0, 1]},
        }]
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")

        item = load_transfer_plan(self.manifest).photoshop_exports[0]

        self.assertIsNone(item.target_layer_id)
        self.assertEqual(item.target_index_path, (0, 1))
        self.assertEqual(item.target_name, "Base")

    def painter(self, layerstack):
        return SimpleNamespace(
            project=SimpleNamespace(
                is_open=lambda: True,
                is_in_edition_state=lambda: True,
                get_uuid=lambda: "project-1",
            ),
            layerstack=layerstack,
            resource=_Resource(),
        )

    def test_photoshop_folder_becomes_a_painter_folder_of_its_layers(self):
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        source = payload["transfers"][0]["source"]
        payload["transfers"][0]["source"] = {
            "host": "photoshop", "kind": "group", "path": "Retouch", "png": None,
            "mask_png": str(self.mask_png), "blend_mode": "pass through", "opacity": 80,
            "visible": True,
            "children": [
                {**source, "path": "Retouch/Top", "mask_png": None},
                {**source, "path": "Retouch/Bottom", "mask_png": None},
            ],
        }
        payload["warnings"] = ["Levels: Adjustment layer · not supported, skipped."]
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        channel = _NamedValue("BaseColor")
        target = _TargetNode(_Stack(channel))
        layerstack = _LayerStack(target)

        plan = load_transfer_plan(self.manifest)
        apply_transfer_plan(plan, self.painter(layerstack))

        folder = layerstack.groups[0]
        self.assertEqual(folder.name, "Retouch")
        self.assertEqual(folder.position, ("below", target))
        self.assertEqual(folder.blending_mode, ("passthrough", channel))
        self.assertEqual(folder.opacity, (0.8, channel))
        self.assertEqual(folder.mask_background, "black")
        mask, top, bottom = layerstack.fills
        self.assertEqual(mask.sources, [(None, "resource:paint_mask.png")])
        self.assertEqual(top.name, "Top")
        self.assertEqual(top.position, ("inside", folder, "substack"))
        self.assertEqual(bottom.name, "Bottom")
        self.assertEqual(bottom.position, ("below", top))
        self.assertEqual(plan.warnings, ("Levels: Adjustment layer · not supported, skipped.",))

    def test_photoshop_colour_fill_stays_an_editable_colour(self):
        payload = json.loads(self.manifest.read_text(encoding="utf-8"))
        source = payload["transfers"][0]["source"]
        source.update({"png": None, "mask_png": None, "color": [1.0, 0.5, 0.0]})
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")
        for is_color, space in ((True, "srgb"), (False, "working")):
            channel = _NamedValue("BaseColor")
            stack = _Stack(channel)
            stack.all_channels = lambda: {channel: SimpleNamespace(is_color=lambda: is_color)}
            layerstack = _LayerStack(_TargetNode(stack))
            painter = self.painter(layerstack)
            painter.colormanagement = SimpleNamespace(
                GenericColorSpace=SimpleNamespace(sRGB="srgb", Working="working"),
                Color=lambda *values: values,
            )

            apply_transfer_plan(load_transfer_plan(self.manifest), painter)

            self.assertEqual(layerstack.fills[0].sources, [(channel, (1.0, 0.5, 0.0, space))])
            self.assertEqual(painter.resource.imported, [])

    def test_missing_source_png_is_rejected_before_painter_import(self):
        self.layer_png.unlink()

        with self.assertRaisesRegex(DesktopTransferError, "does not exist"):
            load_transfer_plan(self.manifest)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from PySide6 import QtGui

from sp_plugin.rizum_sp_to_ps.exporter import _annotate_node_assets
from sp_plugin.rizum_sp_to_ps.geometry_mask import GeometryMaskBaker


class GeometryMaskRasterizationTests(unittest.TestCase):
    def test_adjacent_uv_faces_do_not_leave_internal_wireframe_seams(self):
        baker = GeometryMaskBaker()
        names = frozenset({"mesh"})
        baker._faces = [
            (names, "material", ((0.2, 0.2), (0.8, 0.2), (0.8, 0.8))),
            (names, "material", ((0.2, 0.2), (0.8, 0.8), (0.2, 0.8))),
        ]

        png_bytes, _face_count = baker._rasterize(
            {"mesh"},
            set(),
            {"u": 0, "v": 0},
            64,
            64,
        )
        image = QtGui.QImage.fromData(png_bytes, "PNG")

        # Sample the shared diagonal away from the UV island silhouette. A
        # correct geometry mask is a filled selection, not a UV wireframe.
        diagonal_values = [
            QtGui.qRed(image.pixel(x, 63 - x))
            for x in range(20, 45)
        ]
        self.assertEqual(min(diagonal_values), 255)

    def test_custom_dilation_expands_the_selected_uv_region(self):
        baker = GeometryMaskBaker()
        names = frozenset({"mesh"})
        baker._faces = [
            (names, "material", ((0.3, 0.3), (0.7, 0.3), (0.7, 0.7))),
            (names, "material", ((0.3, 0.3), (0.7, 0.7), (0.3, 0.7))),
        ]

        plain_png, _ = baker._rasterize(
            {"mesh"}, {"material"}, {"u": 0, "v": 0}, 64, 64
        )
        dilated_png, _ = baker._rasterize(
            {"mesh"},
            {"material"},
            {"u": 0, "v": 0},
            64,
            64,
            padding="Transparent",
            dilation=6,
        )
        plain = QtGui.QImage.fromData(plain_png, "PNG")
        dilated = QtGui.QImage.fromData(dilated_png, "PNG")

        self.assertEqual(QtGui.qRed(plain.pixel(16, 32)), 0)
        self.assertEqual(QtGui.qRed(dilated.pixel(16, 32)), 255)

    def test_infinite_padding_fills_empty_uv_space_but_not_excluded_meshes(self):
        baker = GeometryMaskBaker()
        baker._faces = [
            (
                frozenset({"selected"}),
                "material",
                ((0.15, 0.2), (0.35, 0.2), (0.35, 0.8)),
            ),
            (
                frozenset({"excluded"}),
                "material",
                ((0.65, 0.2), (0.85, 0.2), (0.85, 0.8)),
            ),
        ]

        png_bytes, _ = baker._rasterize(
            {"selected"},
            {"material"},
            {"u": 0, "v": 0},
            64,
            64,
            padding="Infinite",
            dilation=0,
        )
        image = QtGui.QImage.fromData(png_bytes, "PNG")

        self.assertEqual(QtGui.qRed(image.pixel(0, 0)), 255)
        self.assertEqual(QtGui.qRed(image.pixel(50, 32)), 0)

    def test_geometry_asset_receives_the_resolved_export_padding(self):
        node = {
            "uid": 7,
            "uid_hex": "7",
            "name": "Masked layer",
            "kind": "FillLayer",
            "has_mask": False,
            "mask_enabled": False,
            "geometry_mask": {
                "mode": "mesh",
                "is_restrictive": True,
                "enabled_meshes": ["mesh"],
            },
        }
        request = {
            "texture_set": "Material",
            "texture_set_original": "Material",
            "uv_tile": {"u": 0, "v": 0},
            "export_settings": {
                "padding": "Transparent",
                "dilation": 12,
                "resolution": [64, 64],
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            _annotate_node_assets(
                node,
                Path(directory),
                request_channel="BaseColor",
                request=request,
            )

        self.assertEqual(node["geometry_mask_asset"]["padding"], "Transparent")
        self.assertEqual(node["geometry_mask_asset"]["dilation"], 12)

    def test_material_coverage_path_is_reused_between_geometry_masks(self):
        baker = GeometryMaskBaker()
        baker._faces = [
            (
                frozenset({"first"}),
                "material",
                ((0.1, 0.1), (0.4, 0.1), (0.4, 0.4)),
            ),
            (
                frozenset({"second"}),
                "material",
                ((0.6, 0.6), (0.9, 0.6), (0.9, 0.9)),
            ),
        ]

        baker._rasterize(
            {"first"}, {"material"}, {"u": 0, "v": 0}, 64, 64, dilation=4
        )
        first_path = next(iter(baker._coverage_path_cache.values()))
        baker._rasterize(
            {"second"}, {"material"}, {"u": 0, "v": 0}, 64, 64, dilation=4
        )

        self.assertEqual(len(baker._coverage_path_cache), 1)
        self.assertIs(first_path, next(iter(baker._coverage_path_cache.values())))


if __name__ == "__main__":
    unittest.main()

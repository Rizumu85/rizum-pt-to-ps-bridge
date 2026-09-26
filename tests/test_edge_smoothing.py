import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6 import QtGui

from sp_plugin.rizum_sp_to_ps import edge_smoothing, png_color_metadata
from sp_plugin.rizum_sp_to_ps.exporter import _smooth_exported_assets


class EdgeSmoothingTests(unittest.TestCase):
    @staticmethod
    def _raw_color_policy():
        return {
            "schema_version": 1,
            "encoding": "raw",
            "photoshop_profile": None,
            "embed_profile": False,
            "preserve_rgb_numbers": True,
        }

    def _write_image(self, path, rows, image_format=QtGui.QImage.Format.Format_RGBA8888):
        height = len(rows)
        width = len(rows[0])
        image = QtGui.QImage(width, height, image_format)
        for y, row in enumerate(rows):
            for x, color in enumerate(row):
                image.setPixelColor(x, y, color)
        self.assertTrue(image.save(str(path), "PNG"))

    def test_straight_edges_and_solid_interiors_remain_exact(self):
        black = QtGui.QColor(0, 0, 0, 255)
        white = QtGui.QColor(255, 255, 255, 255)
        rows = [[black, black, black, white, white] for _ in range(5)]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "straight.png"
            self._write_image(path, rows)
            original_bytes = path.read_bytes()
            result = edge_smoothing.smooth_png(path)
            output = QtGui.QImage(str(path))
            output_bytes = path.read_bytes()

        self.assertEqual(result["changed_pixels"], 0)
        self.assertEqual(output_bytes, original_bytes)
        self.assertEqual(output.pixelColor(1, 2), black)
        self.assertEqual(output.pixelColor(3, 2), white)

    def test_staircase_corners_gain_intermediate_color(self):
        black = QtGui.QColor(0, 0, 0, 255)
        white = QtGui.QColor(255, 255, 255, 255)
        rows = [
            [white if x <= y else black for x in range(7)]
            for y in range(7)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "staircase.png"
            self._write_image(path, rows)
            result = edge_smoothing.smooth_png(path)
            output = QtGui.QImage(str(path))
            values = [
                output.pixelColor(x, y).red()
                for y in range(output.height())
                for x in range(output.width())
            ]

        self.assertGreater(result["changed_pixels"], 0)
        self.assertTrue(any(0 < value < 255 for value in values))

    def test_shallow_transparent_edge_blends_like_clip_studio_paint(self):
        # Rows of five opaque pixels stepping up to the right, as in the CSP
        # reference: each step becomes one ramp, half outside and half inside
        # the original footprint, and keeps the shape's own colour.
        clear = QtGui.QColor(0, 0, 0, 0)
        red = QtGui.QColor(220, 60, 60, 255)
        rows = [
            [red if x >= 30 - 5 * y else clear for x in range(32)]
            for y in range(6)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alpha.png"
            self._write_image(path, rows)
            result = edge_smoothing.smooth_png(path)
            output = QtGui.QImage(str(path))

        self.assertGreater(result["changed_pixels"], 0)
        # Row 3 starts at x=15; the rows around it step at x=20 and x=10.
        ramp = [round(output.pixelColor(x, 3).alpha() / 2.55) for x in range(12, 19)]
        self.assertEqual(ramp, [2, 20, 40, 60, 80, 98, 100])
        self.assertEqual((output.pixelColor(13, 3).red(), output.pixelColor(13, 3).green()), (220, 60))
        before = sum(row.alpha() for row_pixels in rows for row in row_pixels)
        after = sum(output.pixelColor(x, y).alpha() for y in range(6) for x in range(32))
        self.assertLess(abs(after - before), 255)

    def test_corners_of_long_straight_edges_stay_square(self):
        clear = QtGui.QColor(0, 0, 0, 0)
        white = QtGui.QColor(255, 255, 255, 255)
        rows = [
            [white if 2 <= x < 10 and 2 <= y < 10 else clear for x in range(12)]
            for y in range(12)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "square.png"
            self._write_image(path, rows)
            result = edge_smoothing.smooth_png(path)

        self.assertEqual(result["changed_pixels"], 0)

    def test_16_bit_payload_remains_16_bit(self):
        image_format = QtGui.QImage.Format.Format_RGBA64
        black = QtGui.QColor.fromRgba64(0, 0, 0, 65_535)
        white = QtGui.QColor.fromRgba64(65_535, 65_535, 65_535, 65_535)
        rows = [
            [white if x <= y else black for x in range(5)]
            for y in range(5)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sixteen.png"
            self._write_image(path, rows, image_format=image_format)
            result = edge_smoothing.smooth_png(path)
            output = QtGui.QImage(str(path))

        self.assertEqual(result["bit_depth"], 16)
        self.assertGreater(output.depth(), 32)

    def test_request_processing_smooths_layers_and_final_masks_but_not_uv_map(self):
        request = {
            "channel_identifier": "BaseColor",
            "color_management": self._raw_color_policy(),
            "layers": [
                {
                    "asset": {"path": "layer.png", "channel": "BaseColor"},
                    "mask_asset": {"path": "mask.png"},
                }
            ],
            "uv_map_asset": {"path": "uv.png"},
        }
        calls = []

        with mock.patch.object(
            edge_smoothing,
            "smooth_png",
            side_effect=lambda path: calls.append(path) or {"changed_pixels": 3},
        ), mock.patch.object(
            png_color_metadata,
            "normalize_png",
            return_value={"changed": False},
        ):
            result = _smooth_exported_assets(request)

        self.assertEqual(calls, ["layer.png", "mask.png"])
        self.assertEqual(result["layer_assets"], 1)
        self.assertEqual(result["mask_assets"], 1)
        self.assertEqual(result["changed_pixels"], 6)

    def test_smoothing_continues_the_existing_export_progress_range(self):
        request = {
            "channel_identifier": "BaseColor",
            "color_management": self._raw_color_policy(),
            "layers": [{"asset": {"path": "layer.png", "channel": "BaseColor"}}],
        }
        events = []

        with mock.patch.object(
            edge_smoothing,
            "smooth_png",
            return_value={"changed_pixels": 0},
        ), mock.patch.object(
            png_color_metadata,
            "normalize_png",
            return_value={"changed": False},
        ):
            _smooth_exported_assets(
                request,
                progress_callback=lambda event: events.append(event),
                progress_offset=3,
                progress_total=4,
            )

        self.assertEqual([event["value"] for event in events], [3, 4])
        self.assertEqual({event["total"] for event in events}, {4})


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6 import QtGui

from sp_plugin.rizum_sp_to_ps import edge_smoothing
from sp_plugin.rizum_sp_to_ps.exporter import _smooth_exported_assets


class EdgeSmoothingTests(unittest.TestCase):
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

    def test_staircase_corners_gain_intermediate_coverage(self):
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

    def test_transparent_rgb_does_not_bleed_into_antialiased_pixels(self):
        clear_magenta = QtGui.QColor(255, 0, 255, 0)
        opaque_white = QtGui.QColor(255, 255, 255, 255)
        rows = [
            [opaque_white if x <= y else clear_magenta for x in range(7)]
            for y in range(7)
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alpha.png"
            self._write_image(path, rows)
            edge_smoothing.smooth_png(path)
            output = QtGui.QImage(str(path))
            intermediate = [
                output.pixelColor(x, y)
                for y in range(output.height())
                for x in range(output.width())
                if 0 < output.pixelColor(x, y).alpha() < 255
            ]

        self.assertTrue(intermediate)
        self.assertTrue(all(color.green() == 255 for color in intermediate))

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
        ):
            result = _smooth_exported_assets(request)

        self.assertEqual(calls, ["layer.png", "mask.png"])
        self.assertEqual(result["layer_assets"], 1)
        self.assertEqual(result["mask_assets"], 1)
        self.assertEqual(result["changed_pixels"], 6)

    def test_smoothing_continues_the_existing_export_progress_range(self):
        request = {
            "channel_identifier": "BaseColor",
            "layers": [{"asset": {"path": "layer.png", "channel": "BaseColor"}}],
        }
        events = []

        with mock.patch.object(
            edge_smoothing,
            "smooth_png",
            return_value={"changed_pixels": 0},
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

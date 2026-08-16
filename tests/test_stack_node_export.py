from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sp_plugin.rizum_sp_to_ps import pixel_export
from sp_plugin.rizum_sp_to_ps.stack_node_export import StackNodeExporter


class _FakeBackend:
    def __init__(self, tiles=(1001, 1002)):
        self.tiles = tiles
        self.calls = []

    def export(self, uid, channel_name, template, parameters):
        self.calls.append((uid, channel_name, Path(template), parameters))
        paths = []
        for udim in self.tiles:
            suffix = "" if udim is None else f"_{udim}"
            path = Path(str(template).replace("(_$udim)", suffix))
            path.write_bytes(f"tile-{udim or 'single'}".encode("ascii"))
            paths.append(path)
        return paths


def _settings():
    return {
        "padding": "Transparent",
        "dilation": 12,
        "resolution": [2048, 2048],
        "bit_depth": 16,
        "keep_alpha": True,
    }


def _tile(udim):
    return {
        "u": (udim - 1001) % 10,
        "v": (udim - 1001) // 10,
        "udim": udim,
        "is_udim": True,
    }


class StackNodeExporterTests(unittest.TestCase):
    def test_one_node_render_supplies_each_requested_udim(self):
        backend = _FakeBackend()
        exporter = StackNodeExporter(backend=backend)
        try:
            with tempfile.TemporaryDirectory() as directory:
                first = Path(directory) / "1001" / "layer.png"
                second = Path(directory) / "1002" / "layer.png"

                exporter.export_layer(
                    {"uid": 41, "path": str(first)},
                    _settings(),
                    "BaseColor",
                    _tile(1001),
                )
                exporter.export_layer(
                    {"uid": 41, "path": str(second)},
                    _settings(),
                    "BaseColor",
                    _tile(1002),
                )

                self.assertEqual(first.read_bytes(), b"tile-1001")
                self.assertEqual(second.read_bytes(), b"tile-1002")
                self.assertEqual(len(backend.calls), 1)
        finally:
            exporter.close()

    def test_pixel_adapter_forwards_the_canonical_channel_and_tile(self):
        node_exporter = mock.Mock()
        asset = {"uid": 41, "path": "C:/temp/layer.png"}
        tile = _tile(1002)

        with mock.patch.object(
            pixel_export,
            "png_is_fully_transparent",
            return_value=False,
        ):
            transparent = pixel_export.export_layer_png(
                asset,
                _settings(),
                "BaseColor",
                tile,
                node_exporter,
            )

        self.assertFalse(transparent)
        node_exporter.export_layer.assert_called_once_with(
            asset,
            _settings(),
            "BaseColor",
            tile,
        )

    def test_mask_export_uses_the_node_mask_channel(self):
        backend = _FakeBackend(tiles=(1001,))
        exporter = StackNodeExporter(backend=backend)
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "mask.png"
                exporter.export_mask(
                    {"uid": 72, "path": str(output)},
                    _settings(),
                    _tile(1001),
                )

                self.assertEqual(output.read_bytes(), b"tile-1001")
                self.assertIsNone(backend.calls[0][1])
        finally:
            exporter.close()

    def test_non_udim_node_export_uses_the_unsuffixed_payload(self):
        backend = _FakeBackend(tiles=(None,))
        exporter = StackNodeExporter(backend=backend)
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "layer.png"
                exporter.export_layer(
                    {"uid": 18, "path": str(output)},
                    _settings(),
                    "BaseColor",
                    {"udim": 1001, "is_udim": False},
                )

                self.assertEqual(output.read_bytes(), b"tile-single")
        finally:
            exporter.close()

    def test_native_export_parameters_match_painter_texture_export_schema(self):
        backend = _FakeBackend(tiles=(1001,))
        exporter = StackNodeExporter(backend=backend)
        try:
            with tempfile.TemporaryDirectory() as directory:
                exporter.export_layer(
                    {"uid": 9, "path": str(Path(directory) / "layer.png")},
                    _settings(),
                    "User3",
                    _tile(1001),
                )

            parameters = backend.calls[0][3]
            self.assertEqual(parameters["fileFormat"], "png")
            self.assertEqual(parameters["bitDepth"], "16")
            self.assertEqual(parameters["sizeLog2"], 11)
            self.assertEqual(parameters["paddingAlgorithm"], "transparent")
            self.assertEqual(parameters["dilationDistance"], 12)
            self.assertTrue(parameters["keepAlpha"])
        finally:
            exporter.close()


if __name__ == "__main__":
    unittest.main()

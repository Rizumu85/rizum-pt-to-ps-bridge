import tempfile
import unittest
from pathlib import Path

from PySide6 import QtGui

from sp_plugin.rizum_sp_to_ps import exporter, payload_resample


class ExportSizeTests(unittest.TestCase):
    def settings_for(self, native, **settings):
        request = {"uv_tile": {"resolution": {"width": native[0], "height": native[1]}}, "bit_depth": 8}
        return exporter._export_settings(request, {"dilation": 4, **settings})

    def test_texture_set_size_is_the_default_output_and_render(self):
        result = self.settings_for((4096, 4096))
        self.assertEqual(result["output_resolution"], [4096, 4096])
        self.assertEqual(result["resolution"], [4096, 4096])
        self.assertEqual(result["render_scale"], 1)

    def test_a_chosen_psd_size_renders_larger_and_scales_dilation(self):
        # A 4K project exported as a 2K PSD, rendered at 2x: Painter draws 4K.
        result = self.settings_for((4096, 4096), psd_size=2048, render_scale=2)
        self.assertEqual(result["output_resolution"], [2048, 2048])
        self.assertEqual(result["resolution"], [4096, 4096])
        self.assertEqual(result["dilation"], 8)

    def test_render_scale_steps_down_to_painters_limit(self):
        result = self.settings_for((4096, 4096), render_scale=4)
        self.assertEqual(result["render_scale"], 2)
        self.assertEqual(result["resolution"], [8192, 8192])

    def test_a_bridge_target_uses_its_psds_own_size(self):
        result = self.settings_for((4096, 4096), psd_resolution=[2048, 2048], render_scale=2)
        self.assertEqual(result["output_resolution"], [2048, 2048])
        self.assertEqual(result["resolution"], [4096, 4096])

    def test_exports_read_smoothing_cleanup_and_size_from_settings(self):
        from sp_plugin.rizum_sp_to_ps.ui import BridgePanel

        panel = BridgePanel.__new__(BridgePanel)
        panel.user_settings = {
            "edge_smoothing": 40, "cleanup_layer_pngs": False, "psd_size": 2048, "render_scale": 2,
        }
        settings = panel._base_export_settings({"render_scale": 4})
        self.assertEqual(settings["edge_smoothing"], 40)
        self.assertFalse(settings["cleanup_layer_pngs"])
        self.assertEqual(settings["psd_size"], 2048)
        # The Export dialog's choice wins for this export.
        self.assertEqual(settings["render_scale"], 4)

    def test_scaling_averages_edges_without_bleeding_hidden_colour(self):
        image = QtGui.QImage(8, 8, QtGui.QImage.Format.Format_RGBA8888)
        for y in range(8):
            for x in range(8):
                image.setPixelColor(x, y, QtGui.QColor(255, 255, 255, 255) if x < 3 else QtGui.QColor(255, 0, 255, 0))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "layer.png"
            image.save(str(path))
            payload_resample.scale_png(path, (4, 4))
            output = QtGui.QImage(str(path))
        edge = output.pixelColor(1, 1)
        self.assertEqual((output.width(), output.height()), (4, 4))
        self.assertEqual((edge.red(), edge.green(), edge.blue()), (255, 255, 255))
        self.assertAlmostEqual(edge.alpha(), 127, delta=1)


if __name__ == "__main__":
    unittest.main()

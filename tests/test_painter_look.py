import tempfile
import unittest
from pathlib import Path

from PySide6 import QtGui

from sp_plugin.rizum_sp_to_ps import painter_look

SIZE = 12


def lin(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def enc(x):
    x = min(1.0, max(0.0, x))
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


BLEND = {
    "Normal": lambda b, c: c,
    "Multiply": lambda b, c: b * c,
    "Screen": lambda b, c: 1 - (1 - b) * (1 - c),
}


def over(dst, color, alpha, mode):
    """Premultiplied (rgb, a) compositing with backdrop alpha."""
    rgb, a = dst
    if alpha <= 0:
        return dst
    straight = [v / a if a > 0 else 0.0 for v in rgb]
    out = []
    for i in range(3):
        mix = (1 - a) * color[i] + a * min(1.0, max(0.0, BLEND[mode](straight[i], color[i])))
        out.append((1 - alpha) * rgb[i] + alpha * mix)
    return out, alpha + a * (1 - alpha)


def pattern(x, y, seed):
    return [((x * 37 + y * 11 + seed * 53 + i * 71) % 97) / 96 for i in range(3)]


class PainterLookTests(unittest.TestCase):
    def write_rgb(self, path, seed):
        image = QtGui.QImage(SIZE, SIZE, QtGui.QImage.Format.Format_RGB888)
        for y in range(SIZE):
            for x in range(SIZE):
                image.setPixelColor(x, y, QtGui.QColor.fromRgbF(*pattern(x, y, seed)))
        self.assertTrue(image.save(str(path), "PNG"))
        return str(path)

    def write_mask(self, path, seed):
        image = QtGui.QImage(SIZE, SIZE, QtGui.QImage.Format.Format_Grayscale8)
        for y in range(SIZE):
            for x in range(SIZE):
                image.setPixelColor(x, y, QtGui.QColor.fromRgbF(*[pattern(x, y, seed)[0]] * 3))
        self.assertTrue(image.save(str(path), "PNG"))
        return str(path)

    @staticmethod
    def read(path):
        image = QtGui.QImage(path).convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
        return lambda x, y: image.pixelColor(x, y).getRgbF()

    @staticmethod
    def gray(path):
        image = QtGui.QImage(path)
        return lambda x, y: image.pixelColor(x, y).redF()

    def build(self, directory):
        png = Path(directory)
        layer = lambda name, mode, opacity, seed, mask=None: {
            "name": name, "kind": "FillLayer", "visible": True,
            "blend_mode": {"BaseColor": mode}, "opacity": {"BaseColor": opacity},
            "ps_blend_mode": mode.upper(), "blend_decisions": {"BaseColor": {"ps_blend_mode": mode.upper()}},
            "asset": {"path": self.write_rgb(png / f"{name}.png", seed)},
            **({"mask_asset": {"path": self.write_mask(png / f"{name}_mask.png", mask)}} if mask else {}),
        }
        group = {
            "name": "group", "kind": "GroupLayer", "visible": True,
            "blend_mode": {"BaseColor": "Normal"}, "opacity": {"BaseColor": 0.6},
            "ps_blend_mode": "NORMAL", "blend_decisions": {"BaseColor": {"ps_blend_mode": "NORMAL"}},
            "mask_asset": {"path": self.write_mask(png / "group_mask.png", 7)},
            "children": [layer("scr", "Screen", 0.8, 3), layer("inner", "Multiply", 1.0, 4, mask=5)],
        }
        layers = [group, layer("mul", "Multiply", 0.5, 2, mask=6), layer("base", "Normal", 1.0, 1)]
        return {
            "channel": "BaseColor",
            "color_management": {"encoding": "srgb"},
            "export_settings": {"output_resolution": [SIZE, SIZE]},
            "layers": layers,
        }

    def painter_reference(self, request, start=None):
        """Painter's linear composite of the untouched request, per pixel."""
        sources = {}

        def collect(nodes):
            for node in nodes:
                if "asset" in node:
                    sources[node["name"]] = self.read(node["asset"]["path"])
                if "mask_asset" in node:
                    sources[node["name"] + "_mask"] = self.gray(node["mask_asset"]["path"])
                collect(node.get("children", []))

        collect(request["layers"])

        def pixel(x, y):
            def run(nodes, state):
                for node in reversed(nodes):
                    mode = node["blend_mode"]["BaseColor"]
                    cov = node["opacity"]["BaseColor"]
                    if node["name"] + "_mask" in sources:
                        cov *= sources[node["name"] + "_mask"](x, y)
                    if node.get("children"):
                        inner = run(node["children"], ([0.0] * 3, 0.0))
                        a = inner[1]
                        straight = [v / a if a > 0 else 0.0 for v in inner[0]]
                        state = over(state, straight, a * cov, mode)
                        continue
                    color = [lin(v) for v in sources[node["name"]](x, y)[:3]]
                    state = over(state, color, cov, mode)
                return state

            rgb, a = run(request["layers"], start(x, y) if start else ([0.0] * 3, 0.0))
            return [enc(v / a) for v in rgb], a

        return pixel

    def photoshop_composite(self, request, start=None):
        """Photoshop's sRGB composite of the rewritten request (Pass Through folders)."""
        def pixel(x, y):
            def run(nodes, state):
                for node in reversed(nodes):
                    if node.get("children"):
                        self.assertEqual(node["ps_blend_mode"], "PASSTHROUGH")
                        self.assertEqual(node["opacity"]["BaseColor"], 1.0)
                        self.assertNotIn("mask_asset", node)
                        state = run(node["children"], state)
                        continue
                        self.fail("unreachable")
                    self.assertEqual(node["opacity"]["BaseColor"], 1.0)
                    r, g, b, alpha = self.read(node["asset"]["path"])(x, y)
                    if "mask_asset" in node:
                        alpha *= self.gray(node["mask_asset"]["path"])(x, y)
                    mode = node["ps_blend_mode"].capitalize()
                    state = over(state, [r, g, b], alpha, mode)
                return state

            rgb, a = run(request["layers"], start(x, y) if start else ([0.0] * 3, 0.0))
            return [v / a for v in rgb], a

        return pixel

    def test_rewritten_psd_composites_to_painters_look(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.build(directory)
            painter = self.painter_reference(request)
            expected = {(x, y): painter(x, y) for x in range(SIZE) for y in range(SIZE)}

            summary = painter_look.rewrite_request(request, {"blend_modes": painter_look.MATCH_PAINTER})

            self.assertEqual(summary["rewritten_layers"], 4)
            # Multiply at the root keeps its mode; inside the isolated group
            # Painter blends against transparency, so it becomes Normal there.
            self.assertEqual(request["layers"][1]["ps_blend_mode"], "MULTIPLY")
            self.assertEqual(request["layers"][0]["children"][1]["ps_blend_mode"], "NORMAL")
            photoshop = self.photoshop_composite(request)
            worst = max(
                abs(a - b)
                for key, (color, _alpha) in expected.items()
                for a, b in zip(color, photoshop(*key)[0])
            )
            self.assertLess(worst * 255, 2.5)

    def test_bridge_items_match_painter_over_the_psds_own_backdrop(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.build(directory)
            # A Bridge insert of the group and one layer, over what the PSD
            # already shows there. Exactness holds where the backdrop is
            # opaque; where what lies below a layer is partly transparent,
            # Photoshop's alpha fixes its coverage and colors can clip, so
            # the left columns are only rewritten, not checked.
            backdrop = QtGui.QImage(SIZE, SIZE, QtGui.QImage.Format.Format_RGBA8888)
            for y in range(SIZE):
                for x in range(SIZE):
                    r, g, b = pattern(x, y, 9)
                    backdrop.setPixelColor(x, y, QtGui.QColor.fromRgbF(r, g, b, 1.0 if x > 3 else 0.0))
            backdrop_png = str(Path(directory) / "backdrop.png")
            self.assertTrue(backdrop.save(backdrop_png, "PNG"))
            below = self.read(backdrop_png)

            def painter_start(x, y):
                r, g, b, a = below(x, y)
                return [lin(v) * a for v in (r, g, b)], a

            def photoshop_start(x, y):
                r, g, b, a = below(x, y)
                return [v * a for v in (r, g, b)], a

            inserted = {**request, "layers": request["layers"][:2]}
            painter = self.painter_reference(inserted, painter_start)
            expected = {(x, y): painter(x, y) for x in range(SIZE) for y in range(SIZE)}

            items = [{**request, "layers": [layer]} for layer in inserted["layers"]]
            summary = painter_look.rewrite_insertion(items, {}, backdrop_png)

            self.assertEqual(summary["rewritten_layers"], 3)
            photoshop = self.photoshop_composite(inserted, photoshop_start)
            worst = max(
                abs(a - b)
                for key, (color, _alpha) in expected.items()
                if key[0] > 3
                for a, b in zip(color, photoshop(*key)[0])
            )
            self.assertLess(worst * 255, 2.5)

    def test_keep_blend_modes_leaves_structure_and_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.build(directory)
            group_mask = request["layers"][0]["mask_asset"]["path"]
            painter_look.rewrite_request(request, {"blend_modes": painter_look.KEEP_BLEND_MODES})

            group = request["layers"][0]
            self.assertEqual((group["ps_blend_mode"], group["opacity"]["BaseColor"]), ("NORMAL", 0.6))
            self.assertEqual(group["mask_asset"]["path"], group_mask)
            self.assertEqual(request["layers"][1]["opacity"]["BaseColor"], 0.5)
            self.assertEqual(group["children"][0]["ps_blend_mode"], "SCREEN")

    def test_emission_rules(self):
        emission = painter_look._emission
        self.assertEqual(emission("Multiply", True, True), ("multiply", "MULTIPLY"))
        self.assertEqual(emission("Multiply", True, False), ("solve", "NORMAL"))
        self.assertEqual(emission("Darken", True, True), ("solve", "DARKEN"))
        self.assertEqual(emission("Screen", True, True), ("solve", "NORMAL"))
        self.assertEqual(emission("Screen", False, True), ("none", None))
        self.assertEqual(emission("SoftLight", False, True), ("color", "NORMAL"))
        self.assertEqual(emission("Normal", False, False), ("none", None))

    def test_normal_channel_keeps_todays_export(self):
        summary = painter_look.rewrite_request({"channel": "Normal", "layers": []}, {})
        self.assertEqual(summary["mode"], "skipped")


if __name__ == "__main__":
    unittest.main()

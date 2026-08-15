import unittest

from PySide6 import QtGui

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


if __name__ == "__main__":
    unittest.main()

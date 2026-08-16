import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from sp_plugin.rizum_sp_to_ps import color_management, png_color_metadata
from sp_plugin.rizum_sp_to_ps.exporter import build_request_from_preview


def _chunk(kind, data=b""):
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _png(*extra_chunks):
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return (
        png_color_metadata.PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + b"".join(extra_chunks)
        + _chunk(b"IDAT", b"pixel-payload")
        + _chunk(b"IEND")
    )


def _chunk_records(data):
    records = []
    offset = len(png_color_metadata.PNG_SIGNATURE)
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        records.append((kind, payload))
        offset += 12 + length
    return records


class ColorPolicyTests(unittest.TestCase):
    def test_color_channel_uses_srgb_without_converting_numbers(self):
        policy = color_management.resolve_policy(
            channel_role="color",
            channel_format="sRGB8",
            is_color=True,
        )

        self.assertEqual(policy["encoding"], "srgb")
        self.assertEqual(
            policy["photoshop_profile"], color_management.SRGB_PROFILE
        )
        self.assertTrue(policy["embed_profile"])
        self.assertTrue(policy["preserve_rgb_numbers"])

    def test_normal_and_opacity_channels_are_forced_raw(self):
        for role in ("normal", "opacity"):
            with self.subTest(role=role):
                policy = color_management.resolve_policy(
                    channel_role=role,
                    channel_format="sRGB8",
                    is_color=True,
                )
                self.assertEqual(policy["encoding"], "raw")
                self.assertIsNone(policy["photoshop_profile"])
                self.assertFalse(policy["embed_profile"])

    def test_scalar_data_is_raw_but_srgb_format_wins_inconsistent_metadata(self):
        scalar = color_management.resolve_policy(
            channel_role="data", channel_format="L8", is_color=False
        )
        contradictory = color_management.resolve_policy(
            channel_role="data", channel_format="sRGB8", is_color=False
        )

        self.assertEqual(scalar["encoding"], "raw")
        self.assertEqual(contradictory["encoding"], "srgb")

    def test_user_channel_follows_painter_color_metadata(self):
        color = color_management.resolve_policy(
            channel_role="user", channel_format="sRGB8", is_color=True
        )
        data = color_management.resolve_policy(
            channel_role="user", channel_format="RGB16", is_color=False
        )

        self.assertEqual(color["encoding"], "srgb")
        self.assertEqual(data["encoding"], "raw")

    def test_build_request_carries_the_resolved_policy(self):
        preview = {
            "texture_set": "M_body",
            "stack": "",
            "channel": "BaseColor",
            "channel_role": "color",
            "channel_format": "sRGB8",
            "bit_depth": 8,
            "is_color": True,
            "uv_tile": {
                "is_udim": False,
                "resolution": {"width": 32, "height": 32},
            },
            "layers": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            request = build_request_from_preview(preview, Path(directory) / "bundle")

        self.assertEqual(request["color_management"]["encoding"], "srgb")


class PngColorMetadataTests(unittest.TestCase):
    def test_srgb_normalization_preserves_idat_and_replaces_color_chunks(self):
        source = _png(
            _chunk(b"iCCP", b"old-profile"),
            _chunk(b"gAMA", b"old-gamma"),
            _chunk(b"tEXt", b"keep-me"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "color.png"
            path.write_bytes(source)
            result = png_color_metadata.normalize_png(path, "srgb")
            records = _chunk_records(path.read_bytes())

        self.assertTrue(result["changed"])
        self.assertEqual([record for record in records if record[0] == b"sRGB"], [(b"sRGB", b"\x00")])
        self.assertNotIn(b"iCCP", [kind for kind, _ in records])
        self.assertNotIn(b"gAMA", [kind for kind, _ in records])
        self.assertIn((b"tEXt", b"keep-me"), records)
        self.assertIn((b"IDAT", b"pixel-payload"), records)

    def test_raw_normalization_removes_color_chunks_without_touching_pixels(self):
        source = _png(_chunk(b"sRGB", b"\x00"), _chunk(b"cHRM", b"chromaticity"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.png"
            path.write_bytes(source)
            result = png_color_metadata.normalize_png(path, "raw")
            records = _chunk_records(path.read_bytes())

        self.assertTrue(result["changed"])
        self.assertFalse({b"iCCP", b"sRGB", b"gAMA", b"cHRM"}.intersection(kind for kind, _ in records))
        self.assertIn((b"IDAT", b"pixel-payload"), records)

    def test_already_normalized_png_is_not_rewritten(self):
        source = _png(_chunk(b"sRGB", b"\x00"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "color.png"
            path.write_bytes(source)
            result = png_color_metadata.normalize_png(path, "srgb")
            output = path.read_bytes()

        self.assertFalse(result["changed"])
        self.assertEqual(output, source)


if __name__ == "__main__":
    unittest.main()

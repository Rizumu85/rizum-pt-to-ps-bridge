import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sp_plugin.rizum_sp_to_ps import export_naming
from sp_plugin.rizum_sp_to_ps.exporter import build_request_from_preview


def _request(*, is_udim=False, udim=1001):
    return {
        "project": {"name": "Hero", "mesh_path": "C:/mesh/Hero_Source.fbx"},
        "texture_set": "M_body",
        "texture_set_original": "BodyMat",
        "stack": "",
        "channel": "BaseColor",
        "channel_label": "Base Color",
        "channel_identifier": "basecolor",
        "channel_identifier_candidates": ["basecolor"],
        "is_color": True,
        "bit_depth": 8,
        "udim": udim,
        "uv_tile": {
            "u": 0,
            "v": 0,
            "name": str(udim),
            "udim": udim,
            "is_udim": is_udim,
            "resolution": {"width": 64, "height": 64},
        },
        "layers": [],
    }


class ExportNamingTests(unittest.TestCase):
    def test_loads_the_preset_currently_selected_on_the_project(self):
        class Preset:
            name = "Studio Naming"
            url = "predefined://Studio Naming"

        class PainterExport:
            @staticmethod
            def list_predefined_export_presets():
                return [Preset()]

            @staticmethod
            def list_resource_export_presets():
                return []

        with mock.patch.object(
            export_naming.bridge,
            "project_export_preset",
            return_value="Studio Naming",
        ):
            name, preset = export_naming.load_project_preset(PainterExport)

        self.assertEqual(name, "Studio Naming")
        self.assertIsInstance(preset, Preset)

    def test_prefers_a_single_channel_map_over_a_packed_map(self):
        maps = [
            {
                "fileName": "$textureSet_Packed",
                "channels": [
                    {"srcMapType": "documentMap", "srcMapName": "basecolor"},
                    {"srcMapType": "documentMap", "srcMapName": "roughness"},
                ],
            },
            {
                "fileName": "T_$project_$textureSet_D",
                "channels": [
                    {"srcMapType": "documentMap", "srcMapName": "basecolor"},
                ],
            },
        ]

        pattern = export_naming.select_output_pattern(maps, _request())

        self.assertEqual(pattern, "T_$project_$textureSet_D")

    def test_non_udim_name_does_not_include_internal_1001(self):
        stem = export_naming.render_output_pattern(
            "$project_$textureSet_$udim_BaseColor",
            _request(is_udim=False),
        )

        self.assertEqual(stem, "Hero_M_body_BaseColor")

    def test_painter_optional_udim_group_is_removed_without_a_tile(self):
        stem = export_naming.render_output_pattern(
            "Tex_$project_$textureSet(_$udim)",
            _request(is_udim=False),
        )

        self.assertEqual(stem, "Tex_Hero_M_body")

    def test_painter_optional_udim_group_is_unwrapped_with_a_tile(self):
        stem = export_naming.render_output_pattern(
            "Tex_$project_$textureSet(_$udim)",
            _request(is_udim=True, udim=1002),
        )

        self.assertEqual(stem, "Tex_Hero_M_body_1002")

    def test_udim_is_appended_when_project_pattern_omits_it(self):
        stem = export_naming.render_output_pattern(
            "T_$textureSet_BaseColor",
            _request(is_udim=True, udim=1002),
        )

        self.assertEqual(stem, "T_M_body_BaseColor.1002")

    def test_build_request_uses_resolved_project_preset_name_for_psd(self):
        preview = _request()
        preview["output_naming"] = {
            "source": "project_export_preset",
            "preset": "Studio",
            "pattern": "T_$project_$textureSet_D",
            "stem": "T_Hero_M_body_D",
        }

        with tempfile.TemporaryDirectory() as directory:
            request = build_request_from_preview(preview, Path(directory))

        self.assertEqual(Path(request["psd_file"]).name, "T_Hero_M_body_D.psd")


if __name__ == "__main__":
    unittest.main()

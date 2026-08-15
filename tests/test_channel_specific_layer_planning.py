from __future__ import annotations

import unittest

from sp_plugin.rizum_sp_to_ps.exporter import _layers_for_uv_tile


class ChannelSpecificLayerPlanningTests(unittest.TestCase):
    def test_unrelated_normal_blend_mode_does_not_flatten_base_color_group(self):
        layers = [
            {
                "name": "Finished",
                "kind": "GroupLayer",
                "bake_policy": "bake",
                "sync_direction": "sp_to_ps_only",
                "ps_blend_mode": None,
                "warnings": ["NormalMapDetail has no Photoshop equivalent."],
                "blend_decisions": {
                    "BaseColor": {
                        "bake_policy": "keep_editable",
                        "sync_direction": "both",
                        "ps_blend_mode": "NORMAL",
                        "warnings": [],
                    },
                    "Normal": {
                        "bake_policy": "bake",
                        "sync_direction": "sp_to_ps_only",
                        "ps_blend_mode": None,
                        "warnings": [
                            "NormalMapDetail has no Photoshop equivalent."
                        ],
                    },
                },
                "children": [{"name": "Ball", "kind": "GroupLayer"}],
            }
        ]
        uv_tile = {"u": 0, "v": 0}

        planned = _layers_for_uv_tile(layers, uv_tile, "BaseColor")

        self.assertEqual(planned[0]["bake_policy"], "keep_editable")
        self.assertEqual(planned[0]["sync_direction"], "both")
        self.assertEqual(planned[0]["ps_blend_mode"], "NORMAL")
        self.assertEqual(planned[0]["warnings"], [])


if __name__ == "__main__":
    unittest.main()

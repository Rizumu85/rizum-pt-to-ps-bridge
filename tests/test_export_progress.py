import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from sp_plugin.rizum_sp_to_ps import exporter


class ExportProgressTests(unittest.TestCase):
    def events(self, settings, channels=("BaseColor", "Roughness")):
        """Run write_build_bundles over one request per channel, three work units each."""
        requests = [
            {"texture_set": "M_body", "stack": "", "channel": channel, "channel_label": channel, "udim": 1001, "uv_tile": {"is_udim": False}, "layers": []}
            for channel in channels
        ]
        events = []

        def build_request(request, bundle, _settings):
            return {"layers": [{"name": request["channel"]}], "channel": request["channel"], "bundle": str(bundle)}

        def export_assets(build, progress_callback, **_kwargs):
            for value in range(4):
                progress_callback({"stage": "assets", "value": value, "total": 3, "detail": f"{build['channel']} {value}"})

        closer = SimpleNamespace(close=lambda: None)
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            exporter, "_load_painter_modules", return_value={}
        ), mock.patch.object(exporter, "_iter_stack_records", return_value=[]), mock.patch.object(
            exporter, "_build_export_requests", return_value=deepcopy(requests)
        ), mock.patch.object(exporter, "_build_painter_snapshot", return_value={}), mock.patch.object(
            exporter, "validate_request_preview"
        ), mock.patch.object(exporter, "build_request_from_preview", side_effect=build_request), mock.patch.object(
            exporter, "_plan_asset_work", return_value=([], [], [], 0, 3)
        ), mock.patch.object(exporter, "export_request_assets", side_effect=export_assets), mock.patch.object(
            exporter, "_count_layer_assets", return_value=1
        ), mock.patch.object(exporter.painter_look, "rewrite_request", return_value={}), mock.patch.object(
            exporter.stack_node_export, "StackNodeExporter", return_value=closer
        ), mock.patch.object(exporter.geometry_mask, "GeometryMaskBaker", return_value=closer):
            written = exporter.write_build_bundles(directory, settings, progress_callback=lambda event: events.append(event) or True)
            self.assertEqual(len(written), len(channels))
            self.assertTrue(all(Path(path).is_file() for path in written))
        return events

    def test_each_step_counts_all_its_psds_once_and_rendering_ends_before_matching(self):
        events = self.events({"blend_modes": "match_painter"})

        stages = [event["stage"] for event in events]
        self.assertEqual(stages[0], "prepare")
        self.assertEqual(sorted(set(stages[1:]), key=stages.index), ["render", "match"])
        self.assertLess(max(i for i, stage in enumerate(stages) if stage == "render"), stages.index("match"))

        render = [event for event in events if event["stage"] == "render"]
        self.assertEqual({event["total"] for event in render}, {6})
        values = [event["value"] for event in render]
        self.assertEqual(values, sorted(values))
        self.assertEqual((values[0], values[-1]), (0, 6))
        # Several PSDs: each render event says which one it is on.
        self.assertEqual({event["context"] for event in render}, {"M_body / BaseColor", "M_body / Roughness"})

        match = [event for event in events if event["stage"] == "match"]
        self.assertEqual([(event["value"], event["total"]) for event in match], [(0, 2), (1, 2), (2, 2)])

    def test_keeping_blend_modes_has_no_matching_step_and_one_psd_needs_no_context(self):
        events = self.events({"blend_modes": "keep_blend_modes"}, channels=("BaseColor",))

        self.assertNotIn("match", [event["stage"] for event in events])
        self.assertEqual({event["context"] for event in events if event["stage"] == "render"}, {""})

    def test_cancel_stops_the_export(self):
        with self.assertRaises(exporter.ExportCancelled):
            with mock.patch.object(exporter, "_load_painter_modules", side_effect=AssertionError("ran on")):
                exporter.write_build_bundles("unused", {}, progress_callback=lambda _event: False)


if __name__ == "__main__":
    unittest.main()

import unittest
import tempfile
import os
import json

from focussight.ops_report import derive_cog_sci_metrics, render_ops_report, save_ops_report_json


class OpsReportTests(unittest.TestCase):
    def test_derive_cog_sci_metrics(self):
        summary = {
            "avg_focus": 0.8,
            "distracted_pct": 20.0,
            "longest_distracted_streak_seconds": 1.2,
            "avg_fps": 9.5,
        }
        rows = [
            {"state": "FOCUSED", "elapsed_seconds": 0.0},
            {"state": "DISTRACTED", "elapsed_seconds": 0.5},
            {"state": "FOCUSED", "elapsed_seconds": 1.0},
            {"state": "DISTRACTED", "elapsed_seconds": 1.5},
            {"state": "FOCUSED", "elapsed_seconds": 2.0},
        ]

        metrics = derive_cog_sci_metrics(summary, rows)
        self.assertIn("vigilance_index", metrics)
        self.assertIn("operational_readiness", metrics)
        self.assertGreaterEqual(metrics["operational_readiness"], 0.0)
        self.assertLessEqual(metrics["operational_readiness"], 1.0)
        self.assertEqual(metrics["attention_lapse_events"], 2)

    def test_render_ops_report(self):
        report = {
            "file": "logs/focus_session_test.csv",
            "summary": {
                "avg_focus": 0.75,
                "distracted_pct": 25.0,
                "longest_distracted_streak_seconds": 1.1,
                "avg_fps": 8.0,
            },
            "cog_sci": {
                "vigilance_index": 0.75,
                "stability_index": 0.62,
                "operational_readiness": 0.70,
                "attention_lapse_events": 3,
                "mean_recovery_seconds": 0.9,
                "interpretation": "Moderate readiness; include short periodic resets",
            },
        }

        text = render_ops_report(report)
        self.assertIn("Cognitive Operations Metrics", text)
        self.assertIn("Operational readiness", text)

    def test_save_ops_report_json(self):
        report = {
            "file": "logs/focus_session_test.csv",
            "summary": {"avg_focus": 0.7, "distracted_pct": 30.0, "longest_distracted_streak_seconds": 1.0, "avg_fps": 9.0},
            "cog_sci": {
                "vigilance_index": 0.7,
                "stability_index": 0.6,
                "operational_readiness": 0.66,
                "attention_lapse_events": 2,
                "mean_recovery_seconds": 0.8,
                "interpretation": "Moderate readiness; include short periodic resets",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "report.json")
            save_ops_report_json(report, output_path)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            self.assertEqual(loaded["file"], report["file"])


if __name__ == "__main__":
    unittest.main()

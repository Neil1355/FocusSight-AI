import unittest

from focussight.ops_report import derive_cog_sci_metrics, render_ops_report


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


if __name__ == "__main__":
    unittest.main()

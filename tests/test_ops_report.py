import unittest
import tempfile
import os
import json
import csv

from focussight.ops_report import (
    build_ops_report,
    build_recommendations,
    build_session_scorecard,
    build_tag_comparison,
    derive_cog_sci_metrics,
    render_ops_report,
    save_ops_report_json,
)


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

    def test_build_tag_comparison(self):
        rows = [
            {"task_tag": "coding", "context_tag": "study", "location_tag": "lab"},
            {"task_tag": "coding", "context_tag": "study", "location_tag": "lab"},
        ]
        comparison = build_tag_comparison(rows)
        self.assertEqual(comparison["task_tag"], "coding")
        self.assertEqual(comparison["context_tag"], "study")
        self.assertEqual(comparison["location_tag"], "lab")

    def test_build_recommendations(self):
        summary = {
            "avg_focus": 0.45,
            "avg_fps": 5.0,
            "distracted_pct": 55.0,
            "longest_distracted_streak_seconds": 50.0,
        }
        cog = {
            "operational_readiness": 0.5,
        }
        windows = {
            "best": [{"start_seconds": 10.0, "end_seconds": 20.0, "avg_focus": 0.75}],
            "worst": [],
        }
        trends = {
            "by_day": {
                "2026-04-01": {"avg_focus": 0.8},
                "2026-04-02": {"avg_focus": 0.6},
            }
        }
        recs = build_recommendations(summary, cog, windows, trends)
        self.assertGreaterEqual(len(recs), 1)

    def test_build_session_scorecard(self):
        summary = {
            "avg_focus": 0.8,
            "distracted_pct": 20.0,
        }
        cog = {
            "operational_readiness": 0.82,
            "mean_recovery_seconds": 3.2,
        }
        scorecard = build_session_scorecard(summary, cog)
        self.assertIn("score", scorecard)
        self.assertIn("status", scorecard)
        self.assertIn("checks", scorecard)
        self.assertGreaterEqual(scorecard["score"], 0.0)
        self.assertLessEqual(scorecard["score"], 1.0)

    def test_build_ops_report_contains_new_sections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, "logs"), exist_ok=True)
            log_path = os.path.join(temp_dir, "logs", "focus_session_test.csv")
            with open(log_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "timestamp",
                    "elapsed_seconds",
                    "frame_interval_seconds",
                    "observed_fps",
                    "focus_score",
                    "weighted_focus_score",
                    "state",
                    "signal_status",
                    "face_found",
                    "eye_found",
                    "focused_threshold",
                    "alert_after_seconds",
                    "task_tag",
                    "context_tag",
                    "location_tag",
                ])
                writer.writerow(["2026-04-01T10:00:00", "0.0", "0.2", "5.0", "0.8", "0.7", "FOCUSED", "TRACKING_OK", 1, 1, "0.6", "2.5", "coding", "study", "lab"])
                writer.writerow(["2026-04-01T10:00:01", "1.0", "0.2", "5.0", "0.2", "0.2", "DISTRACTED", "LOW_CONFIDENCE", 1, 0, "0.6", "2.5", "coding", "study", "lab"])

            cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                report = build_ops_report(log_path)
            finally:
                os.chdir(cwd)

            self.assertIn("focus_windows", report)
            self.assertIn("temporal_trends", report)
            self.assertIn("recommendations", report)
            self.assertIn("scorecard", report)


if __name__ == "__main__":
    unittest.main()

import csv
import os
import tempfile
import unittest

from session_summary import (
    longest_distracted_streak,
    summarize_file,
    tune_recommendation,
)


class SessionSummaryTests(unittest.TestCase):
    def test_longest_distracted_streak(self):
        rows = [
            {"state": "FOCUSED"},
            {"state": "DISTRACTED"},
            {"state": "DISTRACTED"},
            {"state": "FOCUSED"},
            {"state": "DISTRACTED"},
        ]
        self.assertEqual(longest_distracted_streak(rows), 2)

    def test_tune_recommendation(self):
        threshold, alert = tune_recommendation(0.9)
        self.assertAlmostEqual(threshold, 0.75)
        self.assertAlmostEqual(alert, 1.8)

    def test_summarize_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "focus_session_test.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "timestamp",
                    "focus_score",
                    "state",
                    "face_found",
                    "eye_found",
                    "focused_threshold",
                    "alert_after_seconds",
                ])
                writer.writerow(["2026-04-05T10:00:00", "0.90", "FOCUSED", 1, 1, "0.60", "2.50"])
                writer.writerow(["2026-04-05T10:00:01", "0.20", "DISTRACTED", 1, 0, "0.60", "2.50"])
                writer.writerow(["2026-04-05T10:00:02", "0.10", "DISTRACTED", 1, 0, "0.60", "2.50"])

            summary = summarize_file(path)
            self.assertEqual(summary["rows"], 3)
            self.assertAlmostEqual(summary["avg_focus"], (0.9 + 0.2 + 0.1) / 3)
            self.assertEqual(summary["longest_distracted_streak_frames"], 2)


if __name__ == "__main__":
    unittest.main()

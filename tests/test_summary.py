import csv
import os
import tempfile
import unittest

from focussight.summary import (
    extract_focus_windows,
    longest_distracted_streak,
    longest_distracted_streak_seconds,
    summarize_by_day,
    summarize_by_tag,
    summarize_by_week,
    summarize_file,
    summarize_rows,
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

    def test_longest_distracted_streak_seconds(self):
        rows = [
            {"state": "FOCUSED", "elapsed_seconds": 0.0},
            {"state": "DISTRACTED", "elapsed_seconds": 0.2},
            {"state": "DISTRACTED", "elapsed_seconds": 0.5},
            {"state": "FOCUSED", "elapsed_seconds": 0.9},
            {"state": "DISTRACTED", "elapsed_seconds": 1.4},
        ]
        self.assertAlmostEqual(longest_distracted_streak_seconds(rows), 0.3)

    def test_tune_recommendation(self):
        threshold, alert = tune_recommendation(0.9)
        self.assertAlmostEqual(threshold, 0.75)
        self.assertAlmostEqual(alert, 1.8)

    def test_summarize_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "focus_session_test.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "timestamp",
                        "elapsed_seconds",
                        "frame_interval_seconds",
                        "observed_fps",
                        "focus_score",
                        "state",
                        "face_found",
                        "eye_found",
                        "focused_threshold",
                        "alert_after_seconds",
                    ]
                )
                writer.writerow(["2026-04-05T10:00:00", "0.0", "0.2", "5.0", "0.90", "FOCUSED", 1, 1, "0.60", "2.50"])
                writer.writerow(["2026-04-05T10:00:01", "0.2", "0.2", "5.0", "0.20", "DISTRACTED", 1, 0, "0.60", "2.50"])
                writer.writerow(["2026-04-05T10:00:02", "0.4", "0.2", "5.0", "0.10", "DISTRACTED", 1, 0, "0.60", "2.50"])

            summary = summarize_file(path)
            self.assertEqual(summary["rows"], 3)
            self.assertAlmostEqual(summary["avg_focus"], (0.9 + 0.2 + 0.1) / 3)
            self.assertEqual(summary["longest_distracted_streak_frames"], 2)
            self.assertAlmostEqual(summary["avg_fps"], 5.0)
            self.assertAlmostEqual(summary["longest_distracted_streak_seconds"], 0.2)

    def test_summarize_by_tag(self):
        rows = [
            {"focus_score": 0.9, "state": "FOCUSED", "observed_fps": 5.0, "elapsed_seconds": 0.0, "task_tag": "reading"},
            {"focus_score": 0.2, "state": "DISTRACTED", "observed_fps": 5.0, "elapsed_seconds": 0.2, "task_tag": "reading"},
            {"focus_score": 0.8, "state": "FOCUSED", "observed_fps": 6.0, "elapsed_seconds": 0.0, "task_tag": "coding"},
        ]
        grouped = summarize_by_tag(rows, "task_tag")
        self.assertIn("reading", grouped)
        self.assertIn("coding", grouped)
        self.assertGreater(grouped["reading"]["rows"], 0)

    def test_summarize_rows_empty(self):
        summary = summarize_rows([])
        self.assertEqual(summary["rows"], 0)
        self.assertEqual(summary["avg_focus"], 0.0)

    def test_summarize_by_day_and_week(self):
        rows = [
            {"timestamp": "2026-04-01T10:00:00", "focus_score": 0.9, "state": "FOCUSED", "observed_fps": 6.0, "elapsed_seconds": 0.0},
            {"timestamp": "2026-04-01T10:00:01", "focus_score": 0.7, "state": "FOCUSED", "observed_fps": 6.0, "elapsed_seconds": 1.0},
            {"timestamp": "2026-04-08T10:00:00", "focus_score": 0.3, "state": "DISTRACTED", "observed_fps": 6.0, "elapsed_seconds": 0.0},
        ]
        by_day = summarize_by_day(rows)
        by_week = summarize_by_week(rows)
        self.assertIn("2026-04-01", by_day)
        self.assertIn("2026-04-08", by_day)
        self.assertGreaterEqual(len(by_week), 2)

    def test_extract_focus_windows(self):
        rows = [
            {"elapsed_seconds": 0.0, "focus_score": 0.8},
            {"elapsed_seconds": 4.0, "focus_score": 0.9},
            {"elapsed_seconds": 8.0, "focus_score": 0.2},
            {"elapsed_seconds": 12.0, "focus_score": 0.1},
        ]
        windows = extract_focus_windows(rows, window_seconds=8.0, top_n=1)
        self.assertEqual(len(windows["best"]), 1)
        self.assertEqual(len(windows["worst"]), 1)


if __name__ == "__main__":
    unittest.main()

import csv
import os
import tempfile
import unittest
from datetime import datetime

from focussight.summary import (
    compute_adaptive_thresholds,
    compute_session_comparison,
    export_session_history_csv,
    extract_focus_windows,
    longest_distracted_streak,
    longest_distracted_streak_seconds,
    summarize_by_day,
    summarize_by_tag,
    summarize_by_week,
    summarize_file,
    summarize_rows,
    summarize_today,
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

    def _write_session_csv(self, path, rows):
        fieldnames = [
            "timestamp", "elapsed_seconds", "frame_interval_seconds",
            "observed_fps", "focus_score", "state",
        ]
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def test_export_session_history_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            session_rows = [
                {"timestamp": "2026-04-01T10:00:00", "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.9", "state": "FOCUSED"},
                {"timestamp": "2026-04-01T10:00:01", "elapsed_seconds": "0.2",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.2", "state": "DISTRACTED"},
            ]
            self._write_session_csv(
                os.path.join(logs_dir, "focus_session_01.csv"), session_rows
            )
            out_path = os.path.join(temp_dir, "history.csv")
            result = export_session_history_csv(log_dir=logs_dir, output_path=out_path)
            self.assertIsNotNone(result)
            self.assertTrue(os.path.exists(out_path))
            with open(out_path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                exported = list(reader)
            self.assertEqual(len(exported), 1)
            self.assertIn("avg_focus", exported[0])

    def test_export_session_history_csv_no_logs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = export_session_history_csv(log_dir=temp_dir)
            self.assertIsNone(result)

    def test_compute_session_comparison_single_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            session_rows = [
                {"timestamp": "2026-04-01T10:00:00", "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.9", "state": "FOCUSED"},
            ]
            csv_path = os.path.join(logs_dir, "focus_session_01.csv")
            self._write_session_csv(csv_path, session_rows)
            summary = summarize_file(csv_path)
            result = compute_session_comparison(summary, log_dir=logs_dir)
            self.assertIsNone(result)

    def test_compute_session_comparison_two_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            rows_a = [
                {"timestamp": "2026-04-01T10:00:00", "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.9", "state": "FOCUSED"},
            ]
            rows_b = [
                {"timestamp": "2026-04-02T10:00:00", "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.4", "state": "DISTRACTED"},
            ]
            path_a = os.path.join(logs_dir, "focus_session_01.csv")
            path_b = os.path.join(logs_dir, "focus_session_02.csv")
            self._write_session_csv(path_a, rows_a)
            self._write_session_csv(path_b, rows_b)
            summary_b = summarize_file(path_b)
            result = compute_session_comparison(summary_b, log_dir=logs_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result["sessions_compared"], 1)
            self.assertAlmostEqual(result["historical_avg_focus"], 0.9)
            self.assertAlmostEqual(result["focus_delta"], 0.4 - 0.9)

    def test_compute_adaptive_thresholds_no_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = compute_adaptive_thresholds(log_dir=temp_dir)
            self.assertIsNone(result)

    def test_compute_adaptive_thresholds_with_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            rows = [
                {"timestamp": "2026-04-01T10:00:00", "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.8", "state": "FOCUSED"},
                {"timestamp": "2026-04-01T10:00:01", "elapsed_seconds": "0.2",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.7", "state": "FOCUSED"},
            ]
            self._write_session_csv(
                os.path.join(logs_dir, "focus_session_01.csv"), rows
            )
            result = compute_adaptive_thresholds(log_dir=logs_dir)
            self.assertIsNotNone(result)
            self.assertIn("suggested_threshold", result)
            self.assertIn("suggested_alert_seconds", result)
            self.assertEqual(result["based_on_sessions"], 1)
            self.assertGreaterEqual(result["suggested_threshold"], 0.45)
            self.assertLessEqual(result["suggested_threshold"], 0.80)

    def test_summarize_today_no_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = summarize_today(log_dir=temp_dir)
            self.assertIsNone(result)

    def test_summarize_today_with_old_session_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            old_rows = [
                {"timestamp": "2020-01-01T10:00:00", "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.8", "state": "FOCUSED"},
            ]
            self._write_session_csv(os.path.join(logs_dir, "focus_session_old.csv"), old_rows)
            result = summarize_today(log_dir=logs_dir)
            self.assertIsNone(result)

    def test_summarize_today_with_todays_session(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            today_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            today_rows = [
                {"timestamp": today_ts, "elapsed_seconds": "0.0",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.85", "state": "FOCUSED"},
                {"timestamp": today_ts, "elapsed_seconds": "0.2",
                 "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                 "focus_score": "0.35", "state": "DISTRACTED"},
            ]
            self._write_session_csv(os.path.join(logs_dir, "focus_session_today.csv"), today_rows)
            result = summarize_today(log_dir=logs_dir)
            self.assertIsNotNone(result)
            self.assertEqual(result["session_count"], 1)
            self.assertAlmostEqual(result["avg_focus"], (0.85 + 0.35) / 2)
            self.assertIn("session_files", result)


if __name__ == "__main__":
    unittest.main()

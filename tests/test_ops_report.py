import unittest
import tempfile
import os
import json
import csv
from datetime import datetime

from focussight.ops_report import (
    build_daily_report,
    build_ops_report,
    build_recommendations,
    build_session_scorecard,
    build_tag_comparison,
    derive_cog_sci_metrics,
    render_daily_report,
    render_ops_report,
    render_ops_report_html,
    save_ops_report_html,
    save_ops_report_json,
)


def _write_session_csv(path, rows, today=False):
    """Write a minimal session CSV. If today=True, use today's timestamp."""
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S") if today else "2026-04-01T10:00:00"
    fieldnames = [
        "timestamp", "elapsed_seconds", "frame_interval_seconds",
        "observed_fps", "focus_score", "state",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row_copy = dict(row)
            if today:
                row_copy["timestamp"] = ts
            writer.writerow(row_copy)

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
            self.assertIn("session_comparison", report)

    def test_render_ops_report_includes_session_comparison(self):
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
            "session_comparison": {
                "session_avg_focus": 0.75,
                "historical_avg_focus": 0.65,
                "focus_delta": 0.10,
                "session_distracted_pct": 25.0,
                "historical_distracted_pct": 35.0,
                "distracted_delta": -10.0,
                "session_streak_seconds": 1.1,
                "historical_streak_seconds": 2.5,
                "sessions_compared": 4,
            },
        }
        text = render_ops_report(report)
        self.assertIn("Session vs. Historical Baseline", text)
        self.assertIn("Sessions compared: 4", text)

    def test_render_ops_report_html_structure(self):
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
            "recommendations": ["Take a break after 60 minutes."],
            "scorecard": {
                "score": 0.85,
                "status": "on-track",
                "checks": {
                    "focus_goal": {"target": 0.75, "actual": 0.75, "pass": True, "weight": 30},
                },
            },
        }
        html = render_ops_report_html(report)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("FocusSight Cognitive Operations Report", html)
        self.assertIn("Cognitive Operations Metrics", html)
        self.assertIn("ON-TRACK", html)
        self.assertIn("Take a break after 60 minutes.", html)

    def test_render_ops_report_html_with_comparison(self):
        report = {
            "file": "logs/focus_session_test.csv",
            "summary": {
                "avg_focus": 0.6,
                "distracted_pct": 40.0,
                "longest_distracted_streak_seconds": 3.0,
                "avg_fps": 7.0,
            },
            "cog_sci": {
                "vigilance_index": 0.6,
                "stability_index": 0.55,
                "operational_readiness": 0.58,
                "attention_lapse_events": 5,
                "mean_recovery_seconds": 2.0,
                "interpretation": "Low readiness; schedule recovery and reduce task load",
            },
            "session_comparison": {
                "session_avg_focus": 0.6,
                "historical_avg_focus": 0.75,
                "focus_delta": -0.15,
                "session_distracted_pct": 40.0,
                "historical_distracted_pct": 25.0,
                "distracted_delta": 15.0,
                "session_streak_seconds": 3.0,
                "historical_streak_seconds": 1.5,
                "sessions_compared": 3,
            },
        }
        html = render_ops_report_html(report)
        self.assertIn("Session vs. Historical Baseline", html)
        self.assertIn("3 prior session(s)", html)

    def test_save_ops_report_html(self):
        report = {
            "file": "logs/focus_session_test.csv",
            "summary": {
                "avg_focus": 0.7,
                "distracted_pct": 30.0,
                "longest_distracted_streak_seconds": 1.0,
                "avg_fps": 9.0,
            },
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
            out_path = os.path.join(temp_dir, "report.html")
            save_ops_report_html(report, out_path)
            self.assertTrue(os.path.exists(out_path))
            with open(out_path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("<!DOCTYPE html>", content)

    def test_build_daily_report_no_sessions_today(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_daily_report(log_dir=temp_dir)
            self.assertIsNone(result)

    def test_build_daily_report_with_todays_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            csv_path = os.path.join(logs_dir, "focus_session_today.csv")
            rows = [
                {"elapsed_seconds": "0.0", "frame_interval_seconds": "0.2",
                 "observed_fps": "5.0", "focus_score": "0.8", "state": "FOCUSED"},
                {"elapsed_seconds": "0.2", "frame_interval_seconds": "0.2",
                 "observed_fps": "5.0", "focus_score": "0.3", "state": "DISTRACTED"},
            ]
            _write_session_csv(csv_path, rows, today=True)
            cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                report = build_daily_report(log_dir=logs_dir)
            finally:
                os.chdir(cwd)
            self.assertIsNotNone(report)
            self.assertEqual(report["session_count"], 1)
            self.assertIn("cog_sci", report)
            self.assertIn("recommendations", report)
            self.assertIn("scorecard", report)

    def test_render_daily_report_output(self):
        report = {
            "date": "2026-04-12",
            "session_count": 2,
            "session_files": ["logs/a.csv", "logs/b.csv"],
            "stats": {
                "rows": 40,
                "avg_focus": 0.72,
                "avg_fps": 7.5,
                "distracted_pct": 28.0,
                "longest_distracted_streak_frames": 5,
                "longest_distracted_streak_seconds": 2.5,
            },
            "cog_sci": {
                "vigilance_index": 0.72,
                "stability_index": 0.65,
                "operational_readiness": 0.69,
                "attention_lapse_events": 4,
                "mean_recovery_seconds": 1.2,
                "interpretation": "Moderate readiness; include short periodic resets",
            },
            "focus_windows": {"best": [], "worst": []},
            "recommendations": ["Maintain current routine."],
            "scorecard": {"score": 0.80, "status": "on-track", "checks": {}},
        }
        text = render_daily_report(report)
        self.assertIn("FocusSight Daily Summary", text)
        self.assertIn("2026-04-12", text)
        self.assertIn("Sessions recorded today: 2", text)
        self.assertIn("Recommendations", text)
        self.assertIn("Daily Scorecard", text)

    # --- Phase 11: Session Notes in ops report ---

    def test_render_ops_report_includes_note(self):
        report = {
            "file": "logs/focus_session_test.csv",
            "summary": {
                "avg_focus": 0.75,
                "distracted_pct": 25.0,
                "longest_distracted_streak_seconds": 1.2,
                "avg_fps": 8.0,
            },
            "cog_sci": {
                "vigilance_index": 0.75,
                "stability_index": 0.62,
                "operational_readiness": 0.70,
                "attention_lapse_events": 3,
                "mean_recovery_seconds": 0.9,
                "interpretation": "Moderate readiness",
            },
            "comparison": {},
            "focus_windows": {"best": [], "worst": []},
            "temporal_trends": {"by_day": {}, "by_week": {}},
            "recommendations": [],
            "scorecard": {"score": 0.7, "status": "on-track", "checks": {}},
            "session_comparison": None,
            "note": "Productive coding session",
        }
        text = render_ops_report(report)
        self.assertIn("Productive coding session", text)

    def test_render_ops_report_html_includes_note(self):
        report = {
            "file": "logs/focus_session_test.csv",
            "summary": {
                "avg_focus": 0.75,
                "distracted_pct": 25.0,
                "longest_distracted_streak_seconds": 1.0,
                "avg_fps": 8.0,
            },
            "cog_sci": {
                "vigilance_index": 0.75,
                "stability_index": 0.62,
                "operational_readiness": 0.70,
                "attention_lapse_events": 2,
                "mean_recovery_seconds": 0.8,
                "interpretation": "Moderate readiness",
            },
            "recommendations": ["Rest well."],
            "scorecard": {"score": 0.8, "status": "on-track", "checks": {}},
            "note": "Exam prep day",
        }
        html = render_ops_report_html(report)
        self.assertIn("Exam prep day", html)
        self.assertIn("Session Note", html)

    def test_build_ops_report_note_key_present(self):
        """build_ops_report should always include a 'note' key."""
        import csv as csv_mod
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = os.path.join(temp_dir, "focus_session_01.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv_mod.DictWriter(fh, fieldnames=[
                    "timestamp", "elapsed_seconds", "frame_interval_seconds",
                    "observed_fps", "focus_score", "state",
                ], extrasaction="ignore")
                writer.writeheader()
                writer.writerow({
                    "timestamp": "2026-04-01T10:00:00", "elapsed_seconds": "0.0",
                    "frame_interval_seconds": "0.2", "observed_fps": "5.0",
                    "focus_score": "0.8", "state": "FOCUSED",
                })
            report = build_ops_report(csv_path)
            self.assertIn("note", report)
            self.assertEqual(report["note"], "")


if __name__ == "__main__":
    unittest.main()

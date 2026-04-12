import os
import tempfile
import unittest
from collections import deque
import csv

from focussight.tracker import (
    auto_update_profile_from_history,
    compute_focus_score,
    compute_observed_fps,
    compute_signal_quality,
    derive_calibrated_config,
    evaluate_focus_state,
    format_live_dashboard,
    load_profile,
    normalize_config,
    resolve_runtime_config,
    save_profile,
    generate_ops_artifacts,
    map_flipped_box_to_original,
    parse_session_tags,
    report_output_paths,
    resolve_reminder_policy,
    should_emit_reminder,
    should_suggest_break,
    smooth_box,
    update_stability_seconds,
    tune_parameters_from_scores,
)


class FocusLogicTests(unittest.TestCase):
    def test_smooth_box_returns_none_for_empty(self):
        self.assertIsNone(smooth_box([]))

    def test_smooth_box_averages_coordinates(self):
        boxes = [(10, 20, 30, 40), (14, 22, 34, 38)]
        self.assertEqual(smooth_box(boxes), (12, 21, 32, 39))

    def test_compute_focus_score_empty_history(self):
        self.assertEqual(compute_focus_score(deque()), 0.0)

    def test_compute_focus_score_average(self):
        history = deque([1, 0, 1, 1], maxlen=20)
        self.assertAlmostEqual(compute_focus_score(history), 0.75)

    def test_evaluate_focus_state_focused(self):
        state, color = evaluate_focus_state(True, 0.8, 0.6)
        self.assertEqual(state, "FOCUSED")
        self.assertEqual(color, (0, 220, 0))

    def test_evaluate_focus_state_distracted_without_face(self):
        state, color = evaluate_focus_state(False, 1.0, 0.6)
        self.assertEqual(state, "DISTRACTED")
        self.assertEqual(color, (0, 140, 255))

    def test_tuning_requires_minimum_samples(self):
        threshold, alert_seconds, tuned = tune_parameters_from_scores([0.8] * 10, 0.6, 2.5)
        self.assertFalse(tuned)
        self.assertEqual(threshold, 0.6)
        self.assertEqual(alert_seconds, 2.5)

    def test_tuning_updates_values_with_enough_data(self):
        threshold, alert_seconds, tuned = tune_parameters_from_scores([0.9] * 80, 0.6, 2.5)
        self.assertTrue(tuned)
        self.assertAlmostEqual(threshold, 0.75)
        self.assertAlmostEqual(alert_seconds, 1.8)

    def test_normalize_config_clamps_values(self):
        normalized = normalize_config(
            {
                "camera_index": -2,
                "focused_threshold": 2.0,
                "alert_after_seconds": 0.1,
            }
        )
        self.assertEqual(normalized["camera_index"], 0)
        self.assertAlmostEqual(normalized["focused_threshold"], 0.95)
        self.assertAlmostEqual(normalized["alert_after_seconds"], 0.5)
        self.assertEqual(normalized["reminder_policy"], "balanced")

    def test_resolve_reminder_policy(self):
        key, settings = resolve_reminder_policy("strict")
        self.assertEqual(key, "strict")
        self.assertIn("break_after_seconds", settings)

        key_fallback, _ = resolve_reminder_policy("unknown")
        self.assertEqual(key_fallback, "balanced")

    def test_should_emit_reminder(self):
        self.assertFalse(should_emit_reminder(10.0, None, None, 2.5, 15.0))
        self.assertFalse(should_emit_reminder(10.0, 9.0, None, 2.5, 15.0))
        self.assertTrue(should_emit_reminder(10.0, 5.0, None, 2.5, 15.0))
        self.assertFalse(should_emit_reminder(30.0, 5.0, 20.0, 2.5, 15.0))
        self.assertTrue(should_emit_reminder(36.0, 5.0, 20.0, 2.5, 15.0))

    def test_should_suggest_break(self):
        self.assertFalse(should_suggest_break(20.0, None, 60.0))
        self.assertFalse(should_suggest_break(20.0, 0.0, 60.0))
        self.assertTrue(should_suggest_break(61.0, 0.0, 60.0))

    def test_resolve_runtime_config_cli_overrides_profile(self):
        resolved = resolve_runtime_config(
            {
                "camera_index": 1,
                "focused_threshold": None,
                "alert_after_seconds": 3.0,
            },
            {
                "camera_index": 0,
                "focused_threshold": 0.7,
                "alert_after_seconds": 2.0,
            },
        )
        self.assertEqual(resolved["camera_index"], 1)
        self.assertAlmostEqual(resolved["focused_threshold"], 0.7)
        self.assertAlmostEqual(resolved["alert_after_seconds"], 3.0)

    def test_profile_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = os.path.join(temp_dir, "profile.json")
            save_profile(
                profile_path,
                {
                    "camera_index": 2,
                    "focused_threshold": 0.66,
                    "alert_after_seconds": 2.2,
                },
            )

            loaded = load_profile(profile_path)
            self.assertEqual(loaded["camera_index"], 2)
            self.assertAlmostEqual(loaded["focused_threshold"], 0.66)
            self.assertAlmostEqual(loaded["alert_after_seconds"], 2.2)

    def test_signal_quality_penalizes_noisy_input(self):
        weighted, status = compute_signal_quality(
            raw_focus_score=0.9,
            eye_persistence=0.35,
            missing_face_seconds=0.2,
            rapid_flip_count=6,
        )
        self.assertLess(weighted, 0.9)
        self.assertIn(status, {"LOW_CONFIDENCE", "NOISY_SIGNAL"})

    def test_signal_quality_detects_away_from_camera(self):
        weighted, status = compute_signal_quality(
            raw_focus_score=0.9,
            eye_persistence=1.0,
            missing_face_seconds=2.5,
            rapid_flip_count=0,
        )
        self.assertEqual(status, "AWAY_FROM_CAMERA")
        self.assertLess(weighted, 0.9)

    def test_signal_quality_detects_low_light(self):
        weighted, status = compute_signal_quality(
            raw_focus_score=0.9,
            eye_persistence=1.0,
            missing_face_seconds=0.0,
            rapid_flip_count=0,
            brightness_mean=35.0,
            face_found=True,
            eye_found=True,
        )
        self.assertEqual(status, "LOW_LIGHT")
        self.assertLess(weighted, 0.9)

    def test_signal_quality_detects_occlusion(self):
        weighted, status = compute_signal_quality(
            raw_focus_score=0.9,
            eye_persistence=0.3,
            missing_face_seconds=0.2,
            rapid_flip_count=0,
            brightness_mean=120.0,
            face_found=True,
            eye_found=False,
        )
        self.assertEqual(status, "OCCLUDED")
        self.assertLess(weighted, 0.9)

    def test_compute_observed_fps(self):
        self.assertAlmostEqual(compute_observed_fps(0.2), 5.0)
        self.assertEqual(compute_observed_fps(0.0), 0.0)

    def test_update_stability_seconds(self):
        stable = update_stability_seconds(0.1, True, 0.2)
        decayed = update_stability_seconds(0.5, False, 0.2)
        self.assertGreater(stable, 0.1)
        self.assertLess(decayed, 0.5)

    def test_calibrated_config_requires_minimum_frames(self):
        threshold, alert_seconds, calibrated = derive_calibrated_config(
            [1.0] * 10,
            [1.0] * 10,
            1.0,
            0.6,
            2.5,
        )
        self.assertFalse(calibrated)
        self.assertEqual(threshold, 0.6)
        self.assertEqual(alert_seconds, 2.5)

    def test_calibrated_config_uses_sample_quality(self):
        threshold, alert_seconds, calibrated = derive_calibrated_config(
            [1.0] * 40,
            [0.8] * 40,
            0.95,
            0.6,
            2.5,
        )
        self.assertTrue(calibrated)
        self.assertGreaterEqual(threshold, 0.45)
        self.assertLessEqual(threshold, 0.90)
        self.assertGreaterEqual(alert_seconds, 1.5)
        self.assertLessEqual(alert_seconds, 5.0)

    def test_report_output_paths(self):
        txt_path, json_path = report_output_paths("logs/focus_session_1.csv", "reports")
        self.assertTrue(txt_path.endswith("focus_session_1_ops_report.txt"))
        self.assertTrue(json_path.endswith("focus_session_1_ops_report.json"))

    def test_parse_session_tags(self):
        tags = parse_session_tags("Deep Work", "Exam Prep", "Campus Lab")
        self.assertEqual(tags["task_tag"], "deep_work")
        self.assertEqual(tags["context_tag"], "exam_prep")
        self.assertEqual(tags["location_tag"], "campus_lab")

    def test_map_flipped_box_to_original(self):
        mapped = map_flipped_box_to_original((20, 10, 30, 40), frame_width=200)
        self.assertEqual(mapped, (150, 10, 30, 40))

    def test_generate_ops_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            reports_dir = os.path.join(temp_dir, "reports")
            os.makedirs(logs_dir, exist_ok=True)
            log_path = os.path.join(logs_dir, "focus_session_test.csv")

            with open(log_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
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
                    ]
                )
                writer.writerow(["2026-04-05T10:00:00", "0.0", "0.2", "5.0", "0.8", "0.7", "FOCUSED", "TRACKING_OK", 1, 1, "0.60", "2.50"])
                writer.writerow(["2026-04-05T10:00:01", "0.2", "0.2", "5.0", "0.2", "0.2", "DISTRACTED", "LOW_CONFIDENCE", 1, 0, "0.60", "2.50"])

            artifacts = generate_ops_artifacts(log_path, report_dir=reports_dir, quiet=True)
            if artifacts is None:
                self.fail("Expected generated artifacts but got None")
            self.assertTrue(os.path.exists(artifacts["txt_path"]))
            self.assertTrue(os.path.exists(artifacts["json_path"]))

    def test_auto_update_profile_from_history_no_logs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = os.path.join(temp_dir, "profile.json")
            updated, result = auto_update_profile_from_history(profile_path, log_dir=temp_dir)
            self.assertFalse(updated)
            self.assertIsInstance(result, str)

    def test_auto_update_profile_from_history_with_logs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_dir = os.path.join(temp_dir, "logs")
            os.makedirs(logs_dir)
            log_path = os.path.join(logs_dir, "focus_session_01.csv")
            with open(log_path, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow([
                    "timestamp", "elapsed_seconds", "frame_interval_seconds",
                    "observed_fps", "focus_score", "state",
                ])
                writer.writerow(["2026-04-01T10:00:00", "0.0", "0.2", "5.0", "0.85", "FOCUSED"])
                writer.writerow(["2026-04-01T10:00:01", "0.2", "0.2", "5.0", "0.75", "FOCUSED"])

            profile_path = os.path.join(temp_dir, "profile.json")
            updated, result = auto_update_profile_from_history(profile_path, log_dir=logs_dir)
            self.assertTrue(updated)
            self.assertIn("suggested_threshold", result)
            self.assertTrue(os.path.exists(profile_path))
            loaded = load_profile(profile_path)
            self.assertAlmostEqual(loaded["focused_threshold"], result["suggested_threshold"])

    def test_format_live_dashboard_focused(self):
        line = format_live_dashboard(
            state="FOCUSED",
            focus_pct=82.0,
            distracted_pct=18.0,
            elapsed_seconds=125.0,
            streak_seconds=0.0,
            signal_status="TRACKING_OK",
            logging_enabled=True,
            reminder_policy_key="balanced",
        )
        self.assertIn("FOCUSED", line)
        self.assertIn("82%", line)
        self.assertIn("18%", line)
        self.assertIn("02:05", line)
        self.assertIn("TRACKING_OK", line)
        self.assertIn("LOG:ON", line)
        self.assertIn("balanced", line)

    def test_format_live_dashboard_distracted(self):
        line = format_live_dashboard(
            state="DISTRACTED",
            focus_pct=40.0,
            distracted_pct=60.0,
            elapsed_seconds=60.0,
            streak_seconds=12.0,
            signal_status="LOW_CONFIDENCE",
            logging_enabled=False,
            reminder_policy_key="strict",
        )
        self.assertIn("DISTRACTED", line)
        self.assertIn("streak=12s", line)
        self.assertIn("LOG:OFF", line)
        self.assertIn("strict", line)


if __name__ == "__main__":
    unittest.main()

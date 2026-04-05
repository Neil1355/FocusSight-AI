import os
import tempfile
import unittest
from collections import deque

from focussight.tracker import (
    compute_focus_score,
    compute_signal_quality,
    derive_calibrated_config,
    evaluate_focus_state,
    load_profile,
    normalize_config,
    resolve_runtime_config,
    save_profile,
    smooth_box,
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


if __name__ == "__main__":
    unittest.main()

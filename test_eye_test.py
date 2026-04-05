import unittest
from collections import deque

from eye_test import (
    compute_focus_score,
    evaluate_focus_state,
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


if __name__ == "__main__":
    unittest.main()

# Changelog

## 2026-04-05
- Added smoothed focus scoring to the webcam loop in `eye_test.py` using a rolling history window.
- Added smoothed face box tracking to reduce rectangle jitter.
- Added state overlay (`FOCUSED`/`DISTRACTED`) and delayed on-screen alert after sustained distraction.
- Refactored `eye_test.py` into testable functions and added a main guard so importing the module does not open the webcam.
- Added `test_eye_test.py` with unit tests for smoothing, focus score calculation, and state classification logic.
- Added CSV session logging (`logs/focus_session_*.csv`) with per-frame timestamp, score, state, and active thresholds.
- Added runtime keyboard controls: `L` to start/stop logging, `T` to tune threshold and alert timing from collected real-session scores, `Q` to quit.
- Added data-driven tuning logic and tests that verify minimum sample handling and tuned output values.
- Installed `opencv-python` into workspace `.venv` and pinned VS Code interpreter in `.vscode/settings.json` to resolve `cv2` import diagnostics.
- Added `session_summary.py` to analyze session CSV files and report average focus, distracted percentage, longest distracted streak, and tuning recommendations.
- Added `test_session_summary.py` with unit tests for streak calculation, tuning recommendation math, and file-level summary output.
- Added `README.md` with setup, run, controls, logging, summary, and test instructions.
- Added `requirements.txt` with pinned project dependencies.
- Added `setup.ps1` for one-command Windows environment setup and dependency installation.
- Added `docs/ROADMAP.md` with phased innovation and delivery plan.
- Added Phase 1 configuration foundation in `eye_test.py`: CLI options (`--camera-index`, `--threshold`, `--alert-seconds`, `--profile`, `--save-profile`, `--autolog`) and JSON profile load/save support.
- Added tests for config normalization, CLI/profile precedence resolution, and profile persistence round-trip.
- Reorganized project layout into package structure: `focussight/tracker.py`, `focussight/summary.py`, and `tests/`.
- Kept backward compatibility by converting root scripts `eye_test.py` and `session_summary.py` into wrappers.
- Started Phase 2 signal quality model in tracker with weighted focus scoring, rapid-flip penalty, face-missing penalty, and status labels (`TRACKING_OK`, `LOW_CONFIDENCE`, `FACE_UNSTABLE`, `AWAY_FROM_CAMERA`, `NOISY_SIGNAL`).
- Expanded tests in `tests/test_tracker.py` and `tests/test_summary.py`, including new signal-quality behavior coverage.

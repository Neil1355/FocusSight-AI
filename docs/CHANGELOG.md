# Changelog

## 2026-04-12

- Added Phase 7 live terminal dashboard in `focussight/tracker.py`: `format_live_dashboard()` builds a compact one-line stat summary (state, avg focus, distracted %, current streak, elapsed time, signal status, policy, log status).
- Extended `run_focus_tracker()` with `dashboard` and `dashboard_interval` parameters; when `--dashboard` is passed the dashboard line is printed to stdout every `dashboard_interval` seconds (default 5s).
- Added `--dashboard` and `--dashboard-interval` CLI flags to `eye_test.py` / tracker `main()`.
- Added Phase 8 daily summary in `focussight/summary.py`: `summarize_today(log_dir)` aggregates rows from all sessions recorded on the current local date.
- Added `build_daily_report(log_dir)` in `focussight/ops_report.py` to produce a full cognitive-operations report for the current day (aggregate stats, cognitive metrics, focus windows, recommendations, scorecard).
- Added `render_daily_report(report)` in `focussight/ops_report.py` for readable text output.
- Added `--daily-summary` CLI flag in `ops_report.py`; prints today's aggregate report without needing a specific session file.
- Expanded `tests/test_summary.py` with tests for `summarize_today` (no sessions, old sessions only, and today's sessions).
- Expanded `tests/test_ops_report.py` with tests for `build_daily_report` and `render_daily_report`.
- Expanded `tests/test_tracker.py` with tests for `format_live_dashboard` (focused and distracted states).
- Updated `docs/ROADMAP.md`: added Phase 7 and Phase 8 entries as completed.

## 2026-04-08

- Added Phase 5 multi-session history export in `focussight/summary.py`: `export_session_history_csv()` writes one summary row per session to a single CSV file for external analysis.
- Added Phase 5 session comparison in `focussight/summary.py`: `compute_session_comparison()` returns per-metric deltas between the current session and the historical average of all other sessions.
- Extended `build_ops_report()` in `focussight/ops_report.py` to include a `session_comparison` key in the report payload.
- Extended `render_ops_report()` to display a "Session vs. Historical Baseline" section when historical data is available.
- Added `render_ops_report_html()` and `save_ops_report_html()` in `focussight/ops_report.py` to produce a self-contained HTML report with styled tables, colour-coded scorecard badge, and an optional session-comparison section.
- Added `--save-html` CLI flag to `ops_report.py` to write the HTML report to a specified path.
- Added `--export-history` CLI flag to `ops_report.py` to export all session summaries to a single CSV without needing to generate a full report.
- Added Phase 6 adaptive threshold learning in `focussight/summary.py`: `compute_adaptive_thresholds()` derives threshold and alert-timing suggestions from the most recent N sessions.
- Added `auto_update_profile_from_history()` in `focussight/tracker.py` to update a saved profile's threshold and alert settings from recent session history automatically.
- Added `--auto-update-profile` CLI flag to `focussight/tracker.py`; when paired with `--save-profile`, the profile is updated from recent history before the session starts.
- Expanded `tests/test_summary.py` with tests for `export_session_history_csv`, `compute_session_comparison`, and `compute_adaptive_thresholds`.
- Expanded `tests/test_ops_report.py` with tests for `render_ops_report_html`, `save_ops_report_html`, session comparison rendering, and the updated `build_ops_report` payload.
- Expanded `tests/test_tracker.py` with tests for `auto_update_profile_from_history` with and without available session logs.
- Updated `docs/ROADMAP.md`: marked Phase 3 and Phase 4 as completed; added Phase 5 and Phase 6 entries.

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
- Added calibration mode to personalize threshold and alert timing before tracking starts, with `--calibrate-seconds` support and test coverage for calibration math.
- Added low-light and occlusion fallback handling in `compute_signal_quality`, with new status labels `LOW_LIGHT` and `OCCLUDED` plus tests.
- Added frame-rate aware tracking: time-based eye stability, FPS overlay, and elapsed-time/frame-interval logging.
- Extended session summaries to report average FPS and distracted streak duration in seconds when available.
- Added cognitive operations reporting (`focussight/ops_report.py` and `ops_report.py`) with vigilance index, stability index, operational readiness, lapse counts, and recovery-time interpretation.
- Added tracker-side auto-report generation on log stop/exit (`--auto-report`, `--report-dir`) producing text and JSON artifacts.
- Added quiet runtime mode (`--quiet`) to reduce terminal spam during operations use.
- Added JSON export support to ops report CLI (`--save-json`).
- Added session tags in tracker logging (`--task-tag`, `--context-tag`, `--location-tag`) for operational context grouping.
- Added grouped analytics helpers in summary module and tag-baseline comparison section in ops report output.
- Improved face robustness for real-world usage (hats and head tilt) by adding profile-face cascade fallback, flipped-profile mapping, histogram-equalized preprocessing, and wider eye-search fallback.
- Expanded tests in `tests/test_tracker.py` and `tests/test_summary.py`, including new signal-quality behavior coverage.
- Added `tests/test_ops_report.py` for cognitive operations report metrics/rendering.
- Added temporal analytics helpers in `focussight/summary.py` for per-day and per-week trend summaries.
- Added focus-window extraction in `focussight/summary.py` to identify best and worst timeline windows by average focus.
- Extended `focussight/ops_report.py` with recommendation generation based on readiness, distraction patterns, trends, and window quality.
- Extended operations report output to include focus windows, temporal trend coverage, and recommendation bullets.
- Added regression tests for temporal summaries, focus windows, recommendation generation, and expanded ops report payload sections.
- Added coaching reminder policies (`gentle`, `balanced`, `strict`) to tracker runtime with `--reminder-policy` CLI support.
- Added sustained-distraction break suggestions in live tracker prompts and ops recommendations.
- Added session goal scorecard generation in `focussight/ops_report.py` with focus/readiness/distraction/recovery checks.
- Expanded tests for reminder timing helpers, policy resolution, and scorecard output.

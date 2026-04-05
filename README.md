# FocusSight AI

FocusSight AI is a webcam-based focus tracker that detects face and eyes in real time, computes a rolling focus score, and shows live focus state on screen.

## Features

- Real-time face and eye detection using OpenCV Haar cascades
- Rolling focus score with smoothing to reduce jitter
- Focus state classification (FOCUSED or DISTRACTED)
- Delayed alert after sustained distraction
- Runtime CLI options for camera/threshold/alert settings
- JSON profile load/save for reusable personal settings
- Optional calibration mode to personalize thresholds before tracking starts
- Runtime logging toggle to save session data to CSV
- Auto-generate operational reports when logging ends
- Session tagging for real-world context comparisons
- Runtime tuning from real session data
- Phase 2 weighted signal quality scoring and status labels
- Low-light and occlusion fallback labels for poor camera conditions
- Frame-rate aware stability, FPS overlay, and elapsed-time logging
- Improved robustness for hats/head tilt using profile-face fallback and contrast-normalized detection
- Post-session analytics script for recommendations
- Cognitive operations report with vigilance, stability, and readiness indices
- Unit tests for core logic

## Project Structure

- focussight/tracker.py: Core tracker logic
- focussight/summary.py: Session analytics logic
- focussight/ops_report.py: Cognitive operations report logic
- eye_test.py: Backward-compatible tracker launcher wrapper
- session_summary.py: Backward-compatible summary launcher wrapper
- ops_report.py: Backward-compatible operations report launcher wrapper
- tests/test_tracker.py: Tracker and config unit tests
- tests/test_summary.py: Summary and recommendation unit tests
- requirements.txt: Python dependencies
- setup.ps1: One-command Windows environment bootstrap
- docs/ROADMAP.md: Innovation roadmap and phase plan
- docs/CHANGELOG.md: Change history

## Requirements

- Windows, macOS, or Linux
- Python 3.13+
- Webcam

## Setup

Windows one-command setup:

powershell -ExecutionPolicy Bypass -File .\setup.ps1

Manual setup:

1. Create and activate a virtual environment.
2. Install dependencies from requirements.txt.

PowerShell example:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

## Run Focus Tracker

python -m focussight.tracker

Backward-compatible command:

python eye_test.py

With custom runtime settings:

python eye_test.py --camera-index 0 --threshold 0.62 --alert-seconds 2.8

Load/save reusable profile settings:

python eye_test.py --profile profile.json --save-profile profile.json

Start with logging enabled:

python eye_test.py --autolog

Auto-generate report artifacts when logs end:

python -m focussight.tracker --autolog --auto-report --report-dir reports

Tag a session for grouped analytics:

python -m focussight.tracker --autolog --auto-report --task-tag coding --context-tag study --location-tag lab

Use quiet mode for cleaner terminal output:

python -m focussight.tracker --quiet

Run a short calibration before tracking:

python -m focussight.tracker --calibrate-seconds 30

Controls while running:

- L: Toggle CSV logging on or off
- T: Tune threshold and alert timing from observed scores
- Q: Quit

When logging is on, files are created in logs/ with names like:

- logs/focus_session_YYYYMMDD_HHMMSS.csv

## Run Session Summary

python -m focussight.summary

Backward-compatible command:

python session_summary.py

This prints a summary for the latest log file, including:

- Average focus percent
- Average FPS
- Distracted frame percent
- Longest distracted streak (frames)
- Longest distracted streak (seconds)
- Recommended threshold and alert seconds

## Run Cognitive Operations Report

python -m focussight.ops_report

Backward-compatible command:

python ops_report.py

Save report text to file:

python -m focussight.ops_report --save reports/latest_ops_report.txt

Save report JSON too:

python -m focussight.ops_report --save-json reports/latest_ops_report.json

The report includes:

- Vigilance index
- Stability index
- Operational readiness score
- Attention lapse events
- Mean recovery time
- A practical interpretation line for field use
- Baseline comparisons for matching task/context/location tags

## Run Tests

python -m unittest discover -s tests -v

## Notes

- If your editor reports cv2 import issues, make sure VS Code is using .venv/Scripts/python.exe.
- Haar cascade XML files are downloaded automatically if missing.

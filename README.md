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
- Runtime tuning from real session data
- Phase 2 weighted signal quality scoring and status labels
- Low-light and occlusion fallback labels for poor camera conditions
- Post-session analytics script for recommendations
- Unit tests for core logic

## Project Structure

- focussight/tracker.py: Core tracker logic
- focussight/summary.py: Session analytics logic
- eye_test.py: Backward-compatible tracker launcher wrapper
- session_summary.py: Backward-compatible summary launcher wrapper
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
- Distracted frame percent
- Longest distracted streak (frames)
- Recommended threshold and alert seconds

## Run Tests

python -m unittest discover -s tests -v

## Notes

- If your editor reports cv2 import issues, make sure VS Code is using .venv/Scripts/python.exe.
- Haar cascade XML files are downloaded automatically if missing.

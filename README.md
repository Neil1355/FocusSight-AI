# FocusSight AI

FocusSight AI is a webcam-based focus tracker that detects face and eyes in real time, computes a rolling focus score, and shows live focus state on screen.

## Features

- Real-time face and eye detection using OpenCV Haar cascades
- Rolling focus score with smoothing to reduce jitter
- Focus state classification (FOCUSED or DISTRACTED)
- Delayed alert after sustained distraction
- Runtime logging toggle to save session data to CSV
- Runtime tuning from real session data
- Post-session analytics script for recommendations
- Unit tests for core logic

## Project Files

- eye_test.py: Main webcam tracker app
- session_summary.py: Post-session CSV analytics tool
- test_eye_test.py: Unit tests for tracking logic helpers
- test_session_summary.py: Unit tests for analytics helpers
- requirements.txt: Python dependencies
- setup.ps1: One-command Windows environment bootstrap
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

python eye_test.py

Controls while running:

- L: Toggle CSV logging on or off
- T: Tune threshold and alert timing from observed scores
- Q: Quit

When logging is on, files are created in logs/ with names like:

- logs/focus_session_YYYYMMDD_HHMMSS.csv

## Run Session Summary

python session_summary.py

This prints a summary for the latest log file, including:

- Average focus percent
- Distracted frame percent
- Longest distracted streak (frames)
- Recommended threshold and alert seconds

## Run Tests

python -m unittest -v

## Notes

- If your editor reports cv2 import issues, make sure VS Code is using .venv/Scripts/python.exe.
- Haar cascade XML files are downloaded automatically if missing.

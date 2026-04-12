# FocusSight AI

> **Real-time, webcam-based cognitive focus tracker — built for students, remote workers, and anyone who wants to understand and improve their attention.**

---

## The Problem

Modern work and study environments are built for distraction. Notifications, open-plan offices, social media, and back-to-back video calls fragment attention into increasingly smaller chunks. The cost is measurable:

- A 2023 UC Irvine study found it takes an average of **23 minutes and 15 seconds** to fully regain focus after a single interruption.
- Microsoft Research reports that knowledge workers are interrupted or self-interrupt roughly **every 3–5 minutes** during the workday.
- The American Psychological Association links chronic task-switching to elevated stress hormones, reduced working-memory capacity, and lower-quality output.
- Students who studied in distraction-prone environments scored, on average, **20% lower** on comprehension tests compared to peers in focused conditions (Journal of Experimental Psychology, 2019).

The downstream effects are real: missed deadlines, longer study hours with lower retention, burnout, and the quiet frustration of a full day that produced little of consequence.

Most productivity tools address *scheduling* (calendars, timers) or *environment* (website blockers). None of them tell you **whether your brain is actually engaged right now**, moment by moment.

---

## The Solution — FocusSight AI

**FocusSight AI** uses your existing webcam to passively track eye and face presence during work or study sessions. It computes a real-time focus score, classifies your state (FOCUSED / DISTRACTED), and builds a rich history of your cognitive performance across sessions — no wearables, no subscriptions, no cloud upload.

It answers questions your calendar never could:

- *"When during the day am I actually sharp?"*
- *"How long can I sustain a focused streak before my attention breaks?"*
- *"Am I improving week over week?"*
- *"What is my personal-best focused run?"*

FocusSight AI is fully **local, open-source, and privacy-first** — video frames are never saved or transmitted.

---

## Key Capabilities at a Glance

| Capability | What it does |
|---|---|
| Real-time tracking | Webcam face/eye detection every frame, rolling focus score, FOCUSED/DISTRACTED classification |
| Signal quality weighting | Penalises low-light, occlusion, and jitter; labels session quality |
| Adaptive calibration | 30-second personalised baseline before the session starts |
| Session logging | CSV per session; timestamped, frame-rate-aware rows |
| Coaching reminders | Gentle / balanced / strict reminder policies with break suggestions |
| Cognitive ops report | Vigilance, stability, operational readiness, lapse events, recovery time |
| Session scorecard | Pass/fail goals for focus, readiness, distraction, and recovery |
| History export | One-row-per-session CSV for plotting or external analysis |
| Session comparison | Signed deltas vs. your historical average |
| Adaptive threshold learning | Auto-tunes detection thresholds from your last N sessions |
| Live terminal dashboard | Real-time stat line printed every N seconds during tracking |
| Daily summary report | Aggregates all sessions from today into one report |
| Focus streak records | Tracks all-time best focused run; fires milestone & personal-best alerts |
| Distraction heatmap | Hour-of-day ASCII chart showing when you focus best and worst |
| Session notes | Attach a plain-text annotation to any session; shown in all reports |
| HTML report | Self-contained styled HTML report for sharing or archiving |

---

## Folder Structure

```
FocusSight-AI/
│
├── focussight/                 # Core package
│   ├── __init__.py
│   ├── tracker.py              # Real-time webcam tracking, CLI, session loop
│   ├── summary.py              # Session analytics, history, streaks, heatmap, notes
│   └── ops_report.py           # Cognitive operations report builder and renderer
│
├── tests/                      # Automated test suite (78 tests)
│   ├── test_tracker.py
│   ├── test_summary.py
│   └── test_ops_report.py
│
├── docs/
│   ├── ROADMAP.md              # Phase-by-phase development plan
│   └── CHANGELOG.md            # Release history
│
├── eye_test.py                 # Backward-compatible tracker launcher
├── session_summary.py          # Backward-compatible summary launcher
├── ops_report.py               # Backward-compatible report launcher
│
├── haarcascade_frontalface_default.xml   # Frontal face cascade (auto-downloaded if missing)
├── haarcascade_eye.xml                   # Eye cascade (auto-downloaded if missing)
├── haarcascade_profileface.xml           # Profile face cascade (auto-downloaded if missing)
│
├── requirements.txt            # Python dependencies
├── setup.ps1                   # One-command Windows bootstrap
└── README.md
```

**Runtime directories created automatically:**

```
logs/       # Session CSVs  (focus_session_YYYYMMDD_HHMMSS.csv)
reports/    # Generated text, JSON, and HTML reports
```

---

## Requirements

| Requirement | Version |
|---|---|
| Operating system | Windows, macOS, or Linux |
| Python | 3.10 or newer (3.13 recommended) |
| Webcam | Any USB or built-in webcam |
| OpenCV | `opencv-python==4.13` (installed from `requirements.txt`) |

No GPU required. No cloud account required. No data leaves your machine.

---

## Installation

### Windows — one command

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

### Manual (Windows / macOS / Linux)

```bash
# 1. Clone the repository
git clone https://github.com/Neil1355/FocusSight-AI.git
cd FocusSight-AI

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run the tracker
python eye_test.py
```

> **VS Code tip:** If the editor reports `cv2` import errors, open the Command Palette → *Python: Select Interpreter* → choose `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux).

---

## Running FocusSight AI

### 1 — Start the focus tracker

```bash
# Minimal launch (uses defaults)
python eye_test.py

# Full module form
python -m focussight.tracker
```

An OpenCV window opens showing the live camera feed with bounding boxes around detected faces and eyes, plus a real-time focus percentage and state label.

**Keyboard controls while running:**

| Key | Action |
|---|---|
| `L` | Toggle CSV session logging on/off |
| `T` | Tune detection thresholds from live data |
| `Q` | Quit |

---

## Feature Reference

### Feature 1 — Real-Time Face & Eye Detection

**What it does:** Every video frame is processed through OpenCV Haar cascade classifiers. First, frontal faces are detected; if a frontal pass fails, a profile-face fallback runs to handle head tilt and hats. Within each detected face region, eyes are located. The ratio of eye-visible frames to total frames drives the rolling focus score.

**Why it matters:** Eye presence is the most reliable passive proxy for directed visual attention. When eyes are closed, looking away, or the face leaves frame, attention has almost certainly shifted.

**How to use it:** Simply run the tracker. The overlaid percentage and FOCUSED/DISTRACTED label update every frame.

---

### Feature 2 — Signal Quality Weighting & Labels

**What it does:** Raw focus scores are weighted by a signal-quality multiplier that penalises poor camera conditions — low ambient brightness, partial face occlusion, and high score variance (jitter). The current signal status is shown in the overlay and logged per row.

**Signal status labels:**

| Label | Meaning |
|---|---|
| `GOOD` | Clean detection, reliable score |
| `LOW_LIGHT` | Frame brightness below threshold |
| `OCCLUDED` | Face partially blocked |
| `NOISY` | High score variance across recent frames |
| `AWAY` | No face detected for several seconds |

**How to use it:** No action needed. The weighting is automatic. Check the status label to understand whether a drop in focus score is real attention loss or a camera condition artefact.

---

### Feature 3 — Adaptive Calibration

**What it does:** Optionally runs a personalised 30-second baseline measurement before the tracking session begins. During calibration, you are prompted to look at the screen naturally. The observed average focus score is used to compute a personalised detection threshold and alert delay, replacing the global defaults.

**Why it matters:** Different people, webcams, lighting conditions, and glasses result in very different raw scores. A universal threshold is a poor fit. Calibration makes the system personal.

**How to use it:**

```bash
python eye_test.py --calibrate-seconds 30
```

---

### Feature 4 — CLI Configuration & JSON Profiles

**What it does:** Every detection parameter can be set at the command line. Profiles persist those settings as a JSON file so you never need to re-enter them.

**Key flags:**

| Flag | Description | Default |
|---|---|---|
| `--camera-index N` | Which webcam to use | `0` |
| `--threshold F` | Focus score cutoff (0.1–0.95) | `0.55` |
| `--alert-seconds F` | Seconds of distraction before alert fires | `3.0` |
| `--profile PATH` | Load settings from a JSON profile | — |
| `--save-profile PATH` | Save final settings to a JSON profile | — |
| `--reminder-policy KEY` | `gentle`, `balanced`, or `strict` coaching | `balanced` |
| `--quiet` | Suppress non-essential terminal output | off |

**Example:**

```bash
# Save a calibrated profile for future sessions
python eye_test.py --calibrate-seconds 30 --save-profile my_profile.json

# Load it next time
python eye_test.py --profile my_profile.json
```

---

### Feature 5 — Session Logging

**What it does:** When logging is enabled (press `L` in the tracker, or use `--autolog`), every processed frame writes a row to a CSV in `logs/`. Each row captures: timestamp, elapsed seconds, frame interval, observed FPS, raw focus score, signal-weighted focus score, state, signal status, face/eye flags, thresholds, and optional session tags.

**Why it matters:** The CSV is the foundation for every analytics and report feature. Without it, only live readouts are available.

**How to use it:**

```bash
# Start logging automatically at launch
python eye_test.py --autolog

# Log and auto-generate an ops report when logging ends
python eye_test.py --autolog --auto-report --report-dir reports
```

Log files are written to `logs/focus_session_YYYYMMDD_HHMMSS.csv`.

---

### Feature 6 — Session Tagging

**What it does:** Three free-text tags — `task`, `context`, and `location` — are written to every logged row. The analytics layer groups rows by matching tag values to build per-tag baselines, letting you compare *coding vs. reading* or *home vs. library*.

**How to use it:**

```bash
python eye_test.py --autolog --task-tag coding --context-tag exam_prep --location-tag library
```

---

### Feature 7 — Cognitive Operations Report

**What it does:** Produces a structured performance report from a session CSV, covering six cognitive-science-grounded metrics plus recommendations and a scorecard.

**Metrics:**

| Metric | How it is computed |
|---|---|
| Vigilance index | Proportion of frames in FOCUSED state |
| Stability index | 1 − (state-flip rate), measuring how consistent focus is |
| Operational readiness | Weighted blend of vigilance and stability |
| Attention lapse events | Number of FOCUSED→DISTRACTED transitions |
| Mean recovery time | Average seconds to return to FOCUSED after each lapse |
| Interpretation | A plain-English readiness summary |

**How to use it:**

```bash
# Print report for the latest session
python ops_report.py

# Target a specific session CSV
python ops_report.py --file logs/focus_session_20260412_090000.csv

# Save text + JSON + HTML
python ops_report.py --save reports/ops.txt --save-json reports/ops.json --save-html reports/ops.html
```

---

### Feature 8 — Session Scorecard

**What it does:** Evaluates the session against four pass/fail goals and computes an overall score percentage, assigned a status badge: `excellent`, `on-track`, `needs-work`, or `critical`.

| Goal | Target |
|---|---|
| Focus goal | ≥ 70% average focus score |
| Readiness goal | Operational readiness ≥ 0.65 |
| Distraction-percent goal | ≤ 35% distracted frames |
| Recovery goal | Mean recovery time ≤ 8 seconds |

The scorecard appears at the end of every ops report and HTML report.

---

### Feature 9 — Multi-Session History Export & Comparison

**What it does:** Aggregates every session log in `logs/` into a single one-row-per-session CSV for external plotting or analysis. Also computes signed deltas between the current session and the historical average of all other sessions.

**How to use it:**

```bash
# Export history CSV
python ops_report.py --export-history logs/history.csv

# Show the current session compared to historical baseline
python ops_report.py  # "Session vs. Historical Baseline" section appears automatically
```

---

### Feature 10 — HTML Report

**What it does:** Renders a fully self-contained, styled HTML report including all metrics tables, a colour-coded scorecard badge, the session-vs-history comparison, and any session note. Can be shared via email or saved for archiving.

**Status badge colours:** Green = excellent, Blue = on-track, Orange = needs-work, Red = critical.

**How to use it:**

```bash
python ops_report.py --save-html reports/latest.html
```

---

### Feature 11 — Adaptive Threshold Learning

**What it does:** Analyses the most recent N session logs (default 5) and applies the existing tuning formula to suggest new detection threshold and alert-timing values tailored to your recent performance. When combined with `--save-profile`, the profile file is updated automatically before the next session starts.

**Why it matters:** Your baseline focus scores shift over time with lighting, fatigue level, and camera position changes. Adaptive learning keeps the detection accurate without manual recalibration.

**How to use it:**

```bash
# Update profile from last 5 sessions, then run
python eye_test.py --profile my.json --save-profile my.json --auto-update-profile
```

---

### Feature 12 — Coaching Reminder Policies

**What it does:** Periodically prompts you in the terminal (and the OpenCV overlay) when sustained distraction is detected. Three policies control frequency and tone:

| Policy | Alert interval | Break suggestion threshold |
|---|---|---|
| `gentle` | Every 90 seconds of distraction | After 5 minutes |
| `balanced` | Every 60 seconds | After 3 minutes |
| `strict` | Every 30 seconds | After 2 minutes |

Break suggestions surface separately when a single distraction streak exceeds the policy's threshold.

**How to use it:**

```bash
python eye_test.py --reminder-policy strict
```

---

### Feature 13 — Live Terminal Dashboard

**What it does:** Prints a compact one-line stat summary to stdout every N seconds during the tracking session, without interrupting the OpenCV window. Useful when running the tracker in a terminal split alongside your work.

**Example output:**

```
[FOCUSED]    focus=74%  distracted=18%  streak=0s  elapsed=12:34  signal=GOOD  policy=balanced  LOG:ON
```

**How to use it:**

```bash
# Enable with default 5-second interval
python eye_test.py --dashboard

# Custom interval
python eye_test.py --dashboard --dashboard-interval 10
```

---

### Feature 14 — Daily Summary Report

**What it does:** Aggregates all session logs recorded on today's local date into a single cognitive-ops report — useful for an end-of-day check-in when you have run multiple short sessions.

**How to use it:**

```bash
python ops_report.py --daily-summary
```

---

### Feature 15 — Focus Streak Goals & Personal Records

**What it does:** Tracks the length of the current continuous FOCUSED run in real time. Fires achievement notifications when:
- A round milestone is crossed (30 seconds, 1 minute, 2 minutes, 5 minutes, 10 minutes, 15 minutes, 30 minutes).
- A user-defined personal streak goal is reached.
- An all-time personal-best focused run is beaten.

Personal records are computed by scanning all session logs on startup.

**How to use it:**

```bash
# Set a 10-minute streak goal
python eye_test.py --streak-goal 600

# Example notification printed to the terminal:
# 🎯 Focus milestone: 5 min focused streak!
# 🏆 Streak goal reached: 10 min focused!
# 🥇 New personal best focused streak: 643s!
```

---

### Feature 16 — Distraction Pattern Analysis (Hour-of-Day Heatmap)

**What it does:** Reads all session logs and groups distracted frames by hour-of-day (0–23). Renders an ASCII bar chart and surfaces your three worst and three best focus hours so you can schedule demanding work at your peak times.

**Example output:**

```
Hour | Distracted % | Chart
------------------------------
09:00 |   18.2%      | █████
10:00 |   62.5%      | ████████████████████
14:00 |   44.1%      | ██████████████

Worst focus hours: 10:00 (63%), 14:00 (44%), 15:00 (38%)
Best  focus hours: 09:00 (18%), 08:00 (21%), 16:00 (27%)
```

**How to use it:**

```bash
python ops_report.py --distraction-heatmap
```

---

### Feature 17 — Session Notes & Annotations

**What it does:** Lets you attach a short plain-text note to any session at the command line. The note is saved as `<session>_note.txt` alongside the session CSV and appears in the text ops report and the HTML report.

**Why it matters:** Context you can't measure — exam pressure, poor sleep, noisy environment, medication — often explains anomalies in the data. Notes give that context a permanent home next to the numbers.

**How to use it:**

```bash
python eye_test.py --autolog --note "Exam prep – third coffee, library was loud"
```

---

## All CLI Flags

### Tracker (`eye_test.py` / `python -m focussight.tracker`)

| Flag | Type | Description |
|---|---|---|
| `--camera-index N` | int | Webcam index (default: 0) |
| `--threshold F` | float | Focus score cutoff 0.1–0.95 |
| `--alert-seconds F` | float | Distraction alert delay in seconds |
| `--profile PATH` | str | Load settings from JSON profile |
| `--save-profile PATH` | str | Save settings to JSON profile after run |
| `--auto-update-profile` | flag | Update profile thresholds from recent history before run |
| `--calibrate-seconds F` | float | Run calibration phase for N seconds before tracking |
| `--autolog` | flag | Start session logging immediately |
| `--auto-report` | flag | Generate ops report when logging ends |
| `--report-dir PATH` | str | Directory for generated reports (default: `reports`) |
| `--quiet` | flag | Suppress non-essential terminal output |
| `--reminder-policy KEY` | str | `gentle`, `balanced`, or `strict` |
| `--task-tag TEXT` | str | Session task label (e.g. `coding`) |
| `--context-tag TEXT` | str | Session context label (e.g. `exam_prep`) |
| `--location-tag TEXT` | str | Session location label (e.g. `library`) |
| `--dashboard` | flag | Print live session stats every N seconds |
| `--dashboard-interval F` | float | Seconds between dashboard prints (default: 5) |
| `--streak-goal F` | float | Personal focused-streak goal in seconds |
| `--note TEXT` | str | Annotation saved alongside the session log |

### Ops Report (`ops_report.py` / `python -m focussight.ops_report`)

| Flag | Type | Description |
|---|---|---|
| `--file PATH` | str | Target a specific session CSV |
| `--save PATH` | str | Save report text to file |
| `--save-json PATH` | str | Save report JSON to file |
| `--save-html PATH` | str | Save self-contained HTML report to file |
| `--export-history PATH` | str | Export one-row-per-session history CSV |
| `--daily-summary` | flag | Print aggregate report for today's sessions |
| `--distraction-heatmap` | flag | Print ASCII hour-of-day distraction chart |

---

## Common Workflows

```bash
# ── First ever session ─────────────────────────────────────────────────────
# Calibrate, log the session, save a profile
python eye_test.py --calibrate-seconds 30 --autolog --save-profile my.json

# ── Daily study session ────────────────────────────────────────────────────
# Load profile, log, show live dashboard, set a 5-minute streak goal, add a note
python eye_test.py --profile my.json --autolog --auto-report \
    --dashboard --streak-goal 300 \
    --task-tag reading --note "Chapter 7 revision"

# ── Adaptive profile update ────────────────────────────────────────────────
# Update detection thresholds from the last 5 sessions before starting
python eye_test.py --profile my.json --save-profile my.json \
    --auto-update-profile --autolog

# ── End-of-day review ─────────────────────────────────────────────────────
# Print today's summary, distraction heatmap, and export history
python ops_report.py --daily-summary --distraction-heatmap \
    --export-history logs/history.csv --save-html reports/today.html

# ── Weekly review ─────────────────────────────────────────────────────────
# See when you focus best across all sessions
python ops_report.py --distraction-heatmap
```

---

## Running the Tests

```bash
python -m pytest tests/ -v
```

The test suite covers tracker logic, signal quality, calibration, profile I/O, reminder policies, analytics, streak records, distraction heatmap, session notes, daily reports, HTML rendering, and the adaptive threshold learner — **78 tests** in total.

---

## Project Documentation

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — full phase-by-phase development plan (Phases 1–11 complete)
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — detailed change history per release

---

## Notes & Troubleshooting

| Issue | Fix |
|---|---|
| `cv2` import error in VS Code | Set interpreter to `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux) |
| Haar cascade XML not found | Run the tracker once; missing files are downloaded automatically from the OpenCV GitHub CDN |
| Low signal quality / `LOW_LIGHT` label | Increase ambient lighting; position a lamp facing you, not behind you |
| Score seems too high/low | Run `--calibrate-seconds 30` to personalise thresholds, or adjust `--threshold` manually |
| No logs found for reports | Start a session with `--autolog`; logs must exist in `logs/` before analytics run |

# FocusSight AI Roadmap

## Vision

Evolve FocusSight from a demo detector into a practical personal focus assistant with reliable tracking, calibration, trends, and actionable feedback.

## Phase 1: Usability and Configuration (completed)

Goal: make the app easier to run, tune, and personalize.

Deliverables:

- Add runtime command-line options for camera index, threshold, and alert delay
- Add optional profile save/load in JSON (portable settings)
- Keep existing keyboard controls for logging and tuning
- Extend tests to cover profile and config behavior

## Phase 2: Better Signal Quality (completed)

Goal: improve focus quality beyond binary eye-detection.

Deliverables:

- Add confidence weighting from eye box stability and persistence
- Track missing-face time and rapid state flips
- Add calibration mode to personalize focus thresholds before tracking
- Add low-light and occlusion fallback status labels

## Phase 3: Analytics and Insights (completed)

Goal: make session logs useful for self-improvement.

Deliverables:

- Add aggregate summaries across all sessions
- Add daily/weekly trend output (CSV or JSON)
- Add "best focus window" and "most distracted window" metrics
- Add cognitive-operations interpretation layer (vigilance, stability, readiness)
- Add session tagging and baseline comparisons by task/context/location
- Add recommendation generation from trends and cognitive signals

## Phase 4: Coaching Layer (completed)

Goal: provide non-intrusive actionable coaching.

Deliverables:

- Add configurable reminder policies (gentle/strict)
- Add break recommendations after sustained distracted streaks
- Add session goals and scorecards

## Phase 5: Multi-Session History Export & Comparison (completed)

Goal: give users cross-session perspective to spot long-term patterns.

Deliverables:

- Export all session summaries to a single history CSV (`--export-history`)
- Compare the current session against historical averages (focus delta, distracted %, streak)
- Include session comparison section in text and HTML reports
- Add standalone HTML report output (`--save-html`) for easy sharing and archiving

## Phase 6: Adaptive Threshold Learning (completed)

Goal: automatically improve default settings as more session data accumulates.

Deliverables:

- Derive threshold and alert-timing suggestions from recent session history
- Auto-update a profile file from history before a run (`--auto-update-profile`)
- Fall back gracefully when no history is available

## Phase 7: Live Terminal Dashboard (completed)

Goal: let users monitor session health from the terminal without watching the OpenCV window.

Deliverables:

- `format_live_dashboard()` helper producing a compact one-line stat summary
- Periodic dashboard prints every N seconds during tracking (`--dashboard`, `--dashboard-interval`)
- Tracks rolling session avg focus, distracted %, current streak, and signal status
- Off by default to avoid clutter; respects `--quiet` mode

## Phase 8: Daily Summary Report (completed)

Goal: aggregate all of today's sessions into a single end-of-day report.

Deliverables:

- `summarize_today(log_dir)` in `summary.py` – filters sessions recorded today by timestamp
- `build_daily_report(log_dir)` in `ops_report.py` – produces a full daily report dict (stats, cognitive metrics, windows, recommendations, scorecard)
- `render_daily_report(report)` in `ops_report.py` – text form of the daily report
- `--daily-summary` CLI flag in `ops_report.py` for quick end-of-day check-in

## Phase 9: Focus Streak Goals & Personal Records (completed)

Goal: gamify sustained focus and surface personal-best milestones during tracking.

Deliverables:

- `compute_streak_records(log_dir)` in `summary.py` – finds all-time best focused streak across all sessions
- `check_streak_milestone(current, record, goal)` in `summary.py` – returns achievement messages for round milestones (30s, 1 min, 5 min…), personal bests, and user-defined streak goals
- Live milestone notifications printed to the terminal during tracking sessions
- `--streak-goal <seconds>` CLI flag to set a personal focused-streak target

## Phase 10: Distraction Pattern Analysis (completed)

Goal: surface time-of-day trends so users know when they focus best and worst.

Deliverables:

- `compute_hour_of_day_distraction(log_dir)` in `summary.py` – buckets distracted-frame rate by hour-of-day across all session logs
- `find_worst_focus_hours(buckets, top_n)` and `find_best_focus_hours(buckets, top_n)` helpers
- `render_distraction_heatmap(buckets)` – ASCII hourly bar chart
- `--distraction-heatmap` CLI flag in `ops_report.py`

## Phase 11: Session Notes & Annotations (completed)

Goal: let users attach context to sessions for richer post-hoc analysis.

Deliverables:

- `--note <text>` CLI flag on the tracker – saves a plain-text note file alongside the session CSV after the run
- `save_session_note(csv_path, text)` and `load_session_note(csv_path)` helpers in `summary.py`
- Session note included in `render_ops_report()` text output and HTML report when present
- `build_ops_report()` always includes a `note` key (empty string when no note file exists)

---

## Phase 12: Packaging & Distribution (planned)

Goal: make FocusSight AI trivially installable as a proper Python package so users can `pip install` it and run it anywhere without manually cloning the repo.

Deliverables:

- Add `pyproject.toml` (PEP 517/518) with package metadata, entry-point scripts (`focussight-track`, `focussight-report`), and dependency declarations
- Publish to PyPI (or provide a local `pip install -e .` workflow for development)
- Ensure cascade XML files are bundled as package data so they are always available after install
- Update `README.md` installation section with `pip install focussight-ai` quick-start
- Add a `Makefile` (or `tox.ini`) for one-command test, lint, and build targets

## Phase 13: REST API / WebSocket Server (planned)

Goal: expose FocusSight's real-time tracking data over a local HTTP/WebSocket interface so external clients (browser extensions, dashboards, integrations) can consume focus state without any Python knowledge.

Deliverables:

- Lightweight FastAPI server (`focussight/server.py`) that runs the tracker loop in a background thread
- `/status` GET endpoint – returns current focus state, score, streak, signal quality, and session elapsed time as JSON
- `/events` WebSocket endpoint – streams a focus-state event every second to connected clients
- `/report` GET endpoint – returns the latest session ops-report JSON on demand
- `--serve` CLI flag on the tracker to start the API alongside the webcam loop
- CORS enabled by default for `localhost` origins so the browser extension can connect without extra config
- Add tests for server endpoint contracts using `httpx` / `pytest-asyncio`

## Phase 14: Browser Extension (planned)

Goal: ship a lightweight Chrome/Firefox browser extension that reads focus state from the Phase 13 API and surfaces non-intrusive in-browser nudges — bringing FocusSight into the user's actual work environment.

Deliverables:

- Manifest V3 extension with a popup showing live focus score, state badge, and session streak
- Background service-worker that polls `/status` (or subscribes to `/events` WebSocket) every second
- Non-intrusive banner/toast notification when a distraction streak exceeds the user's alert threshold
- Options page: server URL (default `http://localhost:8765`), notification style (banner / silent / none), distraction threshold override
- Extension icon badge colour changes with state: green (FOCUSED), amber (LOW_CONFIDENCE), red (DISTRACTED)
- Packaged as a `.zip` ready for Chrome Web Store submission and as an unsigned `.xpi` for Firefox
- Developer docs explaining how to load the extension unpacked for local testing

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

## Stepwise Execution Plan

1. Complete Phase 2 fallback labels and reliability metrics.
2. Validate with tests and update docs/changelog.
3. Release and collect sample logs with weighted scoring.
4. Build Phase 3 aggregation on top of richer session logs.
5. Add coaching logic only after metric confidence is acceptable.

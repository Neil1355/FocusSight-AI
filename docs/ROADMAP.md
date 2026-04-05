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

## Phase 2: Better Signal Quality (in progress)

Goal: improve focus quality beyond binary eye-detection.

Deliverables:

- Add confidence weighting from eye box stability and persistence
- Track missing-face time and rapid state flips
- Add calibration mode to personalize focus thresholds before tracking
- Add low-light and occlusion fallback status labels

## Phase 3: Analytics and Insights (in progress)

Goal: make session logs useful for self-improvement.

Deliverables:

- Add aggregate summaries across all sessions
- Add daily/weekly trend output (CSV or JSON)
- Add "best focus window" and "most distracted window" metrics
- Add cognitive-operations interpretation layer (vigilance, stability, readiness)

## Phase 4: Coaching Layer

Goal: provide non-intrusive actionable coaching.

Deliverables:

- Add configurable reminder policies (gentle/strict)
- Add break recommendations after sustained distracted streaks
- Add session goals and scorecards

## Stepwise Execution Plan

1. Complete Phase 2 fallback labels and reliability metrics.
2. Validate with tests and update docs/changelog.
3. Release and collect sample logs with weighted scoring.
4. Build Phase 3 aggregation on top of richer session logs.
5. Add coaching logic only after metric confidence is acceptable.

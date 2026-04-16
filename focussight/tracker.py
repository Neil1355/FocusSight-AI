import argparse
import csv
import json
import os
import time
import urllib.request
from collections import deque
from datetime import datetime

import cv2

from .ops_report import build_ops_report, render_ops_report

face_xml = "haarcascade_frontalface_default.xml"
eye_xml = "haarcascade_eye.xml"
profile_face_xml = "haarcascade_profileface.xml"

FOCUSED_THRESHOLD = 0.6
ALERT_AFTER_SECONDS = 2.5
MIN_TUNE_SAMPLES = 60
CALIBRATION_MIN_FRAMES = 30
DEFAULT_CAMERA_INDEX = 0
DEFAULT_REMINDER_POLICY = "balanced"

REMINDER_POLICIES = {
    "gentle": {
        "min_interval_seconds": 25.0,
        "break_after_seconds": 90.0,
        "message": "Gentle reminder: bring attention back",
        "break_message": "Suggestion: take a short reset break",
    },
    "balanced": {
        "min_interval_seconds": 15.0,
        "break_after_seconds": 60.0,
        "message": "Alert: refocus your eyes",
        "break_message": "Suggestion: take a 2-minute break",
    },
    "strict": {
        "min_interval_seconds": 8.0,
        "break_after_seconds": 40.0,
        "message": "Immediate correction needed: refocus now",
        "break_message": "Suggestion: pause now for a quick reset",
    },
}

DEFAULT_CONFIG = {
    "camera_index": DEFAULT_CAMERA_INDEX,
    "focused_threshold": FOCUSED_THRESHOLD,
    "alert_after_seconds": ALERT_AFTER_SECONDS,
    "reminder_policy": DEFAULT_REMINDER_POLICY,
}


def log_info(message, quiet=False):
    if not quiet:
        print(message)


def format_live_dashboard(
    state,
    focus_pct,
    distracted_pct,
    elapsed_seconds,
    streak_seconds,
    signal_status,
    logging_enabled,
    reminder_policy_key,
):
    """Return a compact single-line dashboard string for terminal output during tracking.

    Designed to be printed periodically (e.g. every 5 seconds) so the user can
    monitor session health without looking at the OpenCV window.
    """
    elapsed_min = int(elapsed_seconds) // 60
    elapsed_sec = int(elapsed_seconds) % 60
    log_indicator = "LOG:ON" if logging_enabled else "LOG:OFF"
    state_label = f"[{state}]"
    return (
        f"{state_label:<12} "
        f"focus={focus_pct:.0f}%  distracted={distracted_pct:.0f}%  "
        f"streak={streak_seconds:.0f}s  "
        f"elapsed={elapsed_min:02d}:{elapsed_sec:02d}  "
        f"signal={signal_status}  "
        f"policy={reminder_policy_key}  {log_indicator}"
    )


def parse_session_tags(task_tag=None, context_tag=None, location_tag=None):
    """Normalize optional session tags used for grouped analytics."""
    def _clean(value):
        if value is None:
            return ""
        return str(value).strip().lower().replace(" ", "_")

    return {
        "task_tag": _clean(task_tag),
        "context_tag": _clean(context_tag),
        "location_tag": _clean(location_tag),
    }


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def normalize_config(config):
    """Clamp and normalize config values into safe runtime bounds."""
    reminder_policy = str(config.get("reminder_policy", DEFAULT_REMINDER_POLICY)).strip().lower()
    if reminder_policy not in REMINDER_POLICIES:
        reminder_policy = DEFAULT_REMINDER_POLICY
    return {
        "camera_index": max(0, int(config.get("camera_index", DEFAULT_CAMERA_INDEX))),
        "focused_threshold": clamp(float(config.get("focused_threshold", FOCUSED_THRESHOLD)), 0.1, 0.95),
        "alert_after_seconds": clamp(float(config.get("alert_after_seconds", ALERT_AFTER_SECONDS)), 0.5, 10.0),
        "reminder_policy": reminder_policy,
    }


def resolve_reminder_policy(policy_name):
    key = str(policy_name or DEFAULT_REMINDER_POLICY).strip().lower()
    if key not in REMINDER_POLICIES:
        key = DEFAULT_REMINDER_POLICY
    return key, REMINDER_POLICIES[key]


def should_emit_reminder(now, distracted_since, last_reminder_at, alert_after_seconds, min_interval_seconds):
    if distracted_since is None:
        return False
    distracted_duration = now - distracted_since
    if distracted_duration < alert_after_seconds:
        return False
    if last_reminder_at is None:
        return True
    return (now - last_reminder_at) >= min_interval_seconds


def should_suggest_break(now, distracted_since, break_after_seconds):
    if distracted_since is None:
        return False
    return (now - distracted_since) >= break_after_seconds


def resolve_runtime_config(cli_values, profile_values):
    """Apply precedence: defaults < profile < CLI."""
    merged = dict(DEFAULT_CONFIG)
    merged.update(profile_values or {})
    for key, value in (cli_values or {}).items():
        if value is not None:
            merged[key] = value
    return normalize_config(merged)


def load_profile(path):
    """Load profile JSON. Returns normalized values or empty dict."""
    if not path:
        return {}
    if not os.path.exists(path):
        print(f"Profile not found at {path}. Using defaults/CLI.")
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Profile JSON must contain an object.")
    allowed = {k: raw[k] for k in DEFAULT_CONFIG if k in raw}
    return normalize_config(allowed)


def save_profile(path, config):
    """Save normalized profile JSON."""
    normalized = normalize_config(config)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)
    print(f"Saved profile: {path}")


def smooth_box(boxes):
    """Average a small history of (x, y, w, h) boxes."""
    count = len(boxes)
    if count == 0:
        return None
    sx = sum(b[0] for b in boxes)
    sy = sum(b[1] for b in boxes)
    sw = sum(b[2] for b in boxes)
    sh = sum(b[3] for b in boxes)
    return (sx // count, sy // count, sw // count, sh // count)


def map_flipped_box_to_original(box, frame_width):
    """Convert a box detected on a horizontally flipped frame back to original coords."""
    x, y, w, h = box
    return (frame_width - x - w, y, w, h)


def compute_observed_fps(frame_interval_seconds):
    if frame_interval_seconds and frame_interval_seconds > 0:
        return 1.0 / frame_interval_seconds
    return 0.0


def update_stability_seconds(stability_seconds, detected, delta_seconds, recovery_multiplier=1.0, decay_multiplier=2.0):
    """Maintain a time-based stability window that is independent of frame rate."""
    if delta_seconds <= 0:
        return stability_seconds
    if detected:
        return min(1.5, stability_seconds + delta_seconds * recovery_multiplier)
    return max(0.0, stability_seconds - delta_seconds * decay_multiplier)


def compute_focus_score(history):
    """Compute rolling focus score from a deque of 0/1 samples."""
    return (sum(history) / len(history)) if history else 0.0


def evaluate_focus_state(face_found, focus_score, threshold):
    """Return (state, color) used by overlay logic."""
    if face_found and focus_score >= threshold:
        return ("FOCUSED", (0, 220, 0))
    return ("DISTRACTED", (0, 140, 255))


def compute_signal_quality(
    raw_focus_score,
    eye_persistence,
    missing_face_seconds,
    rapid_flip_count,
    brightness_mean=None,
    face_found=True,
    eye_found=True,
):
    """Phase 2 weighting: penalize noisy eyes, face loss, low light, and rapid state flipping."""
    eye_weight = clamp(eye_persistence, 0.4, 1.0)
    face_weight = clamp(1.0 - (missing_face_seconds / 2.0), 0.3, 1.0)
    flip_weight = clamp(1.0 - (rapid_flip_count * 0.08), 0.55, 1.0)
    brightness_weight = 1.0
    if brightness_mean is not None:
        brightness_weight = clamp((float(brightness_mean) - 35.0) / 90.0, 0.25, 1.0)

    weighted_score = clamp(
        raw_focus_score * eye_weight * face_weight * flip_weight * brightness_weight,
        0.0,
        1.0,
    )

    if brightness_mean is not None and brightness_mean < 55.0:
        status_label = "LOW_LIGHT"
    elif missing_face_seconds >= 2.0:
        status_label = "AWAY_FROM_CAMERA"
    elif missing_face_seconds >= 0.8:
        status_label = "FACE_UNSTABLE"
    elif face_found and not eye_found and eye_persistence < 0.55:
        status_label = "OCCLUDED"
    elif eye_persistence < 0.55:
        status_label = "LOW_CONFIDENCE"
    elif rapid_flip_count >= 4:
        status_label = "NOISY_SIGNAL"
    else:
        status_label = "TRACKING_OK"

    return weighted_score, status_label


def derive_calibrated_config(
    raw_scores,
    eye_persistence_scores,
    face_presence_ratio,
    current_threshold,
    current_alert_seconds,
):
    """Derive personalized settings from calibration samples."""
    if len(raw_scores) < CALIBRATION_MIN_FRAMES or face_presence_ratio < 0.5:
        return current_threshold, current_alert_seconds, False

    avg_focus = sum(raw_scores) / len(raw_scores)
    avg_eye_persistence = sum(eye_persistence_scores) / len(eye_persistence_scores) if eye_persistence_scores else 0.0
    score_variance = (
        sum((score - avg_focus) ** 2 for score in raw_scores) / len(raw_scores)
        if len(raw_scores) > 1
        else 0.0
    )
    score_spread = score_variance ** 0.5

    tuned_threshold = clamp(avg_focus - max(0.08, score_spread * 1.2), 0.45, 0.90)
    tuned_alert_seconds = clamp(
        1.5 + (1.0 - avg_focus) * 2.5 + (1.0 - avg_eye_persistence) * 1.5,
        1.5,
        5.0,
    )
    return tuned_threshold, tuned_alert_seconds, True


def tune_parameters_from_scores(scores, current_threshold, current_alert_seconds):
    """Tune threshold and alert timing from observed focus scores."""
    if len(scores) < MIN_TUNE_SAMPLES:
        return current_threshold, current_alert_seconds, False

    avg_focus = sum(scores) / len(scores)
    tuned_threshold = clamp(avg_focus - 0.15, 0.45, 0.80)
    tuned_alert_seconds = clamp(1.5 + (1.0 - avg_focus) * 3.0, 1.5, 4.5)
    return tuned_threshold, tuned_alert_seconds, True


def start_session_logger(log_dir="logs"):
    """Create a CSV logger and return (file_handle, writer, path)."""
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"focus_session_{timestamp}.csv")
    file_handle = open(log_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(file_handle)
    writer.writerow(
        [
            "timestamp",
            "elapsed_seconds",
            "frame_interval_seconds",
            "observed_fps",
            "focus_score",
            "weighted_focus_score",
            "state",
            "signal_status",
            "face_found",
            "eye_found",
            "focused_threshold",
            "alert_after_seconds",
            "task_tag",
            "context_tag",
            "location_tag",
        ]
    )
    return file_handle, writer, log_path


def report_output_paths(log_path, report_dir):
    """Build deterministic report artifact paths from a log file path."""
    base_name = os.path.splitext(os.path.basename(log_path))[0]
    txt_path = os.path.join(report_dir, f"{base_name}_ops_report.txt")
    json_path = os.path.join(report_dir, f"{base_name}_ops_report.json")
    return txt_path, json_path


def generate_ops_artifacts(log_path, report_dir="reports", save_json=True, quiet=False):
    """Generate text/json cognitive-operations artifacts for a log file."""
    if not log_path or not os.path.exists(log_path):
        return None

    os.makedirs(report_dir, exist_ok=True)
    report = build_ops_report(log_path)
    text = render_ops_report(report)
    txt_path, json_path = report_output_paths(log_path, report_dir)

    with open(txt_path, "w", encoding="utf-8") as handle:
        handle.write(text)

    result = {"txt_path": txt_path, "json_path": None}
    if save_json:
        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        result["json_path"] = json_path

    log_info(f"Generated ops report: {txt_path}", quiet)
    if result["json_path"]:
        log_info(f"Generated ops report JSON: {json_path}", quiet)
    return result


def auto_update_profile_from_history(profile_path, log_dir="logs", recent_sessions=5):
    """Update a profile's threshold and alert settings based on recent session history.

    Returns (updated: bool, adaptive_info: dict or message: str).
    """
    from .summary import compute_adaptive_thresholds

    adaptive = compute_adaptive_thresholds(log_dir, recent_sessions)
    if adaptive is None:
        return False, "No session history available for adaptive update."

    current_config = load_profile(profile_path) if (profile_path and os.path.exists(profile_path)) else {}
    merged = dict(DEFAULT_CONFIG)
    merged.update(current_config)
    merged["focused_threshold"] = adaptive["suggested_threshold"]
    merged["alert_after_seconds"] = adaptive["suggested_alert_seconds"]
    save_profile(profile_path, merged)
    return True, adaptive


def run_calibration_phase(
    cap,
    face_cascade_local,
    eye_cascade_local,
    duration_seconds,
    current_threshold,
    current_alert_seconds,
    quiet=False,
):
    """Capture a short calibration session and derive personalized settings."""
    raw_scores = []
    eye_persistence_scores = []
    face_frames = 0
    frames = 0
    start_time = time.time()

    log_info(
        f"Calibration started for {duration_seconds:.1f}s. "
        "Look at the camera normally, then press Q to skip.",
        quiet,
    )

    while (time.time() - start_time) < duration_seconds:
        ret, frame = cap.read()
        if not ret:
            break

        frames += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade_local.detectMultiScale(gray, 1.3, 5)
        face_found = len(faces) > 0
        eye_found = False

        if face_found:
            face_frames += 1
            xf, yf, wf, hf = max(faces, key=lambda f: f[2] * f[3])
            roi_gray = gray[yf : yf + hf // 2, xf : xf + wf]
            eyes = eye_cascade_local.detectMultiScale(roi_gray, 1.1, 10)
            eye_found = len(eyes) > 0

        raw_scores.append(1.0 if face_found and eye_found else 0.0)
        eye_persistence_scores.append(1.0 if eye_found else 0.0)

        cv2.putText(
            frame,
            "Calibration in progress",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"Frames: {frames}  Face coverage: {int((face_frames / max(frames, 1)) * 100)}%",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            "Press Q to skip calibration",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (230, 230, 230),
            2,
        )
        cv2.imshow("FocusSight - Calibration", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break

    face_presence_ratio = face_frames / max(frames, 1)
    threshold, alert_seconds, calibrated = derive_calibrated_config(
        raw_scores,
        eye_persistence_scores,
        face_presence_ratio,
        current_threshold,
        current_alert_seconds,
    )

    if calibrated:
        log_info(
            f"Calibration complete -> threshold={threshold:.2f}, alert={alert_seconds:.1f}s",
            quiet,
        )
    else:
        log_info(
            "Calibration skipped or insufficient. "
            "Keeping existing threshold and alert timing.",
            quiet,
        )

    cv2.destroyWindow("FocusSight - Calibration")
    return threshold, alert_seconds, calibrated


def ensure_cascades(face_path, eye_path):
    """Download cascades if missing and return initialized classifiers."""
    for xml in [face_path, eye_path, profile_face_xml]:
        if not os.path.exists(xml):
            print(f"Downloading {xml}...")
            url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{xml}"
            urllib.request.urlretrieve(url, xml)

    face_cascade_local = cv2.CascadeClassifier(face_path)
    eye_cascade_local = cv2.CascadeClassifier(eye_path)
    profile_face_cascade_local = cv2.CascadeClassifier(profile_face_xml)

    if face_cascade_local.empty() or eye_cascade_local.empty() or profile_face_cascade_local.empty():
        raise RuntimeError("Could not load haarcascade xml files.")

    return face_cascade_local, eye_cascade_local, profile_face_cascade_local


def run_focus_tracker(
    camera_index=DEFAULT_CAMERA_INDEX,
    focused_threshold=FOCUSED_THRESHOLD,
    alert_after_seconds=ALERT_AFTER_SECONDS,
    auto_start_logging=False,
    calibrate_seconds=0.0,
    auto_report=False,
    report_dir="reports",
    quiet=False,
    task_tag="",
    context_tag="",
    location_tag="",
    reminder_policy=DEFAULT_REMINDER_POLICY,
    dashboard=False,
    dashboard_interval=5.0,
    streak_goal_seconds=0.0,
    note="",
):
    face_cascade_local, eye_cascade_local, profile_face_cascade_local = ensure_cascades(face_xml, eye_xml)
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open webcam (index {camera_index}).")

    if calibrate_seconds and calibrate_seconds > 0:
        focused_threshold, alert_after_seconds, calibrated = run_calibration_phase(
            cap,
            face_cascade_local,
            eye_cascade_local,
            calibrate_seconds,
            focused_threshold,
            alert_after_seconds,
            quiet,
        )
        if calibrated:
            log_info("Calibration values are now active for the session.", quiet)

    focus_history = deque(maxlen=20)
    tuning_history = deque(maxlen=900)
    face_history = deque(maxlen=8)
    distracted_since = None

    logging_enabled = auto_start_logging
    log_file_handle = None
    log_writer = None
    active_log_path = None
    generated_report_logs = set()
    session_tags = parse_session_tags(task_tag, context_tag, location_tag)
    reminder_policy_key, reminder_settings = resolve_reminder_policy(reminder_policy)

    eye_stable_seconds = 0.0
    last_face_seen_time = time.time()
    last_state = None
    state_flip_timestamps = deque(maxlen=40)
    session_start_time = time.time()
    last_frame_time = None
    last_reminder_at = None
    last_dashboard_at = 0.0
    active_prompt_text = ""
    active_prompt_until = 0.0
    session_focus_scores = []
    session_distracted_count = 0
    session_frame_count = 0

    # Phase 9: personal best streak tracking
    from .summary import compute_streak_records, check_streak_milestone
    _records = compute_streak_records("logs")
    all_time_best_streak = _records["best_streak_seconds"] if _records else 0.0
    current_focused_streak = 0.0
    session_best_streak = 0.0
    last_milestone_reported = ""

    if logging_enabled:
        log_file_handle, log_writer, active_log_path = start_session_logger()
        log_info(f"Logging started: {active_log_path}", quiet)

    try:
        while True:
            now = time.time()
            frame_interval_seconds = 0.0 if last_frame_time is None else now - last_frame_time
            last_frame_time = now
            observed_fps = compute_observed_fps(frame_interval_seconds)
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_blur = cv2.GaussianBlur(gray, (3, 3), 0)
            gray_proc = cv2.equalizeHist(gray_blur)
            brightness_mean = float(gray.mean())

            faces = []
            # Multi-pass face search for robustness to hats/angles.
            for scale_factor, min_neighbors in [(1.2, 5), (1.1, 4)]:
                frontal_faces = face_cascade_local.detectMultiScale(gray_proc, scale_factor, min_neighbors)
                faces.extend(frontal_faces)
                if faces:
                    break

            if not faces:
                profile_faces = profile_face_cascade_local.detectMultiScale(gray_proc, 1.1, 4)
                faces.extend(profile_faces)

                flipped = cv2.flip(gray_proc, 1)
                flipped_profiles = profile_face_cascade_local.detectMultiScale(flipped, 1.1, 4)
                width = gray_proc.shape[1]
                faces.extend([map_flipped_box_to_original(box, width) for box in flipped_profiles])

            face_found = len(faces) > 0
            eye_found = False

            if face_found:
                last_face_seen_time = now
                xf, yf, wf, hf = max(faces, key=lambda f: f[2] * f[3])
                face_history.append((xf, yf, wf, hf))
                smoothed_face = smooth_box(face_history)

                if smoothed_face is not None:
                    xf, yf, wf, hf = smoothed_face
                    cv2.rectangle(frame, (xf, yf), (xf + wf, yf + hf), (255, 0, 0), 2)

                    roi_gray = gray_proc[yf : yf + hf // 2, xf : xf + wf]
                    roi_color = frame[yf : yf + hf // 2, xf : xf + wf]
                    eyes = eye_cascade_local.detectMultiScale(roi_gray, 1.05, 8)

                    if len(eyes) == 0:
                        # Fallback: scan whole face ROI if upper-half misses due to pose/hat occlusion.
                        roi_gray_full = gray_proc[yf : yf + hf, xf : xf + wf]
                        eyes = eye_cascade_local.detectMultiScale(roi_gray_full, 1.05, 10)
                        roi_color = frame[yf : yf + hf, xf : xf + wf]

                    for (ex, ey, ew, eh) in eyes[:2]:
                        cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

                    eye_found = len(eyes) > 0
            else:
                face_history.clear()

            eye_stable_seconds = update_stability_seconds(eye_stable_seconds, eye_found, frame_interval_seconds)

            focus_history.append(1 if face_found and eye_found else 0)
            raw_focus_score = compute_focus_score(focus_history)
            tuning_history.append(raw_focus_score)

            missing_face_seconds = max(0.0, now - last_face_seen_time)
            eye_persistence = clamp(eye_stable_seconds / 0.75, 0.0, 1.0)
            recent_flips = sum(1 for t in state_flip_timestamps if now - t <= 5.0)
            weighted_focus_score, signal_status = compute_signal_quality(
                raw_focus_score,
                eye_persistence,
                missing_face_seconds,
                recent_flips,
                brightness_mean,
                face_found,
                eye_found,
            )

            state, state_color = evaluate_focus_state(face_found, weighted_focus_score, focused_threshold)
            if state != last_state and last_state is not None:
                state_flip_timestamps.append(now)
            last_state = state

            session_frame_count += 1
            session_focus_scores.append(weighted_focus_score)
            if state == "DISTRACTED":
                session_distracted_count += 1

            if state == "FOCUSED":
                distracted_since = None
                active_prompt_text = ""
                active_prompt_until = 0.0
                prev_focused_streak = current_focused_streak
                current_focused_streak += frame_interval_seconds
                if current_focused_streak > session_best_streak:
                    session_best_streak = current_focused_streak
                milestone = check_streak_milestone(
                    current_focused_streak,
                    record_seconds=all_time_best_streak,
                    streak_goal_seconds=streak_goal_seconds,
                    prev_streak_seconds=prev_focused_streak,
                )
                if milestone and milestone != last_milestone_reported:
                    log_info(milestone, quiet)
                    last_milestone_reported = milestone
            else:
                current_focused_streak = 0.0
                if distracted_since is None:
                    distracted_since = now

            if dashboard and (now - last_dashboard_at) >= dashboard_interval:
                elapsed = now - session_start_time
                avg_focus_pct = (
                    (sum(session_focus_scores) / len(session_focus_scores)) * 100.0
                    if session_focus_scores
                    else 0.0
                )
                distracted_pct = (
                    (session_distracted_count / session_frame_count) * 100.0
                    if session_frame_count
                    else 0.0
                )
                streak = max(0.0, now - distracted_since) if distracted_since else 0.0
                dashboard_line = format_live_dashboard(
                    state,
                    avg_focus_pct,
                    distracted_pct,
                    elapsed,
                    streak,
                    signal_status,
                    logging_enabled,
                    reminder_policy_key,
                )
                print(dashboard_line)
                last_dashboard_at = now

            # Phase 13: push live state to the API server (no-op if not running).
            try:
                from .server import update_live_state as _push
                elapsed_now = now - session_start_time
                avg_f = (
                    (sum(session_focus_scores) / len(session_focus_scores)) * 100.0
                    if session_focus_scores else 0.0
                )
                dist_pct = (
                    (session_distracted_count / session_frame_count) * 100.0
                    if session_frame_count else 0.0
                )
                _push(
                    state=state,
                    focus_score=round(weighted_focus_score, 4),
                    signal_status=signal_status,
                    elapsed_seconds=round(elapsed_now, 2),
                    focused_streak_seconds=round(current_focused_streak, 2),
                    distracted_streak_seconds=round(now - distracted_since, 2) if distracted_since else 0.0,
                    avg_focus_pct=round(avg_f, 2),
                    distracted_pct=round(dist_pct, 2),
                    reminder_policy=reminder_policy_key,
                    logging_enabled=logging_enabled,
                    session_log_path=active_log_path,
                )
            except Exception:
                pass

            if logging_enabled and log_writer is not None:
                log_writer.writerow(
                    [
                        datetime.now().isoformat(timespec="seconds"),
                        f"{now - session_start_time:.3f}",
                        f"{frame_interval_seconds:.4f}",
                        f"{observed_fps:.2f}",
                        f"{raw_focus_score:.4f}",
                        f"{weighted_focus_score:.4f}",
                        state,
                        signal_status,
                        int(face_found),
                        int(eye_found),
                        f"{focused_threshold:.3f}",
                        f"{alert_after_seconds:.2f}",
                        session_tags["task_tag"],
                        session_tags["context_tag"],
                        session_tags["location_tag"],
                    ]
                )

            cv2.putText(
                frame,
                f"Focus: {int(weighted_focus_score * 100)}% (raw {int(raw_focus_score * 100)}%)",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"State: {state}",
                (20, 68),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                state_color,
                2,
            )
            cv2.putText(
                frame,
                f"Signal: {signal_status}  FPS: {observed_fps:.1f}",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (220, 220, 220),
                2,
            )
            cv2.putText(
                frame,
                f"Threshold: {focused_threshold:.2f}  Alert: {alert_after_seconds:.1f}s",
                (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (230, 230, 230),
                2,
            )
            log_status = "ON" if logging_enabled else "OFF"
            cv2.putText(
                frame,
                f"Log [{log_status}]  Policy: {reminder_policy_key}  Keys: L toggle log | T tune | Q quit",
                (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (210, 210, 210),
                2,
            )

            if should_emit_reminder(
                now,
                distracted_since,
                last_reminder_at,
                alert_after_seconds,
                reminder_settings["min_interval_seconds"],
            ):
                active_prompt_text = reminder_settings["message"]
                active_prompt_until = max(active_prompt_until, now + 2.0)
                last_reminder_at = now

            if should_suggest_break(now, distracted_since, reminder_settings["break_after_seconds"]):
                active_prompt_text = reminder_settings["break_message"]
                active_prompt_until = max(active_prompt_until, now + 2.0)

            if active_prompt_text and now <= active_prompt_until:
                cv2.putText(
                    frame,
                    active_prompt_text,
                    (20, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("FocusSight - Face/Eye Logic", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("l"):
                if not logging_enabled:
                    log_file_handle, log_writer, active_log_path = start_session_logger()
                    logging_enabled = True
                    log_info(f"Logging started: {active_log_path}", quiet)
                else:
                    logging_enabled = False
                    if log_file_handle is not None:
                        log_file_handle.close()
                    log_file_handle = None
                    log_writer = None
                    log_info("Logging stopped", quiet)
                    if auto_report and active_log_path and active_log_path not in generated_report_logs:
                        generate_ops_artifacts(active_log_path, report_dir=report_dir, quiet=quiet)
                        generated_report_logs.add(active_log_path)

            if key == ord("t"):
                focused_threshold, alert_after_seconds, tuned = tune_parameters_from_scores(
                    tuning_history,
                    focused_threshold,
                    alert_after_seconds,
                )
                if tuned:
                    log_info(
                        f"Tuned from data -> threshold={focused_threshold:.2f}, "
                        f"alert={alert_after_seconds:.1f}s",
                        quiet,
                    )
                else:
                    log_info(
                        f"Need at least {MIN_TUNE_SAMPLES} focus samples before tuning "
                        f"(current={len(tuning_history)}).",
                        quiet,
                    )

            if key == ord("q"):
                break
    finally:
        if log_file_handle is not None:
            log_file_handle.close()
        if auto_report and active_log_path and active_log_path not in generated_report_logs:
            generate_ops_artifacts(active_log_path, report_dir=report_dir, quiet=quiet)
        if note and active_log_path:
            from .summary import save_session_note
            note_file = save_session_note(active_log_path, note)
            log_info(f"Session note saved: {note_file}", quiet)

    cap.release()
    cv2.destroyAllWindows()
    return {
        "camera_index": camera_index,
        "focused_threshold": focused_threshold,
        "alert_after_seconds": alert_after_seconds,
        "reminder_policy": reminder_policy_key,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="FocusSight AI webcam focus tracker")
    parser.add_argument("--camera-index", type=int, default=None, help="Camera index (default from config)")
    parser.add_argument("--threshold", type=float, default=None, help="Focused threshold 0.1-0.95")
    parser.add_argument("--alert-seconds", type=float, default=None, help="Alert delay in seconds 0.5-10")
    parser.add_argument("--profile", type=str, default=None, help="Path to JSON profile to load")
    parser.add_argument("--save-profile", type=str, default=None, help="Path to save JSON profile after run")
    parser.add_argument(
        "--calibrate-seconds",
        type=float,
        default=0.0,
        help="Optional calibration duration before tracking begins",
    )
    parser.add_argument("--autolog", action="store_true", help="Start logging immediately")
    parser.add_argument("--auto-report", action="store_true", help="Generate ops report when logging stops")
    parser.add_argument("--report-dir", type=str, default="reports", help="Directory for generated reports")
    parser.add_argument("--quiet", action="store_true", help="Reduce terminal output noise")
    parser.add_argument(
        "--reminder-policy",
        type=str,
        default=None,
        choices=sorted(REMINDER_POLICIES.keys()),
        help="Coaching reminder profile: gentle, balanced, or strict",
    )
    parser.add_argument("--task-tag", type=str, default="", help="Optional task label (e.g., reading, coding)")
    parser.add_argument("--context-tag", type=str, default="", help="Optional context label (e.g., study, exam_prep)")
    parser.add_argument("--location-tag", type=str, default="", help="Optional location label (e.g., lab, library)")
    parser.add_argument(
        "--auto-update-profile",
        action="store_true",
        help="Update --save-profile thresholds from recent session history before running",
    )
    parser.add_argument("--dashboard", action="store_true", help="Print live session stats to the terminal periodically")
    parser.add_argument(
        "--dashboard-interval",
        type=float,
        default=5.0,
        help="Seconds between live dashboard prints (default: 5.0)",
    )
    parser.add_argument(
        "--streak-goal",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help="Personal focused-streak goal in seconds; notifies when goal is reached",
    )
    parser.add_argument(
        "--note",
        type=str,
        default="",
        metavar="TEXT",
        help="Short annotation saved alongside the session log after the run",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the FocusSight local API server (Phase 13) alongside the tracker on port 8765",
    )
    parser.add_argument(
        "--serve-port",
        type=int,
        default=8765,
        help="Port for the local API server when --serve is used (default: 8765)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.serve:
        from .server import start_server
        start_server(port=args.serve_port)
        log_info(
            f"FocusSight API server started on http://127.0.0.1:{args.serve_port} "
            "(GET /status  GET /report  GET /health  WS /events)",
            False,
        )

    profile_values = load_profile(args.profile)
    cli_values = {
        "camera_index": args.camera_index,
        "focused_threshold": args.threshold,
        "alert_after_seconds": args.alert_seconds,
        "reminder_policy": args.reminder_policy,
    }
    runtime_config = resolve_runtime_config(cli_values, profile_values)

    if args.auto_update_profile and args.save_profile:
        updated, result = auto_update_profile_from_history(args.save_profile)
        if updated:
            log_info(
                f"Auto-updated profile from history: threshold={result['suggested_threshold']:.2f}, "
                f"alert={result['suggested_alert_seconds']:.1f}s "
                f"(based on {result['based_on_sessions']} session(s))",
                args.quiet,
            )
            profile_values = load_profile(args.save_profile)
            runtime_config = resolve_runtime_config(cli_values, profile_values)
        else:
            log_info(f"Auto-update profile skipped: {result}", args.quiet)

    final_config = run_focus_tracker(
        camera_index=runtime_config["camera_index"],
        focused_threshold=runtime_config["focused_threshold"],
        alert_after_seconds=runtime_config["alert_after_seconds"],
        auto_start_logging=args.autolog,
        calibrate_seconds=args.calibrate_seconds,
        auto_report=args.auto_report,
        report_dir=args.report_dir,
        quiet=args.quiet,
        task_tag=args.task_tag,
        context_tag=args.context_tag,
        location_tag=args.location_tag,
        reminder_policy=runtime_config["reminder_policy"],
        dashboard=args.dashboard,
        dashboard_interval=args.dashboard_interval,
        streak_goal_seconds=args.streak_goal,
        note=args.note,
    )

    if args.save_profile:
        save_profile(args.save_profile, final_config)


if __name__ == "__main__":
    main()

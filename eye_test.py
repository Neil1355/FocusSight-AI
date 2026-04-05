import cv2
import csv
import os
import urllib.request
import time
from datetime import datetime
from collections import deque

# 1. Setup both models (Face and Eye)
face_xml = 'haarcascade_frontalface_default.xml'
eye_xml = 'haarcascade_eye.xml'

FOCUSED_THRESHOLD = 0.6
ALERT_AFTER_SECONDS = 2.5
MIN_TUNE_SAMPLES = 60


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


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


def compute_focus_score(history):
    """Compute rolling focus score from a deque of 0/1 samples."""
    return (sum(history) / len(history)) if history else 0.0


def evaluate_focus_state(face_found, focus_score, threshold):
    """Return (state, color) used by overlay logic."""
    if face_found and focus_score >= threshold:
        return ("FOCUSED", (0, 220, 0))
    return ("DISTRACTED", (0, 140, 255))


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
    writer.writerow([
        "timestamp",
        "focus_score",
        "state",
        "face_found",
        "eye_found",
        "focused_threshold",
        "alert_after_seconds",
    ])
    return file_handle, writer, log_path


def ensure_cascades(face_path, eye_path):
    """Download cascades if missing and return initialized classifiers."""
    for xml in [face_path, eye_path]:
        if not os.path.exists(xml):
            print(f"Downloading {xml}...")
            url = f"https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/{xml}"
            urllib.request.urlretrieve(url, xml)

    face_cascade_local = cv2.CascadeClassifier(face_path)
    eye_cascade_local = cv2.CascadeClassifier(eye_path)

    if face_cascade_local.empty() or eye_cascade_local.empty():
        raise RuntimeError("Could not load haarcascade xml files.")

    return face_cascade_local, eye_cascade_local


def run_focus_tracker():
    face_cascade_local, eye_cascade_local = ensure_cascades(face_xml, eye_xml)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise RuntimeError("Could not open webcam (index 0).")

    focus_history = deque(maxlen=20)
    tuning_history = deque(maxlen=900)
    face_history = deque(maxlen=8)
    distracted_since = None
    focused_threshold = FOCUSED_THRESHOLD
    alert_after_seconds = ALERT_AFTER_SECONDS

    logging_enabled = False
    log_file_handle = None
    log_writer = None
    active_log_path = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Find faces and keep only the largest one for stable tracking.
            faces = face_cascade_local.detectMultiScale(gray, 1.3, 5)
            face_found = len(faces) > 0
            eye_found = False

            if face_found:
                xf, yf, wf, hf = max(faces, key=lambda f: f[2] * f[3])
                face_history.append((xf, yf, wf, hf))
                smoothed_face = smooth_box(face_history)

                if smoothed_face is not None:
                    xf, yf, wf, hf = smoothed_face
                    cv2.rectangle(frame, (xf, yf), (xf + wf, yf + hf), (255, 0, 0), 2)

                    # Eyes are usually in the upper half of the face ROI.
                    roi_gray = gray[yf : yf + hf // 2, xf : xf + wf]
                    roi_color = frame[yf : yf + hf // 2, xf : xf + wf]
                    eyes = eye_cascade_local.detectMultiScale(roi_gray, 1.1, 10)

                    for (ex, ey, ew, eh) in eyes[:2]:
                        cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

                    eye_found = len(eyes) > 0
            else:
                face_history.clear()

            # Focus sample: eyes detected while a face is visible.
            focus_history.append(1 if face_found and eye_found else 0)
            focus_score = compute_focus_score(focus_history)
            tuning_history.append(focus_score)

            state, state_color = evaluate_focus_state(face_found, focus_score, focused_threshold)
            if state == "FOCUSED":
                distracted_since = None
            elif distracted_since is None:
                distracted_since = time.time()

            if logging_enabled and log_writer is not None:
                log_writer.writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    f"{focus_score:.4f}",
                    state,
                    int(face_found),
                    int(eye_found),
                    f"{focused_threshold:.3f}",
                    f"{alert_after_seconds:.2f}",
                ])

            cv2.putText(
                frame,
                f"Focus: {int(focus_score * 100)}%",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                f"State: {state}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                state_color,
                2,
            )
            cv2.putText(
                frame,
                f"Threshold: {focused_threshold:.2f}  Alert: {alert_after_seconds:.1f}s",
                (20, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (230, 230, 230),
                2,
            )
            log_status = "ON" if logging_enabled else "OFF"
            cv2.putText(
                frame,
                f"Log [{log_status}]  Keys: L toggle log | T tune | Q quit",
                (20, 135),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (210, 210, 210),
                2,
            )

            if distracted_since is not None and (time.time() - distracted_since) >= alert_after_seconds:
                cv2.putText(
                    frame,
                    "Alert: refocus your eyes",
                    (20, 165),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow('FocusSight - Face/Eye Logic', frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('l'):
                if not logging_enabled:
                    log_file_handle, log_writer, active_log_path = start_session_logger()
                    logging_enabled = True
                    print(f"Logging started: {active_log_path}")
                else:
                    logging_enabled = False
                    if log_file_handle is not None:
                        log_file_handle.close()
                    log_file_handle = None
                    log_writer = None
                    print("Logging stopped")

            if key == ord('t'):
                focused_threshold, alert_after_seconds, tuned = tune_parameters_from_scores(
                    tuning_history,
                    focused_threshold,
                    alert_after_seconds,
                )
                if tuned:
                    print(
                        f"Tuned from data -> threshold={focused_threshold:.2f}, "
                        f"alert={alert_after_seconds:.1f}s"
                    )
                else:
                    print(
                        f"Need at least {MIN_TUNE_SAMPLES} focus samples before tuning "
                        f"(current={len(tuning_history)})."
                    )

            if key == ord('q'):
                break
    finally:
        if log_file_handle is not None:
            log_file_handle.close()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_focus_tracker()
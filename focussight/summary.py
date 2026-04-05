import csv
import glob
import os
from datetime import datetime


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def _parse_focus_score(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_state(value):
    state = (value or "").strip().upper()
    if state in {"FOCUSED", "DISTRACTED"}:
        return state
    return None


def _parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_session_rows(csv_path):
    rows = []
    with open(csv_path, "r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            score = _parse_focus_score(row.get("focus_score"))
            state = _parse_state(row.get("state"))
            elapsed_seconds = _parse_float(row.get("elapsed_seconds"))
            frame_interval_seconds = _parse_float(row.get("frame_interval_seconds"))
            observed_fps = _parse_float(row.get("observed_fps"))
            if score is None or state is None:
                continue
            rows.append(
                {
                    "timestamp": row.get("timestamp", ""),
                    "elapsed_seconds": elapsed_seconds,
                    "frame_interval_seconds": frame_interval_seconds,
                    "observed_fps": observed_fps,
                    "focus_score": score,
                    "state": state,
                    "task_tag": (row.get("task_tag") or "").strip(),
                    "context_tag": (row.get("context_tag") or "").strip(),
                    "location_tag": (row.get("location_tag") or "").strip(),
                }
            )
    return rows


def longest_distracted_streak(rows):
    longest = 0
    current = 0
    for row in rows:
        if row["state"] == "DISTRACTED":
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0
    return longest


def longest_distracted_streak_seconds(rows):
    longest = 0.0
    streak_start_elapsed = None
    previous_state = None

    for row in rows:
        elapsed_seconds = row.get("elapsed_seconds")
        if elapsed_seconds is None:
            previous_state = row["state"]
            continue

        if row["state"] == "DISTRACTED":
            if previous_state != "DISTRACTED" or streak_start_elapsed is None:
                streak_start_elapsed = elapsed_seconds
            current = max(0.0, elapsed_seconds - streak_start_elapsed)
            if current > longest:
                longest = current
        else:
            streak_start_elapsed = None

        previous_state = row["state"]

    return longest


def tune_recommendation(avg_focus):
    threshold = clamp(avg_focus - 0.15, 0.45, 0.80)
    alert_seconds = clamp(1.5 + (1.0 - avg_focus) * 3.0, 1.5, 4.5)
    return threshold, alert_seconds


def summarize_file(csv_path):
    rows = load_session_rows(csv_path)
    if not rows:
        raise ValueError(f"No valid rows found in {csv_path}")

    scores = [row["focus_score"] for row in rows]
    avg_focus = sum(scores) / len(scores)
    distracted = sum(1 for row in rows if row["state"] == "DISTRACTED")
    distracted_pct = (distracted / len(rows)) * 100.0
    streak_frames = longest_distracted_streak(rows)
    streak_seconds = longest_distracted_streak_seconds(rows)
    fps_values = [row["observed_fps"] for row in rows if row.get("observed_fps") is not None]
    avg_fps = (sum(fps_values) / len(fps_values)) if fps_values else 0.0
    rec_threshold, rec_alert_seconds = tune_recommendation(avg_focus)

    return {
        "file": csv_path,
        "rows": len(rows),
        "avg_focus": avg_focus,
        "avg_fps": avg_fps,
        "distracted_pct": distracted_pct,
        "longest_distracted_streak_frames": streak_frames,
        "longest_distracted_streak_seconds": streak_seconds,
        "recommended_threshold": rec_threshold,
        "recommended_alert_seconds": rec_alert_seconds,
    }


def summarize_directory(log_dir="logs"):
    pattern = os.path.join(log_dir, "focus_session_*.csv")
    files = sorted(glob.glob(pattern))
    return [summarize_file(path) for path in files]


def group_rows_by_tag(rows, tag_name):
    grouped = {}
    for row in rows:
        tag_value = (row.get(tag_name) or "unspecified").strip() or "unspecified"
        grouped.setdefault(tag_value, []).append(row)
    return grouped


def summarize_rows(rows):
    if not rows:
        return {
            "rows": 0,
            "avg_focus": 0.0,
            "avg_fps": 0.0,
            "distracted_pct": 0.0,
            "longest_distracted_streak_frames": 0,
            "longest_distracted_streak_seconds": 0.0,
        }

    scores = [row["focus_score"] for row in rows]
    avg_focus = sum(scores) / len(scores)
    distracted = sum(1 for row in rows if row["state"] == "DISTRACTED")
    distracted_pct = (distracted / len(rows)) * 100.0
    fps_values = [row["observed_fps"] for row in rows if row.get("observed_fps") is not None]
    avg_fps = (sum(fps_values) / len(fps_values)) if fps_values else 0.0

    return {
        "rows": len(rows),
        "avg_focus": avg_focus,
        "avg_fps": avg_fps,
        "distracted_pct": distracted_pct,
        "longest_distracted_streak_frames": longest_distracted_streak(rows),
        "longest_distracted_streak_seconds": longest_distracted_streak_seconds(rows),
    }


def summarize_by_tag(rows, tag_name):
    grouped = group_rows_by_tag(rows, tag_name)
    output = {}
    for tag_value, tag_rows in grouped.items():
        output[tag_value] = summarize_rows(tag_rows)
    return output


def summarize_directory_with_tags(log_dir="logs"):
    pattern = os.path.join(log_dir, "focus_session_*.csv")
    files = sorted(glob.glob(pattern))
    all_rows = []
    for file_path in files:
        all_rows.extend(load_session_rows(file_path))

    return {
        "total_sessions": len(files),
        "total_rows": len(all_rows),
        "by_task_tag": summarize_by_tag(all_rows, "task_tag"),
        "by_context_tag": summarize_by_tag(all_rows, "context_tag"),
        "by_location_tag": summarize_by_tag(all_rows, "location_tag"),
    }


def summarize_by_day(rows):
    grouped = {}
    for row in rows:
        ts = _parse_timestamp(row.get("timestamp"))
        day_key = ts.date().isoformat() if ts else "unspecified"
        grouped.setdefault(day_key, []).append(row)
    return {day: summarize_rows(day_rows) for day, day_rows in grouped.items()}


def summarize_by_week(rows):
    grouped = {}
    for row in rows:
        ts = _parse_timestamp(row.get("timestamp"))
        if ts:
            iso_year, iso_week, _ = ts.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
        else:
            week_key = "unspecified"
        grouped.setdefault(week_key, []).append(row)
    return {week: summarize_rows(week_rows) for week, week_rows in grouped.items()}


def summarize_directory_temporal(log_dir="logs"):
    pattern = os.path.join(log_dir, "focus_session_*.csv")
    files = sorted(glob.glob(pattern))
    all_rows = []
    for file_path in files:
        all_rows.extend(load_session_rows(file_path))

    return {
        "total_sessions": len(files),
        "by_day": summarize_by_day(all_rows),
        "by_week": summarize_by_week(all_rows),
    }


def extract_focus_windows(rows, window_seconds=12.0, top_n=3):
    """Find best and worst focus windows using elapsed-time rolling windows."""
    timeline = [row for row in rows if row.get("elapsed_seconds") is not None]
    if len(timeline) < 2:
        return {"best": [], "worst": []}

    windows = []
    n = len(timeline)
    end = 0
    running_sum = 0.0

    for start in range(n):
        start_elapsed = timeline[start]["elapsed_seconds"]
        if end < start:
            end = start
            running_sum = 0.0

        while end < n and (timeline[end]["elapsed_seconds"] - start_elapsed) <= window_seconds:
            running_sum += timeline[end]["focus_score"]
            end += 1

        count = end - start
        if count >= 2:
            avg_focus = running_sum / count
            windows.append(
                {
                    "start_seconds": timeline[start]["elapsed_seconds"],
                    "end_seconds": timeline[end - 1]["elapsed_seconds"],
                    "avg_focus": avg_focus,
                    "samples": count,
                }
            )

        running_sum -= timeline[start]["focus_score"]

    best = sorted(windows, key=lambda w: w["avg_focus"], reverse=True)[:top_n]
    worst = sorted(windows, key=lambda w: w["avg_focus"])[:top_n]
    return {"best": best, "worst": worst}


def print_report(summary):
    print(f"Session file: {summary['file']}")
    print(f"Rows: {summary['rows']}")
    print(f"Average focus: {summary['avg_focus'] * 100:.1f}%")
    if summary.get("avg_fps"):
        print(f"Average FPS: {summary['avg_fps']:.1f}")
    print(f"Distracted frames: {summary['distracted_pct']:.1f}%")
    print(f"Longest distracted streak (frames): {summary['longest_distracted_streak_frames']}")
    if summary.get("longest_distracted_streak_seconds"):
        print(f"Longest distracted streak (seconds): {summary['longest_distracted_streak_seconds']:.2f}")
    print(
        "Recommended tuning: "
        f"threshold={summary['recommended_threshold']:.2f}, "
        f"alert={summary['recommended_alert_seconds']:.1f}s"
    )


def main():
    summaries = summarize_directory("logs")
    if not summaries:
        print("No log files found in logs/. Run eye_test.py and press L to generate logs.")
        return

    latest = max(summaries, key=lambda item: os.path.getmtime(item["file"]))
    print_report(latest)


if __name__ == "__main__":
    main()

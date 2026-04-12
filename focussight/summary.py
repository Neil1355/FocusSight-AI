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


def export_session_history_csv(log_dir="logs", output_path=None):
    """Export a one-row-per-session summary CSV for trend analysis and external tooling."""
    summaries = summarize_directory(log_dir)
    if not summaries:
        return None

    if output_path is None:
        output_path = os.path.join(log_dir, "session_history.csv")

    fieldnames = [
        "file",
        "rows",
        "avg_focus",
        "avg_fps",
        "distracted_pct",
        "longest_distracted_streak_frames",
        "longest_distracted_streak_seconds",
        "recommended_threshold",
        "recommended_alert_seconds",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for summary in summaries:
            writer.writerow(summary)

    return output_path


def compute_session_comparison(summary, log_dir="logs"):
    """Compare a session summary to the historical average of all other sessions.

    Returns a dict with deltas, or None when fewer than two sessions exist.
    """
    all_summaries = summarize_directory(log_dir)
    if len(all_summaries) < 2:
        return None

    session_file = os.path.abspath(summary["file"])
    others = [s for s in all_summaries if os.path.abspath(s["file"]) != session_file]
    if not others:
        return None

    hist_avg_focus = sum(s["avg_focus"] for s in others) / len(others)
    hist_avg_distracted = sum(s["distracted_pct"] for s in others) / len(others)
    hist_avg_streak = sum(s["longest_distracted_streak_seconds"] for s in others) / len(others)

    return {
        "session_avg_focus": summary["avg_focus"],
        "historical_avg_focus": hist_avg_focus,
        "focus_delta": summary["avg_focus"] - hist_avg_focus,
        "session_distracted_pct": summary["distracted_pct"],
        "historical_distracted_pct": hist_avg_distracted,
        "distracted_delta": summary["distracted_pct"] - hist_avg_distracted,
        "session_streak_seconds": summary["longest_distracted_streak_seconds"],
        "historical_streak_seconds": hist_avg_streak,
        "sessions_compared": len(others),
    }


def compute_adaptive_thresholds(log_dir="logs", recent_sessions=5):
    """Derive suggested threshold and alert settings from recent session history.

    Returns a dict with suggested values and context, or None when no history exists.
    """
    summaries = summarize_directory(log_dir)
    if not summaries:
        return None

    recent = summaries[-recent_sessions:]
    avg_focus = sum(s["avg_focus"] for s in recent) / len(recent)
    suggested_threshold, suggested_alert_seconds = tune_recommendation(avg_focus)

    return {
        "suggested_threshold": suggested_threshold,
        "suggested_alert_seconds": suggested_alert_seconds,
        "based_on_sessions": len(recent),
        "avg_focus_across_sessions": avg_focus,
    }


def compute_streak_records(log_dir="logs"):
    """Find the all-time best focused streak (in seconds) across all sessions.

    Returns a dict with ``best_streak_seconds``, ``best_streak_file``, and
    ``session_bests`` (one entry per session that has streak data), or None when
    no session history exists.
    """
    summaries = summarize_directory(log_dir)
    if not summaries:
        return None

    all_time_best_seconds = 0.0
    all_time_best_file = None
    session_bests = []

    pattern = os.path.join(log_dir, "focus_session_*.csv")
    files = sorted(glob.glob(pattern))
    for file_path in files:
        rows = load_session_rows(file_path)
        best = _longest_focused_streak_seconds(rows)
        session_bests.append({"file": file_path, "best_focused_streak_seconds": best})
        if best > all_time_best_seconds:
            all_time_best_seconds = best
            all_time_best_file = file_path

    return {
        "best_streak_seconds": all_time_best_seconds,
        "best_streak_file": all_time_best_file,
        "session_bests": session_bests,
    }


def _longest_focused_streak_seconds(rows):
    """Return the longest continuous FOCUSED run in seconds from a list of row dicts."""
    best = 0.0
    current = 0.0
    for row in rows:
        state = _parse_state(row.get("state") or "")
        interval = _parse_float(row.get("frame_interval_seconds") or "") or 0.0
        if state == "FOCUSED":
            current += interval
            if current > best:
                best = current
        else:
            current = 0.0
    return best


def check_streak_milestone(current_streak_seconds, record_seconds=0.0, streak_goal_seconds=0.0, prev_streak_seconds=0.0):
    """Return an achievement message when the user hits a new record or round milestone.

    Args:
        current_streak_seconds: The current continuous focused streak duration.
        record_seconds: All-time best focused streak (0 = no prior record).
        streak_goal_seconds: User-defined personal target (0 = no goal set).
        prev_streak_seconds: Streak value from the previous check (used to detect
            first-crossing of the goal threshold without relying on a fixed frame interval).

    Returns a non-empty string when noteworthy; empty string otherwise.
    """
    milestones = [30, 60, 120, 300, 600, 900, 1800]
    for m in milestones:
        lower = m - 0.5
        upper = m + 0.5
        if lower <= current_streak_seconds <= upper:
            minutes = m // 60
            label = f"{minutes} min" if minutes >= 1 else f"{m}s"
            return f"🎯 Focus milestone: {label} focused streak!"

    if streak_goal_seconds > 0 and prev_streak_seconds < streak_goal_seconds <= current_streak_seconds:
        goal_min = streak_goal_seconds / 60
        return f"🏆 Streak goal reached: {goal_min:.0f} min focused!"

    if record_seconds > 0 and current_streak_seconds > record_seconds:
        return f"🥇 New personal best focused streak: {current_streak_seconds:.0f}s!"

    return ""


def compute_hour_of_day_distraction(log_dir="logs"):
    """Bucket distracted-frame rates by hour-of-day (0–23) across all session logs.

    Returns a dict mapping hour int → {'total_frames': int, 'distracted_frames': int,
    'distracted_pct': float}, or an empty dict when no data is available.
    """
    buckets = {h: {"total_frames": 0, "distracted_frames": 0} for h in range(24)}
    pattern = os.path.join(log_dir, "focus_session_*.csv")
    files = sorted(glob.glob(pattern))

    for file_path in files:
        rows = load_session_rows(file_path)
        for row in rows:
            ts = _parse_timestamp(row.get("timestamp") or "")
            if ts is None:
                continue
            hour = ts.hour
            buckets[hour]["total_frames"] += 1
            state = _parse_state(row.get("state") or "")
            if state == "DISTRACTED":
                buckets[hour]["distracted_frames"] += 1

    result = {}
    for hour, counts in buckets.items():
        total = counts["total_frames"]
        if total == 0:
            continue
        pct = (counts["distracted_frames"] / total) * 100.0
        result[hour] = {
            "total_frames": total,
            "distracted_frames": counts["distracted_frames"],
            "distracted_pct": pct,
        }
    return result


def find_worst_focus_hours(buckets, top_n=3):
    """Return the top_n hours with the highest distracted percentage from an hour-of-day bucket dict."""
    if not buckets:
        return []
    ranked = sorted(buckets.items(), key=lambda kv: kv[1]["distracted_pct"], reverse=True)
    return [{"hour": h, **v} for h, v in ranked[:top_n]]


def find_best_focus_hours(buckets, top_n=3):
    """Return the top_n hours with the lowest distracted percentage from an hour-of-day bucket dict."""
    if not buckets:
        return []
    ranked = sorted(buckets.items(), key=lambda kv: kv[1]["distracted_pct"])
    return [{"hour": h, **v} for h, v in ranked[:top_n]]


def render_distraction_heatmap(buckets, bar_width=30):
    """Render an ASCII bar chart of distraction % by hour-of-day.

    Returns a multi-line string; empty string when no data.
    """
    if not buckets:
        return ""

    max_pct = max(v["distracted_pct"] for v in buckets.values()) or 1.0
    lines = ["Hour | Distracted % | Chart"]
    lines.append("-" * (bar_width + 30))
    for hour in range(24):
        if hour not in buckets:
            continue
        pct = buckets[hour]["distracted_pct"]
        bar_len = int(round((pct / max_pct) * bar_width))
        bar = "█" * bar_len
        lines.append(f"{hour:02d}:00 | {pct:6.1f}%      | {bar}")
    return "\n".join(lines)


def summarize_today(log_dir="logs"):
    """Aggregate rows from all sessions logged today (local date).

    Returns a dict with aggregate stats and the list of today's session files,
    or None when no sessions were recorded today.
    """
    today = datetime.now().date()
    pattern = os.path.join(log_dir, "focus_session_*.csv")
    files = sorted(glob.glob(pattern))

    today_files = []
    all_rows = []
    for file_path in files:
        rows = load_session_rows(file_path)
        if not rows:
            continue
        ts = _parse_timestamp(rows[0].get("timestamp") or "")
        if ts and ts.date() == today:
            today_files.append(file_path)
            all_rows.extend(rows)

    if not today_files:
        return None

    stats = summarize_rows(all_rows)
    stats["date"] = today.isoformat()
    stats["session_files"] = today_files
    stats["session_count"] = len(today_files)
    return stats


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
    note = load_session_note(summary["file"])
    if note:
        print(f"Session note: {note}")


def note_path_for_session(session_csv_path):
    """Return the canonical .txt note path for a given session CSV path."""
    base = os.path.splitext(session_csv_path)[0]
    return base + "_note.txt"


def save_session_note(session_csv_path, note_text):
    """Persist note_text alongside the session CSV as <session>_note.txt."""
    path = note_path_for_session(session_csv_path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(note_text.strip())
    return path


def load_session_note(session_csv_path):
    """Load and return the note text for a session CSV, or empty string if none exists."""
    path = note_path_for_session(session_csv_path)
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read().strip()



def main():
    summaries = summarize_directory("logs")
    if not summaries:
        print("No log files found in logs/. Run eye_test.py and press L to generate logs.")
        return

    latest = max(summaries, key=lambda item: os.path.getmtime(item["file"]))
    print_report(latest)


if __name__ == "__main__":
    main()

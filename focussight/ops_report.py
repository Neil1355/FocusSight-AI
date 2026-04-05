import argparse
import json
import os
from statistics import mean

from .summary import load_session_rows, summarize_directory, summarize_file


def _clip(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(value, maximum))


def _attention_lapse_events(rows):
    lapses = 0
    previous = None
    for row in rows:
        current = row["state"]
        if previous == "FOCUSED" and current == "DISTRACTED":
            lapses += 1
        previous = current
    return lapses


def _recovery_durations_seconds(rows):
    durations = []
    lapse_start = None

    for row in rows:
        elapsed = row.get("elapsed_seconds")
        if elapsed is None:
            continue

        if row["state"] == "DISTRACTED":
            if lapse_start is None:
                lapse_start = elapsed
        elif lapse_start is not None:
            durations.append(max(0.0, elapsed - lapse_start))
            lapse_start = None

    return durations


def derive_cog_sci_metrics(summary, rows):
    """Derive interpretable cognitive-operations metrics from a session."""
    avg_focus = summary["avg_focus"]
    distracted_ratio = summary["distracted_pct"] / 100.0

    lapse_events = _attention_lapse_events(rows)
    recovery_durations = _recovery_durations_seconds(rows)
    mean_recovery = mean(recovery_durations) if recovery_durations else 0.0

    vigilance_index = _clip((avg_focus * 0.7) + ((1.0 - distracted_ratio) * 0.3))
    stability_index = _clip(1.0 / (1.0 + lapse_events * 0.4 + mean_recovery * 0.2))
    operational_readiness = _clip((vigilance_index * 0.6) + (stability_index * 0.4))

    if operational_readiness >= 0.8:
        interpretation = "High readiness for sustained operational tasks"
    elif operational_readiness >= 0.6:
        interpretation = "Moderate readiness; include short periodic resets"
    else:
        interpretation = "Low readiness; schedule recovery and reduce task load"

    return {
        "vigilance_index": vigilance_index,
        "stability_index": stability_index,
        "operational_readiness": operational_readiness,
        "attention_lapse_events": lapse_events,
        "mean_recovery_seconds": mean_recovery,
        "interpretation": interpretation,
    }


def build_ops_report(csv_path):
    summary = summarize_file(csv_path)
    rows = load_session_rows(csv_path)
    metrics = derive_cog_sci_metrics(summary, rows)

    report = {
        "file": csv_path,
        "summary": summary,
        "cog_sci": metrics,
    }
    return report


def render_ops_report(report):
    summary = report["summary"]
    cog = report["cog_sci"]

    lines = [
        "FocusSight Cognitive Operations Report",
        f"Session: {report['file']}",
        "",
        "Core Session Metrics",
        f"- Average focus: {summary['avg_focus'] * 100:.1f}%",
        f"- Distracted frames: {summary['distracted_pct']:.1f}%",
        f"- Longest distracted streak: {summary['longest_distracted_streak_seconds']:.2f}s",
        f"- Average FPS: {summary['avg_fps']:.1f}",
        "",
        "Cognitive Operations Metrics",
        f"- Vigilance index: {cog['vigilance_index']:.2f}",
        f"- Stability index: {cog['stability_index']:.2f}",
        f"- Operational readiness: {cog['operational_readiness']:.2f}",
        f"- Attention lapse events: {cog['attention_lapse_events']}",
        f"- Mean recovery time: {cog['mean_recovery_seconds']:.2f}s",
        "",
        f"Interpretation: {cog['interpretation']}",
    ]
    return "\n".join(lines)


def save_ops_report_json(report, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)


def latest_session_file(log_dir="logs"):
    summaries = summarize_directory(log_dir)
    if not summaries:
        return None
    latest = max(summaries, key=lambda item: os.path.getmtime(item["file"]))
    return latest["file"]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate cognitive-operations report for a FocusSight session")
    parser.add_argument("--file", type=str, default=None, help="Path to a specific session CSV")
    parser.add_argument("--save", type=str, default=None, help="Optional output path for report text")
    parser.add_argument("--save-json", type=str, default=None, help="Optional output path for report JSON")
    return parser.parse_args()


def main():
    args = parse_args()
    csv_path = args.file or latest_session_file("logs")
    if not csv_path:
        print("No session logs found in logs/. Start tracker logging first.")
        return

    report = build_ops_report(csv_path)
    text = render_ops_report(report)
    print(text)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Saved report: {args.save}")

    if args.save_json:
        save_ops_report_json(report, args.save_json)
        print(f"Saved report JSON: {args.save_json}")


if __name__ == "__main__":
    main()

import argparse
import json
import os
from statistics import mean

from .summary import (
    compute_session_comparison,
    extract_focus_windows,
    load_session_rows,
    summarize_directory,
    summarize_directory_temporal,
    summarize_directory_with_tags,
    summarize_file,
)


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


def _dominant_tag(rows, tag_name):
    counts = {}
    for row in rows:
        value = (row.get(tag_name) or "unspecified").strip() or "unspecified"
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "unspecified"
    return max(counts, key=lambda key: counts[key])


def build_tag_comparison(rows, log_dir="logs"):
    if not rows:
        return {}

    grouped = summarize_directory_with_tags(log_dir)
    task_tag = _dominant_tag(rows, "task_tag")
    context_tag = _dominant_tag(rows, "context_tag")
    location_tag = _dominant_tag(rows, "location_tag")

    return {
        "task_tag": task_tag,
        "context_tag": context_tag,
        "location_tag": location_tag,
        "task_baseline": grouped["by_task_tag"].get(task_tag),
        "context_baseline": grouped["by_context_tag"].get(context_tag),
        "location_baseline": grouped["by_location_tag"].get(location_tag),
    }


def build_recommendations(summary, cog_metrics, windows, temporal_trends):
    recommendations = []

    if cog_metrics["operational_readiness"] < 0.6:
        recommendations.append("Schedule a 5-10 minute reset before the next high-load task.")
    if summary["longest_distracted_streak_seconds"] >= 45:
        recommendations.append("Use shorter work intervals with more frequent check-ins.")
    if summary["longest_distracted_streak_seconds"] >= 75:
        recommendations.append("Take a 2-5 minute break now before continuing deep-focus work.")
    if summary["avg_fps"] and summary["avg_fps"] < 6.0:
        recommendations.append("Camera FPS is low; improve lighting or reduce camera load for cleaner signals.")

    best_windows = windows.get("best", [])
    if best_windows:
        top = best_windows[0]
        recommendations.append(
            f"Strongest focus window appeared around {top['start_seconds']:.0f}-{top['end_seconds']:.0f}s; schedule demanding work near similar conditions."
        )

    by_day = temporal_trends.get("by_day", {})
    if len(by_day) >= 2:
        ordered = sorted(by_day.items(), key=lambda item: item[0])
        first = ordered[0][1]["avg_focus"]
        last = ordered[-1][1]["avg_focus"]
        if last < first - 0.05:
            recommendations.append("Daily focus trend is declining; reduce workload density and add recovery windows.")
        elif last > first + 0.05:
            recommendations.append("Daily focus trend is improving; maintain current routine and calibration cadence.")

    if not recommendations:
        recommendations.append("Current session profile is stable; continue with present workflow and monitoring.")

    return recommendations


def build_session_scorecard(
    summary,
    cog_metrics,
    focus_goal=0.75,
    readiness_goal=0.65,
    distracted_pct_goal=35.0,
    recovery_goal_seconds=8.0,
):
    checks = {
        "focus_goal": {
            "target": focus_goal,
            "actual": summary["avg_focus"],
            "pass": summary["avg_focus"] >= focus_goal,
            "weight": 30,
        },
        "readiness_goal": {
            "target": readiness_goal,
            "actual": cog_metrics["operational_readiness"],
            "pass": cog_metrics["operational_readiness"] >= readiness_goal,
            "weight": 30,
        },
        "distracted_pct_goal": {
            "target": distracted_pct_goal,
            "actual": summary["distracted_pct"],
            "pass": summary["distracted_pct"] <= distracted_pct_goal,
            "weight": 20,
        },
        "recovery_goal": {
            "target": recovery_goal_seconds,
            "actual": cog_metrics["mean_recovery_seconds"],
            "pass": cog_metrics["mean_recovery_seconds"] <= recovery_goal_seconds,
            "weight": 20,
        },
    }

    total_weight = sum(item["weight"] for item in checks.values())
    achieved = sum(item["weight"] for item in checks.values() if item["pass"])
    score = achieved / total_weight if total_weight else 0.0

    if score >= 0.85:
        status = "on-track"
    elif score >= 0.6:
        status = "mixed"
    else:
        status = "needs-adjustment"

    return {
        "score": score,
        "status": status,
        "checks": checks,
    }


def build_ops_report(csv_path):
    summary = summarize_file(csv_path)
    rows = load_session_rows(csv_path)
    metrics = derive_cog_sci_metrics(summary, rows)
    comparison = build_tag_comparison(rows)
    windows = extract_focus_windows(rows)
    temporal_trends = summarize_directory_temporal("logs")
    recommendations = build_recommendations(summary, metrics, windows, temporal_trends)
    scorecard = build_session_scorecard(summary, metrics)
    session_comparison = compute_session_comparison(summary)

    report = {
        "file": csv_path,
        "summary": summary,
        "cog_sci": metrics,
        "comparison": comparison,
        "focus_windows": windows,
        "temporal_trends": temporal_trends,
        "recommendations": recommendations,
        "scorecard": scorecard,
        "session_comparison": session_comparison,
    }
    return report


def render_ops_report(report):
    summary = report["summary"]
    cog = report["cog_sci"]
    comparison = report.get("comparison", {})
    windows = report.get("focus_windows", {"best": [], "worst": []})
    temporal_trends = report.get("temporal_trends", {"by_day": {}, "by_week": {}})
    recommendations = report.get("recommendations", [])
    scorecard = report.get("scorecard", {"score": 0.0, "status": "unknown", "checks": {}})
    session_comparison = report.get("session_comparison")

    def _baseline_line(label, baseline):
        if not baseline:
            return f"- {label}: no baseline yet"
        return (
            f"- {label}: avg_focus={baseline['avg_focus'] * 100:.1f}% "
            f"over {baseline['rows']} samples"
        )

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
        "Tag Baselines",
        f"- Session task tag: {comparison.get('task_tag', 'unspecified')}",
        f"- Session context tag: {comparison.get('context_tag', 'unspecified')}",
        f"- Session location tag: {comparison.get('location_tag', 'unspecified')}",
        _baseline_line("Task baseline", comparison.get("task_baseline")),
        _baseline_line("Context baseline", comparison.get("context_baseline")),
        _baseline_line("Location baseline", comparison.get("location_baseline")),
        "",
        "Focus Windows",
    ]

    best_windows = windows.get("best", [])
    worst_windows = windows.get("worst", [])
    if best_windows:
        top_best = best_windows[0]
        lines.append(
            f"- Best window: {top_best['start_seconds']:.0f}-{top_best['end_seconds']:.0f}s at {top_best['avg_focus'] * 100:.1f}% focus"
        )
    else:
        lines.append("- Best window: insufficient elapsed-time data")

    if worst_windows:
        top_worst = worst_windows[0]
        lines.append(
            f"- Worst window: {top_worst['start_seconds']:.0f}-{top_worst['end_seconds']:.0f}s at {top_worst['avg_focus'] * 100:.1f}% focus"
        )
    else:
        lines.append("- Worst window: insufficient elapsed-time data")

    lines.extend([
        "",
        "Temporal Trends",
        f"- Days tracked: {len(temporal_trends.get('by_day', {}))}",
        f"- Weeks tracked: {len(temporal_trends.get('by_week', {}))}",
    ])

    if session_comparison:
        sign = "+" if session_comparison["focus_delta"] >= 0 else ""
        lines.extend([
            "",
            "Session vs. Historical Baseline",
            f"- Sessions compared: {session_comparison['sessions_compared']}",
            f"- This session focus: {session_comparison['session_avg_focus'] * 100:.1f}%",
            f"- Historical avg focus: {session_comparison['historical_avg_focus'] * 100:.1f}%",
            f"- Focus delta: {sign}{session_comparison['focus_delta'] * 100:.1f}%",
            f"- This session distracted: {session_comparison['session_distracted_pct']:.1f}%",
            f"- Historical avg distracted: {session_comparison['historical_distracted_pct']:.1f}%",
        ])

    lines.extend([
        "",
        "Recommendations",
    ])

    for rec in recommendations:
        lines.append(f"- {rec}")

    lines.extend([
        "",
        "Session Scorecard",
        f"- Goal score: {scorecard.get('score', 0.0) * 100:.1f}%",
        f"- Status: {scorecard.get('status', 'unknown')}",
        f"- Focus goal pass: {scorecard.get('checks', {}).get('focus_goal', {}).get('pass', False)}",
        f"- Readiness goal pass: {scorecard.get('checks', {}).get('readiness_goal', {}).get('pass', False)}",
        f"- Distracted-percent goal pass: {scorecard.get('checks', {}).get('distracted_pct_goal', {}).get('pass', False)}",
        f"- Recovery goal pass: {scorecard.get('checks', {}).get('recovery_goal', {}).get('pass', False)}",
        "",
        f"Interpretation: {cog['interpretation']}",
    ])
    return "\n".join(lines)


def render_ops_report_html(report):
    """Render a self-contained HTML report for sharing or archiving."""
    summary = report["summary"]
    cog = report["cog_sci"]
    recommendations = report.get("recommendations", [])
    scorecard = report.get("scorecard", {"score": 0.0, "status": "unknown", "checks": {}})
    windows = report.get("focus_windows", {"best": [], "worst": []})
    temporal_trends = report.get("temporal_trends", {"by_day": {}, "by_week": {}})
    session_comparison = report.get("session_comparison")

    status_color = {
        "on-track": "#27ae60",
        "mixed": "#e67e22",
        "needs-adjustment": "#e74c3c",
    }.get(scorecard.get("status", ""), "#888")

    rec_items = "\n".join(f"      <li>{rec}</li>" for rec in recommendations)

    best_windows = windows.get("best", [])
    worst_windows = windows.get("worst", [])
    best_line = (
        f"{best_windows[0]['start_seconds']:.0f}–{best_windows[0]['end_seconds']:.0f}s "
        f"({best_windows[0]['avg_focus'] * 100:.1f}%)"
        if best_windows
        else "insufficient data"
    )
    worst_line = (
        f"{worst_windows[0]['start_seconds']:.0f}–{worst_windows[0]['end_seconds']:.0f}s "
        f"({worst_windows[0]['avg_focus'] * 100:.1f}%)"
        if worst_windows
        else "insufficient data"
    )

    comparison_section = ""
    if session_comparison:
        delta = session_comparison["focus_delta"]
        delta_color = "#27ae60" if delta >= 0 else "#e74c3c"
        sign = "+" if delta >= 0 else ""
        comparison_section = (
            "  <section>\n"
            "    <h2>Session vs. Historical Baseline</h2>\n"
            "    <table>\n"
            "      <tr><th>Metric</th><th>This session</th><th>Historical avg</th><th>Delta</th></tr>\n"
            f"      <tr><td>Avg focus</td>"
            f"<td>{session_comparison['session_avg_focus'] * 100:.1f}%</td>"
            f"<td>{session_comparison['historical_avg_focus'] * 100:.1f}%</td>"
            f"<td style=\"color:{delta_color}\">{sign}{delta * 100:.1f}%</td></tr>\n"
            f"      <tr><td>Distracted %</td>"
            f"<td>{session_comparison['session_distracted_pct']:.1f}%</td>"
            f"<td>{session_comparison['historical_distracted_pct']:.1f}%</td>"
            f"<td>{session_comparison['distracted_delta']:+.1f}%</td></tr>\n"
            f"      <tr><td>Longest distracted streak</td>"
            f"<td>{session_comparison['session_streak_seconds']:.2f}s</td>"
            f"<td>{session_comparison['historical_streak_seconds']:.2f}s</td><td>—</td></tr>\n"
            "    </table>\n"
            f"    <p>Compared against {session_comparison['sessions_compared']} prior session(s).</p>\n"
            "  </section>\n"
        )

    scorecard_rows = "".join(
        f"      <tr><td>{k}</td><td>{v.get('target')}</td>"
        f"<td>{v.get('actual', 0.0):.2f}</td>"
        f"<td>{'&#10003;' if v.get('pass') else '&#10007;'}</td></tr>\n"
        for k, v in scorecard.get("checks", {}).items()
    )

    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <title>FocusSight Ops Report</title>\n"
        "  <style>\n"
        "    body { font-family: sans-serif; max-width: 820px; margin: 40px auto; color: #222; }\n"
        "    h1 { color: #1a1a2e; }\n"
        "    h2 { border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 28px; }\n"
        "    table { border-collapse: collapse; width: 100%; margin: 12px 0; }\n"
        "    th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }\n"
        "    th { background: #f0f0f0; }\n"
        "    .badge { display: inline-block; padding: 4px 12px; border-radius: 4px;"
        " color: #fff; font-weight: bold; }\n"
        "    ul { margin: 8px 0; padding-left: 20px; }\n"
        "    li { margin: 4px 0; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>FocusSight Cognitive Operations Report</h1>\n"
        f"  <p><strong>Session:</strong> {report.get('file', 'unknown')}</p>\n"
        "  <section>\n"
        "    <h2>Core Session Metrics</h2>\n"
        "    <table>\n"
        "      <tr><th>Metric</th><th>Value</th></tr>\n"
        f"      <tr><td>Average focus</td><td>{summary['avg_focus'] * 100:.1f}%</td></tr>\n"
        f"      <tr><td>Distracted frames</td><td>{summary['distracted_pct']:.1f}%</td></tr>\n"
        f"      <tr><td>Longest distracted streak</td><td>{summary['longest_distracted_streak_seconds']:.2f}s</td></tr>\n"
        f"      <tr><td>Average FPS</td><td>{summary['avg_fps']:.1f}</td></tr>\n"
        "    </table>\n"
        "  </section>\n"
        "  <section>\n"
        "    <h2>Cognitive Operations Metrics</h2>\n"
        "    <table>\n"
        "      <tr><th>Metric</th><th>Value</th></tr>\n"
        f"      <tr><td>Vigilance index</td><td>{cog['vigilance_index']:.2f}</td></tr>\n"
        f"      <tr><td>Stability index</td><td>{cog['stability_index']:.2f}</td></tr>\n"
        f"      <tr><td>Operational readiness</td><td>{cog['operational_readiness']:.2f}</td></tr>\n"
        f"      <tr><td>Attention lapse events</td><td>{cog['attention_lapse_events']}</td></tr>\n"
        f"      <tr><td>Mean recovery time</td><td>{cog['mean_recovery_seconds']:.2f}s</td></tr>\n"
        "    </table>\n"
        f"    <p><em>{cog['interpretation']}</em></p>\n"
        "  </section>\n"
        "  <section>\n"
        "    <h2>Focus Windows</h2>\n"
        "    <table>\n"
        "      <tr><th>Category</th><th>Window</th></tr>\n"
        f"      <tr><td>Best focus window</td><td>{best_line}</td></tr>\n"
        f"      <tr><td>Worst focus window</td><td>{worst_line}</td></tr>\n"
        "    </table>\n"
        "  </section>\n"
        "  <section>\n"
        "    <h2>Temporal Trends</h2>\n"
        "    <table>\n"
        "      <tr><th>Span</th><th>Count</th></tr>\n"
        f"      <tr><td>Days tracked</td><td>{len(temporal_trends.get('by_day', {}))}</td></tr>\n"
        f"      <tr><td>Weeks tracked</td><td>{len(temporal_trends.get('by_week', {}))}</td></tr>\n"
        "    </table>\n"
        "  </section>\n"
        f"{comparison_section}"
        "  <section>\n"
        "    <h2>Recommendations</h2>\n"
        "    <ul>\n"
        f"{rec_items}\n"
        "    </ul>\n"
        "  </section>\n"
        "  <section>\n"
        "    <h2>Session Scorecard</h2>\n"
        f"    <p>Score: <strong>{scorecard.get('score', 0.0) * 100:.1f}%</strong> &nbsp;\n"
        f"    <span class=\"badge\" style=\"background:{status_color}\">"
        f"{scorecard.get('status', 'unknown').upper()}</span></p>\n"
        "    <table>\n"
        "      <tr><th>Goal</th><th>Target</th><th>Actual</th><th>Pass</th></tr>\n"
        f"{scorecard_rows}"
        "    </table>\n"
        "  </section>\n"
        "</body>\n"
        "</html>"
    )
    return html


def save_ops_report_html(report, path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_ops_report_html(report))


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
    parser.add_argument("--save-html", type=str, default=None, help="Optional output path for HTML report")
    parser.add_argument(
        "--export-history",
        type=str,
        default=None,
        metavar="PATH",
        help="Export a one-row-per-session history CSV to PATH",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.export_history:
        from .summary import export_session_history_csv
        result = export_session_history_csv(output_path=args.export_history)
        if result:
            print(f"Saved session history CSV: {result}")
        else:
            print("No session logs found in logs/. Nothing exported.")
        if not args.file:
            return

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

    if args.save_html:
        save_ops_report_html(report, args.save_html)
        print(f"Saved HTML report: {args.save_html}")


if __name__ == "__main__":
    main()

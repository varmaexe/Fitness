#!/usr/bin/env python3
# analyze.py
"""
AI Personal Trainer — analyze your fitness logs.

Usage:
    python analyze.py push              # today's push session
    python analyze.py legs 2026-04-07  # specific date
    python analyze.py summary          # weekly overview
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import date as date_cls

from trainer.context import build_context, FOLDER_MAP
from trainer.prompt import build_prompt, _format_sleep, _format_weight, _format_calories
from trainer.api import call_claude
from trainer.writer import write_feedback

ROOT = Path(__file__).parent

VALID_TYPES = list(FOLDER_MAP.keys())


def resolve_date(date_arg: str | None) -> str:
    if date_arg:
        return date_arg
    return date_cls.today().strftime("%Y-%m-%d")


def run_analysis(session_type: str, date_str: str) -> None:
    print(f"[Trainer] Analyzing {session_type} session for {date_str}...")

    ctx = build_context(ROOT, session_type, date_str)
    system_prompt, user_message = build_prompt(ctx)

    print("[Trainer] Calling Claude API...")
    feedback = call_claude(system_prompt, user_message)

    folder_name = FOLDER_MAP[session_type]
    session_folder = ROOT / folder_name / date_str
    output_path = write_feedback(session_folder, feedback)

    print(f"[Trainer] Feedback written to: {output_path}")
    print("\n" + "="*60)
    print(feedback[:500] + "..." if len(feedback) > 500 else feedback)


def run_summary(date_str: str) -> None:
    """Weekly overview: collect all sessions from the last 7 days and summarise."""
    from trainer.history import get_recent_sessions, get_recent_single_logs
    from trainer.parsers import parse_workout

    print(f"[Trainer] Building weekly summary up to {date_str}...")

    workout_folders = {
        "push": ROOT / "push",
        "pull": ROOT / "pull",
        "legs-abs": ROOT / "legs-abs",
        "arms": ROOT / "arms",
    }

    sessions_found = []
    for label, folder in workout_folders.items():
        if not folder.exists():
            continue
        recent = get_recent_sessions(folder, "log.txt", "workout", 7, "9999-99-99")
        for s in recent:
            sessions_found.append({"type": label, **s})

    config = json.loads((ROOT / "config.json").read_text())

    sleep_folder = ROOT / "sleep"
    weight_folder = ROOT / "weight"
    calories_folder = ROOT / "calories-count"

    recent_sleep = (get_recent_single_logs(sleep_folder, "log.md", "sleep", 7, "9999-99-99")
                    if sleep_folder.exists() else [])
    recent_weight = (get_recent_single_logs(weight_folder, "log.txt", "weight", 7, "9999-99-99")
                     if weight_folder.exists() else [])
    recent_calories = (get_recent_single_logs(calories_folder, "log.txt", "calories", 3, "9999-99-99")
                       if calories_folder.exists() else [])

    sessions_text = ""
    for s in sorted(sessions_found, key=lambda x: x["date"], reverse=True)[:14]:
        sessions_text += f"\n{s['type'].upper()} — {s['date']}: "
        sessions_text += f"{s['total_volume_kg']}kg total, {s['total_sets']} sets\n"

    phase = config.get("phase", "cut")
    system_prompt = (
        f"You are an experienced personal trainer reviewing {config['name']}'s weekly training summary. "
        f"Current phase: {phase.upper()}. Phase goal: {config.get('phase_notes', '')} "
        f"Provide a structured weekly review covering: training consistency, volume trends, "
        f"recovery quality, nutrition adequacy, and top priorities for next week. Be direct and specific."
    )

    user_message = (
        f"## Weekly Summary — up to {date_str}\n\n"
        f"## Sessions This Week\n{sessions_text or 'No sessions logged.'}\n\n"
        f"## Sleep (last 7 days)\n{_format_sleep(recent_sleep)}\n\n"
        f"## Weight (last 7 days)\n{_format_weight(recent_weight)}\n\n"
        f"## Nutrition (last 3 days)\n{_format_calories(recent_calories)}\n\n"
        f"Provide a full weekly review with top 3 priorities for next week."
    )

    print("[Trainer] Calling Claude API for weekly summary...")
    feedback = call_claude(system_prompt, user_message)

    output_file = ROOT / f"summary-{date_str}.md"
    output_file.write_text(feedback)
    print(f"[Trainer] Weekly summary written to: {output_file}")
    print("\n" + feedback[:500] + "...")


def main():
    parser = argparse.ArgumentParser(description="AI Personal Trainer")
    parser.add_argument("type", choices=VALID_TYPES + ["summary"],
                        help="Session type to analyze")
    parser.add_argument("date", nargs="?", default=None,
                        help="Date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    date_str = resolve_date(args.date)

    if args.type == "summary":
        run_summary(date_str)
    else:
        try:
            run_analysis(args.type, date_str)
        except FileNotFoundError as e:
            print(f"[Error] {e}")
            print(f"Make sure you have a log file at: "
                  f"{FOLDER_MAP[args.type]}/{date_str}/log.txt")
            sys.exit(1)


if __name__ == "__main__":
    main()

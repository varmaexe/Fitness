#!/usr/bin/env python3
# analyze.py
"""
AI Personal Trainer — analyze fitness logs, generate files, or init workspace.

Usage:
    python analyze.py push              # today's push session
    python analyze.py legs 2026-04-07  # specific date
    python analyze.py summary          # weekly overview
    python analyze.py init             # create top-level folders
    python analyze.py gen push         # generate 10 upcoming log files for push
    python analyze.py gen sleep --count 5
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import date as date_cls, timedelta

from trainer.context import build_context, FOLDER_MAP, FLAT_TYPES
from trainer.prompt import build_prompt, _format_sleep, _format_weight, _format_calories
from trainer.api import call_claude
from trainer.writer import write_feedback
from trainer.history import get_recent_sessions, get_recent_single_logs

ROOT = Path(__file__).parent

WORKOUT_TYPES = [t for t in FOLDER_MAP if t not in FLAT_TYPES]
VALID_ANALYSIS_TYPES = list(FOLDER_MAP.keys())


def resolve_date(date_arg: str | None) -> str:
    if date_arg:
        return date_arg
    return date_cls.today().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

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
    print(f"[Trainer] Building weekly summary up to {date_str}...")

    sessions_found = []
    for session_key in WORKOUT_TYPES:
        folder = ROOT / FOLDER_MAP[session_key]
        if not folder.exists():
            continue
        parser_type = "cardio" if session_key == "cardio" else "workout"
        recent = get_recent_sessions(folder, "log.txt", parser_type, 7, "9999-99-99",
                                     up_to_date=date_str)
        for s in recent:
            sessions_found.append({"type": session_key, **s})

    config_file = ROOT / "config.json"
    if not config_file.exists():
        print("[Error] config.json not found. Run: python analyze.py init")
        sys.exit(1)
    config = json.loads(config_file.read_text())

    sleep_folder = ROOT / "sleep"
    weight_folder = ROOT / "weight"
    calories_folder = ROOT / "calories"

    recent_sleep = (get_recent_single_logs(sleep_folder, "", "sleep", 7, "9999-99-99",
                                           up_to_date=date_str, flat=True)
                    if sleep_folder.exists() else [])
    recent_weight = (get_recent_single_logs(weight_folder, "", "weight", 7, "9999-99-99",
                                            up_to_date=date_str, flat=True)
                     if weight_folder.exists() else [])
    recent_calories = (get_recent_single_logs(calories_folder, "", "calories", 3, "9999-99-99",
                                              up_to_date=date_str, flat=True)
                       if calories_folder.exists() else [])

    sessions_text = ""
    for s in sorted(sessions_found, key=lambda x: x["date"], reverse=True)[:14]:
        sessions_text += f"\n{s['type'].upper()} — {s['date']}: "
        if "total_volume_kg" in s:
            sessions_text += f"{s['total_volume_kg']}kg total, {s['total_sets']} sets"
        elif "duration_minutes" in s:
            sessions_text += f"{s['duration_minutes']}min cardio"
        sessions_text += "\n"

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


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def run_init() -> None:
    """Create top-level folder structure for a fresh workspace."""
    for folder_name in FOLDER_MAP.values():
        path = ROOT / folder_name
        path.mkdir(exist_ok=True)
        print(f"  {folder_name}/")
    (ROOT / "progress-pics").mkdir(exist_ok=True)
    print("  progress-pics/")
    print("\nWorkspace ready.")
    print("Workout logs:   push/YYYY-MM-DD/log.txt")
    print("Daily logs:     sleep/YYYY-MM-DD.txt  |  weight/YYYY-MM-DD.txt  |  calories/YYYY-MM-DD.txt")


# ---------------------------------------------------------------------------
# Generate files
# ---------------------------------------------------------------------------

def run_gen(target: str, count: int) -> None:
    """Generate upcoming empty log files starting from today."""
    if target not in FOLDER_MAP:
        print(f"[Error] Unknown target '{target}'. Valid: {', '.join(FOLDER_MAP)}")
        sys.exit(1)
    if not (1 <= count <= 30):
        print("[Error] --count must be between 1 and 30.")
        sys.exit(1)

    folder = ROOT / FOLDER_MAP[target]
    if not folder.exists():
        print(f"[Error] Folder '{folder}' doesn't exist. Run: python analyze.py init")
        sys.exit(1)

    today = date_cls.today()
    created = skipped = 0
    is_flat = target in FLAT_TYPES

    for i in range(count):
        date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        if is_flat:
            path = folder / f"{date_str}.txt"
            if path.exists():
                skipped += 1
            else:
                path.write_text("")
                created += 1
        else:
            date_dir = folder / date_str
            log_file = date_dir / "log.txt"
            if date_dir.exists():
                skipped += 1
            else:
                date_dir.mkdir(parents=True)
                log_file.write_text("")
                created += 1

    print(f"Target: {FOLDER_MAP[target]}/")
    print(f"Created: {created}  Skipped: {skipped} (already existed)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI Personal Trainer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python analyze.py push              # today's push session\n"
            "  python analyze.py pull 2026-04-10   # specific date\n"
            "  python analyze.py summary           # weekly overview\n"
            "  python analyze.py init              # create folder structure\n"
            "  python analyze.py gen push          # generate 10 push log files\n"
            "  python analyze.py gen sleep --count 7\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Analysis subcommands (one per session type + summary)
    for stype in VALID_ANALYSIS_TYPES + ["summary"]:
        sp = subparsers.add_parser(stype, help=f"Analyze {stype} session")
        if stype != "summary":
            sp.add_argument("date", nargs="?", default=None,
                            help="YYYY-MM-DD (default: today)")

    # Init
    subparsers.add_parser("init", help="Create top-level folder structure")

    # Gen
    gen_p = subparsers.add_parser("gen", help="Generate empty log files")
    gen_p.add_argument("target", help=f"Type: {', '.join(FOLDER_MAP)}")
    gen_p.add_argument("--count", type=int, default=10,
                       help="Number of files to create (default: 10)")

    args = parser.parse_args()

    if args.command == "init":
        run_init()
    elif args.command == "gen":
        run_gen(args.target, args.count)
    elif args.command == "summary":
        run_summary(resolve_date(None))
    else:
        date_str = resolve_date(getattr(args, "date", None))
        try:
            run_analysis(args.command, date_str)
        except FileNotFoundError as e:
            print(f"[Error] {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

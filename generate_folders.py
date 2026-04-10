#!/usr/bin/env python3
# generate_folders.py
"""
Generate consecutive date folders (YYYY-MM-DD) with empty log.txt files.

Usage:
    python generate_folders.py push
    python generate_folders.py cardio --count 5
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

from trainer.context import FOLDER_MAP

ROOT = Path(__file__).parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate date folders with empty log.txt files."
    )
    parser.add_argument(
        "target",
        help=f"Workout type. Valid: {', '.join(FOLDER_MAP.keys())}",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of folders to create (1–10, default: 10)",
    )
    return parser.parse_args()


def validate_target(target: str) -> None:
    if target not in FOLDER_MAP:
        valid = ", ".join(FOLDER_MAP.keys())
        print(f"Error: unknown target '{target}'. Valid options: {valid}")
        raise SystemExit(1)


def validate_count(count: int) -> None:
    if not (1 <= count <= 10):
        print(f"Error: --count must be between 1 and 10, got {count}")
        raise SystemExit(1)


def generate_folders(target_dir: Path, start: date, count: int) -> tuple[int, int]:
    """Create date folders with empty log.txt. Returns (created, skipped)."""
    created = 0
    skipped = 0
    for i in range(count):
        folder_name = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        folder = target_dir / folder_name
        if folder.exists():
            skipped += 1
        else:
            folder.mkdir(parents=True)
            (folder / "log.txt").write_text("")
            created += 1
    return created, skipped


def main() -> None:
    args = parse_args()
    validate_target(args.target)
    validate_count(args.count)

    folder_name = FOLDER_MAP[args.target]
    target_dir = ROOT / folder_name

    if not target_dir.exists():
        print(f"Error: target directory '{target_dir}' does not exist.")
        raise SystemExit(1)

    today = date.today()
    created, skipped = generate_folders(target_dir, today, args.count)

    print(f"Target: {folder_name}/")
    print(f"Created: {created} folder(s)")
    print(f"Skipped: {skipped} folder(s) (already existed)")


if __name__ == "__main__":
    main()

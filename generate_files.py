#!/usr/bin/env python3
# generate_files.py — standalone shortcut for generating empty log files
"""
Generate empty log files for a given type, starting from today.

Workout types (push/pull/legs/arms/cardio): creates YYYY-MM-DD/log.txt folders.
Daily log types (sleep/weight/calories):    creates YYYY-MM-DD.txt flat files.

Usage:
    python generate_files.py push
    python generate_files.py sleep --count 7
"""
import argparse
from analyze import run_gen
from trainer.context import FOLDER_MAP


def main():
    parser = argparse.ArgumentParser(description="Generate empty log files starting from today.")
    parser.add_argument("target", help=f"Type: {', '.join(FOLDER_MAP)}")
    parser.add_argument("--count", type=int, default=10,
                        help="Number of files to create (default: 10)")
    args = parser.parse_args()
    run_gen(args.target, args.count)


if __name__ == "__main__":
    main()

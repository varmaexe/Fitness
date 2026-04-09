#!/usr/bin/env python3
# init_folders.py — run once to create the folder structure
from pathlib import Path

FOLDERS = [
    "push", "pull", "legs-abs", "arms",
    "cardio-notes", "calories-count", "weight", "sleep", "progress-pics",
]

root = Path(__file__).parent
for folder in FOLDERS:
    (root / folder).mkdir(exist_ok=True)
    print(f"Created: {folder}/")

print("\nDone. Drop your log files into the date subfolders:")
print("  push/YYYY-MM-DD/log.txt")
print("  sleep/YYYY-MM-DD/log.md")
print("  calories-count/YYYY-MM-DD/log.txt")
print("  weight/YYYY-MM-DD/log.txt")

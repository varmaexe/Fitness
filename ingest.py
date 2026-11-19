#!/usr/bin/env python3
# ingest.py — file a FitNotes workout export into <split>/<YYYY-MM-DD>/log.txt
"""
Take a FitNotes workout share text and save it in the right place automatically.

The date comes from the header ("FitNotes Workout - Tuesday 10th November 2026").
The split (push/pull/legs/arms) is inferred by matching exercise names against
your existing logs. If it can't tell, it asks (or use --split).

Usage:
    python ingest.py                 # read from clipboard (falls back to stdin)
    python ingest.py --stdin         # paste the log, then Ctrl-D
    python ingest.py workout.txt     # read from a file
    python ingest.py --split pull    # force the split
    python ingest.py --watch inbox/  # file every .txt dropped into inbox/ (e.g. Syncthing)
    python ingest.py --no-analyze    # just file it, skip the trainer feedback

After saving, the trainer analysis runs and the feedback is printed in the terminal.
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPLITS = ["push", "pull", "legs", "arms"]

HEADER_RE = re.compile(
    r"FitNotes Workout - \w+ (\d{1,2})(?:st|nd|rd|th)? (\w+) (\d{4})"
)
EXERCISE_RE = re.compile(r"^\*\*\s*(.+?)\s*\*\*\s*$", re.MULTILINE)


class IngestError(Exception):
    pass


def parse_date(text: str) -> str:
    """Return YYYY-MM-DD from the FitNotes header line."""
    m = HEADER_RE.search(text)
    if not m:
        raise IngestError("No 'FitNotes Workout - <day> <date>' header found.")
    day, month, year = m.groups()
    try:
        return datetime.strptime(f"{day} {month} {year}", "%d %B %Y").strftime("%Y-%m-%d")
    except ValueError as e:
        raise IngestError(f"Couldn't parse date from header: {m.group(0)!r}") from e


def normalize_log(text: str) -> str:
    """Restore '** Name **' exercise headers that got stripped in transit.

    Telegram turns FitNotes' '** Name **' into bold formatting, so the message
    text arrives as ' Name '. An exercise header is recognisable regardless: it
    is a plain line directly followed by a '- Total ...' summary line.
    """
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        nxt = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
        bare = line.strip()
        if (bare and not bare.startswith(("-", "**")) and nxt.startswith("- Total ")
                and not HEADER_RE.search(bare)):
            line = f"** {bare} **"
        out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def exercises(text: str) -> list[str]:
    return [e.lower() for e in EXERCISE_RE.findall(text)]


def build_exercise_map(root: Path) -> dict[str, Counter]:
    """exercise name (lowercase) -> Counter of splits it has appeared in."""
    mapping: dict[str, Counter] = {}
    for split in SPLITS:
        for log in (root / split).glob("*/log.txt"):
            for ex in exercises(log.read_text(errors="ignore")):
                mapping.setdefault(ex, Counter())[split] += 1
    return mapping


def guess_split(text: str, mapping: dict[str, Counter]) -> tuple[str | None, Counter]:
    """Return (split, scores). split is None when there's no clear winner."""
    scores: Counter = Counter()
    for ex in exercises(text):
        if ex in mapping:
            total = sum(mapping[ex].values())
            for split, n in mapping[ex].items():
                scores[split] += n / total
    ranked = scores.most_common(2)
    if not ranked:
        return None, scores
    if len(ranked) == 2 and ranked[0][1] == ranked[1][1]:
        return None, scores
    return ranked[0][0], scores


def save(root: Path, text: str, split: str, date: str, force: bool = False) -> Path:
    dest = root / split / date / "log.txt"
    if dest.exists() and dest.read_text().strip():
        if dest.read_text().strip() == text.strip():
            return dest  # identical, nothing to do
        if not force:
            raise IngestError(f"{dest.relative_to(root)} already has a different log (use --force).")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text.strip() + "\n")
    return dest


def ingest(text: str, root: Path = ROOT, split: str | None = None,
           force: bool = False, interactive: bool = True) -> Path:
    text = normalize_log(text)
    date = parse_date(text)
    if split is None:
        split, scores = guess_split(text, build_exercise_map(root))
        if split is None:
            if not interactive:
                raise IngestError(f"Couldn't infer split for {date} (scores: {dict(scores) or 'none'}).")
            split = ask_split(date)
    if split not in SPLITS:
        raise IngestError(f"Unknown split {split!r}; expected one of {SPLITS}.")
    return save(root, text, split, date, force)


def ask_split(date: str) -> str:
    # stdin may already be consumed by the log text, so read from the terminal.
    try:
        tty = open("/dev/tty")
    except OSError:
        raise IngestError("Couldn't infer split and no terminal to ask; use --split.")
    with tty:
        while True:
            print(f"Which split was {date}? [{'/'.join(SPLITS)}]: ", end="", flush=True, file=sys.stderr)
            ans = tty.readline().strip().lower()
            if ans in SPLITS:
                return ans


def read_clipboard() -> str | None:
    for cmd in (["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"],
                ["xsel", "--clipboard", "--output"]):
        if shutil.which(cmd[0]):
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            except subprocess.TimeoutExpired:
                continue
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout
    return None


def analyze_saved(dest: Path, root: Path) -> None:
    """Run the trainer on a freshly saved log; feedback prints to the terminal."""
    import analyze  # lazy: keeps plain filing usable even if the trainer breaks
    split, date = dest.relative_to(root).parts[:2]
    try:
        analyze.run_analysis(split, date)
    except Exception as e:  # filing already succeeded; don't lose that
        print(f"✗ Analysis failed: {e}  (retry: python analyze.py {split} {date})", file=sys.stderr)


def watch(inbox: Path, root: Path, poll: float = 2.0, run_analysis: bool = True) -> None:
    """File every *.txt that appears in inbox; move processed files to inbox/done/."""
    done = inbox / "done"
    done.mkdir(parents=True, exist_ok=True)
    print(f"Watching {inbox} (Ctrl-C to stop)…")
    failed: set[tuple[Path, float]] = set()
    while True:
        for f in sorted(inbox.glob("*.txt")):
            key = (f, f.stat().st_mtime)
            if key in failed:
                continue
            try:
                dest = ingest(f.read_text(errors="ignore"), root, interactive=False)
            except IngestError as e:
                print(f"✗ {f.name}: {e}", file=sys.stderr)
                failed.add(key)
                continue
            f.rename(done / f.name)
            print(f"✓ {f.name} → {dest.relative_to(root)}")
            if run_analysis:
                analyze_saved(dest, root)
        time.sleep(poll)


def main() -> int:
    p = argparse.ArgumentParser(description="File a FitNotes workout log into <split>/<date>/log.txt.")
    p.add_argument("file", nargs="?", help="Read the log from this file instead of the clipboard.")
    p.add_argument("--stdin", action="store_true", help="Read the log from stdin (paste, then Ctrl-D).")
    p.add_argument("--split", choices=SPLITS, help="Force the split instead of inferring it.")
    p.add_argument("--force", action="store_true", help="Overwrite an existing, different log.")
    p.add_argument("--watch", metavar="DIR", help="Watch DIR and file every .txt dropped into it.")
    p.add_argument("--no-analyze", action="store_true", help="Don't run the trainer after saving.")
    args = p.parse_args()

    if args.watch:
        try:
            watch(Path(args.watch).expanduser().resolve(), ROOT, run_analysis=not args.no_analyze)
        except KeyboardInterrupt:
            pass
        return 0

    if args.file:
        text = Path(args.file).read_text()
    elif args.stdin or not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        text = read_clipboard()
        if not text or "FitNotes Workout" not in text:
            print("Clipboard has no FitNotes log. Paste it below, then Ctrl-D:", file=sys.stderr)
            text = sys.stdin.read()

    try:
        dest = ingest(text, ROOT, split=args.split, force=args.force)
    except IngestError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    print(f"✓ Saved → {dest.relative_to(ROOT)}")
    if not args.no_analyze:
        analyze_saved(dest, ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# trainer/tracking.py — bot-side bookkeeping: weight trend, undo snapshots, git auto-commit
import logging
import subprocess
from datetime import date, timedelta
from pathlib import Path

from trainer.parsers import parse_weight

log = logging.getLogger("fitbot")


# ---------------------------------------------------------------------------
# weight trend
# ---------------------------------------------------------------------------

def _weights(root: Path, start: date, end: date) -> list[float]:
    out = []
    d = start
    while d <= end:
        p = root / "weight" / f"{d.isoformat()}.txt"
        if p.exists():
            kg = parse_weight(p.read_text())["weight_kg"]
            if kg > 0:
                out.append(kg)
        d += timedelta(days=1)
    return out


def weight_trend(root: Path, day: str) -> str | None:
    """'7-day avg 80.1 kg (−0.3 vs prior week)' — None when there's nothing to average."""
    end = date.fromisoformat(day)
    this_week = _weights(root, end - timedelta(days=6), end)
    if len(this_week) < 2:
        return None
    avg = sum(this_week) / len(this_week)
    text = f"7-day avg {avg:.1f} kg ({len(this_week)} weigh-ins)"
    prior = _weights(root, end - timedelta(days=13), end - timedelta(days=7))
    if len(prior) >= 2:
        diff = avg - sum(prior) / len(prior)
        sign = "+" if diff >= 0 else "−"
        text = f"7-day avg {avg:.1f} kg ({sign}{abs(diff):.1f} vs prior week)"
    return text


# ---------------------------------------------------------------------------
# undo
# ---------------------------------------------------------------------------

def snapshot(root: Path, paths: list[Path]) -> dict[str, str | None]:
    """Current content of each path (None = didn't exist), keyed by path relative to root."""
    return {str(p.relative_to(root)): (p.read_text() if p.exists() else None) for p in paths}


def restore(root: Path, snap: dict[str, str | None]) -> list[Path]:
    """Put files back as they were in `snap`. Returns the touched paths."""
    touched = []
    for rel, content in snap.items():
        p = root / rel
        if content is None:
            if p.exists():
                p.unlink()
                if p.parent != root and not any(p.parent.iterdir()):
                    p.parent.rmdir()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        touched.append(p)
    return touched


# ---------------------------------------------------------------------------
# git
# ---------------------------------------------------------------------------

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60)


def git_commit(root: Path, paths: list[Path], message: str, push: bool = False) -> bool:
    """Commit only `paths` (never anything else that's staged or modified). Best effort:
    failures are logged, not raised. Returns True if a commit was made."""
    try:
        rels = [str(p.relative_to(root)) for p in paths]
        # Skip paths git can't see: deleted files that were never committed.
        rels = [r for r in rels if (root / r).exists() or _git(root, "ls-files", "--", r).stdout.strip()]
        if not rels:
            return False
        r = _git(root, "add", "-A", "--", *rels)
        if r.returncode:
            log.warning("git add failed: %s", r.stderr.strip())
            return False
        if not _git(root, "diff", "--cached", "--quiet", "--", *rels).returncode:
            return False  # nothing changed
        r = _git(root, "commit", "-q", "-m", message, "--", *rels)
        if r.returncode:
            log.warning("git commit failed: %s", r.stderr.strip())
            return False
        if push:
            r = _git(root, "push", "-q")
            if r.returncode:
                log.warning("git push failed: %s", r.stderr.strip())
        return True
    except Exception:
        log.exception("git commit failed")
        return False

# trainer/display.py
"""Render feedback markdown in the terminal (pretty with `rich`, plain otherwise)."""
import re
from pathlib import Path

_GENERATED_RE = re.compile(r"^<!--.*?-->\s*", re.DOTALL)


def show_markdown(text: str, title: str | None = None) -> None:
    text = _GENERATED_RE.sub("", text, count=1)
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.rule import Rule
    except ImportError:
        bar = "=" * 60
        print(f"\n{bar}\n{title}\n{bar}" if title else f"\n{bar}")
        print(text)
        return
    console = Console()
    console.print()
    console.print(Rule(title or "", style="cyan"))
    console.print(Markdown(text))
    console.print(Rule(style="cyan"))


def find_feedback(root: Path, folders: list[str], session_type: str | None = None,
                  date: str | None = None) -> Path | None:
    """Locate a feedback.md. With no filters, return the most recently written one."""
    if session_type and date:
        path = root / session_type / date / "feedback.md"
        return path if path.exists() else None
    candidates = [
        p for f in ([session_type] if session_type else folders)
        for p in (root / f).glob("*/feedback.md")
        if not date or p.parent.name == date
    ]
    candidates += [] if session_type else [
        p for p in root.glob("summary-*.md") if not date or p.stem == f"summary-{date}"
    ]
    return max(candidates, key=lambda p: p.stat().st_mtime, default=None)

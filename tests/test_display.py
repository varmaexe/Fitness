# tests/test_display.py
import os

from trainer.display import find_feedback, show_markdown


def _fb(root, split, date, mtime):
    p = root / split / date / "feedback.md"
    p.parent.mkdir(parents=True)
    p.write_text(f"{split} {date}")
    os.utime(p, (mtime, mtime))
    return p


def test_find_feedback(tmp_path):
    old = _fb(tmp_path, "push", "2026-11-01", 1000)
    new = _fb(tmp_path, "arms", "2026-11-11", 2000)
    folders = ["push", "pull", "legs", "arms"]
    assert find_feedback(tmp_path, folders) == new
    assert find_feedback(tmp_path, folders, "push") == old
    assert find_feedback(tmp_path, folders, date="2026-11-01") == old
    assert find_feedback(tmp_path, folders, "push", "2026-11-01") == old
    assert find_feedback(tmp_path, folders, "legs") is None


def test_show_markdown_strips_generated_header(capsys):
    show_markdown("<!-- Generated: 2026-11-11 10:00 -->\n\n# Hello")
    out = capsys.readouterr().out
    assert "Hello" in out and "Generated" not in out

import pytest
from pathlib import Path
from trainer.writer import write_feedback


def test_write_feedback_creates_file(tmp_path):
    folder = tmp_path / "push" / "2026-04-10"
    folder.mkdir(parents=True)
    write_feedback(folder, "# Feedback\n\nGreat session.")
    feedback_file = folder / "feedback.md"
    assert feedback_file.exists()
    assert "Great session." in feedback_file.read_text()


def test_write_feedback_overwrites_existing(tmp_path):
    folder = tmp_path / "push" / "2026-04-10"
    folder.mkdir(parents=True)
    (folder / "feedback.md").write_text("old content")
    write_feedback(folder, "new content")
    assert "new content" in (folder / "feedback.md").read_text()
    assert "old" not in (folder / "feedback.md").read_text()


def test_write_feedback_returns_path(tmp_path):
    folder = tmp_path / "push" / "2026-04-10"
    folder.mkdir(parents=True)
    result = write_feedback(folder, "some feedback")
    assert result == folder / "feedback.md"

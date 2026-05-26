# tests/test_generate_files.py
import pytest
from pathlib import Path
from datetime import date
from unittest.mock import patch

from analyze import run_gen


def test_workout_type_creates_folder_and_log(tmp_path, monkeypatch):
    """Workout types (push/pull/legs/arms) create YYYY-MM-DD/log.txt."""
    push_dir = tmp_path / "push"
    push_dir.mkdir()
    monkeypatch.setattr("analyze.ROOT", tmp_path)

    today = date(2026, 4, 10)
    with patch("analyze.date_cls") as mock_date:
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        run_gen("push", 3)

    assert (push_dir / "2026-04-10" / "log.txt").exists()
    assert (push_dir / "2026-04-11" / "log.txt").exists()
    assert (push_dir / "2026-04-12" / "log.txt").exists()
    assert (push_dir / "2026-04-10" / "log.txt").read_text() == ""


def test_flat_type_creates_txt_files(tmp_path, monkeypatch):
    """Flat types (sleep/weight/calories) create YYYY-MM-DD.txt directly."""
    sleep_dir = tmp_path / "sleep"
    sleep_dir.mkdir()
    monkeypatch.setattr("analyze.ROOT", tmp_path)

    today = date(2026, 4, 10)
    with patch("analyze.date_cls") as mock_date:
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        run_gen("sleep", 3)

    assert (sleep_dir / "2026-04-10.txt").exists()
    assert (sleep_dir / "2026-04-11.txt").exists()
    assert (sleep_dir / "2026-04-12.txt").exists()
    assert (sleep_dir / "2026-04-10.txt").read_text() == ""
    # No subdirectories created
    assert not any(p.is_dir() for p in sleep_dir.iterdir())


def test_skips_existing_workout(tmp_path, monkeypatch):
    push_dir = tmp_path / "push"
    push_dir.mkdir()
    existing = push_dir / "2026-04-10"
    existing.mkdir()
    (existing / "log.txt").write_text("already here")
    monkeypatch.setattr("analyze.ROOT", tmp_path)

    today = date(2026, 4, 10)
    with patch("analyze.date_cls") as mock_date:
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        run_gen("push", 2)

    assert (existing / "log.txt").read_text() == "already here"


def test_skips_existing_flat(tmp_path, monkeypatch):
    sleep_dir = tmp_path / "sleep"
    sleep_dir.mkdir()
    (sleep_dir / "2026-04-10.txt").write_text("had 7h sleep")
    monkeypatch.setattr("analyze.ROOT", tmp_path)

    today = date(2026, 4, 10)
    with patch("analyze.date_cls") as mock_date:
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        run_gen("sleep", 2)

    assert (sleep_dir / "2026-04-10.txt").read_text() == "had 7h sleep"


def test_invalid_target_exits(tmp_path, monkeypatch):
    monkeypatch.setattr("analyze.ROOT", tmp_path)
    with pytest.raises(SystemExit):
        run_gen("deadlift", 5)


def test_invalid_count_exits(tmp_path, monkeypatch):
    monkeypatch.setattr("analyze.ROOT", tmp_path)
    with pytest.raises(SystemExit):
        run_gen("push", 0)

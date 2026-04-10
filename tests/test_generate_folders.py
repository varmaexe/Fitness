# tests/test_generate_folders.py
import pytest
import sys
from unittest.mock import patch
from pathlib import Path
from datetime import date


def test_imports():
    """Script can be imported without side effects."""
    import generate_folders  # noqa


def test_parse_args_target_only():
    with patch("sys.argv", ["generate_folders.py", "push"]):
        import generate_folders
        args = generate_folders.parse_args()
    assert args.target == "push"
    assert args.count == 10


def test_parse_args_with_count():
    with patch("sys.argv", ["generate_folders.py", "cardio", "--count", "5"]):
        import generate_folders
        args = generate_folders.parse_args()
    assert args.target == "cardio"
    assert args.count == 5


def test_validate_target_valid():
    from generate_folders import validate_target
    validate_target("push")
    validate_target("cardio")
    validate_target("sleep")


def test_validate_target_invalid():
    from generate_folders import validate_target
    with pytest.raises(SystemExit) as exc_info:
        validate_target("deadlift")
    assert exc_info.value.code != 0


def test_validate_count_valid():
    from generate_folders import validate_count
    validate_count(1)
    validate_count(10)


def test_validate_count_invalid_zero():
    from generate_folders import validate_count
    with pytest.raises(SystemExit):
        validate_count(0)


def test_validate_count_invalid_over():
    from generate_folders import validate_count
    with pytest.raises(SystemExit):
        validate_count(11)


def test_generate_folders_creates_dirs(tmp_path):
    from generate_folders import generate_folders
    target_dir = tmp_path / "push"
    target_dir.mkdir()

    today = date(2026, 4, 10)
    created, skipped = generate_folders(target_dir, today, count=3)

    assert created == 3
    assert skipped == 0
    assert (target_dir / "2026-04-10" / "log.txt").exists()
    assert (target_dir / "2026-04-11" / "log.txt").exists()
    assert (target_dir / "2026-04-12" / "log.txt").exists()


def test_generate_folders_skips_existing(tmp_path):
    from generate_folders import generate_folders
    target_dir = tmp_path / "push"
    target_dir.mkdir()
    existing = target_dir / "2026-04-10"
    existing.mkdir()
    (existing / "log.txt").write_text("already here")

    today = date(2026, 4, 10)
    created, skipped = generate_folders(target_dir, today, count=2)

    assert created == 1
    assert skipped == 1
    assert (existing / "log.txt").read_text() == "already here"


def test_generate_folders_log_txt_is_empty(tmp_path):
    from generate_folders import generate_folders
    target_dir = tmp_path / "sleep"
    target_dir.mkdir()

    today = date(2026, 4, 10)
    generate_folders(target_dir, today, count=1)

    log_file = target_dir / "2026-04-10" / "log.txt"
    assert log_file.read_text() == ""


def test_main_end_to_end(tmp_path, monkeypatch, capsys):
    from generate_folders import main

    push_dir = tmp_path / "push"
    push_dir.mkdir()
    monkeypatch.setattr("generate_folders.ROOT", tmp_path)

    with patch("sys.argv", ["generate_folders.py", "push", "--count", "3"]):
        main()

    captured = capsys.readouterr()
    assert "Created: 3" in captured.out
    assert "Skipped: 0" in captured.out
    date_folders = list(push_dir.iterdir())
    assert len(date_folders) == 3
    assert all((f / "log.txt").exists() for f in date_folders)


def test_main_invalid_target_exits(tmp_path, monkeypatch):
    from generate_folders import main
    monkeypatch.setattr("generate_folders.ROOT", tmp_path)

    with patch("sys.argv", ["generate_folders.py", "invalid_type"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
    assert exc_info.value.code != 0

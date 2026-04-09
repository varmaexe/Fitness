# tests/test_history.py
import pytest
import tempfile
from pathlib import Path
from trainer.history import get_recent_sessions, get_recent_single_logs

WORKOUT_CONTENT = """FitNotes Workout - Monday 6th April 2026
Total Volume: 3,000 Kg
Total Sets: 15
Total Reps: 90

** Bench Press **
- Total Volume: 3,000 Kg
- Total Sets: 15
- Total Reps: 90
- 80.0 kgs x 6 reps
"""

WEIGHT_CONTENT_1 = "79.5kg\nNotes: Morning\n"
WEIGHT_CONTENT_2 = "79.8kg\nNotes: Morning\n"
WEIGHT_CONTENT_3 = "80.0kg\nNotes: Morning\n"


@pytest.fixture
def workout_folder(tmp_path):
    """Create a temporary push folder with 3 past sessions."""
    for date, content in [
        ("2026-04-06", WORKOUT_CONTENT.replace("Monday 6th", "Monday 6th")),
        ("2026-04-03", WORKOUT_CONTENT.replace("Monday 6th", "Friday 3rd")),
        ("2026-03-31", WORKOUT_CONTENT.replace("Monday 6th", "Tuesday 31st")),
    ]:
        d = tmp_path / date
        d.mkdir()
        (d / "log.txt").write_text(content)
    return tmp_path


@pytest.fixture
def weight_folder(tmp_path):
    for date, content in [
        ("2026-04-09", WEIGHT_CONTENT_1),
        ("2026-04-08", WEIGHT_CONTENT_2),
        ("2026-04-07", WEIGHT_CONTENT_3),
    ]:
        d = tmp_path / date
        d.mkdir()
        (d / "log.txt").write_text(content)
    return tmp_path


def test_get_recent_sessions_count(workout_folder):
    sessions = get_recent_sessions(workout_folder, log_filename="log.txt",
                                   parser_type="workout", n=5, exclude_date="2026-04-10")
    assert len(sessions) == 3


def test_get_recent_sessions_sorted_newest_first(workout_folder):
    sessions = get_recent_sessions(workout_folder, log_filename="log.txt",
                                   parser_type="workout", n=5, exclude_date="2026-04-10")
    assert sessions[0]["date"] == "2026-04-06"
    assert sessions[1]["date"] == "2026-04-03"
    assert sessions[2]["date"] == "2026-03-31"


def test_get_recent_sessions_respects_n(workout_folder):
    sessions = get_recent_sessions(workout_folder, log_filename="log.txt",
                                   parser_type="workout", n=2, exclude_date="2026-04-10")
    assert len(sessions) == 2
    assert sessions[0]["date"] == "2026-04-06"


def test_get_recent_sessions_excludes_today(workout_folder):
    # Add today's folder
    today_dir = workout_folder / "2026-04-10"
    today_dir.mkdir()
    (today_dir / "log.txt").write_text(WORKOUT_CONTENT)

    sessions = get_recent_sessions(workout_folder, log_filename="log.txt",
                                   parser_type="workout", n=5, exclude_date="2026-04-10")
    dates = [s["date"] for s in sessions]
    assert "2026-04-10" not in dates


def test_get_recent_single_logs(weight_folder):
    logs = get_recent_single_logs(weight_folder, log_filename="log.txt",
                                  parser_type="weight", n=7, exclude_date="2026-04-10")
    assert len(logs) == 3
    assert logs[0]["date"] == "2026-04-09"
    assert logs[0]["weight_kg"] == 79.5

# tests/test_context.py
import pytest
import json
from pathlib import Path
from trainer.context import build_context

WORKOUT_LOG = """FitNotes Workout - Thursday 9th April 2026
Total Volume: 3,055 Kg
Total Sets: 19
Total Reps: 110

** Bench Press **
- Total Volume: 3,055 Kg
- Total Sets: 19
- Total Reps: 110
- 80.0 kgs x 6 reps
"""

CONFIG = {
    "name": "Sai", "age": 25, "sex": "male",
    "weight_kg": 80, "body_fat_pct": 20, "experience_years": 4,
    "phase": "cut",
    "phase_notes": "Mini-cut.",
    "training_days_target": 7,
    "split": ["push", "pull", "legs", "arms"],
    "maintenance_calories": 2600,
    "goal_calories": 2200,
    "goal_protein_g": 160,
}


@pytest.fixture
def fitness_root(tmp_path):
    # Config
    (tmp_path / "config.json").write_text(json.dumps(CONFIG))

    # Today's push log
    push_today = tmp_path / "push" / "2026-04-10"
    push_today.mkdir(parents=True)
    (push_today / "log.txt").write_text(WORKOUT_LOG)

    # One past push session
    push_past = tmp_path / "push" / "2026-04-06"
    push_past.mkdir(parents=True)
    (push_past / "log.txt").write_text(WORKOUT_LOG.replace("9th April", "6th April"))

    # Flat daily log files
    (tmp_path / "sleep").mkdir()
    (tmp_path / "sleep" / "2026-04-10.txt").write_text("Sleep Time: 7h 0m\nPhysical Recovery: 80%\n")
    (tmp_path / "weight").mkdir()
    (tmp_path / "weight" / "2026-04-10.txt").write_text("79.0kg\nNotes: Morning\n")
    (tmp_path / "calories").mkdir()
    (tmp_path / "calories" / "2026-04-10.txt").write_text("Calories: 2200\nProtein: 160\n")

    return tmp_path


def test_build_context_has_config(fitness_root):
    ctx = build_context(fitness_root, "push", "2026-04-10")
    assert ctx["config"]["name"] == "Sai"
    assert ctx["config"]["phase"] == "cut"


def test_build_context_has_today(fitness_root):
    ctx = build_context(fitness_root, "push", "2026-04-10")
    assert ctx["today"] is not None
    assert ctx["today"]["total_sets"] == 19


def test_build_context_has_history(fitness_root):
    ctx = build_context(fitness_root, "push", "2026-04-10")
    assert len(ctx["history"]) == 1
    assert ctx["history"][0]["date"] == "2026-04-06"


def test_build_context_missing_today_raises(fitness_root):
    with pytest.raises(FileNotFoundError):
        build_context(fitness_root, "push", "2026-04-11")


def test_build_context_sleep_weight_calories_present(fitness_root):
    ctx = build_context(fitness_root, "push", "2026-04-10")
    assert len(ctx["recent_sleep"]) == 1
    assert ctx["recent_sleep"][0]["sleep_time_minutes"] == 420
    assert len(ctx["recent_weight"]) == 1
    assert ctx["recent_weight"][0]["weight_kg"] == 79.0
    assert len(ctx["recent_calories"]) == 1
    assert ctx["recent_calories"][0]["calories"] == 2200


def test_build_context_sleep_weight_calories_empty_when_missing(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps(CONFIG))
    push_today = tmp_path / "push" / "2026-04-10"
    push_today.mkdir(parents=True)
    (push_today / "log.txt").write_text(WORKOUT_LOG)
    ctx = build_context(tmp_path, "push", "2026-04-10")
    assert ctx["recent_sleep"] == []
    assert ctx["recent_weight"] == []
    assert ctx["recent_calories"] == []

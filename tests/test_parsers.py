# tests/test_parsers.py
import pytest
from trainer.parsers import parse_workout, parse_calories, parse_weight, parse_sleep, parse_cardio

WORKOUT_LOG = """FitNotes Workout - Thursday 9th April 2026
Total Volume: 3,055 Kg
Total Sets: 19
Total Reps: 110

** Incline Dumbbell Bench Press **
- Total Volume: 790 Kg
- Total Sets: 5
- Total Reps: 28
- 25.0 kgs x 7 reps
- 27.5 kgs x 6 reps
- 30.0 kgs x 6 reps
- 30.0 kgs x 3 reps
- 30.0 kgs x 6 reps [Okayish form. Good contraction.]

** Weighted Dips **
- Total Volume: 180 Kg
- Total Sets: 4
- Total Reps: 24
- 10.0 kgs x 6 reps [Bodyweight 80kg]
- 10.0 kgs x 6 reps [Bodyweight 80kg]
- 10.0 kgs x 6 reps
- 6 reps [Only bodyweight]
"""


def test_parse_workout_header():
    result = parse_workout(WORKOUT_LOG)
    assert result["date_label"] == "Thursday 9th April 2026"
    assert result["total_volume_kg"] == 3055
    assert result["total_sets"] == 19
    assert result["total_reps"] == 110


def test_parse_workout_exercise_count():
    result = parse_workout(WORKOUT_LOG)
    assert len(result["exercises"]) == 2


def test_parse_workout_exercise_name():
    result = parse_workout(WORKOUT_LOG)
    assert result["exercises"][0]["name"] == "Incline Dumbbell Bench Press"


def test_parse_workout_sets_with_weight():
    result = parse_workout(WORKOUT_LOG)
    sets = result["exercises"][0]["sets"]
    assert sets[0] == {"weight_kg": 25.0, "reps": 7, "notes": ""}
    assert sets[4] == {"weight_kg": 30.0, "reps": 6, "notes": "Okayish form. Good contraction."}


def test_parse_workout_bodyweight_set():
    result = parse_workout(WORKOUT_LOG)
    dips_sets = result["exercises"][1]["sets"]
    # "- 6 reps [Only bodyweight]" — no weight prefix
    assert dips_sets[3] == {"weight_kg": 0.0, "reps": 6, "notes": "Only bodyweight"}


def test_parse_workout_set_with_note_no_weight():
    result = parse_workout(WORKOUT_LOG)
    dips_sets = result["exercises"][1]["sets"]
    # "- 10.0 kgs x 6 reps [Bodyweight 80kg]"
    assert dips_sets[0] == {"weight_kg": 10.0, "reps": 6, "notes": "Bodyweight 80kg"}


def test_parse_workout_empty_input():
    result = parse_workout("")
    assert result["date_label"] == ""
    assert result["total_volume_kg"] == 0
    assert result["exercises"] == []


def test_parse_workout_per_exercise_totals():
    result = parse_workout(WORKOUT_LOG)
    incline = result["exercises"][0]
    assert incline["total_volume_kg"] == 790
    assert incline["total_sets"] == 5
    assert incline["total_reps"] == 28

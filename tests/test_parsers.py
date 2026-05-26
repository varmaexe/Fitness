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


CALORIES_LOG = """Calories: 2200
Protein: 160g
Carbs: 220g
Fats: 65g
Fiber: 28g
Notes: Ate late, skipped breakfast
"""

WEIGHT_LOG = """79.85kg
Notes: Morning, after bathroom
"""

SLEEP_LOG = """Sleep Time: 6h 50m
Physical Recovery: 64%
Restfulness: 87%
Mental Recovery: 84%
Sleep Cycles: 4
Awake: 57m (13%)
REM: 1h 23m (20%)
Light: 3h 58m (60%)
Deep: 32m (7%)
Notes: Woke up twice, felt groggy
"""

CARDIO_LOG = """Type: Treadmill
Duration: 30min
Intensity: Moderate
Heart Rate: ~145bpm
Notes: Felt easy, could push harder
"""


def test_parse_calories():
    result = parse_calories(CALORIES_LOG)
    assert result["calories"] == 2200
    assert result["protein_g"] == 160
    assert result["carbs_g"] == 220
    assert result["fats_g"] == 65
    assert result["fiber_g"] == 28
    assert result["notes"] == "Ate late, skipped breakfast"


def test_parse_weight():
    result = parse_weight(WEIGHT_LOG)
    assert result["weight_kg"] == 79.85
    assert result["notes"] == "Morning, after bathroom"


def test_parse_sleep_top_level():
    result = parse_sleep(SLEEP_LOG)
    assert result["sleep_time_minutes"] == 410  # 6h50m
    assert result["physical_recovery_pct"] == 64
    assert result["restfulness_pct"] == 87
    assert result["mental_recovery_pct"] == 84
    assert result["sleep_cycles"] == 4
    assert result["notes"] == "Woke up twice, felt groggy"


def test_parse_sleep_stages():
    result = parse_sleep(SLEEP_LOG)
    assert result["stages"]["awake_minutes"] == 57
    assert result["stages"]["awake_pct"] == 13
    assert result["stages"]["rem_minutes"] == 83   # 1h 23m
    assert result["stages"]["rem_pct"] == 20
    assert result["stages"]["light_minutes"] == 238  # 3h 58m
    assert result["stages"]["light_pct"] == 60
    assert result["stages"]["deep_minutes"] == 32
    assert result["stages"]["deep_pct"] == 7


def test_parse_cardio():
    result = parse_cardio(CARDIO_LOG)
    assert result["type"] == "Treadmill"
    assert result["duration_minutes"] == 30
    assert result["intensity"] == "Moderate"
    assert result["heart_rate_bpm"] == 145
    assert result["notes"] == "Felt easy, could push harder"

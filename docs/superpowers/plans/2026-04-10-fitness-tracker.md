# Fitness Tracker — AI Personal Trainer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that reads daily workout/nutrition/sleep logs and uses the Claude API to generate professional trainer feedback with next-session planning.

**Architecture:** A single `analyze.py` entry point delegates to a `trainer/` package. Parsers convert raw log files into dicts. A history fetcher collects the last N sessions. A context builder assembles everything. A prompt builder formats the context for Claude. The API module calls Claude. A writer saves `feedback.md` back to the date folder.

**Tech Stack:** Python 3.10+, `anthropic` SDK, `pytest` for tests, stdlib only (`pathlib`, `re`, `json`, `datetime`, `argparse`).

---

## File Map

```
Fitness/
├── analyze.py                  # CLI entry point — arg parsing, date resolution, orchestration
├── config.json                 # user profile + current phase (created in Task 1)
├── requirements.txt            # anthropic only
├── trainer/
│   ├── __init__.py
│   ├── parsers.py              # all log format parsers → dicts
│   ├── history.py              # scan date folders, return last N parsed sessions
│   ├── context.py              # assemble today + history + sleep + weight + calories
│   ├── prompt.py               # build system prompt + user message from context dict
│   ├── api.py                  # call Claude API, return response text
│   └── writer.py               # write feedback.md to the correct date folder
└── tests/
    ├── test_parsers.py
    ├── test_history.py
    ├── test_context.py
    └── test_writer.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `config.json`
- Create: `trainer/__init__.py`
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Create requirements.txt**

```
anthropic>=0.25.0
pytest>=8.0.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: installs without errors.

- [ ] **Step 3: Create config.json**

```json
{
  "name": "Sai",
  "age": 25,
  "sex": "male",
  "weight_kg": 80,
  "body_fat_pct": 20,
  "experience_years": 4,
  "phase": "cut",
  "phase_notes": "Mini-cut. Slight caloric deficit. Prioritise muscle preservation.",
  "training_days_target": 7,
  "split": ["push", "pull", "legs-abs", "arms"],
  "maintenance_calories": 2600,
  "goal_calories_cut": 2200,
  "goal_protein_g": 160
}
```

- [ ] **Step 4: Create trainer/__init__.py**

```python
```

(empty file — marks trainer as a package)

- [ ] **Step 5: Create tests/__init__.py**

```python
```

(empty)

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt config.json trainer/__init__.py tests/__init__.py
git commit -m "feat: project scaffold and config"
```

---

## Task 2: FitNotes Workout Log Parser

**Files:**
- Create: `trainer/parsers.py`
- Create: `tests/test_parsers.py`

The FitNotes format:
```
FitNotes Workout - Thursday 9th April 2026
Total Volume: 3,055 Kg
Total Sets: 19
Total Reps: 110

** Incline Dumbbell Bench Press **
- Total Volume: 790 Kg
- Total Sets: 5
- Total Reps: 28
- 25.0 kgs x 7 reps
- 30.0 kgs x 6 reps [Okayish form]
- 6 reps [Only bodyweight]
```

- [ ] **Step 1: Write failing tests for FitNotes parser**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_parsers.py::test_parse_workout_header -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `parsers.py` does not exist yet.

- [ ] **Step 3: Implement parse_workout in trainer/parsers.py**

```python
# trainer/parsers.py
import re
from pathlib import Path


def parse_workout(text: str) -> dict:
    """Parse a FitNotes plain-text workout export into a structured dict."""
    lines = text.strip().splitlines()

    # Header
    date_label = ""
    total_volume_kg = 0
    total_sets = 0
    total_reps = 0

    header_date = re.search(r"FitNotes Workout - (.+)", lines[0])
    if header_date:
        date_label = header_date.group(1).strip()

    for line in lines[1:4]:
        m = re.search(r"Total Volume:\s*([\d,]+)", line)
        if m:
            total_volume_kg = int(m.group(1).replace(",", ""))
        m = re.search(r"Total Sets:\s*(\d+)", line)
        if m:
            total_sets = int(m.group(1))
        m = re.search(r"Total Reps:\s*(\d+)", line)
        if m:
            total_reps = int(m.group(1))

    # Exercises
    exercises = []
    current_exercise = None

    for line in lines:
        # Exercise header: ** Name **
        ex_match = re.match(r"\*\*\s*(.+?)\s*\*\*", line)
        if ex_match:
            if current_exercise:
                exercises.append(current_exercise)
            current_exercise = {
                "name": ex_match.group(1),
                "total_volume_kg": 0,
                "total_sets": 0,
                "total_reps": 0,
                "sets": [],
            }
            continue

        if current_exercise is None:
            continue

        # Exercise summary lines
        m = re.match(r"-\s*Total Volume:\s*([\d,]+)", line)
        if m:
            current_exercise["total_volume_kg"] = int(m.group(1).replace(",", ""))
            continue
        m = re.match(r"-\s*Total Sets:\s*(\d+)", line)
        if m:
            current_exercise["total_sets"] = int(m.group(1))
            continue
        m = re.match(r"-\s*Total Reps:\s*(\d+)", line)
        if m:
            current_exercise["total_reps"] = int(m.group(1))
            continue

        # Set line with weight: "- 25.0 kgs x 7 reps" or "- 25.0 kgs x 7 reps [note]"
        set_match = re.match(r"-\s*([\d.]+)\s*kgs?\s*x\s*(\d+)\s*reps?(?:\s*\[(.+?)\])?", line)
        if set_match:
            current_exercise["sets"].append({
                "weight_kg": float(set_match.group(1)),
                "reps": int(set_match.group(2)),
                "notes": (set_match.group(3) or "").strip(),
            })
            continue

        # Bodyweight-only set: "- 6 reps [note]" or "- 6 reps"
        bw_match = re.match(r"-\s*(\d+)\s*reps?(?:\s*\[(.+?)\])?$", line)
        if bw_match:
            current_exercise["sets"].append({
                "weight_kg": 0.0,
                "reps": int(bw_match.group(1)),
                "notes": (bw_match.group(2) or "").strip(),
            })

    if current_exercise:
        exercises.append(current_exercise)

    return {
        "date_label": date_label,
        "total_volume_kg": total_volume_kg,
        "total_sets": total_sets,
        "total_reps": total_reps,
        "exercises": exercises,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_parsers.py -k "workout" -v
```

Expected: all 6 workout tests PASS.

- [ ] **Step 5: Commit**

```bash
git add trainer/parsers.py tests/test_parsers.py
git commit -m "feat: FitNotes workout log parser with tests"
```

---

## Task 3: Supplementary Parsers (Calories, Weight, Sleep, Cardio)

**Files:**
- Modify: `trainer/parsers.py`
- Modify: `tests/test_parsers.py`

- [ ] **Step 1: Write failing tests for all supplementary parsers**

Append to `tests/test_parsers.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_parsers.py -k "calories or weight or sleep or cardio" -v
```

Expected: all fail with `ImportError`.

- [ ] **Step 3: Implement supplementary parsers — append to trainer/parsers.py**

```python
def _parse_duration_to_minutes(text: str) -> int:
    """Convert '6h 50m' or '1h 23m' or '57m' or '32m' to total minutes."""
    h_match = re.search(r"(\d+)\s*h", text)
    m_match = re.search(r"(\d+)\s*m", text)
    hours = int(h_match.group(1)) if h_match else 0
    minutes = int(m_match.group(1)) if m_match else 0
    return hours * 60 + minutes


def parse_calories(text: str) -> dict:
    """Parse a manual calories log file into a dict."""
    result = {
        "calories": 0, "protein_g": 0, "carbs_g": 0,
        "fats_g": 0, "fiber_g": 0, "notes": "",
    }
    for line in text.strip().splitlines():
        m = re.match(r"Calories:\s*(\d+)", line)
        if m:
            result["calories"] = int(m.group(1))
        m = re.match(r"Protein:\s*(\d+)", line)
        if m:
            result["protein_g"] = int(m.group(1))
        m = re.match(r"Carbs:\s*(\d+)", line)
        if m:
            result["carbs_g"] = int(m.group(1))
        m = re.match(r"Fats:\s*(\d+)", line)
        if m:
            result["fats_g"] = int(m.group(1))
        m = re.match(r"Fiber:\s*(\d+)", line)
        if m:
            result["fiber_g"] = int(m.group(1))
        m = re.match(r"Notes:\s*(.+)", line)
        if m:
            result["notes"] = m.group(1).strip()
    return result


def parse_weight(text: str) -> dict:
    """Parse a manual weight log file into a dict."""
    result = {"weight_kg": 0.0, "notes": ""}
    for line in text.strip().splitlines():
        m = re.match(r"([\d.]+)\s*kg", line)
        if m:
            result["weight_kg"] = float(m.group(1))
        m = re.match(r"Notes:\s*(.+)", line)
        if m:
            result["notes"] = m.group(1).strip()
    return result


def parse_sleep(text: str) -> dict:
    """Parse a Samsung Health sleep extraction file into a dict."""
    result = {
        "sleep_time_minutes": 0,
        "physical_recovery_pct": 0,
        "restfulness_pct": 0,
        "mental_recovery_pct": 0,
        "sleep_cycles": 0,
        "stages": {
            "awake_minutes": 0, "awake_pct": 0,
            "rem_minutes": 0, "rem_pct": 0,
            "light_minutes": 0, "light_pct": 0,
            "deep_minutes": 0, "deep_pct": 0,
        },
        "notes": "",
    }
    for line in text.strip().splitlines():
        m = re.match(r"Sleep Time:\s*(.+)", line)
        if m:
            result["sleep_time_minutes"] = _parse_duration_to_minutes(m.group(1))
        m = re.match(r"Physical Recovery:\s*(\d+)%", line)
        if m:
            result["physical_recovery_pct"] = int(m.group(1))
        m = re.match(r"Restfulness:\s*(\d+)%", line)
        if m:
            result["restfulness_pct"] = int(m.group(1))
        m = re.match(r"Mental Recovery:\s*(\d+)%", line)
        if m:
            result["mental_recovery_pct"] = int(m.group(1))
        m = re.match(r"Sleep Cycles:\s*(\d+)", line)
        if m:
            result["sleep_cycles"] = int(m.group(1))
        m = re.match(r"Awake:\s*(.+?)\s*\((\d+)%\)", line)
        if m:
            result["stages"]["awake_minutes"] = _parse_duration_to_minutes(m.group(1))
            result["stages"]["awake_pct"] = int(m.group(2))
        m = re.match(r"REM:\s*(.+?)\s*\((\d+)%\)", line)
        if m:
            result["stages"]["rem_minutes"] = _parse_duration_to_minutes(m.group(1))
            result["stages"]["rem_pct"] = int(m.group(2))
        m = re.match(r"Light:\s*(.+?)\s*\((\d+)%\)", line)
        if m:
            result["stages"]["light_minutes"] = _parse_duration_to_minutes(m.group(1))
            result["stages"]["light_pct"] = int(m.group(2))
        m = re.match(r"Deep:\s*(.+?)\s*\((\d+)%\)", line)
        if m:
            result["stages"]["deep_minutes"] = _parse_duration_to_minutes(m.group(1))
            result["stages"]["deep_pct"] = int(m.group(2))
        m = re.match(r"Notes:\s*(.+)", line)
        if m:
            result["notes"] = m.group(1).strip()
    return result


def parse_cardio(text: str) -> dict:
    """Parse a manual cardio log file into a dict."""
    result = {
        "type": "", "duration_minutes": 0,
        "intensity": "", "heart_rate_bpm": 0, "notes": "",
    }
    for line in text.strip().splitlines():
        m = re.match(r"Type:\s*(.+)", line)
        if m:
            result["type"] = m.group(1).strip()
        m = re.match(r"Duration:\s*(\d+)", line)
        if m:
            result["duration_minutes"] = int(m.group(1))
        m = re.match(r"Intensity:\s*(.+)", line)
        if m:
            result["intensity"] = m.group(1).strip()
        m = re.match(r"Heart Rate:\s*~?(\d+)", line)
        if m:
            result["heart_rate_bpm"] = int(m.group(1))
        m = re.match(r"Notes:\s*(.+)", line)
        if m:
            result["notes"] = m.group(1).strip()
    return result
```

- [ ] **Step 4: Run all parser tests**

```bash
pytest tests/test_parsers.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add trainer/parsers.py tests/test_parsers.py
git commit -m "feat: add calories, weight, sleep, cardio parsers with tests"
```

---

## Task 4: History Fetcher

**Files:**
- Create: `trainer/history.py`
- Create: `tests/test_history.py`

The history fetcher scans date subfolders (`YYYY-MM-DD`) in a given folder, sorts them by date descending, and returns the last N parsed sessions (excluding today's date).

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_history.py -v
```

Expected: all fail with `ImportError`.

- [ ] **Step 3: Implement trainer/history.py**

```python
# trainer/history.py
from pathlib import Path
from datetime import datetime
from trainer.parsers import parse_workout, parse_calories, parse_weight, parse_sleep, parse_cardio

PARSERS = {
    "workout": parse_workout,
    "calories": parse_calories,
    "weight": parse_weight,
    "sleep": parse_sleep,
    "cardio": parse_cardio,
}


def _sorted_date_dirs(folder: Path) -> list[tuple[str, Path]]:
    """Return (date_str, path) tuples sorted newest-first, only YYYY-MM-DD dirs."""
    dirs = []
    for d in folder.iterdir():
        if d.is_dir() and len(d.name) == 10:
            try:
                datetime.strptime(d.name, "%Y-%m-%d")
                dirs.append((d.name, d))
            except ValueError:
                pass
    return sorted(dirs, key=lambda x: x[0], reverse=True)


def get_recent_sessions(folder: Path, log_filename: str, parser_type: str,
                        n: int, exclude_date: str) -> list[dict]:
    """Return last n parsed workout sessions from a folder, excluding exclude_date."""
    parser = PARSERS[parser_type]
    results = []
    for date_str, date_dir in _sorted_date_dirs(folder):
        if date_str == exclude_date:
            continue
        log_file = date_dir / log_filename
        if not log_file.exists():
            continue
        parsed = parser(log_file.read_text())
        parsed["date"] = date_str
        results.append(parsed)
        if len(results) >= n:
            break
    return results


def get_recent_single_logs(folder: Path, log_filename: str, parser_type: str,
                           n: int, exclude_date: str) -> list[dict]:
    """Same as get_recent_sessions — alias for clarity when reading weight/sleep/calories."""
    return get_recent_sessions(folder, log_filename, parser_type, n, exclude_date)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_history.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add trainer/history.py tests/test_history.py
git commit -m "feat: history fetcher with date-sorted session lookup"
```

---

## Task 5: Context Builder

**Files:**
- Create: `trainer/context.py`
- Create: `tests/test_context.py`

The context builder assembles everything into one dict that the prompt builder will use. It reads today's log, fetches history, and packages config.

- [ ] **Step 1: Write failing tests**

```python
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
    "split": ["push", "pull", "legs-abs", "arms"],
    "maintenance_calories": 2600,
    "goal_calories_cut": 2200,
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


def test_build_context_sleep_weight_calories_empty_when_missing(fitness_root):
    ctx = build_context(fitness_root, "push", "2026-04-10")
    assert ctx["recent_sleep"] == []
    assert ctx["recent_weight"] == []
    assert ctx["recent_calories"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_context.py -v
```

Expected: all fail with `ImportError`.

- [ ] **Step 3: Implement trainer/context.py**

```python
# trainer/context.py
import json
from pathlib import Path
from trainer.parsers import parse_workout, parse_calories, parse_weight, parse_sleep, parse_cardio
from trainer.history import get_recent_sessions, get_recent_single_logs

FOLDER_MAP = {
    "push": "push",
    "pull": "pull",
    "legs": "legs-abs",
    "arms": "arms",
    "cardio": "cardio-notes",
    "calories": "calories-count",
    "weight": "weight",
    "sleep": "sleep",
}

WORKOUT_TYPES = {"push", "pull", "legs", "arms", "cardio"}

PARSER_FOR_TYPE = {
    "push": parse_workout,
    "pull": parse_workout,
    "legs": parse_workout,
    "arms": parse_workout,
    "cardio": parse_cardio,
    "calories": parse_calories,
    "weight": parse_weight,
    "sleep": parse_sleep,
}

LOG_FILENAME = {
    "push": "log.txt", "pull": "log.txt", "legs": "log.txt",
    "arms": "log.txt", "cardio": "log.txt", "calories": "log.txt",
    "weight": "log.txt", "sleep": "log.md",
}

HISTORY_PARSER_TYPE = {
    "push": "workout", "pull": "workout", "legs": "workout",
    "arms": "workout", "cardio": "cardio",
}


def build_context(root: Path, session_type: str, date: str) -> dict:
    """
    Assemble full context for a given session type and date.
    root: Path to the Fitness directory (contains config.json)
    session_type: push | pull | legs | arms | cardio | calories | weight | sleep
    date: YYYY-MM-DD string
    """
    config = json.loads((root / "config.json").read_text())

    folder_name = FOLDER_MAP[session_type]
    folder = root / folder_name
    log_file = folder / date / LOG_FILENAME[session_type]

    if not log_file.exists():
        raise FileNotFoundError(f"No log found at {log_file}")

    parser = PARSER_FOR_TYPE[session_type]
    today = parser(log_file.read_text())
    today["date"] = date

    # History for same session type
    history = []
    if session_type in HISTORY_PARSER_TYPE:
        history = get_recent_sessions(
            folder=folder,
            log_filename=LOG_FILENAME[session_type],
            parser_type=HISTORY_PARSER_TYPE[session_type],
            n=5,
            exclude_date=date,
        )

    # Cross-reference data
    sleep_folder = root / "sleep"
    weight_folder = root / "weight"
    calories_folder = root / "calories-count"

    recent_sleep = (get_recent_single_logs(sleep_folder, "log.md", "sleep", 7, "9999-99-99")
                    if sleep_folder.exists() else [])
    recent_weight = (get_recent_single_logs(weight_folder, "log.txt", "weight", 7, "9999-99-99")
                     if weight_folder.exists() else [])
    recent_calories = (get_recent_single_logs(calories_folder, "log.txt", "calories", 3, "9999-99-99")
                       if calories_folder.exists() else [])

    return {
        "config": config,
        "session_type": session_type,
        "date": date,
        "today": today,
        "history": history,
        "recent_sleep": recent_sleep,
        "recent_weight": recent_weight,
        "recent_calories": recent_calories,
    }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_context.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add trainer/context.py tests/test_context.py
git commit -m "feat: context builder assembles today + history + sleep + weight + calories"
```

---

## Task 6: Trainer Prompt Builder

**Files:**
- Create: `trainer/prompt.py`

No unit tests for this task — the prompt is validated by reading the output. The builder produces a `(system_prompt, user_message)` tuple.

- [ ] **Step 1: Create trainer/prompt.py**

```python
# trainer/prompt.py
from datetime import datetime

PHASE_RULES = {
    "cut": """
- Target weight loss: 0.5kg/week. Flag if dropping faster than 0.75kg/week (muscle loss risk).
- Flag if weight is not decreasing after 2 consecutive weeks (deficit too small).
- Protein must stay at or above {goal_protein_g}g/day. Flag if below.
- Protect strength: flag any compound lift drop exceeding 10% from the previous session.
- Caloric deficit should be moderate — never sacrifice training performance severely.
""",
    "lean-bulk": """
- Target weight gain: 0.25–0.5kg/week. Flag if gaining faster than 0.5kg/week (too much fat).
- Flag if weight not increasing after 3 weeks (under-eating).
- Push progressive overload every session — add reps or weight compared to last session.
- Volume should increase gradually every 2–3 weeks.
- Ensure adequate caloric surplus — flag if calories are at or below maintenance.
""",
}


def _format_workout_history(sessions: list[dict]) -> str:
    if not sessions:
        return "No previous sessions recorded."
    lines = []
    for s in sessions:
        lines.append(f"\n### Session: {s['date']}")
        lines.append(f"Total volume: {s['total_volume_kg']}kg | Sets: {s['total_sets']} | Reps: {s['total_reps']}")
        for ex in s.get("exercises", []):
            set_strs = []
            for st in ex["sets"]:
                w = f"{st['weight_kg']}kg" if st["weight_kg"] > 0 else "BW"
                note = f" [{st['notes']}]" if st["notes"] else ""
                set_strs.append(f"{w}×{st['reps']}{note}")
            lines.append(f"  {ex['name']}: {' | '.join(set_strs)}")
    return "\n".join(lines)


def _format_today_workout(today: dict) -> str:
    lines = [f"Date: {today['date']} ({today.get('date_label', '')})",
             f"Total volume: {today['total_volume_kg']}kg | Sets: {today['total_sets']} | Reps: {today['total_reps']}"]
    for ex in today.get("exercises", []):
        set_strs = []
        for st in ex["sets"]:
            w = f"{st['weight_kg']}kg" if st["weight_kg"] > 0 else "BW"
            note = f" [{st['notes']}]" if st["notes"] else ""
            set_strs.append(f"{w}×{st['reps']}{note}")
        lines.append(f"  {ex['name']}: {' | '.join(set_strs)}")
    return "\n".join(lines)


def _format_sleep(recent_sleep: list[dict]) -> str:
    if not recent_sleep:
        return "No sleep data available."
    lines = []
    for s in recent_sleep[:3]:
        lines.append(
            f"{s['date']}: {s['sleep_time_minutes']//60}h{s['sleep_time_minutes']%60}m | "
            f"Physical: {s['physical_recovery_pct']}% | Mental: {s['mental_recovery_pct']}% | "
            f"Deep: {s['stages']['deep_minutes']}m ({s['stages']['deep_pct']}%) | "
            f"REM: {s['stages']['rem_minutes']}m | Notes: {s['notes'] or 'none'}"
        )
    return "\n".join(lines)


def _format_weight(recent_weight: list[dict]) -> str:
    if not recent_weight:
        return "No weight data available."
    return "\n".join(f"{w['date']}: {w['weight_kg']}kg" for w in recent_weight)


def _format_calories(recent_calories: list[dict]) -> str:
    if not recent_calories:
        return "No calorie data available."
    lines = []
    for c in recent_calories:
        lines.append(
            f"{c['date']}: {c['calories']} kcal | Protein: {c['protein_g']}g | "
            f"Carbs: {c['carbs_g']}g | Fats: {c['fats_g']}g | Fiber: {c['fiber_g']}g"
            + (f" | Notes: {c['notes']}" if c['notes'] else "")
        )
    return "\n".join(lines)


def build_prompt(ctx: dict) -> tuple[str, str]:
    """
    Build (system_prompt, user_message) from a context dict.
    Returns a tuple ready to pass to the Claude API.
    """
    cfg = ctx["config"]
    phase = cfg.get("phase", "cut")
    phase_rule = PHASE_RULES.get(phase, PHASE_RULES["cut"]).format(
        goal_protein_g=cfg.get("goal_protein_g", 160)
    )

    system_prompt = f"""You are an experienced, direct personal trainer and sports nutritionist with deep knowledge of exercise science, hypertrophy, body composition, and periodisation.

You are coaching {cfg['name']}, a {cfg['age']}-year-old {cfg['sex']}, {cfg['weight_kg']}kg bodyweight, approximately {cfg['body_fat_pct']}% body fat, with {cfg['experience_years']} years of training experience. Estimated lean mass: {round(cfg['weight_kg'] * (1 - cfg['body_fat_pct']/100), 1)}kg.

Current training phase: {phase.upper()}
Phase goal: {cfg.get('phase_notes', '')}

Phase-specific rules you must apply:
{phase_rule}

Your coaching style:
- Direct and honest. Zero motivational fluff. Treat the athlete as an experienced adult.
- Always compare today's performance to the previous session using exact numbers.
- Call out exercise selection problems: wrong order, missing muscle groups, redundant movements.
- Pick up every inline form note in the log and respond to it specifically.
- Cross-reference sleep recovery scores with performance — low physical recovery explains strength drops.
- Cross-reference nutrition with training days — flag low protein or under-eating on heavy training days.
- Flag consistency issues — missed training days affect progress and must be named.
- Every feedback ends with a concrete next session plan: exact exercises, sets, reps, weights.
- One single priority for the week — the most important thing to fix or focus on.

Output format — always use exactly these sections in this order:
1. **Session Verdict** (2-3 sentences)
2. **Exercise-by-Exercise Review** (compare to previous session, flag progressive overload status per exercise)
3. **Exercise Selection Review** (flag missing muscle groups, wrong order, redundant movements — use a table)
4. **Form Notes** (respond to every inline comment from the log)
5. **Recovery Cross-Reference** (sleep data vs today's performance)
6. **Nutrition Cross-Reference** (protein and calorie adequacy)
7. **Weight Trend** (is the cut/bulk progressing correctly?)
8. **Next Session Plan** (markdown table: Exercise | Sets×Reps | Weight | Notes)
9. **This Week's Priority** (one sentence, one thing)

Be specific. Use actual numbers from the log. If data is missing, say so and explain why it matters."""

    session_type = ctx["session_type"]

    user_message = f"""## Today's Session ({session_type.upper()} — {ctx['date']})

{_format_today_workout(ctx['today'])}

## Previous {session_type.upper()} Sessions (most recent first)

{_format_workout_history(ctx['history'])}

## Recent Sleep Data

{_format_sleep(ctx['recent_sleep'])}

## Recent Weight Data (last 7 days)

{_format_weight(ctx['recent_weight'])}

## Recent Nutrition Data (last 3 days)

{_format_calories(ctx['recent_calories'])}

---

Please provide full trainer feedback following your output format."""

    return system_prompt, user_message
```

- [ ] **Step 2: Commit**

```bash
git add trainer/prompt.py
git commit -m "feat: trainer prompt builder with phase-aware system prompt"
```

---

## Task 7: Claude API Integration + Feedback Writer

**Files:**
- Create: `trainer/api.py`
- Create: `trainer/writer.py`
- Create: `tests/test_writer.py`

- [ ] **Step 1: Create trainer/api.py**

```python
# trainer/api.py
import os
import anthropic


def call_claude(system_prompt: str, user_message: str, model: str = "claude-sonnet-4-6") -> str:
    """Call the Claude API and return the response text."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Run: export ANTHROPIC_API_KEY=your_key_here"
        )
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
```

- [ ] **Step 2: Write failing test for feedback writer**

```python
# tests/test_writer.py
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
```

- [ ] **Step 3: Run writer tests to verify they fail**

```bash
pytest tests/test_writer.py -v
```

Expected: fail with `ImportError`.

- [ ] **Step 4: Create trainer/writer.py**

```python
# trainer/writer.py
from pathlib import Path
from datetime import datetime


def write_feedback(session_folder: Path, feedback_text: str) -> Path:
    """Write feedback.md into the session's date folder. Returns the file path."""
    output_file = session_folder / "feedback.md"
    header = f"<!-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} -->\n\n"
    output_file.write_text(header + feedback_text)
    return output_file
```

- [ ] **Step 5: Run writer tests**

```bash
pytest tests/test_writer.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add trainer/api.py trainer/writer.py tests/test_writer.py
git commit -m "feat: Claude API integration and feedback file writer"
```

---

## Task 8: CLI Entry Point (analyze.py)

**Files:**
- Create: `analyze.py`

This wires everything together. No unit tests — verified manually.

- [ ] **Step 1: Create analyze.py**

```python
#!/usr/bin/env python3
# analyze.py
"""
AI Personal Trainer — analyze your fitness logs.

Usage:
    python analyze.py push              # today's push session
    python analyze.py legs 2026-04-07  # specific date
    python analyze.py summary          # weekly overview
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import date as date_cls

from trainer.context import build_context, FOLDER_MAP
from trainer.prompt import build_prompt
from trainer.api import call_claude
from trainer.writer import write_feedback

ROOT = Path(__file__).parent

VALID_TYPES = list(FOLDER_MAP.keys())


def resolve_date(date_arg: str | None) -> str:
    if date_arg:
        return date_arg
    return date_cls.today().strftime("%Y-%m-%d")


def run_analysis(session_type: str, date_str: str) -> None:
    print(f"[Trainer] Analyzing {session_type} session for {date_str}...")

    ctx = build_context(ROOT, session_type, date_str)
    system_prompt, user_message = build_prompt(ctx)

    print("[Trainer] Calling Claude API...")
    feedback = call_claude(system_prompt, user_message)

    folder_name = FOLDER_MAP[session_type]
    session_folder = ROOT / folder_name / date_str
    output_path = write_feedback(session_folder, feedback)

    print(f"[Trainer] Feedback written to: {output_path}")
    print("\n" + "="*60)
    print(feedback[:500] + "..." if len(feedback) > 500 else feedback)


def run_summary(date_str: str) -> None:
    """Weekly overview: collect all sessions from the last 7 days and summarise."""
    from datetime import datetime, timedelta
    from trainer.parsers import parse_workout, parse_sleep, parse_weight, parse_calories
    from trainer.history import get_recent_single_logs

    print(f"[Trainer] Building weekly summary up to {date_str}...")

    workout_folders = {
        "push": ROOT / "push",
        "pull": ROOT / "pull",
        "legs-abs": ROOT / "legs-abs",
        "arms": ROOT / "arms",
    }

    sessions_found = []
    for label, folder in workout_folders.items():
        if not folder.exists():
            continue
        from trainer.history import get_recent_sessions
        recent = get_recent_sessions(folder, "log.txt", "workout", 7, "9999-99-99")
        for s in recent:
            sessions_found.append({"type": label, **s})

    config = json.loads((ROOT / "config.json").read_text())

    sleep_folder = ROOT / "sleep"
    weight_folder = ROOT / "weight"
    calories_folder = ROOT / "calories-count"

    recent_sleep = (get_recent_single_logs(sleep_folder, "log.md", "sleep", 7, "9999-99-99")
                    if sleep_folder.exists() else [])
    recent_weight = (get_recent_single_logs(weight_folder, "log.txt", "weight", 7, "9999-99-99")
                     if weight_folder.exists() else [])
    recent_calories = (get_recent_single_logs(calories_folder, "log.txt", "calories", 3, "9999-99-99")
                       if calories_folder.exists() else [])

    from trainer.prompt import _format_sleep, _format_weight, _format_calories

    sessions_text = ""
    for s in sorted(sessions_found, key=lambda x: x["date"], reverse=True)[:14]:
        sessions_text += f"\n{s['type'].upper()} — {s['date']}: "
        sessions_text += f"{s['total_volume_kg']}kg total, {s['total_sets']} sets\n"

    phase = config.get("phase", "cut")
    system_prompt = f"""You are an experienced personal trainer reviewing {config['name']}'s weekly training summary.
Current phase: {phase.upper()}. Phase goal: {config.get('phase_notes', '')}
Provide a structured weekly review covering: training consistency, volume trends, recovery quality, nutrition adequacy, and top priorities for next week. Be direct and specific."""

    user_message = f"""## Weekly Summary — up to {date_str}

## Sessions This Week
{sessions_text or 'No sessions logged.'}

## Sleep (last 7 days)
{_format_sleep(recent_sleep)}

## Weight (last 7 days)
{_format_weight(recent_weight)}

## Nutrition (last 3 days)
{_format_calories(recent_calories)}

Provide a full weekly review with top 3 priorities for next week."""

    print("[Trainer] Calling Claude API for weekly summary...")
    feedback = call_claude(system_prompt, user_message)

    output_file = ROOT / f"summary-{date_str}.md"
    output_file.write_text(feedback)
    print(f"[Trainer] Weekly summary written to: {output_file}")
    print("\n" + feedback[:500] + "...")


def main():
    parser = argparse.ArgumentParser(description="AI Personal Trainer")
    parser.add_argument("type", choices=VALID_TYPES + ["summary"],
                        help="Session type to analyze")
    parser.add_argument("date", nargs="?", default=None,
                        help="Date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    date_str = resolve_date(args.date)

    if args.type == "summary":
        run_summary(date_str)
    else:
        try:
            run_analysis(args.type, date_str)
        except FileNotFoundError as e:
            print(f"[Error] {e}")
            print(f"Make sure you have a log file at: "
                  f"{FOLDER_MAP[args.type]}/{date_str}/log.txt")
            sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Set up ANTHROPIC_API_KEY**

```bash
export ANTHROPIC_API_KEY=your_key_here
```

- [ ] **Step 3: Create today's push folder and drop the sample log**

```bash
mkdir -p push/2026-04-09
cp push-day-sample.txt push/2026-04-09/log.txt
```

- [ ] **Step 4: Run end-to-end test**

```bash
python analyze.py push 2026-04-09
```

Expected: prints analysis to terminal, writes `push/2026-04-09/feedback.md`.

- [ ] **Step 5: Verify feedback file was created**

```bash
cat push/2026-04-09/feedback.md
```

Expected: full markdown trainer feedback with all 9 sections.

- [ ] **Step 6: Commit**

```bash
git add analyze.py
git commit -m "feat: CLI entry point — analyze.py with date auto-resolution and summary command"
```

---

## Task 9: Folder Structure Initialisation

**Files:**
- Create: `init_folders.py` (one-time setup script)

- [ ] **Step 1: Create init_folders.py**

```python
#!/usr/bin/env python3
# init_folders.py — run once to create the folder structure
from pathlib import Path

FOLDERS = [
    "push", "pull", "legs-abs", "arms",
    "cardio-notes", "calories-count", "weight", "sleep", "progress-pics",
]

root = Path(__file__).parent
for folder in FOLDERS:
    (root / folder).mkdir(exist_ok=True)
    print(f"Created: {folder}/")

print("\nDone. Drop your log files into the date subfolders:")
print("  push/YYYY-MM-DD/log.txt")
print("  sleep/YYYY-MM-DD/log.md")
print("  calories-count/YYYY-MM-DD/log.txt")
print("  weight/YYYY-MM-DD/log.txt")
```

- [ ] **Step 2: Run it**

```bash
python init_folders.py
```

Expected: all folders created, confirmation printed.

- [ ] **Step 3: Move sample log files into correct structure**

```bash
mkdir -p push/2026-04-09 legs-abs/2026-04-07
cp push-day-sample.txt push/2026-04-09/log.txt
cp legdaysample.txt legs-abs/2026-04-07/log.txt
```

- [ ] **Step 4: Run full test on legs day**

```bash
python analyze.py legs 2026-04-07
```

Expected: `legs-abs/2026-04-07/feedback.md` created with full trainer feedback.

- [ ] **Step 5: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Final commit**

```bash
git add init_folders.py push/ legs-abs/
git commit -m "feat: folder init script and sample log placement — system ready"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|-----------------|-----------------|
| Folder structure with YYYY-MM-DD subfolders | Task 1 + Task 9 |
| FitNotes log parser | Task 2 |
| Calories / weight / sleep / cardio parsers | Task 3 |
| History: last 5 sessions of same type | Task 4 |
| History: last 7 days sleep + weight, 3 days calories | Task 5 |
| config.json with phase + user profile | Task 1 |
| Claude API call | Task 7 |
| feedback.md written to date folder | Task 7 |
| CLI: `python analyze.py push` with auto-date | Task 8 |
| CLI: optional date override | Task 8 |
| Summary command | Task 8 |
| Phase-aware trainer prompt | Task 6 |
| Next session plan in output | Task 6 (system prompt instructs it) |
| Exercise selection review | Task 6 (system prompt instructs it) |
| Sleep/nutrition cross-reference | Task 6 (system prompt instructs it) |

All spec requirements covered. No placeholders. Types and function signatures are consistent across tasks.

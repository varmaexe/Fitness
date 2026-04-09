# trainer/parsers.py
import re


def parse_workout(text: str) -> dict:
    """Parse a FitNotes plain-text workout export into a structured dict."""
    lines = text.strip().splitlines()
    if not lines:
        return {"date_label": "", "total_volume_kg": 0, "total_sets": 0, "total_reps": 0, "exercises": []}

    # Header
    date_label = ""
    total_volume_kg = 0
    total_sets = 0
    total_reps = 0

    header_date = re.search(r"FitNotes Workout - (.+)", lines[0])
    if header_date:
        date_label = header_date.group(1).strip()

    for line in lines[1:]:
        if re.match(r"\*\*\s*.+?\s*\*\*", line):
            break  # hit first exercise header, stop scanning totals
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
        set_match = re.match(r"-\s*(\d+(?:\.\d+)?)\s*kgs?\s*x\s*(\d+)\s*reps?(?:\s*\[(.+?)\])?", line)
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
        m = re.match(r"(\d+(?:\.\d+)?)\s*kg", line)
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

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


def parse_calories(text: str) -> dict:
    raise NotImplementedError("parse_calories not yet implemented")


def parse_weight(text: str) -> dict:
    raise NotImplementedError("parse_weight not yet implemented")


def parse_sleep(text: str) -> dict:
    raise NotImplementedError("parse_sleep not yet implemented")


def parse_cardio(text: str) -> dict:
    raise NotImplementedError("parse_cardio not yet implemented")

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
    if session_type not in FOLDER_MAP:
        raise ValueError(
            f"Unknown session_type '{session_type}'. Valid types: {list(FOLDER_MAP)}"
        )
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

    # Use "9999-99-99" as exclude_date sentinel to retrieve all recent cross-reference
    # data without excluding any date (sleep/weight/calories are always fully loaded).
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

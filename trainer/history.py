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
    """Return last n parsed sessions from a folder, excluding exclude_date."""
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

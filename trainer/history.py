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
    """Return (date_str, dir_path) tuples for YYYY-MM-DD subdirectories, newest-first."""
    if not folder.exists():
        return []
    dirs = []
    for d in folder.iterdir():
        if d.is_dir() and len(d.name) == 10:
            try:
                datetime.strptime(d.name, "%Y-%m-%d")
                dirs.append((d.name, d))
            except ValueError:
                pass
    return sorted(dirs, key=lambda x: x[0], reverse=True)


def _sorted_date_files(folder: Path) -> list[tuple[str, Path]]:
    """Return (date_str, file_path) tuples for YYYY-MM-DD.txt flat files, newest-first."""
    if not folder.exists():
        return []
    files = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix == ".txt" and len(f.stem) == 10:
            try:
                datetime.strptime(f.stem, "%Y-%m-%d")
                files.append((f.stem, f))
            except ValueError:
                pass
    return sorted(files, key=lambda x: x[0], reverse=True)


def get_recent_sessions(folder: Path, log_filename: str, parser_type: str,
                        n: int, exclude_date: str,
                        up_to_date: str | None = None,
                        flat: bool = False) -> list[dict]:
    """Return last n parsed sessions from a folder, excluding exclude_date.

    flat=True: reads YYYY-MM-DD.txt files directly (sleep, weight, calories).
    flat=False: reads YYYY-MM-DD/log_filename (workout sessions).
    up_to_date: skip dates strictly after this value (prevents empty future
    placeholder files from shadowing real historical data).
    """
    if parser_type not in PARSERS:
        raise ValueError(f"Unknown parser_type '{parser_type}'. Valid types: {list(PARSERS)}")
    parser = PARSERS[parser_type]
    results = []

    if flat:
        entries = _sorted_date_files(folder)
        for date_str, file_path in entries:
            if date_str == exclude_date:
                continue
            if up_to_date is not None and date_str > up_to_date:
                continue
            parsed = parser(file_path.read_text())
            parsed["date"] = date_str
            results.append(parsed)
            if len(results) >= n:
                break
    else:
        for date_str, date_dir in _sorted_date_dirs(folder):
            if date_str == exclude_date:
                continue
            if up_to_date is not None and date_str > up_to_date:
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
                           n: int, exclude_date: str,
                           up_to_date: str | None = None,
                           flat: bool = False) -> list[dict]:
    """Same as get_recent_sessions — alias for clarity when reading weight/sleep/calories."""
    return get_recent_sessions(folder, log_filename, parser_type, n, exclude_date,
                               up_to_date, flat)

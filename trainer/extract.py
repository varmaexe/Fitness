# trainer/extract.py
"""Read sleep / nutrition numbers out of app screenshots using the claude CLI."""
import json
import re
import subprocess
from pathlib import Path

EXTRACT_PROMPT = """Look at the screenshot file(s) below using the Read tool. They come from a phone health app
and show EITHER one night's sleep (e.g. Samsung Health) OR one day's nutrition totals (a food tracker).
If there are several images, they belong to the same entry — combine them.

Reply with ONLY a JSON object, no prose, no code fence. Use null for anything not visible. Never guess.

For sleep:
{"kind": "sleep", "date": "YYYY-MM-DD or null (the morning the sleep ended, only if a date is visible)",
 "sleep_time": "6h 8m", "physical_recovery_pct": 68, "restfulness_pct": 93, "mental_recovery_pct": 77,
 "sleep_cycles": 3, "awake": "29m", "awake_pct": 7, "rem": "1h 8m", "rem_pct": 18,
 "light": "3h 48m", "light_pct": 64, "deep": "43m", "deep_pct": 11}

For nutrition (day totals, grams as numbers):
{"kind": "nutrition", "date": "YYYY-MM-DD or null (only if visible)",
 "calories": 2000, "protein_g": 150, "carbs_g": 188, "fats_g": 63, "fiber_g": 17,
 "notes": "null, or a short note if the app says not all meals are tracked"}
Apps like HealthifyMe show "consumed / target" (e.g. "945 / 2,700 Cal", "78.0 g/135.0 g"):
always take the FIRST number (consumed), never the target. "Fibre" means fiber.

If it is neither: {"kind": "unknown", "reason": "<short reason>"}

Files:
"""


class ExtractError(Exception):
    pass


def extract_screenshots(paths: list[Path], model: str = "claude-sonnet-4-6", timeout: int = 180) -> dict:
    if not paths:
        raise ExtractError("No images.")
    folder = paths[0].parent
    prompt = EXTRACT_PROMPT + "\n".join(str(p) for p in paths)
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--output-format", "text",
             "--allowedTools", "Read", "--add-dir", str(folder)],
            capture_output=True, text=True, timeout=timeout, cwd=folder,
        )
    except subprocess.TimeoutExpired as e:
        raise ExtractError("Reading the screenshot timed out.") from e
    if result.returncode != 0:
        raise ExtractError(f"claude CLI failed: {result.stderr.strip()[:300]}")
    return parse_json_reply(result.stdout)


def parse_json_reply(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ExtractError(f"No JSON in reply: {text.strip()[:200]}")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ExtractError(f"Bad JSON in reply: {e}") from e
    if data.get("kind") not in {"sleep", "nutrition", "unknown"}:
        raise ExtractError(f"Unexpected reply: {data}")
    return data


def _num(v) -> str:
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


def format_sleep(d: dict) -> str:
    """Fields → the sleep/YYYY-MM-DD.txt format that parse_sleep understands."""
    lines = []
    if d.get("sleep_time"):
        lines.append(f"Sleep Time: {d['sleep_time']}")
    for key, label in (("physical_recovery_pct", "Physical Recovery"),
                       ("restfulness_pct", "Restfulness"),
                       ("mental_recovery_pct", "Mental Recovery")):
        if d.get(key) is not None:
            lines.append(f"{label}: {_num(d[key])}%")
    if d.get("sleep_cycles") is not None:
        lines.append(f"Sleep Cycles: {_num(d['sleep_cycles'])}")
    for key, label in (("awake", "Awake"), ("rem", "REM"), ("light", "Light"), ("deep", "Deep")):
        if d.get(key):
            pct = d.get(f"{key}_pct")
            lines.append(f"{label}: {d[key]}" + (f" ({_num(pct)}%)" if pct is not None else ""))
    if d.get("notes"):
        lines.append(f"Notes: {d['notes']}")
    return "\n".join(lines)


def format_nutrition(d: dict) -> str:
    """Fields → the calories/YYYY-MM-DD.txt format that parse_calories understands."""
    lines = []
    if d.get("calories") is not None:
        lines.append(f"Calories: {_num(d['calories'])}")
    for key, label in (("protein_g", "Protein"), ("carbs_g", "Carbs"),
                       ("fats_g", "Fats"), ("fiber_g", "Fiber")):
        if d.get(key) is not None:
            lines.append(f"{label}: {_num(d[key])}g")
    if d.get("notes"):
        lines.append(f"Notes: {d['notes']}")
    return "\n".join(lines)

# tests/test_bot_helpers.py
import pytest

from trainer.extract import ExtractError, format_nutrition, format_sleep, parse_json_reply
from trainer.parsers import parse_calories, parse_sleep, parse_weight
from trainer.render import extract_tldr, to_html, to_telegram_html

FEEDBACK = """<!-- Generated: 2026-11-11 10:00 -->

## TL;DR
Volume up **80%**. Right bicep lagging.
1. Unilateral curls first
2. Drop one hammer variation
3. Keep 6–8 reps

---

## 1. Session Verdict
Long text here.

| Exercise | Sets |
|---|---|
| Curl | 3 |
"""


def test_extract_tldr():
    t = extract_tldr(FEEDBACK)
    assert t.startswith("Volume up") and "3. Keep 6–8 reps" in t
    assert "Session Verdict" not in t


def test_extract_tldr_fallback_without_section():
    t = extract_tldr("## 1. Session Verdict\n" + "x" * 900, fallback_chars=100)
    assert len(t) <= 101 and t.endswith("…")


def test_telegram_html_escapes_and_bolds():
    assert to_telegram_html("**a** < b & c") == "<b>a</b> &lt; b &amp; c"


def test_to_html_is_self_contained():
    page = to_html(FEEDBACK, "ARMS — 2026-11-11")
    assert "<table>" in page and "table-wrap" in page
    assert "http" not in page and "Generated" not in page


def test_nutrition_roundtrip():
    d = {"kind": "nutrition", "calories": 945, "protein_g": 78.0, "carbs_g": 67.1,
         "fats_g": 39.6, "fiber_g": 7.0, "notes": "not all meals tracked"}
    p = parse_calories(format_nutrition(d))
    assert (p["calories"], p["protein_g"], p["carbs_g"], p["fats_g"], p["fiber_g"]) == (945, 78, 67.1, 39.6, 7)
    assert p["notes"] == "not all meals tracked"


def test_sleep_roundtrip_skips_missing():
    d = {"kind": "sleep", "sleep_time": "6h 8m", "physical_recovery_pct": 68, "mental_recovery_pct": None,
         "deep": "43m", "deep_pct": 11, "rem": "1h 8m", "rem_pct": None}
    text = format_sleep(d)
    assert "Mental" not in text
    p = parse_sleep(text)
    assert p["sleep_time_minutes"] == 368 and p["stages"]["deep_minutes"] == 43
    assert p["stages"]["rem_minutes"] == 68


def test_parse_json_reply():
    assert parse_json_reply('Here:\n{"kind": "unknown", "reason": "cat"}')["kind"] == "unknown"
    with pytest.raises(ExtractError):
        parse_json_reply("no json")


@pytest.mark.parametrize("text,kg", [
    ("78.85kg\nNotes: Morning", 78.85),
    ("Weight: 79.90kg\nNotes : Measured in evening", 79.90),
    ("79.9kg\n", 79.9),
])
def test_parse_weight_formats(text, kg):
    assert parse_weight(text)["weight_kg"] == kg
    assert parse_weight("Weight: 79.90kg\nNotes : evening")["notes"] == "evening"

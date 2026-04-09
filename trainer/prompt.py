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
- Protein must stay at or above {goal_protein_g}g/day — muscle synthesis requires it even in a surplus.
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
    lines = [
        f"Date: {today.get('date', 'unknown')} ({today.get('date_label', '')})",
        f"Total volume: {today.get('total_volume_kg', 0)}kg | "
        f"Sets: {today.get('total_sets', 0)} | Reps: {today.get('total_reps', 0)}",
    ]
    for ex in today.get("exercises", []):
        set_strs = []
        for st in ex.get("sets", []):
            w = f"{st.get('weight_kg', 0)}kg" if st.get("weight_kg", 0) > 0 else "BW"
            note = f" [{st['notes']}]" if st.get("notes") else ""
            set_strs.append(f"{w}×{st.get('reps', 0)}{note}")
        lines.append(f"  {ex.get('name', 'Unknown Exercise')}: {' | '.join(set_strs)}")
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

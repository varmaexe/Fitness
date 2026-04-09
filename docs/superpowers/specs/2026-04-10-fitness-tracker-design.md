# Fitness Tracker — AI Personal Trainer Design Spec
**Date:** 2026-04-10
**Status:** Approved

---

## 1. Overview

A local Python-based system that acts as a professional AI personal trainer. The user logs daily workouts, nutrition, weight, and sleep into structured folders. Running a single command triggers analysis using Claude API, which reads today's data alongside recent history and writes back a detailed feedback file — including performance review, recovery cross-reference, and a guided plan for the next session.

---

## 2. User Profile

| Field | Value |
|-------|-------|
| Name | Sai |
| Age | 25 |
| Sex | Male |
| Weight | ~80kg |
| Body Fat | ~20% |
| Lean Mass | ~64kg |
| Experience | 4 years |
| Current Phase | Mini-cut |
| Phase Roadmap | Mini-cut → Lean bulk (hypertrophy) → Cut (preserve muscle) |
| Split | Push / Pull / Legs-Abs / Arms |
| Training target | 7 days/week (current reality: ~4 days) |

---

## 3. Folder Structure

```
Fitness/
├── push/
│   └── 2026-04-10/
│       ├── log.txt          ← FitNotes export (user drops this)
│       └── feedback.md      ← trainer analysis (auto-generated)
├── pull/
│   └── YYYY-MM-DD/
│       ├── log.txt
│       └── feedback.md
├── legs-abs/
│   └── YYYY-MM-DD/
│       ├── log.txt
│       └── feedback.md
├── arms/
│   └── YYYY-MM-DD/
│       ├── log.txt
│       └── feedback.md
├── cardio-notes/
│   └── YYYY-MM-DD/
│       ├── log.txt
│       └── feedback.md
├── calories-count/
│   └── YYYY-MM-DD/
│       └── log.txt
├── weight/
│   └── YYYY-MM-DD/
│       └── log.txt
├── sleep/
│   └── YYYY-MM-DD/
│       └── log.md
├── progress-pics/
│   └── YYYY-MM-DD/
│       └── front.jpg        ← optional, no code needed now
├── config.json              ← user profile and current phase
└── analyze.py               ← single entry point script
```

Date folders always use `YYYY-MM-DD` format for automatic chronological sorting.

---

## 4. CLI Interface

```bash
python analyze.py push              # analyze today's push workout
python analyze.py pull              # analyze today's pull workout
python analyze.py legs              # analyze today's legs-abs workout
python analyze.py arms              # analyze today's arms workout
python analyze.py cardio            # analyze today's cardio session
python analyze.py calories          # analyze today's nutrition
python analyze.py weight            # weight trend review
python analyze.py sleep             # sleep analysis
python analyze.py summary           # full weekly overview across all folders

# Optional: override date
python analyze.py push 2026-04-09   # analyze a specific past date
```

No date required by default — always resolves to today automatically.

---

## 5. How It Works (Data Flow)

```
1. Parse CLI args → resolve workout type + date
2. Load config.json (user profile, current phase)
3. Read today's log file from the appropriate folder
4. Fetch last 5 sessions of the same workout type (history context)
5. Fetch last 7 days of sleep data
6. Fetch last 7 days of weight data
7. Fetch last 3 days of calorie data
8. Build structured prompt with all context → send to Claude API
9. Write response to feedback.md in the same date folder
10. Print short confirmation to terminal
```

---

## 6. config.json

```json
{
  "name": "Sai",
  "age": 25,
  "weight_kg": 80,
  "body_fat_pct": 20,
  "phase": "cut",
  "phase_notes": "Mini-cut. Slight caloric deficit. Prioritise muscle preservation.",
  "training_days_target": 7,
  "split": ["push", "pull", "legs-abs", "arms"],
  "maintenance_calories": 2600,
  "goal_calories_cut": 2200,
  "goal_protein_g": 160
}
```

User manually updates `phase` when transitioning between cut / lean-bulk / cut.

---

## 7. Log File Formats

### Workout (`push/2026-04-10/log.txt`)
FitNotes plain text export — no modification needed. Drop and run.

### Calories (`calories-count/2026-04-10/log.txt`)
```
Calories: 2200
Protein: 160g
Carbs: 220g
Fats: 65g
Fiber: 28g
Notes: Ate late, skipped breakfast
```

### Weight (`weight/2026-04-10/log.txt`)
```
79.85kg
Notes: Morning, after bathroom
```

### Sleep (`sleep/2026-04-10/log.md`)
```
Sleep Time: 6h 50m
Physical Recovery: 64%
Restfulness: 87%
Mental Recovery: 84%
Sleep Cycles: 4
Awake: 57m (13%)
REM: 1h 23m (20%)
Light: 3h 58m (60%)
Deep: 32m (7%)
Notes: Woke up twice, felt groggy
```

### Cardio (`cardio-notes/2026-04-10/log.txt`)
```
Type: Treadmill
Duration: 30min
Intensity: Moderate
Heart Rate: ~145bpm
Notes: Felt easy, could push harder
```

---

## 8. Feedback File (feedback.md) Structure

Every generated `feedback.md` will contain:

1. **Session Summary** — overall verdict on today's session
2. **Exercise-by-Exercise Review** — performance vs previous session, progressive overload status
3. **Form Notes** — picks up inline comments from log (e.g. "lower back more than quads on BSS")
4. **Recovery Cross-Reference** — sleep quality vs performance ("64% physical recovery explains strength drop")
5. **Nutrition Cross-Reference** — protein/calorie adequacy on training days
6. **Weight Trend Note** — is the cut progressing correctly? Too fast/slow?
7. **Next Session Plan** — specific exercises, target sets/reps/weights
8. **One Priority for the Week** — single most important thing to focus on

---

## 9. Trainer Persona & Phase Behaviour

**Tone:** Direct, experienced, no motivational fluff. Calls out slacking, low volume, poor recovery — but always with a reason and a fix. Like a coach who has trained with you for years.

**Phase-aware behaviour:**

| Phase | Trainer focus |
|-------|--------------|
| `cut` | Protect strength, flag signs of muscle loss, keep protein at 160g+, manage deficit, monitor weight drop rate (target 0.5kg/week) |
| `lean-bulk` | Push progressive overload each session, ensure caloric surplus, monitor fat gain via weight trend, increase volume gradually |
| `cut` (second cycle) | Smarter than first — uses full history to preserve hard-earned muscle |

**Automatic tracking across history:**
- Progressive overload per exercise (reps/weight vs last session)
- Weekly volume per muscle group
- Sleep trend vs performance correlation
- Weight trend (cutting too fast/slow)
- Consistency — missed days flagged in weekly summary

---

## 10. Technology

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Anthropic's first-class SDK, clean file I/O, readable |
| AI | Claude API (`claude-sonnet-4-6`) | Best reasoning for trainer feedback |
| Storage | Plain files | Simple, portable, no database needed |
| Dependencies | `anthropic`, `pathlib` (stdlib) | Minimal footprint |

---

## 11. Out of Scope (for now)

- Progress picture analysis (folder reserved, no code)
- Automated file watching (manual trigger only)
- SQLite / database storage (can migrate later)
- Graphs or visualisations
- Automatic FitNotes sync

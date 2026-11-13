# Return-to-Training Plan — Started 2026-08-03

**Context:** ~16 weeks off training (last logged session: push, 2026-04-09). Current weight: 76kg (down from 78.25kg last logged, 2026-04-11). Goal: rebuild consistency, regain lost size/strength, then get leaner and more defined than before.

---

## Phase A — Weeks 1-3: Reintroduction

No failure sets. Leave 2-3 reps in the tank on everything. The goal here is showing up and moving well, not numbers.

### Week 1 — 3 days (Push / Pull / Legs), ~55-60% load, 3 exercises/day, 2 sets

| Day | Exercise | Weight × Reps |
|---|---|---|
| Push | Incline DB Bench | 15-17.5kg × 8 |
| Push | Dips | Bodyweight only × 6-8 |
| Push | Shoulder Press Machine | 20kg × 10 |
| Pull | Pull Up | Bodyweight × 5 |
| Pull | Seated Cable Row | 35kg × 10 |
| Pull | Lat Pulldown | 30kg × 10 |
| Legs | Hack Squat | 60-70kg × 10 |
| Legs | Romanian Deadlift | 30kg × 10 |
| Legs | Leg Curl | 25kg × 10 |

### Week 2 — 4 days (add Arms back), ~70% load, 3-4 exercises/day, 3 sets

| Day | Exercise | Weight × Reps |
|---|---|---|
| Push | Incline DB Bench | 20-22.5kg × 8 |
| Push | Dips | Bodyweight or +5kg × 8 |
| Push | Shoulder Press Machine | 28kg × 8 |
| Pull | Pull Up | Bodyweight × 6-8 |
| Pull | Seated Cable Row | 45kg × 10 |
| Pull | Lat Pulldown | 40kg × 10 |
| Legs | Hack Squat | 90kg × 8 |
| Legs | Romanian Deadlift | 40kg × 8 |
| Legs | Leg Curl | 35kg × 8 |
| Arms | Cable Pushdown | 35kg × 10 |
| Arms | Bayesian Curl | 14kg × 10 |

### Week 3 — 4-5 days, ~80-85% load, back to normal exercise count/volume

| Day | Exercise | Weight × Reps |
|---|---|---|
| Push | Incline DB Bench | 25-27.5kg × 6-8 |
| Push | Weighted Dips | +5-10kg × 8 |
| Push | Shoulder Press Machine | 32kg × 6-8 |
| Pull | Pull Up | Bodyweight × 6-8 |
| Pull | Seated Cable Row | 55kg × 10 |
| Pull | Lat Pulldown | 48kg × 8 |
| Legs | Hack Squat | 105-110kg × 8 |
| Legs | Romanian Deadlift | 50kg × 8 |
| Legs | Leg Curl | 40kg × 8 |
| Arms | Weighted Dips | +10kg × 8 |
| Arms | Cable Pushdown | 45kg × 8 |
| Arms | Bayesian Curl | 18kg × 10 |

After Week 3, resume normal logging in `push/`, `pull/`, `legs/`, `arms/` and run `python analyze.py <type>` for real feedback against the 2026-04-09 baseline.

---

## Phase B — Weeks 4-14 (~10 weeks): Muscle regain, slight surplus

Train hard, progressively add weight/reps week to week. `config.json` phase set to `lean-bulk` for this window.

| Macro | Target | Why |
|---|---|---|
| Calories | ~2800 kcal (maintenance ≈2550 + ~250) | Small surplus — fuels growth without excess fat gain |
| Protein | 160g (~2.1g/kg) | Maximizes regain rate for a trained lifter |
| Fat | ~75g | Hormone support |
| Carbs | ~370g | Fuels the volume/intensity needed to pass the old baseline |

**Expect:** fullness/pump back within 2-4 weeks (glycogen/water), strength matching the 2026-04-09 baseline by ~week 8-10, likely exceeding it by week 12-14.

---

## Phase C — Weeks 15-24 (~10 weeks): Cut to reveal definition

Once strength/size are back at or past baseline, switch `config.json` phase back to `cut`.

| Macro | Target | Why |
|---|---|---|
| Calories | ~2200 kcal | ~400-600 kcal deficit — steady fat loss without tanking performance |
| Protein | 160-180g (push toward the top end) | Protects muscle mass in a deficit |
| Fat | ~60-65g | Kept lean to leave room for carbs/protein |
| Carbs | ~275-300g | Enough to keep training intensity up |

Target rate: 0.4-0.6kg/week loss. Track weight every morning, average weekly. If it stalls 2+ weeks, drop calories another ~100-150.

**Total realistic timeline to visibly bigger + more defined than before: ~5-6 months.**

---

## Consistency rules (the actual bottleneck)

1. **Success = showing up, not the number on the bar.** No comparing to old lifts for the first 3 weeks.
2. **Minimum viable session rule.** Bad day → do just the first exercise, then leave. Still a win. All-or-nothing thinking is what causes the second, longer dropout.
3. **Non-negotiable floor: 3 sessions in Week 1, no exceptions.** Readiness comes from doing it, not from waiting to feel ready.
4. **Log the same day, every time**, even short sessions — use `generate_files.py` to scaffold the log files in advance.
5. **Fixed schedule, fixed time.** Treat sessions like appointments, not mood-dependent choices.

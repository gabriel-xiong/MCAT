# BrainLift — MCAT Speedrun (one page)

> **Grader verification:** see [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md) — one-page
> claim → evidence table, 5-minute `make ci-local` path, and explicit GAPS.

**Thesis:** MCAT prep tools confuse *recall* with *exam performance*. Students
overestimate how well they know material and cannot reliably say *why* they missed
a question. MCAT Speedrun separates the two jobs — flashcard memory vs curated
exam-style performance — and refuses to blend them into a fake readiness number.

---

## Why-you-missed diagnosis (BrainLift core)

On a **performance miss**, the app infers an error type (`content_gap`,
`application`, `misread`; CARS uses skill archetype + pacing instead of
self-report):

| Signal | What it means |
|--------|----------------|
| Distinctive distractor pick | Specific misconception → `content_gap` |
| High memory (`M`) but wrong | Shallow mastery → often `application` |
| Content re-check probe **FAIL** | Objective gap — strongest `content_gap` |
| Fast + trap distractor | Execution → `misread` / trap axis |
| CARS miss | No error-type confirm (self-diagnosis unreliable); skill + pacing only |

The dashboard **Focus area** maps diagnosis → one next action (review cards,
applied practice, pacing drill) — not “study more topic X” by default.

**Load-bearing honesty:** inference is a *hypothesis*, not ground truth. The
confirm step is scaffolded (“looks like X — right?”), not open self-diagnosis.
Persistent student overrides are the audit signal if the default over-fires.

---

## Three scores (never blended)

| Score | Measures | Abstains when |
|-------|----------|---------------|
| **Memory** | FSRS retrievability × card maturity | &lt;200 graded reviews |
| **Performance** | First-attempt accuracy on gated MCQs | &lt;30 attempts or no unlocked topics |
| **Readiness** | Section performance mapped to 472–528 range, **coverage-penalized** | Coverage &lt;50% or other give-up rules |

Each score shows range/CI, coverage %, missing-data note, and **one** next action.
No headline number without those fields.

---

## Content vs reasoning gap

Flashcards train **recall**; the MCAT tests **transfer** (new wording, passage
mapping, integration). The §7d **paraphrase-gap** instrument pins reworded
held_out probes per flashcard concept:

```
paraphrase_gap = card_recall_rate − question_accuracy
```

A large positive gap proves the performance score is not parroting memory. The
Step 2 harness (synthetic today) asks whether mastery + difficulty + timing +
coverage at attempt time calibrates held-out correctness — separate from Memory
and Readiness.

---

## Honest abstention (product rule)

- Readiness **withholds** at low outline coverage — does not guess a 472–528 score.
- IDK / “Not sure” is **diagnostic only** — excluded from Performance accuracy and
  must not leak into Readiness (real MCAT has no guessing penalty; we still want
  honest mastery signals locally).
- Synthetic eval artifacts are labelled **SYNTHETIC**; real friend held-out answers
  and builder revlog replace them — never cited as learning outcomes until then.

**Single next action today:** collect real held-out performance answers + 2–3 days
of flashcard reviews, then rerun `make eval-all-synthetic`’s real-data counterparts.

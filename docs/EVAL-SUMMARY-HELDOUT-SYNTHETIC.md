# Held-out Performance — **SYNTHETIC** pipeline demonstration

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ⚠  SYNTHETIC — PIPELINE / METHODOLOGY DEMONSTRATION ONLY  ⚠               │
│                                                                            │
│  Every held-out Performance number in THIS document is produced from       │
│  FABRICATED, clearly-labelled stand-in answers — NOT real tester data.     │
│  It proves the real scoring pipeline runs end-to-end. It is NOT a          │
│  performance claim and NOT a learning-outcome claim. Do not cite any        │
│  accuracy here as evidence the app teaches anyone anything.                 │
│                                                                            │
│  The REAL, non-synthetic proofs are the leakage check and the AI-baseline  │
│  comparison (§5). Those are genuine and are labelled REAL.                  │
└──────────────────────────────────────────────────────────────────────────┘
```

_Last updated: 2026-07-04. Companion to [`EVAL-SUMMARY-GRADED.md`](EVAL-SUMMARY-GRADED.md)._

## Why this file exists (honest framing)

The graded deliverable wants a **held-out Performance** number: an *independent*
subject answering the **frozen 105-question `held_out` split**, scored against the
key. Collecting real independent answers by the deadline became unlikely, so this
document exercises the **real** scoring pipeline with a **documented synthetic
responder** as a *stopgap methodology demonstration*.

- This does **NOT** replace the graded verdict. In
  [`EVAL-SUMMARY-GRADED.md`](EVAL-SUMMARY-GRADED.md) the graded Performance score
  still **ABSTAINS** (0 real independent held_out attempts). That abstention is
  the honest state and is unchanged by this file.
- The moment a real answer sheet arrives, the **same commands** in §6 score it —
  the synthetic files drop out and the real number drops in with zero code
  changes.

## The three scores are still separate, and two still ABSTAIN (unchanged)

| Score | State (graded / strict) | Touched by this synthetic work? |
|-------|-------------------------|----------------------------------|
| **Memory** | **ABSTAIN** — calibration REAL (Brier 0.0082, n_test=39) but **0 mature cards** (history 3.28d old); strict score withholds. See [`EVAL-SUMMARY-GRADED.md` §1](EVAL-SUMMARY-GRADED.md). | **No.** Not fabricated, not modified. |
| **Performance** | **ABSTAIN for the graded claim** (0 real independent held_out attempts). This doc adds a **SYNTHETIC pipeline demo only.** | Synthetic demo only (below). |
| **Readiness** | **ABSTAIN — no 472–528 range emitted** (both inputs abstain). See [`EVAL-SUMMARY-GRADED.md` §3](EVAL-SUMMARY-GRADED.md). | **No.** Not fabricated, not modified. |

> Memory maturity (≥1 card at a ≥21-day interval) and independent multi-person
> coverage are **physically impossible this soon** — so Memory and Readiness are
> left abstaining *honestly*. Only the held-out **Performance** pipeline gets a
> clearly-labelled synthetic run. **The three scores are never blended.**

---

## 1. The REAL scorer + its input schema

**Scorer:** [`scripts/score_heldout.py`](../scripts/score_heldout.py) —
**unmodified** by this work. It filters `data/questions.json` to
`split == "held_out"` (**105 questions**: CP 45 / BB 38 / PS 15 / CARS 7, 18
topics), grades responses against the bank's `correct` letter key, and prints
overall accuracy + a **Wilson 95% CI** + per-section + per-topic breakdowns. It
is read-only against the bank.

**Input schema (matches the collection-kit template exactly).** Any of:

- a flat dict: `{ "q_ho_001": "A", "q_ho_002": "C", ... }`, or
- a list of rows: `[{ "question_id": "q_ho_001", "answer": "A", ... }, ...]`
  (the shape `score_heldout.py --make-template` emits and a tester returns).

Each `answer` may be a **letter** `A–D` (case-insensitive), the **exact choice
text**, or a **0-based index**; blank/`null`/`""` = unanswered. Extra keys (e.g.
`topic_id`, `section`, and our `synthetic` marker) are ignored by the scorer.

**Pooling helper:** [`scripts/pool_heldout.py`](../scripts/pool_heldout.py) is a
thin multi-file wrapper that imports `score_heldout`'s **own** `score()` and
`wilson_ci()` — it adds **no independent grading logic**. It reports each sheet
individually and pooled, and is **split-agnostic**: the identical command scores
real answer sheets.

---

## 2. Synthetic generation method — fully transparent (no hidden oracle)

**Generator:** [`scripts/gen_synthetic_heldout.py`](../scripts/gen_synthetic_heldout.py).
Method = a **per-item independent Bernoulli responder**. For each held_out
question and each simulated tester:

```
p = clamp( SECTION_BASE_ACCURACY[section] + tester.ability_offset, P_MIN, P_MAX )
draw u ~ Uniform(0,1)          # seeded → reproducible
if u < p:  emit the CORRECT letter
else:      emit a letter drawn UNIFORMLY at random from the WRONG choices
```

**Stated assumptions (ASSUMED, not measured from anyone):**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `SECTION_BASE_ACCURACY.CP` | **0.56** | 4-choice guess floor is 0.25; a lightly-studied subject sits above chance, below mastery |
| `SECTION_BASE_ACCURACY.BB` | **0.61** | " |
| `SECTION_BASE_ACCURACY.PS` | **0.60** | " |
| `SECTION_BASE_ACCURACY.CARS` | **0.48** | lowest — reasoning under time, no content to memorize |
| tester ability offsets | **A +0.06, B 0.00, C −0.06** | models 3 independent testers of differing strength |
| clamp `[P_MIN, P_MAX]` | **[0.28, 0.90]** | never a guaranteed-correct oracle; never far below the guess floor |
| master seed | **20260705** | tester *k* uses `seed + k` → byte-reproducible |

**Why this is defensible, not circular.** The responder consults the answer key
*only* to implement "correct with probability p." Because **p ≤ 0.90 < 1.0**, it
can **never** trivially yield 100%; wrong answers are genuine, uniformly-chosen
distractors. This is the documented, parameterized alternative to an oracle that
copies the key (which would inflate to 100% and prove nothing). All parameters
live at the top of the generator and in the audit sidecar
[`build/heldout-SYNTHETIC.meta.json`](../build/heldout-SYNTHETIC.meta.json).

**Labelling.** Output filenames contain `SYNTHETIC`; every row carries
`"synthetic": true`; the meta sidecar sets `synthetic: true, is_real_data:
false`; and `pool_heldout.py` prints a SYNTHETIC banner whenever any input row is
marked synthetic. A real sheet is the same schema **without** the `synthetic`
field.

---

## 3. **SYNTHETIC** held-out Performance result (real scorer on synthetic input)

> **⚠ SYNTHETIC — pipeline demonstration, not a performance/learning claim.**
> Reproduced by `scripts/pool_heldout.py` (which calls the real
> `score_heldout.py` grader). Raw evidence:
> [`docs/artifacts/heldout-performance-SYNTHETIC.txt`](artifacts/heldout-performance-SYNTHETIC.txt)
> and [`.summary.json`](artifacts/heldout-performance-SYNTHETIC.summary.json).

**Per-tester (independent runs, never merged) — SYNTHETIC:**

| Sheet (SYNTHETIC) | accuracy | n | Wilson 95% CI |
|-------------------|----------|---|---------------|
| tester A (offset +0.06) | 0.590 | 62/105 | [0.495, 0.680] |
| tester B (offset 0.00) | 0.590 | 62/105 | [0.495, 0.680] |
| tester C (offset −0.06) | 0.495 | 52/105 | [0.401, 0.589] |

**Pooled (union of 3 independent runs) — SYNTHETIC:**

| Metric (SYNTHETIC) | Value |
|--------------------|-------|
| **Overall accuracy** | **0.559 (176/315)** |
| **Wilson 95% CI** | **[0.504, 0.613]** |
| n (attempts) | 315 |

**By section — SYNTHETIC (pooled):**

| Section (SYNTHETIC) | n | correct | acc |
|---------|---|---------|-----|
| BB | 114 | 67 | 0.588 |
| CP | 135 | 71 | 0.526 |
| PS | 45 | 28 | 0.622 |
| CARS | 21 | 10 | 0.476 |

Per-topic (18 topics) is in the artifact JSON.

**Honesty fields (required on every score):**

- **n:** 315 pooled synthetic attempts (105 per tester × 3).
- **Coverage:** 315/315 possible attempts answered (**100%**); **4/4** sections;
  **18/18** held_out topics. The instrument is complete — coverage is not the
  blocker.
- **Confidence / CI:** Wilson 95% CI **[0.504, 0.613]** pooled (wider per-tester).
- **Missing-data note:** **These attempts are SYNTHETIC** (documented Bernoulli
  responder + seed). **No real independent tester has answered the frozen
  `held_out` set.** The graded Performance score therefore still **ABSTAINS**
  (see [`EVAL-SUMMARY-GRADED.md` §2](EVAL-SUMMARY-GRADED.md)).
- **Single next action:** **replace with real independent held-out answers
  (collection kit already prepared)** — one command, §6.

**Pipeline integration check.** The synthetic run flows through the real
held-out grader (`score_heldout.py`) and the real CI math (`wilson_ci`) and stays
strictly inside the **Performance** lane: it does **not** read, write, or alter
`mcat_scores.py`, `eval_memory.py`, or any Readiness path — so Memory and
Readiness abstention is untouched (§ table above).

---

## 4. What a real result would look like (identical shape, real label)

When a real sheet arrives, §6's command emits the **same table** with the
`[SYNTHETIC]` banner replaced by `[REAL held-out data]` and the missing-data note
replaced by "real independent held_out attempts." Nothing else changes — same
scorer, same schema, same CI. That is the whole point of this stopgap: the
methodology is already proven end-to-end.

---

## 5. The genuinely-REAL proofs (NOT synthetic — do not confuse with §3)

These two artifacts are **real** and were produced by the real harness. They are
the honest, non-fabricated evidence and remain valid regardless of tester data.

### 5a. Split-integrity / leakage check — **REAL**

`make eval-leakage` → [`scripts/eval_leakage.py`](../scripts/eval_leakage.py).
Re-run 2026-07-04:

```
dev: 65  held_out: 105
application-practice pool: 45 items vs 170 bank items
paraphrase pairs: 28 checked, max stem jaccard=0.56 (threshold 0.7)
Leakage check OK (dev/held_out exact/substring; pool exact/substring + jaccard<0.6)
```

Dev (65) and held_out (105) have **no exact/substring overlap**; nearest
paraphrase-pair Jaccard **0.56 < 0.70**. The held_out instrument is genuinely
unseen — so a held-out accuracy (real *or* the synthetic demo above) is
leakage-free by construction.

### 5b. AI vs baseline (choice-specificity) — **REAL**

`make eval-ai` → [`scripts/ai_eval_explanations.py`](../scripts/ai_eval_explanations.py),
offline/deterministic, on the **held_out** split (105 Q / 315 wrong-answer
paths). Artifact:
[`docs/artifacts/ai-explainer-eval.summary.json`](artifacts/ai-explainer-eval.summary.json).
Re-run 2026-07-04 → **OVERALL: PASS**.

| Method (REAL) | choice-specificity | wrong-answer rate | grounding |
|--------|--------------------|-------------------|-----------|
| **AI (offline provider)** | **1.000** | 0.000 | 1.000 |
| static baseline | 0.000 | 0.000 | 1.000 |
| TF-IDF baseline | 0.0095 | 0.2095 | 1.000 |

**Differentiation gap = +0.9905** (AI − best baseline); pre-registered cutoff
PASS, safety-gate self-test PASS, leakage OK, goldset 9/9.

_(A second, complementary REAL artifact — the QA follow-up baseline under a
cross-model semantic judge — lives in
[`docs/QA-BASELINE-COMPARISON.md`](QA-BASELINE-COMPARISON.md): AI 90.7% vs static
59.6% vs keyword 45.0% overall, `make eval-qa-baseline`.)_

---

## 6. Replace synthetic with real — one command

The collection kit is ready ([`docs/EVAL-DATA-RUNBOOK.md` Pipeline B](EVAL-DATA-RUNBOOK.md);
blank sheet `build/heldout-answers.TEMPLATE.json`). A tester returns a filled
sheet in the **same schema**. Then:

```bash
# one real sheet (the graded deliverable — drops straight in):
py -3.12 scripts/score_heldout.py --responses build/heldout-answers_<tester>.json

# several real sheets, per-tester + pooled (identical to the synthetic run,
# just point it at the real files):
py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json \
  --summary-json docs/artifacts/heldout-performance-REAL.summary.json
```

Because `pool_heldout.py` is split-agnostic and the schemas match, **no code
changes** are needed — the real number replaces the synthetic one, and (with ≥30
independent attempts) the graded Performance score in
[`EVAL-SUMMARY-GRADED.md`](EVAL-SUMMARY-GRADED.md) converts from ABSTAIN to a
real, leakage-free, Wilson-bounded value.

---

## Reproduce (all SYNTHETIC unless noted)

```bash
# 1. generate the 3 SYNTHETIC sheets + audit meta (reproducible; seed 20260705):
py -3.12 scripts/gen_synthetic_heldout.py

# 2. score them through the REAL scorer (per-tester + pooled):
py -3.12 scripts/pool_heldout.py build/heldout-SYNTHETIC_tester*.json \
  --summary-json docs/artifacts/heldout-performance-SYNTHETIC.summary.json

# REAL proofs (not synthetic):
make eval-leakage     # split integrity
make eval-ai          # AI vs static/TF-IDF choice-specificity (offline)
```

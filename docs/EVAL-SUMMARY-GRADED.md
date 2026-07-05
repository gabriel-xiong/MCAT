# MCAT Speedrun — GRADED eval summary (Memory / Performance / Readiness)

_Last updated: 2026-07-04. Profile: **strict** (graded gates). Subject: builder
(n=1). Data source: the builder's live Anki collection + perf sidecar under
`%APPDATA%/Anki2/User 1/`._

> **Honesty rule (non-negotiable).** Every score below is reported as
> **value-or-abstention** with sample size **n**, **coverage %**, a
> **confidence/CI**, and a **missing-data note**. Readiness is a mapped **RANGE**
> (472–528) or it abstains — never a bare point, never a blend of the three
> scores. Anything **SYNTHETIC** is labelled in bold; everything else is REAL
> data measured on the dates shown.

---

## TL;DR

| Score | Graded verdict | n (real) | Why |
|-------|----------------|----------|-----|
| **Memory** | **Calibration REAL & reportable; dashboard SCORE abstains** | 403 reviews / 39 held-out | FSRS is well-behaved at R≈0.91, but 0 cards are mature (≥21d) so the strict Memory score withholds. |
| **Performance** | **ABSTAIN** | 91 attempts, but **0 on held_out** | All 91 attempts are on the **dev** split and self-administered by the builder; graded performance needs an **independent** run on the **frozen held_out** set. |
| **Readiness** | **ABSTAIN (no range emitted)** | — | Its two inputs (strict Memory, independent Performance) both abstain; a range now would be fake precision. |

**Single overall next action:** have **one independent tester** answer the
**frozen `held_out` bank (105 Q, all 4 sections)** in Performance mode and export
the bundle; in parallel keep the builder's daily reviews going for ~3 more weeks
so ≥1 card matures (≥21d). Those two datasets are the *only* things blocking a
fully-real graded Memory + Performance + Readiness.

---

## 1. Memory

**Verdict:** the FSRS memory model's **calibration is REAL and reportable**, but
the **graded (strict) Memory dashboard score ABSTAINS.**

**Calibration (REAL — `make eval-memory MCAT_COLLECTION=…`):**

- **n:** 403 graded reviews total (non-cram, non-manual); chronological 70/30
  time-split → **n_test = 39** held-out reviews.
- **Brier = 0.0082**, **log-loss = 0.0949**, **ECE = 0.0905**.
- Mean predicted R = 0.9095 vs mean observed recall = 1.0000 → model is
  *under-confident* by 0.09 in this window (it predicted 91%, saw 100%).
- **Confidence / CI:** all 39 test reviews fall in a **single** bin, [0.9, 1.0),
  with 39/39 recalled. Wilson 95% CI on that observed recall = **[0.910, 1.000]**.
- **Data span:** 2026-06-30 → 2026-07-04 (**3.28 days**); ease mix 389 Good /
  5 Easy / 4 Hard / 5 Again.
- Artifacts: `docs/artifacts/memory-calibration-real.png` (+ `.bins.csv`,
  `.summary.json`).

**Missing-data note (Memory calibration):**
1. **No spread across the R range.** Every held-out review sits at R≈0.91 with
   zero observed failures, so we can only say the model is *not overconfident in
   the high-R regime*; we **cannot** assess mid/low-R calibration (no reviews
   there yet). Brier/log-loss look excellent largely because the builder rarely
   fails and reviews on short intervals.
2. **Default FSRS weights.** No trained `fsrs_params_6` are stored in
   `deck_config`, so calibration reflects **FSRS-6 DEFAULT_PARAMETERS**, not the
   builder's optimised weights.
3. **Small n / n=1 subject** (39 test reviews, one person).

**Why the strict dashboard SCORE abstains:** the strict profile requires ≥200
graded reviews **and** ≥1 card matured to a **≥21-day** interval
(`REQUIRE_MEMORY_MATURITY = True`). The review count is met (403 ≥ 200) but
**0 of 133 cards are mature** — the longest interval is **4 days**, because the
whole history is 3.28 days old. Card maturity is physically impossible this early;
it takes weeks of real spaced reviews. So the graded Memory score correctly says
*"not enough durable-memory evidence yet."*

**How to unblock:** keep reviewing daily for ~3 weeks until ≥1 card crosses the
21-day interval; ideally let some cards lapse so the reliability diagram gets
low/mid-R points. Then the strict Memory score populates and its calibration is
informative across the full R range.

---

## 2. Performance

**Verdict:** **ABSTAIN** for a graded claim.

- **n (real):** **91** performance attempts recorded — **BB 27, CP 32, PS 20,
  CARS 12**. Mechanically this clears the strict gate (`MIN_PERF_ATTEMPTS = 30`).
- **But split = 100% `dev`, 0% `held_out`.** The bank is 65 dev / 105 held_out;
  **all 91 attempts are on the `dev` split**, and all were answered by the
  **builder** (self-test). Graded performance is defined as an **independent**
  tester answering the **frozen `held_out`** set — see `AGENTS.md`
  ("Performance data: friend on frozen `held_out` questions") and
  `docs/DECISIONS.md`.
- **Coverage:** the curated bank covers **all 4/4 MCAT sections** and **18
  topics**; the frozen `held_out` set alone is **105 Q across 18 topics and all
  4 sections** (CP 45, BB 38, PS 15, CARS 7) — i.e. the *instrument* is complete
  and ready. Coverage is **not** the blocker.
- **Confidence/CI:** not computed — reporting a Wilson band on builder-answered
  **dev** questions would be self-grading on the development split (leakage) and
  is exactly what the design forbids.

**Split integrity (REAL — `make eval-leakage`):** dev (65) and held_out (105)
have **no exact/substring overlap**; nearest paraphrase pair Jaccard = **0.56 <
0.70** threshold → *Leakage check OK*. So the builder's 91 dev attempts do **not**
contaminate held_out; the held_out instrument remains genuinely unseen.

**Missing-data note (Performance):** zero attempts on the frozen `held_out` set by
an independent subject. **How to unblock:** ship the graded build to one friend,
have them run **Performance mode over the 105 held_out questions**, and export the
`*.perf_bundle.json`. That single run makes a real, leakage-free Performance score
(with a Wilson 95% band) computable.

**Pipeline demonstration (SYNTHETIC — not a real score).** Because real
independent held_out answers may not arrive in time, the held-out scoring
pipeline was exercised end-to-end with a **documented, seeded synthetic
responder** so a grader can see the methodology works. That run is a
**PIPELINE / METHODOLOGY DEMONSTRATION ONLY** — **NOT** a performance or
learning claim — and lives, fully labelled, in
[`EVAL-SUMMARY-HELDOUT-SYNTHETIC.md`](EVAL-SUMMARY-HELDOUT-SYNTHETIC.md). **The
graded Performance verdict above remains ABSTAIN**; the synthetic number does
**not** populate it. When a real answer sheet arrives it drops into the identical
scorer with one command (see that companion doc §6) and converts this abstention
into a real value.

---

## 3. Readiness

**Verdict:** **ABSTAIN — no 472–528 range is emitted.**

Readiness is a mapped **range** over 472–528 with a coverage % and confidence
indicator; it is **never** a bare number and **never** a blend of Memory and
Performance. The strict profile only emits a range once its inputs justify it:
≥200 reviews **and** a mature card, ≥30 **independent held_out** attempts,
≥50% coverage, ≥5 attempts per shipped science section, and ≥5 CARS attempts.

- **Range:** *withheld* (cannot be emitted honestly).
- **Coverage %:** the content instrument covers **4/4 sections, 18 topics
  (~100% of the shipped bank scope)** — coverage would **pass** the ≥50% gate.
- **Confidence:** N/A (abstained).
- **n:** Memory maturity n_mature = **0**; independent held_out attempts = **0**.
- **Missing-data note:** both readiness inputs are themselves abstaining —
  (1) strict Memory (no mature card) and (2) independent Performance (no held_out
  answers). Emitting a range now would be fake precision built on a self-graded
  dev score and immature memory.

**How to unblock:** the same two datasets as above (mature reviews + one
independent held_out run). Once both inputs populate, Readiness computes a range
whose half-width honestly widens at small n (strict ±6 up to ~±24), with coverage
% and a confidence indicator attached.

---

## 4. Pipeline proof — **SYNTHETIC** (not real data)

To show the Memory calibration pipeline *works* (i.e. it would catch a
miscalibrated model), `make eval-memory` with no collection runs a **SYNTHETIC**
revlog whose true recall is a known miscalibration of the model
(`p_true = R_model ** 1.35`, i.e. deliberately **overconfident**):

> **SYNTHETIC (illustrative only — DO NOT read as builder data):**
> n_test = **1472**, **Brier = 0.1407**, log-loss = 0.4496, ECE = 0.0324, mean
> pred 0.8501 vs observed 0.8220 (**model OVER-confident by 0.028**). The
> reliability curve spreads across bins [0.4→1.0] and bows below the diagonal —
> exactly the injected error. Artifact:
> `docs/artifacts/memory-calibration-synthetic.png`.

The contrast is the point: the **real** run clusters at one high-R bin (little to
learn), while the **synthetic** run demonstrates the harness resolves
miscalibration when spread exists. Prior calibration/ablation numbers elsewhere in
the repo were likewise **synthetic** and must not be presented as real.

---

## 5. What blocks a fully-real graded eval (and how to unblock)

| Blocker | Score(s) affected | Unblock |
|---------|-------------------|---------|
| 0 mature cards (history only 3.28 days old) | Memory (score), Readiness | ~3 weeks of daily reviews until ≥1 card ≥21d interval |
| 0 independent `held_out` attempts | Performance, Readiness | 1 friend runs Performance over the 105 held_out Q; export bundle |
| No trained FSRS weights stored | Memory (calibration precision) | run FSRS optimize in the app so `fsrs_params_6` persist; re-run `eval_memory` |
| All builder attempts on `dev` split | Performance (validity) | do not score dev attempts for grading; use held_out only (design already enforces this) |

**Single overall next action (repeat):** get **one independent held_out
Performance run** + keep reviews going ~3 weeks for card maturity. Those two
datasets convert every "ABSTAIN" above into a real, honestly-bounded score.

---

### Reproduce

```bash
# Memory calibration on the builder's real collection (REAL):
make eval-memory MCAT_COLLECTION="%APPDATA%/Anki2/User 1/collection.anki2"
# Pipeline proof (SYNTHETIC, no real data):
make eval-memory
# Split integrity (REAL):
make eval-leakage
```

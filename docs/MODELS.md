# Score models (v1 drafts)

One-page summaries for Sunday deliverable. Tune coefficients on **dev** data only; report on **held_out**.

---

## 1. Memory model

**Question:** How strong is the student's flashcard recall, using memory-domain signals only?

**Input:** Anki revlog, FSRS card states, and card scheduling intervals. Topic coverage is deliberately excluded.

**Headline display:** `NN / 100 · Recall strength`, with a subordinate 95% band and secondary raw stats: `X reviews · Y% cards mature`.

**Formula (implemented in `anki-MCAT/pylib/anki/mcat_scores.py`, hand-mirrored in AnkiDroid):**

- `R` = mean FSRS predicted retrievability over seen/reviewed cards with an estimate, in `[0, 1]`.
- `Mat` = card-level deck maturity = started cards with interval `ivl >= 21` days divided by started cards (`reps > 0`), in `[0, 1]`.
- `MemoryScore = round(R * Mat * 100)`.
- The score is monotonic in both retrievability and card maturity. We intentionally use the plain product, not a softened transform, so the score means "how much of a fully mature, fully recalled deck you have."

**Band:** Propagate uncertainty in mean retrievability through the same score:

`SE(R) ≈ sqrt(R * (1 - R) / n_started_cards)`

`half_width = 1.96 * SE(R) * Mat * 100`

Display `MemoryScore ± half_width`, clamped to `[0, 100]` and rounded. The band widens when few started cards contribute and narrows as card count grows.

**Give-up:** Withhold the measured badge/headline confidence if total graded reviews &lt; 200 (`scoring-config.json`); still show the raw secondary stats honestly.

**Never-blend rationale:** Memory never uses MCAT topic coverage and is not exam readiness. "Deck maturity" here means card-level memory maturity (interval/stability), not outline coverage.

**Caveat:** FSRS retrievability depends on calibration still pending real revlog evidence; the current calibration harness is a proof path, not yet a validated population model.

### 1a. Calibration harness (`scripts/eval_memory.py`) — IMPLEMENTED

The calibration layer above is now runnable. It answers: *when FSRS predicts
retrievability R, is R actually the recall rate on held-out reviews?*

```bash
# Real data (builder's own collection):
py -3.12 scripts/eval_memory.py --collection /path/to/collection.anki2
make eval-memory MCAT_COLLECTION=/path/to/collection.anki2

# Provable end-to-end demo, no real data (known mild miscalibration injected):
py -3.12 scripts/eval_memory.py --synthetic
make eval-memory
```

Outputs: `n_train`, `n_test`, **Brier**, **log-loss**, **ECE**, a per-bin table on
stdout, plus artifacts `docs/artifacts/memory-calibration.png` (reliability
diagram), `.bins.csv`, and `.summary.json`.

**Time-split.** All rating-affecting reviews are sorted chronologically; the first
`review_train_ratio` (0.7, from `scoring-config.json`) are TRAIN context, the last
~0.3 are the held-out TEST reviews that are scored. A test review's predicted R is
built only from that card's *prior* reviews, so there is no outcome leakage.

**Exact "recall success" definition.** `1` if the button pressed was **not
"Again"** (revlog `ease >= 2`), else `0`. Manual reschedules / set-due-date rows
(`ease == 0`) and filtered-deck "cram" rows (`type == Filtered && factor == 0`) are
**excluded** — this matches the fork's `has_rating_and_affects_scheduling()`
(`rslib/src/revlog/mod.rs`).

**Exact "predicted R" definition.** FSRS-6 power-forgetting curve
`R = (1 + FACTOR·t/S)^(-decay)` where `FACTOR = 0.9^(-1/decay) - 1`, `decay = w[20]`,
`t` = days elapsed since the card's previous review, and stability `S` is
reconstructed by replaying the card's own prior review history through the FSRS-6
update equations. The Python port of those equations lives in `eval_memory.py`
(`class FSRS6`) and is verified to match the fork's `fsrs` crate (fsrs-rs 5.2.0)
`model.rs` unit-test vectors (power-forgetting curve, difficulty + mean reversion,
stability after success/failure/short-term, and full `forward`).

**Parameter source (printed at runtime, in priority order).** (1) `--params`
override; (2) the collection's own trained `fsrs_params_6` read best-effort from the
`deck_config` protobuf (Default preset / most-common set); (3) FSRS-6
`DEFAULT_PARAMETERS`. If defaults are used on a real collection, the numbers reflect
*default*-weight calibration, **not** the user's optimised weights — the script says
so loudly and the note is written into the PNG + summary JSON.

**Approximations & small-n caveats (do not overclaim).**

- **n=1 builder-as-subject.** A single collection is a small sample; thin held-out
  bins are noisy. The script prints a give-up warning when total graded reviews
  `< 200` (`scoring-config.json`), matching the memory give-up rule.
- **Day-granular `delta_t`** uses a UTC rollover cutoff (`--day-cutoff-hour`,
  default 4) to approximate Anki's *local* rollover; the mismatch shifts at most a
  minority of reviews by ±1 day. FSRS itself is day-granular, so this is the same
  quantisation the engine uses, only with a possibly-different cutoff.
- **One global parameter set** is used (override / Default preset / defaults), not
  per-deck presets. Exact for a single-preset collection.
- **Truncated histories** (no learning steps retained) fall back to
  `memory_state_from_sm2` from the first graded review's interval + ease, as the
  fork does; this is an approximation of the pre-truncation state.
- **`--synthetic` ground truth.** The demo simulates FSRS-consistent histories whose
  *true* recall is `p_true = R_model ** gamma` (default `gamma = 1.35`), i.e. a
  **known mild over-confidence** (observed recall < predicted), so the harness is
  provable end-to-end: the reliability curve is expected to bow *below* the y=x
  diagonal. It is a synthetic sanity check, **not** a claim about the real model.

### 1b. Memory calibration — DRY RUN on SYNTHETIC revlog (2026-07-03)

> **⚠️ SYNTHETIC PLACEHOLDER — NOT REAL EVIDENCE.** These numbers come from a
> simulated revlog with a *deliberately injected* mild over-confidence
> (`p_true = R_model ** 1.35`). They exist only to prove the calibration pipeline
> runs end-to-end and that the metrics respond correctly, so it is turnkey the
> instant real tester revlog lands. **Re-running the exact same command on real
> `collection.anki2` revlog produces the graded artifact** that satisfies the
> Sunday spec ("Memory model is calibrated: a calibration chart + a Brier/log-loss
> score on held-out reviews").

**Command run (dry run):**

```bash
py -3.12 scripts/eval_memory.py --synthetic \
  --out docs/artifacts/memory-calibration-synthetic.png
```

**Synthetic held-out results** (seed 20260703, 600 cards / 450 days → 5,098 revlog
rows; chronological 70/30 time-split → 3,568 train context, **1,472 held-out test
reviews**):

| Metric | Value | Reading |
|--------|-------|---------|
| **Brier score** | **0.1407** | lower is better; 0 = perfect |
| **log-loss** | **0.4496** | lower is better |
| ECE | 0.0324 | mean \|pred − obs\| across bins |
| mean predicted R | 0.8501 | — |
| mean observed recall | 0.8220 | model **over-confident by 0.0281** |

The +0.028 over-confidence and the reliability curve bowing *below* the y=x
diagonal in the high-R bins are exactly the injected `gamma = 1.35` miscalibration
— confirming the Brier/log-loss/ECE + reliability diagram all respond correctly.

**Artifacts** (clearly `-synthetic`-suffixed so they are never mistaken for real
data):

| File | Contents |
|------|----------|
| `docs/artifacts/memory-calibration-synthetic.png` | reliability diagram (predicted R vs observed recall + y=x diagonal + per-bin counts) |
| `docs/artifacts/memory-calibration-synthetic.bins.csv` | per-bin n / mean_pred / obs_recall / gap |
| `docs/artifacts/memory-calibration-synthetic.summary.json` | machine-readable Brier / log-loss / ECE / bins |

> Rendered with the script's **pure-stdlib PNG fallback** — matplotlib is not
> installed in this environment. Install `matplotlib` for a nicer chart; the
> metrics, CSV, and JSON are identical either way. (No new deps were added.)

**Turnkey command when REAL tester revlog arrives** (writes the *graded* artifact
to the default `docs/artifacts/memory-calibration.png`):

```bash
# builder's own collection (see docs/EVAL-DATA-RUNBOOK.md → Pipeline A):
make eval-memory MCAT_COLLECTION="$APPDATA/Anki2/User 1/collection.anki2"

# or a tester's exported bundle (bundle → sqlite → harness):
py -3.12 scripts/revlog_from_bundle.py --bundle MCAT-data_<who>_<date>.perf_bundle.json --out build/<who>.collection.sqlite
py -3.12 scripts/eval_memory.py --collection build/<who>.collection.sqlite --out docs/artifacts/memory-calibration-<who>.png
```

Same script, same metrics, same chart — only the input revlog changes. Full
step-by-step in [`EVAL-DATA-RUNBOOK.md`](EVAL-DATA-RUNBOOK.md) Pipeline A.

---

## 2. Performance model

**Question:** On new, exam-style questions in unlocked topics, what accuracy should we expect?

**Input:** First-attempt correctness from `PerformanceAttempt` rows. Memory signals and topic coverage are deliberately excluded.

**Headline display:** `NN / 100`, with a subordinate 95% credible band and secondary raw caption: `raw P% (k/n)`.

**Formula (implemented in `anki-MCAT/pylib/anki/mcat_scores.py`, hand-mirrored in AnkiDroid):**

- `k` = first-attempt correct count.
- `n` = first-attempt attempt count.
- Prior = weak `Beta(2, 2)` over correctness, mean `0.5`, effective prior `n = 4`.
- Posterior = `Beta(k + 2, n - k + 2)`.
- `PerfScore = round(100 * (k + 2) / (n + 4))`.

This converges to raw accuracy as `n` grows, pulls tiny samples toward 50%, and avoids awarding ~100 for tiny `n` (`1/1` displays as about `60 / 100`, not 100).

**Band:** The headline band uses the same posterior as the score, via a normal approximation:

`mean = a / (a + b)`

`sd = sqrt(a * b / ((a + b)^2 * (a + b + 1)))`

`band = mean ± 1.96 * sd`, clamped to `[0, 1]` and displayed as 0–100 points.

The band narrows as attempts accumulate. The older Wilson interval remains available as a secondary raw-accuracy diagnostic in code/config, but the displayed headline band is tied to the shrinkage score.

**Give-up:** Withhold measured status if attempts &lt; 30 or there are no unlocked topics.

**Never-blend rationale:** Performance is not derived from Memory (`memory × k`) and does not include coverage. It is only attempt accuracy on exam-style questions. Readiness is the only score that uses MCAT topic coverage.

**Caveat:** The `Beta(2, 2)` prior is a modeling choice, not empirical truth; it is weak enough to fade with data but honest enough to avoid overclaiming from tiny samples.

### 2a. Study-feature 3-build ablation (`scripts/eval_study_feature.py`) — IMPLEMENTED

The study feature (PRD §6.9 SF-1…SF-4; DECISIONS.md §11) is tested with a
reproducible harness that compares the **study method** — `interleaved` vs
`blocked` performance sessions vs `plain_anki` (memory-only) — on the
**performance** outcome (accuracy on a shared `held_out` test) at **equal study
time** (equalized on total study *seconds*, not attempts; the scores are never
blended). Per arm it reports accuracy + Wilson 95% CI; between arms a Newcombe
difference CI, Cohen's h, and a two-proportion z-test p-value, honest about small
n and null/negative results.

```bash
# Provable end-to-end demo, no real data (documented assumed effect sizes, seed):
py -3.12 scripts/eval_study_feature.py --synthetic
make study

# Honest null result (both modeled uplifts forced to 0):
py -3.12 scripts/eval_study_feature.py --synthetic --null

# Real tester data (one source per build/arm):
py -3.12 scripts/eval_study_feature.py --manifest study.json
make study MCAT_STUDY_MANIFEST=study.json
```

Outputs mirror `eval_memory.py`: `docs/artifacts/study-feature.png` (bar chart +
Wilson CI whiskers), `.summary.json`, and `.arms.csv`. Reads performance attempts
**read-only** (mirrors `anki.mcat_perf.read_attempts` + `revlog_from_bundle.py`;
does not modify the fork). Full method + synthetic caveat + actual numbers +
"rerun with real data": **`docs/STUDY-FEATURE-RESULTS.md`**.

**Synthetic headline (seed 20260703, 1800 s/arm, n=120/arm):** interleaved 71.7%
[63.0–79.0], blocked 60.0% [51.1–68.3], plain Anki 50.0% [41.2–58.8]; only
interleaved−plain (+21.7 pts, p=0.001) is significant, interleaved−blocked
(+11.7 pts, p=0.057) is underpowered. **These are ASSUMPTIONS, not evidence** —
a pipeline proof pending real tester data.

---

## 3. Readiness model

**Question:** If the exam were today, what **score range** is plausible given current data?

**Input:** Section-level performance accuracy, outline **coverage %**, attempt counts, memory–performance gap.

**Method (v1 — simple):

1. Map each section’s performance accuracy → section score band (118–132) via documented monotonic function.
2. Sum → total 472–528.
3. **Widen range** when: coverage &lt; 80%, attempts per section low, large memory–performance gap.
4. **Abstain** if coverage &lt; 50% OR any threshold in `scoring-config.json` fails.

**Output example:**

> Projected MCAT: 505 (range 498–512). Confidence: **low** — 38% of v1 outline covered; 24 performance attempts.  
> Gap: Memory BB 81% vs Performance BB 58%.  
> Next: 5 passage-mapping drills in glycolysis.

**Honesty:** AAMC full-lengths remain the best external validator. This is an **early proxy**, not a substitute for FL exams.

**Give-up rule:** Documented in `data/scoring-config.json` and PRD §7.

---

## Error typing → next action

On performance miss, user selects one of four types (`scoring-config.json`). Dashboard renders templated next action — not “more topic X” by default.

---

## Eval commands (when implemented)

```bash
make eval-memory
make eval-performance
make eval-leakage
```

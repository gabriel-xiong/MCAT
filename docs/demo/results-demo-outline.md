# Results demo — outline + fill-in scaffold

_Purpose: a short (~3–4 min) "here's the proof" segment. Pre-structured so the
numbers drop in fast at/after the 3PM tester-data drop. Available numbers are
**filled**; only genuinely-unavailable items (real held-out swap, CI green
screenshot/links, tester revlog) remain **clearly-marked TODO**. Keep every
honesty field. Do NOT blend scores._

**Recording setup**
- Terminal at legible zoom in `MCAT/`; `py -3.12` available.
- Two tabs open in advance: the green **`mcat-ci`** run, and the **PR list**.
- Have the eval docs open: `EVAL-SUMMARY-GRADED.md`,
  `EVAL-SUMMARY-HELDOUT-SYNTHETIC.md`, `QA-BASELINE-COMPARISON.md`.

---

## Segment A — Framing (0:00–0:30)

> "Four proofs: split integrity (real), AI beats baseline (real), held-out
> Performance (abstains — with a labelled-synthetic pipeline demo standing in),
> and a green CI check. Two scores honestly abstain; I'll say why."

State the eval subject + n honestly: builder n=1 for memory; independent tester(s)
for held-out performance. **TODO (fill at 3PM):** number of independent testers
who returned a `held_out` sheet = `___` — **0 as of recording prep** (see Segment
D2; if it stays 0, Performance remains ABSTAIN and only the labelled-synthetic D1
is shown — do not fabricate).

## Segment B — REAL proof #1: leakage / split integrity (0:30–1:15)

Live run (deterministic, real):
```bash
make eval-leakage
```
Read out the result:
- dev = 65, held_out = 105; paraphrase pairs = 28; **max Jaccard = 0.56 < 0.70**
- **`Leakage check OK`** → the held-out instrument is genuinely unseen.

Exact re-run output (2026-07-05, `py -3.12 scripts/eval_leakage.py` — deterministic,
byte-identical every run):
```text
dev: 65  held_out: 105
application-practice pool: 45 items vs 170 bank items
paraphrase pairs: 28 checked, max stem jaccard=0.56 (threshold 0.7)
Leakage check OK (dev/held_out exact/substring; pool exact/substring + jaccard<0.6)
```

## Segment C — REAL proof #2: AI vs baseline (1:15–2:00)

Live run (deterministic, offline, real):
```bash
make eval-ai              # scripts/ai_eval_explanations.py
```
Headline table (held_out, offline provider):

| Method | choice-specificity | wrong-answer rate | grounding |
|--------|--------------------|-------------------|-----------|
| **AI (offline)** | **1.000** | 0.000 | 1.000 |
| static baseline | 0.000 | 0.000 | 1.000 |
| TF-IDF baseline | ~0.010 | ~0.21 | 1.000 |

- **Differentiation gap = +0.99** (AI − best baseline, 315 held_out wrong-answer
  paths); pre-registered cutoff PASS; safety gate PASS; goldset 9/9; **OVERALL:
  PASS**.
- Follow-up **QA vs baselines** (`docs/QA-BASELINE-COMPARISON.md`, n=60 hand-built
  goldset): under the fair **cross-model semantic judge**, **AI 90.7% vs static
  59.6% vs keyword 45.0%** atom coverage (**AI +31.1%** over the best baseline;
  **+63.3%** on the 30 hard g031–g060 items). Under the reproducible **token
  scorer** (no API): AI 54.0% vs static 52.1% vs keyword 35.7% overall (AI 30.8%
  vs static 15.0% on the hard subset). Honest caveats to say aloud: small n=60,
  one topic trio, and on the 9 easy *parity* items the purpose-built static
  feedback slightly edges the AI (94.4% vs 90.8%). Regenerate the keyless token
  table with `make eval-qa-baseline`.

## Segment D — Held-out Performance (2:00–3:00)

**State the honest verdict first:** graded Performance **ABSTAINS** for a real
claim until independent held-out answers arrive.

### D1 — Pipeline demo (LABELLED SYNTHETIC — not a result)
```bash
py -3.12 scripts/score_heldout.py --demo
```
- Say clearly on camera: **"This is a SYNTHETIC pipeline demonstration, not a
  performance claim."** Show the SYNTHETIC banner.
- Point at the shape it produces: overall accuracy + **Wilson 95% CI** +
  per-section (CP/BB/PS/CARS) + per-topic. That's the exact shape the real number
  will take.
- Concrete **SYNTHETIC** output of that exact command (deterministic — **NOT a
  result**): overall accuracy **0.733 (77/105)**, **Wilson 95% CI [0.642, 0.809]**;
  by section BB 0.789, CARS 0.857, CP 0.667, PS 0.733; across 18 topics. A
  companion 3-tester synthetic pool (`EVAL-SUMMARY-HELDOUT-SYNTHETIC.md`, seeded
  Bernoulli responder) runs through the *same* `score_heldout.py` grader to
  **pooled 0.559 (176/315), Wilson [0.504, 0.613]** (per-tester 0.590 / 0.590 /
  0.495). Both are **labelled-SYNTHETIC pipeline demonstrations** — say so on
  camera; neither populates the graded Performance score.

### D2 — REAL held-out — **TODO (unavailable until the ~3PM tester drop)**
```bash
py -3.12 scripts/score_heldout.py --responses build/heldout-answers_<tester>.json
# multiple sheets, per-tester + pooled:
py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json \
  --summary-json docs/artifacts/heldout-performance-REAL.summary.json
```
Fill the REAL pooled result (never merge sheets — report per-tester **and** pooled):

| Sheet (REAL) | accuracy | n | Wilson 95% CI |
|--------------|----------|---|---------------|
| tester A | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |
| tester B | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |
| **Pooled** | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |

By section (REAL, pooled):

| Section | n | correct | acc |
|---------|---|---------|-----|
| CP | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |
| BB | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |
| PS | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |
| CARS | `TODO (3PM)` | `TODO (3PM)` | `TODO (3PM)` |

Honesty fields (say all of them):
- **n (independent held-out attempts):** `TODO (3PM)`
- **vs 25% chance floor:** `TODO (3PM): pooled acc __ vs 0.25 floor`
- **Coverage:** `TODO (3PM): sections answered / 4, topics / 18`
- **Confidence/CI:** the pooled Wilson band above (wider per-tester at small n).
- **Missing-data note:** `TODO (3PM): e.g. "only N independent attempts; <30 keeps
  this INDICATIVE, not a strict graded score" — or, if ≥30, "clears the strict
  gate"`
- **Single next action:** `TODO (3PM)`

> If **zero** real sheets arrived: leave D2 empty, keep Performance **ABSTAIN**,
> and show only D1 (clearly labelled synthetic). Do **not** fabricate.

## Segment E — Memory + Readiness: honest abstention (3:00–3:30)

- **Memory:** calibration **REAL** — Brier **0.0082**, log-loss 0.0949, n_test=39
  (`docs/artifacts/memory-calibration-real.png`). But the **strict score
  ABSTAINS**: 0 of 133 cards mature (history ~3.28 days; longest interval 4 days).
  Say: *"calibration real, score withholds — maturity takes weeks."*
  **TODO (optional, post-3PM):** refresh Brier / n_test if re-run on tester revlog
  via `make eval-memory MCAT_COLLECTION=…`.
- **Readiness:** **ABSTAINS — no 472–528 range emitted** (both inputs abstain).
  State the missing-data note; do **not** show a range.

## Segment F — CI + engineering workflow (3:30–4:00)

- Show the **green `mcat-ci` check**: **6 workflow steps** (validate-data, leakage,
  held-out demo, AI-vs-baseline eval, paraphrase, unit tests) ending in **"Ran 56
  tests … OK"** (33 explainer/QA/judge + 23 proxy client/server; re-verified
  locally on `py -3.12`, 2026-07-05). **TODO (post-push):** link to the specific
  green run.
- Show the **PR list** (feature branches → PRs). **TODO (post-push):** links to
  `feat/ai-keyless-proxy`, `feat/graded-strict-build`, `feat/honest-eval-artifacts`,
  `ci/github-actions`, `docs/final-submission` (+ `feat/android-three-scores`).
- One line: "Feature branches, PRs, and a green MCAT-scoped CI — not the inherited
  upstream Anki builds."

## Close (spoken)

> "Real where it can be real, abstaining where it can't, and labelled either way."

---

## Artifact checklist (attach to the submission packet)
- [ ] `docs/EVAL-SUMMARY-GRADED.md` (the three verdicts)
- [ ] `docs/EVAL-SUMMARY-HELDOUT-SYNTHETIC.md` (labelled-synthetic demo)
- [ ] `docs/artifacts/heldout-performance-REAL.summary.json` — **TODO (after 3PM)**
- [ ] `docs/artifacts/memory-calibration-real.png`
- [ ] `docs/QA-BASELINE-COMPARISON.md`
- [ ] `docs/artifacts/ai-explainer-eval.summary.json`
- [ ] Green `mcat-ci` run screenshot + PR list — **TODO (post-push)**

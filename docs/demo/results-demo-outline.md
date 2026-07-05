# Results demo — outline + fill-in scaffold

_Purpose: a short (~3–4 min) "here's the proof" segment. Pre-structured so the
numbers drop in fast at/after the 3PM tester-data drop. **Fill-in slots are
marked `<<FILL: … >>`.** Keep every honesty field. Do NOT blend scores._

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
for held-out performance. `<<FILL: number of independent testers who returned a
held_out sheet = ___ >>`

## Segment B — REAL proof #1: leakage / split integrity (0:30–1:15)

Live run (deterministic, real):
```bash
make eval-leakage
```
Read out the result:
- dev = 65, held_out = 105; paraphrase pairs = 28; **max Jaccard = 0.56 < 0.70**
- **`Leakage check OK`** → the held-out instrument is genuinely unseen.

`<<FILL: paste the exact re-run output line if re-run on demo day >>`

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

- **Differentiation gap = +0.99**; pre-registered cutoff PASS; safety gate PASS;
  goldset 9/9.
- Optional (needs keys): `<<FILL: live cross-model judge numbers from
  `make eval-qa-baseline` / `docs/QA-BASELINE-COMPARISON.md` — AI __% vs static
  __% vs keyword __% >>`.

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

### D2 — REAL held-out (fill after 3PM)
```bash
py -3.12 scripts/score_heldout.py --responses build/heldout-answers_<tester>.json
# multiple sheets, per-tester + pooled:
py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json \
  --summary-json docs/artifacts/heldout-performance-REAL.summary.json
```
Fill the REAL pooled result (never merge sheets — report per-tester **and** pooled):

| Sheet (REAL) | accuracy | n | Wilson 95% CI |
|--------------|----------|---|---------------|
| tester A | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |
| tester B | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |
| **Pooled** | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |

By section (REAL, pooled):

| Section | n | correct | acc |
|---------|---|---------|-----|
| CP | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |
| BB | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |
| PS | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |
| CARS | `<<FILL>>` | `<<FILL>>` | `<<FILL>>` |

Honesty fields (say all of them):
- **n (independent held-out attempts):** `<<FILL>>`
- **vs 25% chance floor:** `<<FILL: pooled acc __ vs 0.25 >>`
- **Coverage:** `<<FILL: sections answered / 4, topics / 18 >>`
- **Confidence/CI:** the pooled Wilson band above (wider per-tester at small n).
- **Missing-data note:** `<<FILL: e.g. "only N independent attempts; <30 keeps
  this INDICATIVE, not a strict graded score" — or, if ≥30, "clears the strict
  gate" >>`
- **Single next action:** `<<FILL>>`

> If **zero** real sheets arrived: leave D2 empty, keep Performance **ABSTAIN**,
> and show only D1 (clearly labelled synthetic). Do **not** fabricate.

## Segment E — Memory + Readiness: honest abstention (3:00–3:30)

- **Memory:** calibration **REAL** — Brier **0.0082**, log-loss 0.0949, n_test=39
  (`docs/artifacts/memory-calibration-real.png`). But the **strict score
  ABSTAINS**: 0 of 133 cards mature (history ~3.28 days; longest interval 4 days).
  Say: *"calibration real, score withholds — maturity takes weeks."*
  `<<FILL: refresh Brier/n_test if re-run on tester revlog via `make eval-memory
  MCAT_COLLECTION=…` >>`
- **Readiness:** **ABSTAINS — no 472–528 range emitted** (both inputs abstain).
  State the missing-data note; do **not** show a range.

## Segment F — CI + engineering workflow (3:30–4:00)

- Show the **green `mcat-ci` check**: 6 steps green, **"Ran 56 tests … OK"**.
  `<<FILL: link to the specific green run >>`
- Show the **PR list** (feature branches → PRs): `<<FILL: links to
  feat/ai-keyless-proxy, feat/graded-strict-build, feat/honest-eval-artifacts,
  ci/github-actions, docs/final-submission >>`
- One line: "Feature branches, PRs, and a green MCAT-scoped CI — not the inherited
  upstream Anki builds."

## Close (spoken)

> "Real where it can be real, abstaining where it can't, and labelled either way."

---

## Artifact checklist (attach to the submission packet)
- [ ] `docs/EVAL-SUMMARY-GRADED.md` (the three verdicts)
- [ ] `docs/EVAL-SUMMARY-HELDOUT-SYNTHETIC.md` (labelled-synthetic demo)
- [ ] `docs/artifacts/heldout-performance-REAL.summary.json` `<<FILL: after 3PM>>`
- [ ] `docs/artifacts/memory-calibration-real.png`
- [ ] `docs/QA-BASELINE-COMPARISON.md`
- [ ] `docs/artifacts/ai-explainer-eval.summary.json`
- [ ] Green `mcat-ci` run screenshot + PR list

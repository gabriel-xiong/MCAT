# feat/honest-eval-artifacts — held-out scorer, leakage check, AI baseline, summaries

> Paste target: `gh pr create --title "feat: honest eval harness + graded/held-out summaries" --body-file docs/pr-drafts/feat-honest-eval-artifacts.md`
> Repo: **MCAT**.

## Summary (the "why")

The grader asked for held-out eval results, a baseline comparison, and a leakage
check. This PR lands the **data-independent** half of that in an honest form: the
**real** proofs (split-integrity leakage check + AI-vs-baseline choice
specificity) are computed and reproducible **now**, and the held-out
**Performance** score is reported as an honest **ABSTAIN** (no independent tester
answers yet) accompanied by a **clearly-labelled synthetic pipeline demo** that
proves the scorer runs end-to-end. When a real answer sheet arrives, the same
commands drop the real number in with zero code changes. Memory calibration is
**real and reportable** (Brier 0.0082, n_test=39) while the strict Memory *score*
abstains (0 mature cards) — reported as such.

## What changed

**Scorers / harness**
- `scripts/score_heldout.py` *(committed)* — filters `data/questions.json` to
  `split=="held_out"` (105 Q: CP 45 / BB 38 / PS 15 / CARS 7), grades vs the key,
  prints accuracy + **Wilson 95% CI** + per-section/topic; `--demo`,
  `--responses`, `--make-template`, `--emit-attempts`.
- `scripts/eval_leakage.py` *(committed)* — dev↔held_out exact/substring +
  Jaccard, pool leakage, paraphrase-pair check. **REAL, reproducible.**
- `scripts/ai_eval_explanations.py` *(committed)* — AI vs static vs TF-IDF
  choice-specificity on held_out (offline provider); pre-registered cutoff +
  safety gate. **REAL.**
- `scripts/qa_baseline_compare.py` *(committed)* — QA follow-up baseline under a
  cross-model semantic judge. **REAL.**
- `scripts/pool_heldout.py`, `scripts/gen_synthetic_heldout.py`
  *(in flight — concurrent worker)* — multi-sheet pooling wrapper (reuses
  `score_heldout.score()`/`wilson_ci()`, **no independent grading logic**) and a
  seeded Bernoulli synthetic responder (`p ≤ 0.90`, never an oracle).

**Docs / artifacts**
- `docs/EVAL-SUMMARY-GRADED.md` *(new, shared)* — the three graded verdicts with
  full honesty fields (Memory calibration REAL / score ABSTAIN; Performance
  ABSTAIN; Readiness ABSTAIN, no range).
- `docs/EVAL-SUMMARY-HELDOUT-SYNTHETIC.md` *(new)* — the labelled-synthetic
  held-out pipeline demo (transparent generator + assumptions) with a prominent
  SYNTHETIC banner.
- `docs/artifacts/memory-calibration-real.{png,bins.csv,summary.json}` *(new)* —
  REAL calibration on the builder's collection.
- `docs/artifacts/ai-explainer-eval.summary.json` *(modified)* — refreshed offline
  AI-eval artifact.
- `out/heldout-collection/answer-sheet.TEMPLATE.json` *(new)* — blank tester
  answer sheet (collection kit) matching the scorer's input schema.

## Test plan

All commands below are deterministic, offline, and run in **CI** (`mcat-ci`):

```bash
py -3.12 scripts/validate_data.py       # 170 Q (65 dev / 105 held_out); Validation OK
py -3.12 scripts/eval_leakage.py        # Leakage check OK (Jaccard 0.56 < 0.70)
py -3.12 scripts/score_heldout.py --demo   # synthetic self-test: overall + Wilson CI + per-section/topic
py -3.12 scripts/ai_eval_explanations.py   # OVERALL: PASS (AI choice-spec 1.000 vs static 0.000 / TF-IDF ~0.01)
py -3.12 scripts/eval_paraphrase.py     # PARAPHRASE GAP +0.16 (recall 0.83 - accuracy 0.67)
```

Expected exit `0` on each; verified locally 2026-07-04 and pinned into the
green `mcat-ci` workflow — see the check on this PR.

When a real held-out sheet arrives (post-3PM), one command converts ABSTAIN → real:
```bash
py -3.12 scripts/score_heldout.py --responses build/heldout-answers_<tester>.json
```

## Screenshots / artifacts

- [ ] `docs/artifacts/memory-calibration-real.png` (reliability diagram, REAL).
- [ ] Terminal capture of `eval_leakage.py` → "Leakage check OK".
- [ ] Terminal capture of `ai_eval_explanations.py` → "OVERALL: PASS".
- [ ] (post-3PM) real held-out per-section table with Wilson CIs.

## Risks / rollback

- **Tester data late / thin (<30 attempts).** Report honestly with the small-n
  warning the scorer already prints; keep Performance labelled indicative;
  never fabricate. The synthetic demo stays clearly labelled and never populates
  the graded score.
- **Synthetic mistaken for real.** Mitigated by SYNTHETIC banners, `synthetic:
  true` row markers, and a meta sidecar (`is_real_data: false`).
- **Rollback:** the harness is read-only over `data/`; reverting removes only
  docs/artifacts, not any product behavior.

## Honesty note

- Every score carries **n, coverage %, confidence/CI, a missing-data note, and a
  single next action**. Readiness emits **no range** (both inputs abstain).
- The three scores are **never blended**. Anything synthetic is **labelled
  synthetic** and does **not** populate a graded verdict. The leakage check and
  AI-baseline comparison are the genuinely-REAL proofs and are labelled REAL.

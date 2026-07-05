# How to verify MCAT Speedrun (grader-facing)

_Single page for graders and reviewers. Last updated: **2026-07-05**._

This doc maps **every Speedrun rubric item** (§7a–7h, §8–10) and the core product
claims to **concrete evidence** you can inspect in minutes — commands, JSON
artifacts, code paths, and demo scripts. Synthetic runs are labelled; three scores
are **never blended**.

**Related:** [`GRADED-QUICKSTART.md`](GRADED-QUICKSTART.md) (install the MSI),
[`demo/product-ai-demo-runofshow.md`](demo/product-ai-demo-runofshow.md) (6–8 min
product walkthrough), [`MVP-TO-FINAL.md`](MVP-TO-FINAL.md) (what changed since MVP),
[`SUBMISSION-RESULTS.md`](SUBMISSION-RESULTS.md) (unified eval table).

---

## 5-minute verifier path

From a clean checkout of `MCAT/` (Python 3.12):

```bash
cd MCAT
make ci-local          # validate-data + leakage + held-out demo + AI eval + 56 unit tests
make eval-leakage      # re-run leakage alone if you want the fresh JSON timestamp
```

Then open these JSON files (all under `docs/artifacts/`):

| File | What it proves in ~30 s |
|------|-------------------------|
| [`leakage-check.summary.json`](artifacts/leakage-check.summary.json) | dev/held_out split clean; max paraphrase Jaccard **0.563** |
| [`ai-explainer-eval.summary.json`](artifacts/ai-explainer-eval.summary.json) | AI vs static/TF-IDF baselines on 315 wrong-answer paths |
| [`heldout-performance-SYNTHETIC.summary.json`](artifacts/heldout-performance-SYNTHETIC.summary.json) | held-out **scoring pipeline** works (labelled synthetic) |
| [`memory-calibration-alt.summary.json`](artifacts/memory-calibration-alt.summary.json) | **REAL** memory calibration (participant alt, n_test=38) |
| [`heldout-performance-REAL-alt.summary.json`](artifacts/heldout-performance-REAL-alt.summary.json) | **REAL** bundle received; **`scorable: false`** (no held_out sheet) |

Optional 30-second sanity on the fork:

```bash
cd ../anki-MCAT && cargo test -p anki mcat   # 4/4 Rust mastery tests
```

**Install + product (human, ~6 min):** see [`GRADED-QUICKSTART.md`](GRADED-QUICKSTART.md) —
install `MCAT-Speedrun-graded.msi`, then double-click **`Start MCAT Speedrun.cmd`**
(not `./run`). Walkthrough script: [`demo/product-ai-demo-runofshow.md`](demo/product-ai-demo-runofshow.md).

---

## Verification table (Claim → Evidence → REAL vs SYNTHETIC → Status)

| # | Claim (rubric / product) | Evidence (file or command) | REAL / SYNTHETIC | Status |
|---|--------------------------|----------------------------|------------------|--------|
| **7a** | **Rust mastery query** in shared engine; ≥3 Rust tests + 1 Python test; undo safe | `anki-MCAT/rslib/src/mcat/`; `cargo test -p anki mcat`; `pylib/tests/test_mcat_mastery.py`; [`UNDO-INTEGRITY-PROOF.md`](UNDO-INTEGRITY-PROOF.md); [`artifacts/undo-integrity-results.json`](artifacts/undo-integrity-results.json) | REAL (automated) | **Pass** — 4/4 Rust + 15/15 undo checks |
| **7b** | **Two-device sync:** 10 phone + 10 desktop offline reviews; same-card conflict winner | [`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) (written rule); [`RECORDING-RUNBOOK.md`](RECORDING-RUNBOOK.md) §D; optional capture script [`SYNC-DEMO-SCRIPT.md`](SYNC-DEMO-SCRIPT.md) | REAL rule; **no recording** | **Gap** — rule documented; perf bundle merge proven headlessly; **memory sync not recorded** |
| **7c** | **Coverage map** on official outline; dashboard %; abstain below line | `data/mcat-outline.v1.json`; `anki-MCAT/qt/aqt/deckbrowser.py`; `anki-MCAT/pylib/anki/mcat_scores.py` (`MIN_OUTLINE_COVERAGE`); demo beat §2 in run-of-show | REAL (in app) | **Pass** — strict Readiness abstains until ≥50% coverage |
| **7d** | **Paraphrase gap** — recall vs reworded question accuracy | `make eval-performance` → [`paraphrase-gap.summary.json`](artifacts/paraphrase-gap.summary.json); [`PARAPHRASE-TEST.md`](PARAPHRASE-TEST.md) | SYNTHETIC (n=28 concepts) | **Pass (instrument)** — gap **+0.16**; **Gap:** no real `--recall` + attempts yet |
| **7e** | **Leakage check** — no train/test overlap | `make eval-leakage` → [`leakage-check.summary.json`](artifacts/leakage-check.summary.json) | REAL (static bank scan) | **Pass** — 0 issues; max Jaccard **0.563** < 0.70 |
| **7f** | **AI quality gate** — gold set, pre-registered cutoff, block bad output | `make eval-ai` → [`ai-explainer-eval.summary.json`](artifacts/ai-explainer-eval.summary.json); live rerun → [`ai-explainer-eval-live.summary.json`](artifacts/ai-explainer-eval-live.summary.json); QA follow-ups → [`QA-BASELINE-COMPARISON.md`](QA-BASELINE-COMPARISON.md) | REAL eval harness; offline provider deterministic | **Pass (explainer + QA)** — choice-spec **1.0 vs 0.0**; semantic judge **90.7% vs 59.6%**; card-*generation* gold set not in scope (curated bank, no runtime LLM) |
| **7g** | **Crash / offline** — 20 kills → 0 corruption; AI off cleanly | [`artifacts/undo-integrity-results.json`](artifacts/undo-integrity-results.json); `scripts/ai_explain.py` offline fallback; `anki-MCAT/qt/aqt/mcat/ai_bridge.py` | REAL (undo + AI-off code paths) | **Partial Pass** — undo/convergence **15/15**; **Gap:** 20-kill GUI test not recorded; AI-off fallback demo in run-of-show |
| **7h** | **One-command benchmark** on ~50k deck (p50/p95/worst) | `make bench` → [`artifacts/bench-50k-results.json`](artifacts/bench-50k-results.json); [`LATENCY-RELIABILITY.md`](LATENCY-RELIABILITY.md) | SYNTHETIC deck (~5k in latest run; ~50k row historical) | **Partial Pass** — command exists; mastery p50 **~19 ms**; dashboard p50 **~140 ms** @ ~5k; **Gap:** full 50k dashboard misses §10 p95 <1 s target (~2.9 s historical) |
| **§8** | **Study feature** — 3-build ablation at equal time; fair null acceptable | `make study` → [`study-feature.summary.json`](artifacts/study-feature.summary.json), [`.arms.csv`](artifacts/study-feature.arms.csv); [`STUDY-FEATURE-RESULTS.md`](STUDY-FEATURE-RESULTS.md) | SYNTHETIC | **Gap (honest null)** — interleaved−blocked **p=0.057** (fails pre-registered win); interleaved−plain **p=0.001**; **no real multi-arm data** |
| **§9 Step 1** | Memory model **calibrated** on held-back reviews | Builder: [`memory-calibration-real.summary.json`](artifacts/memory-calibration-real.summary.json) (Brier **0.0082**, n_test=39); Alt tester: [`memory-calibration-alt.summary.json`](artifacts/memory-calibration-alt.summary.json) (Brier **0.0028**, n_test=38) | **REAL** (n=1 each) | **Pass (calibration)** — strict Memory **score** still abstains (no mature cards / alt n<200) |
| **§9 Step 2** | Predict held-out correctness from mastery + difficulty + timing + coverage | `make eval-step2-synthetic` → [`step2-prediction-SYNTHETIC.summary.json`](artifacts/step2-prediction-SYNTHETIC.summary.json); [`STEP2-PREDICTION.md`](STEP2-PREDICTION.md) | SYNTHETIC | **Pass (harness)** — Brier **0.219**, acc@0.5 **66.7%**; **Gap:** not fit on real snapshots |
| **§9 Step 3** | Performance → mapped score with range | [`EVAL-SUMMARY-GRADED.md`](EVAL-SUMMARY-GRADED.md); synthetic pipeline [`heldout-performance-SYNTHETIC.summary.json`](artifacts/heldout-performance-SYNTHETIC.summary.json) | REAL abstain + SYNTHETIC demo | **Gap** — Performance **ABSTAIN** (0 independent held_out attempts); real alt bundle [`heldout-performance-REAL-alt.summary.json`](artifacts/heldout-performance-REAL-alt.summary.json) **`scorable: false`** |
| **§10** | Speed / reliability targets (p50/p95) | [`bench-50k-results.json`](artifacts/bench-50k-results.json); [`PRE-DEMO-VERIFICATION.md`](PRE-DEMO-VERIFICATION.md) | SYNTHETIC scale test | **Partial** — mastery fast; dashboard at scale **slow**; sync/crash targets partly doc-only |
| — | **Three scores never blended** | `anki-MCAT/pylib/anki/mcat_scores.py`; `pylib/tests/test_mcat_scores.py`; dashboard UI | REAL | **Pass** |
| — | **Topic gate + CARS exception** | `anki-MCAT/pylib/anki/mcat_perf.py`; [`PERFORMANCE-MODE-SPEC.md`](PERFORMANCE-MODE-SPEC.md) | REAL | **Pass** |
| — | **Error typing → next action** | `performance_dialog.py`; [`ERROR-DIAGNOSIS-SPEC.md`](ERROR-DIAGNOSIS-SPEC.md) | REAL | **Pass** (hypothesis + confirm UX) |
| — | **CI reproducible offline** | `make ci-local`; `.github/workflows/mcat-ci.yml` | REAL | **Pass** locally (56 tests); remote green run linked in [`PRE-DEMO-VERIFICATION.md`](PRE-DEMO-VERIFICATION.md) |
| — | **Strict graded MSI + launcher** | [`GRADED-QUICKSTART.md`](GRADED-QUICKSTART.md); `anki-MCAT/docs/GRADED-HANDOFF.md` | REAL (when MSI rebuilt) | **Pass (docs)** — MSI may be stale pre-merge; rebuild in progress |

**Table row count:** **22** claim rows (7a–7h + §8–§10 steps + core product checks).

---

## All `docs/artifacts/*.summary.json` files

| Artifact | Label | One-line result |
|----------|-------|-----------------|
| [`leakage-check.summary.json`](artifacts/leakage-check.summary.json) | REAL | PASS — 0 leakage issues |
| [`memory-calibration.summary.json`](artifacts/memory-calibration.summary.json) | SYNTHETIC | Brier 0.141, n_test=1472 |
| [`memory-calibration-real.summary.json`](artifacts/memory-calibration-real.summary.json) | REAL (builder) | Brier 0.0082, n_test=39 |
| [`memory-calibration-synthetic.summary.json`](artifacts/memory-calibration-synthetic.summary.json) | SYNTHETIC | duplicate path for labelled synthetic run |
| [`memory-calibration-alt.summary.json`](artifacts/memory-calibration-alt.summary.json) | **REAL (alt)** | Brier **0.0028**, n_test=**38** |
| [`paraphrase-gap.summary.json`](artifacts/paraphrase-gap.summary.json) | SYNTHETIC | gap **+0.16**, n=28 |
| [`heldout-performance-SYNTHETIC.summary.json`](artifacts/heldout-performance-SYNTHETIC.summary.json) | SYNTHETIC | pooled acc **55.9%**, pipeline demo |
| [`heldout-performance-REAL-alt.summary.json`](artifacts/heldout-performance-REAL-alt.summary.json) | **REAL (alt)** | **`scorable: false`** — 0 held_out attempts |
| [`step2-prediction-SYNTHETIC.summary.json`](artifacts/step2-prediction-SYNTHETIC.summary.json) | SYNTHETIC | Brier 0.219, acc@0.5 66.7% |
| [`study-feature.summary.json`](artifacts/study-feature.summary.json) | SYNTHETIC | interleaved−blocked p=0.057 (inconclusive) |
| [`ai-explainer-eval.summary.json`](artifacts/ai-explainer-eval.summary.json) | REAL harness / offline provider | choice-spec 1.0 vs 0.0 |
| [`ai-explainer-eval-live.summary.json`](artifacts/ai-explainer-eval-live.summary.json) | REAL (live API) | choice-spec 0.86 live |

Supporting non-JSON: [`bench-50k-results.json`](artifacts/bench-50k-results.json),
[`undo-integrity-results.json`](artifacts/undo-integrity-results.json),
[`study-feature.arms.csv`](artifacts/study-feature.arms.csv),
[`ai-explainer-eval.baselines.csv`](artifacts/ai-explainer-eval.baselines.csv).

---

## 30-minute deep verify (optional)

| Step | Time | Action |
|------|------|--------|
| 1 | 5 min | `make ci-local` + skim all summary JSONs above |
| 2 | 6 min | Install graded MSI + `Start MCAT Speedrun.cmd`; confirm three abstaining scores + coverage map |
| 3 | 5 min | One memory review + one performance miss → error type + Assistant (AI on/off) |
| 4 | 5 min | Export perf bundle; confirm sidecar JSON shape |
| 5 | 5 min | Read [`QA-BASELINE-COMPARISON.md`](QA-BASELINE-COMPARISON.md) + [`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) |
| 6 | 4 min | `cargo test -p anki mcat`; optional `make eval-all-synthetic` for full battery |

---

## GAPS (explicit — do not infer as shipped)

1. **No sync recording** — §7b two-device memory sync (10+10 offline, same-card
   winner) is documented in [`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md) but
   **not captured on video**. Optional script if recorded later:
   [`SYNC-DEMO-SCRIPT.md`](SYNC-DEMO-SCRIPT.md).
2. **No real held_out answer sheet** — participant **alt** exported dev practice
   only; [`heldout-performance-REAL-alt.summary.json`](artifacts/heldout-performance-REAL-alt.summary.json)
   sets **`scorable: false`**. Graded Performance remains **ABSTAIN**.
3. **Synthetic study ablation** — §8 headline contrast (interleaved vs blocked) **not
   significant** at synthetic n; real equal-time 3-build data not collected.
4. **Strict Memory score abstains** — calibration is real (builder + alt) but strict
   dashboard score needs mature cards / n≥200 (alt has 135 reviews).
5. **50k dashboard latency** — historical ~50k run exceeds §10 refresh target; latest
   bench uses ~5k-card smoke scale.
6. **Graded MSI may be stale** — rebuild after `main` merge; see
   [`PRE-DEMO-VERIFICATION.md`](PRE-DEMO-VERIFICATION.md).

---

## Reproduce everything (builder)

```bash
cd MCAT
make eval-all-synthetic    # full synthetic battery + leakage
make ci-local              # CI mirror (56 tests)
make test-ai-proxy         # proxy client + mock server (optional)
```

Real-data counterparts (when bundles/sheets exist):

```bash
make eval-memory MCAT_COLLECTION=/path/to/collection.anki2
py -3.12 scripts/pool_heldout.py build/heldout-answers_*.json --summary-json docs/artifacts/heldout-performance-REAL.summary.json
```

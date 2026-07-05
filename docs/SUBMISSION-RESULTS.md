# Submission results — unified eval report (2026-07-05)

Local pass executed from `MCAT/` with `py -3.12` / Makefile targets. **No API
keys, no network, no push.** Synthetic runs are labelled; three scores are never
blended.

---

## Summary table

| Command / target | Mode | Result | Key numbers | Artifact |
|------------------|------|--------|-------------|----------|
| `make validate-data` | real bank | **PASS** | 170 Q (65 dev / 105 held_out); 28 paraphrase concepts | — |
| `make eval-leakage` | static scan | **PASS** | 0 issues; max paraphrase Jaccard **0.563** (&lt;0.70) | `docs/artifacts/leakage-check.summary.json` |
| `make eval-memory` | **synthetic** | **PASS** | Brier **0.1407**, log-loss **0.4496**, ECE **0.0324**, n_test **1472** | `docs/artifacts/memory-calibration.summary.json`, `.png`, `.bins.csv` |
| `make eval-performance` | **synthetic** | **PASS** | paraphrase gap **+0.16** (recall 0.83 − acc 0.67), n=28 concepts | `docs/artifacts/paraphrase-gap.summary.json` |
| `make eval-heldout-synthetic` | **synthetic** | **PASS** | pooled acc **55.9%** (176/315), Wilson **[0.504, 0.613]**; 3 testers × 105 Q | `docs/artifacts/heldout-performance-SYNTHETIC.summary.json` |
| `make eval-step2-synthetic` | **synthetic** | **PASS** | Brier **0.219**, log-loss **0.624**, acc@0.5 **66.7%** (70/105), Wilson **[0.572, 0.750]** | `docs/artifacts/step2-prediction-SYNTHETIC.summary.json` |
| `make study` | **synthetic** | **PASS** (inconclusive headline) | interleaved **71.7%** vs blocked **60.0%** → Δ **+11.7 pts, p=0.057** (not sig.); interleaved vs plain **p=0.001** * | `docs/artifacts/study-feature.{summary.json,arms.csv,png}` |
| `make eval-ai` | offline | **PASS** | held_out wrong-path acc **1.000**, choice_spec **1.000** vs static **0.000** | `docs/artifacts/ai-explainer-eval.summary.json` |
| `make test` | unit | **PASS** | 33/33 AI harness tests | — |
| `make test-eval-step2` | unit | **PASS** | 8/8 Step 2 tests | — |
| `make bench` (5k cards, 3 iters) | synthetic scale | **PASS** (local smoke) | dashboard p50 **140 ms** @ ~5k cards | `docs/artifacts/bench-50k-results.json` (refreshed) |
| `make bench` @ ~50k (prior artifact) | synthetic scale | **MISS vs product target** | dashboard p50 **2893 ms**, p95 **5189 ms** @ ~50k cards | same file (historical 50k row in repo) |
| `cargo test -p anki mcat` | fork Rust | **PASS** | 4/4 mastery tests | — |
| `pytest pylib/tests/test_mcat_*.py` | fork Python | **SKIP** | `ModuleNotFoundError: anki.buildinfo` — fork pylib not fully built in this shell | — |
| `mcat_undo_integrity_check.py` | integration | **PASS** | 15/15 checks | `docs/artifacts/undo-integrity-results.json` |
| `make test-ai-proxy` | mock server | **PASS** | 23/23 on `feat/ai-keyless-proxy` | — |

\* Study ablation: only interleaved−plain Anki significant; **headline interleaved−blocked contrast fails §8 criterion** (p≥0.05). See `docs/STUDY-FEATURE-RESULTS.md` §8.

---

## Failures / blockers (honest)

1. **50k dashboard latency:** Committed `bench-50k-results.json` at ~50k cards shows
   end-to-end `dashboard_data` p50 **~2.9 s** (p95 **~5.2 s**) — misses a snappy
   dashboard story at full prototype scale. Mastery query alone stays ~300 ms.
2. **Study feature not demonstrated on real data:** Synthetic interleaved vs blocked
   is **inconclusive** (p=0.057); §8 failure criterion applies until real equal-time
   multi-arm data passes p&lt;0.05.
3. **No real held-out performance or memory calibration:** All performance/readiness
   evidence paths have **synthetic** stand-ins; friend answers + builder revlog still
   required.
4. **AnkiDroid pylib tests:** Collection bootstrap (`anki.buildinfo`) missing —
   run from a full fork build tree or CI image.

---

## Synthetic artifact checklist

Every synthetic JSON includes `mode: synthetic` or `synthetic: true`, sample **n**,
**missing_data_note**, and **next_action**:

| Artifact | n | next action (one line) |
|----------|---|------------------------|
| memory-calibration.summary.json | 1472 test reviews | `make eval-memory MCAT_COLLECTION=…` |
| paraphrase-gap.summary.json | 28 concepts | `--recall` + `--attempts` real files |
| heldout-performance-SYNTHETIC.summary.json | 315 pooled attempts | `pool_heldout.py build/heldout-answers_*.json` |
| step2-prediction-SYNTHETIC.summary.json | 105 attempts | real attempts + mastery snapshots |
| study-feature.summary.json | 120/arm | `--manifest` real 3-build data |
| leakage-check.summary.json | 170 bank items | re-run after bank edits |

---

## Reproduce (builder one-liner)

```bash
cd MCAT && make eval-all-synthetic && make test && make test-eval-step2
```

Optional fork checks (after full Anki build):

```bash
cd anki-MCAT && cargo test -p anki mcat
../anki-MCAT/out/pyenv/Scripts/python.exe ../anki-MCAT/tools/mcat_undo_integrity_check.py
```

Proxy (on `feat/ai-keyless-proxy`):

```bash
make test-ai-proxy
```

---

## Branch / commit map (this pass)

| Branch | Commit | Contents |
|--------|--------|----------|
| `feat/honest-eval-artifacts` | `0d66ee9` | Step 2 harness, JSON artifact writers, Makefile `eval-all-synthetic` |
| `docs/final-submission` | *(this commit)* | `BRAINLIFT.md`, `SUBMISSION-RESULTS.md` |

No pushes performed.

# MCAT Speedrun — Eval presenter notes

**Grader packet (print / Google Docs):** [`GRADER-PACKET.html`](GRADER-PACKET.html)

**Screen-share deck:** [`eval-presentation.html`](eval-presentation.html) (reviewer-facing — no speaker script on slides)  
**This file:** speaker script, term definitions, commands, and artifact paths for Gabriel.

---

## Artifact coverage checklist (HTML vs rubric §7 / §8 / §9)

Does [`eval-presentation.html`](eval-presentation.html) cover every rubric item and every `docs/artifacts/*.summary.json`?

| Rubric / claim | In HTML? | Where | Gap / note |
|----------------|----------|-------|------------|
| **§7a** Rust mastery query + undo | Partial | Gaps slide #4 (undo 15/15) | Rust 4/4 tests not charted — say aloud from HOW-TO-VERIFY; no dedicated slide (code-path evidence, not JSON summary) |
| **§7c** Coverage map / Readiness abstain | Partial | Gaps slide #3 | Product demo only — no JSON artifact; say in product segment |
| **§7d** Paraphrase gap | Yes | Slide 06 + artifact index | SYNTHETIC instrument only |
| **§7e** Leakage check | Yes | Slide 03 | REAL static |
| **§7f** AI explainer gate | Yes | Slide 04 | Offline + live harness; QA semantic judge (90.7% vs 59.6%) not on slide — mention verbally or QA-BASELINE-COMPARISON |
| **§7g** Crash / offline / AI-off | Partial | Gaps slide #4 | Undo 15/15 yes; 20-kill GUI test gap; AI-off fallback in product run-of-show |
| **§7h** Bench / latency | Partial | Gaps slide #5 | Numbers on gaps slide; full bench JSON not charted (supporting artifact, not `.summary.json`) |
| **§8** Study feature 3-build | Yes | Slide 08 | SYNTHETIC; p=0.057 fail stated |
| **§9 Step 1** Memory calibration | Yes | Slide 05 | Builder + alt REAL; synthetic demo |
| **§9 Step 2** Held-out prediction | Yes | Slide 07 | SYNTHETIC harness |
| **§9 Step 3** Performance → mapped score | Yes | Slide 09 | REAL abstain + SYNTHETIC demo |
| **§10** Speed targets | Partial | Gaps slide #5 | Historical 50k miss; not a summary JSON |
| **Three scores never blended** | Yes | Slide 02 | — |
| **All 12 `.summary.json` files** | Yes | Slides 03–09 + index slide 10 | `memory-calibration` and `memory-calibration-synthetic` are duplicate numbers — shown once on slide 05, both listed on index |

**Missing from HTML (by design — not dense enough for reviewer deck):**

- Rust 4/4 + Python mastery test counts (§7a) — verifier runs `cargo test -p anki mcat`
- QA gold-set semantic judge table (§7f supplement) — see [`QA-BASELINE-COMPARISON.md`](../QA-BASELINE-COMPARISON.md)
- CI / unit test matrix (56 tests) — mention if grader asks; [`SUBMISSION-RESULTS.md`](../SUBMISSION-RESULTS.md)
- Product walkthrough (coverage bar, error typing, AI toggle) — [`product-ai-demo-runofshow.md`](product-ai-demo-runofshow.md)
- Graded MSI install — [`GRADED-QUICKSTART.md`](../GRADED-QUICKSTART.md)

---

## Term definitions (say if asked)

| Term | Definition |
|------|------------|
| **Brier score** | Mean squared error between predicted probability (0–1) and binary outcome (0/1). Lower = better calibrated probabilities. |
| **ECE** | Expected Calibration Error — average \|predicted − observed\| across probability bins. Lower = better. |
| **Log-loss** | Cross-entropy loss on predicted probabilities; penalizes confident wrong predictions heavily. |
| **Wilson CI** | Wilson score 95% confidence interval for a binomial proportion (accuracy). Used instead of normal approx for small n. |
| **choice_spec (choice specificity)** | Fraction of wrong-answer explanation paths where the text differs meaningfully by which wrong option was chosen (not identical static blurb). Cutoff ≥ 0.80 for AI path. |
| **Jaccard** | Token-set overlap: \|A∩B\| / \|A∪B\|. Used for near-duplicate detection between dev and held_out stems. |
| **held_out vs dev** | `dev` = practice questions visible during tuning; `held_out` = frozen eval set never used for threshold tuning. |
| **scorable** | `score_heldout.py` / `pool_heldout.py` require an independent answer sheet (letter per qid) on the frozen held_out set. In-app dev practice does not count. |
| **Three scores** | Memory (FSRS calibration), Performance (held_out MCQ accuracy), Readiness (mapped range with coverage penalty). Never blended into one headline. |
| **Coverage map** | Fraction of official outline topics with enough data; Readiness abstains below ~50% coverage. |
| **Paraphrase gap** | Mean card recall minus mean accuracy on reworded questions for the same concept — large gap means Performance measures transfer, not rote recall. |
| **acc@0.5** | Classification accuracy when predicted P(correct) ≥ 0.5 is treated as “predict yes.” |
| **Cohen's h** | Effect size for difference in proportions (study ablation). |
| **REAL participant** | Human revlog or perf bundle export (builder collection or alt tester). |
| **REAL static / harness** | Deterministic scan of committed question bank, or eval script run on real bank paths — no human learning claim. |
| **SYNTHETIC** | Seeded / injected demo data proving the pipeline runs; not evidence about real users. |

---

## Data provenance table

| Data point | REAL participant? | Who / what | Artifact file |
|------------|-------------------|------------|---------------|
| Bank split 170 Q, 0 leakage | No — REAL static | Static `data/questions.json` scan | `leakage-check.summary.json` |
| Memory Brier 0.141, n=1472 | No — SYNTHETIC | Injected miscalibration revlog | `memory-calibration.summary.json` (= `memory-calibration-synthetic.summary.json`) |
| Memory Brier 0.0082, n=39 | **Yes — builder** | Builder Anki collection revlog | `memory-calibration-real.summary.json` |
| Memory Brier 0.0028, n=38 | **Yes — alt** | Participant alt perf bundle revlog | `memory-calibration-alt.summary.json` |
| Paraphrase gap +0.159 | No — SYNTHETIC | Deterministic manifest n=28 | `paraphrase-gap.summary.json` |
| Held-out pooled 55.9% | No — SYNTHETIC | 3× seeded answer sheets | `heldout-performance-SYNTHETIC.summary.json` |
| Alt held_out scorable false | **Yes — alt bundle** | 0 held_out attempts; dev 73.0% only | `heldout-performance-REAL-alt.summary.json` |
| Step 2 Brier 0.219 | No — SYNTHETIC | Mock mastery features + seed | `step2-prediction-SYNTHETIC.summary.json` |
| Study interleaved 71.7%, p=0.057 | No — SYNTHETIC | Equal-time 3-arm simulation | `study-feature.summary.json` |
| AI offline choice_spec 1.0 | No — REAL harness | Offline deterministic provider on real bank | `ai-explainer-eval.summary.json` |
| AI live choice_spec 0.860 | No — REAL harness | Live gpt-4o-mini on real bank | `ai-explainer-eval-live.summary.json` |
| Undo integrity 15/15 | No — REAL automated | Headless perf merge script | `undo-integrity-results.json` (supporting) |
| Bench dashboard ~2.9 s @ 50k | No — SYNTHETIC scale | `make bench` historical row | `bench-50k-results.json` (supporting) |

**Explicit labelling rule:** Alt participant exported a **REAL** bundle — memory calibration **yes**, held_out performance sheet **no** (`scorable: false`). Builder REAL memory **yes**. Everything else in the eval battery is **SYNTHETIC** unless the badge says REAL participant or REAL static/harness.

---

## Slide-by-slide script (matches eval-presentation.html)

### Slide 01 — Title

> MCAT Speedrun is an Anki fork with three separate scores — Memory, Performance, and Readiness — and we never blend them. Every number in this deck is labelled: green is a real human participant, blue is a real bank scan or eval harness, amber is synthetic pipeline demo. Synthetic proves the scripts work; it is not a learning claim. Scoring and the question bank run with no AI at runtime.

---

### Slide 02 — Three scores

> Memory comes from FSRS calibration on flashcard reviews — predicted recall versus what actually happened. Performance is separate: accuracy on curated exam-style MCQs from a frozen held_out split, scored only from an independent answer sheet. Readiness maps to an MCAT-style range but abstains until outline coverage is high enough, around fifty percent. We compute and display all three independently — no composite headline, ever.

---

### Slide 03 — Leakage (REAL static)

**What we measure:** Dev vs held_out split integrity — no train/test overlap, no near-duplicate stems crossing the split.  
**How:** `make eval-leakage` → `scripts/eval_leakage.py` on committed bank.  
**Artifact:** `docs/artifacts/leakage-check.summary.json`

> REAL static bank scan: 170 questions, 65 dev, 105 held_out. Zero leakage issues. Max paraphrase Jaccard 0.563, under the 0.70 threshold, 28 pairs checked. This proves split integrity on the committed bank — it does not prove runtime session leakage.

| Metric | Value |
|--------|-------|
| n_dev / n_held_out | 65 / 105 |
| n_issues | 0 |
| max Jaccard | 0.5625 |

---

### Slide 04 — AI explainer (REAL harness)

**What we measure:** Post-answer explainer quality on wrong-answer paths — does AI text differ by which wrong option was picked (choice specificity), stay grounded in source, and avoid telling the user they picked the right answer.  
**How:** `make eval-ai` → `scripts/ai_eval_explanations.py` on 315 wrong paths (105 held_out × 3 wrong choices). Pre-registered cutoff choice_spec ≥ 0.80.  
**Artifacts:** `ai-explainer-eval.summary.json` (offline), `ai-explainer-eval-live.summary.json` (live API)

> AI is optional help after a performance miss only — never in the score path. Static baseline gives identical text regardless of wrong pick — choice specificity zero. TF-IDF barely differentiates at 0.0095. Our offline harness hits 1.0; live gpt-4o-mini 0.8603. Both pass the 0.80 cutoff. If asked about follow-up Q&A quality: semantic judge on n=60 gold set is 90.7% vs static 59.6% — see QA-BASELINE-COMPARISON.

| Provider | choice_spec | Pass? |
|----------|-------------|-------|
| Static | 0.000 | baseline |
| TF-IDF | 0.0095 | fail |
| AI offline | 1.000 | PASS |
| AI live | 0.8603 | PASS |

---

### Slide 05 — Memory calibration

**What we measure:** Whether FSRS predicted recall matches observed recall on held-back reviews (Brier, ECE, log-loss).  
**How:** `make eval-memory` (synthetic) or `make eval-memory MCAT_COLLECTION=…` (real). Time-split 70/30 train/test.  
**Artifacts:** `memory-calibration.summary.json`, `memory-calibration-synthetic.summary.json` (duplicate), `memory-calibration-real.summary.json`, `memory-calibration-alt.summary.json`

> Synthetic demo Brier 0.141 on n_test 1472 proves the calibration script. Builder REAL Brier 0.0082 on 39 test reviews — genuine revlog, small n, default FSRS weights not collection-tuned. Alt participant REAL Brier 0.0028 on 38 test reviews — also small n, 135 total reviews. Alt is under the 200-review gate, so we still withhold the strict Memory headline score on the dashboard despite good calibration numbers.

| Run | Badge | Brier | n_test |
|-----|-------|-------|--------|
| Synthetic | SYNTHETIC | 0.1407 | 1472 |
| Builder | REAL participant | 0.0082 | 39 |
| Alt | REAL participant | 0.0028 | 38 |

---

### Slide 06 — Paraphrase gap (SYNTHETIC)

**What we measure:** Whether high card recall on a concept still leaves a gap on reworded exam questions — evidence Performance is not just parroting Memory.  
**How:** `make eval-performance` → `scripts/eval_paraphrase.py` on synthetic manifest.  
**Artifact:** `paraphrase-gap.summary.json`

> SYNTHETIC instrument demo: 28 concepts. Mean recall 82.8%, mean question accuracy 66.9%, gap plus 15.9 points. Verdict in artifact: recall outstrips transfer. Real `--recall` JSON plus held_out attempts not collected yet.

---

### Slide 07 — Step 2 prediction (SYNTHETIC)

**What we measure:** Can we predict held_out correctness from mastery, difficulty, timing, and coverage features (Step 2 of graded eval).  
**How:** `make eval-step2-synthetic` → `scripts/eval_step2_prediction.py` with seeded mock features.  
**Artifact:** `step2-prediction-SYNTHETIC.summary.json`

> SYNTHETIC harness only. Brier 0.219, log-loss 0.624. Accuracy at threshold 0.5 is 66.7% — 70 of 105 — Wilson 0.572 to 0.750. Observed accuracy 59.0%. Features are mock, not live mastery snapshots at attempt time. Pipeline works; model not validated on real data.

---

### Slide 08 — Study feature (SYNTHETIC)

**What we measure:** At equal study time, does interleaved performance practice beat blocked practice on held_out accuracy (§8 pre-registered contrast).  
**How:** `make study` → synthetic 3-build simulation, 1800 s budget per arm, n_test=120.  
**Artifact:** `study-feature.summary.json`, `study-feature.arms.csv`

> SYNTHETIC equal-time ablation. Interleaved 71.7%, blocked 60%, plain Anki 50%. Pre-registered headline interleaved minus blocked: plus 11.7 points, p equals 0.057 — not significant at 0.05. We report that honestly. Interleaved minus plain Anki is significant at p 0.001 but that is a secondary contrast only. No real multi-arm participant data.

---

### Slide 09 — Held-out performance

**What we measure:** Pooled accuracy on frozen held_out questions with Wilson CI; whether real participants submitted scorable answer sheets.  
**How:** `make eval-heldout-synthetic` / `scripts/pool_heldout.py` + `scripts/score_heldout.py`. Real path needs `heldout-answers_<who>.json`.  
**Artifacts:** `heldout-performance-SYNTHETIC.summary.json`, `heldout-performance-REAL-alt.summary.json`

> Synthetic pooled 55.9% — 176 of 315 — Wilson 0.504 to 0.613. Three testers times 105 questions. Pipeline demo only, not a real learning claim. Participant alt exported a REAL bundle but scorable is false: zero held_out attempts, only 37 dev practice attempts at 73.0%. That is why Performance abstains on the dashboard. Dev practice is not held-out performance.

---

### Slide 10 — Artifact index

> Quick index for graders: all twelve summary JSON files are listed with badges. Two synthetic memory paths are duplicate filenames for the same run. Supporting non-summary artifacts: undo integrity fifteen of fifteen pass, and bench results for latency.

---

### Slide 11 — Honest gaps

> These are intentional honesty — we abstain rather than inflate. One: Performance has no independent held_out sheet; alt bundle scorable false. Two: Study pre-registered win fails at p 0.057; synthetic only. Three: Readiness abstains below coverage — show in product demo. Four: Undo integrity fifteen of fifteen automated checks pass; we did not record twenty-kill GUI crash test. Five: Mastery query is fast; full dashboard at fifty thousand cards historically about 2.9 seconds p50 — misses section ten target; latest smoke bench uses about five thousand cards.

---

### Slide 12 — Not yet measured

> Post-Sunday backlog from mentor feedback — instruments exist, real data pending: real held_out answer sheet, real study arms, real paraphrase recall export, live Step 2 snapshots, sync recording, gold-set think-aloud. Full list in feedback doc and LOOSE-ENDS.

**Pointer:** [`feedback/2026-07-05-demo.md`](../feedback/2026-07-05-demo.md), [`LOOSE-ENDS.md`](../LOOSE-ENDS.md)

---

### Slide 13 — Verify

> Full artifact paths, commands, rubric map, and reproduce steps are in HOW-TO-VERIFY.md. Optional unified table in SUBMISSION-RESULTS. Reproduce offline: `make ci-local` from a clean checkout.

---

## Metric reference (what / how / command / artifact)

| Metric | What we're trying to measure | How we measured it | Command / path |
|--------|------------------------------|--------------------|----------------|
| Leakage issues | Split contamination | Pairwise Jaccard + rule checks on bank | `make eval-leakage` → `leakage-check.summary.json` |
| Max Jaccard | Worst near-dup across split | 28 paraphrase pairs | same |
| choice_spec | Wrong-path explanation differentiation | Token/semantic rules on 315 paths | `make eval-ai` → `ai-explainer-eval.summary.json` |
| Brier (memory) | FSRS calibration quality | Time-split revlog, FSRS predicted R vs ease≥2 | `make eval-memory` → `memory-calibration*.summary.json` |
| Paraphrase gap | Recall vs transfer | Per-concept recall − MCQ accuracy | `make eval-performance` → `paraphrase-gap.summary.json` |
| Brier (step2) | Prediction quality | Logistic on mock features | `make eval-step2-synthetic` → `step2-prediction-SYNTHETIC.summary.json` |
| Study Δ accuracy | Interleaving benefit at equal time | Simulated 3 arms, z-test on proportions | `make study` → `study-feature.summary.json` |
| Held-out accuracy | Real exam-style performance | Independent answer sheet on held_out | `pool_heldout.py` → `heldout-performance-*.summary.json` |
| scorable | Eligibility for Performance headline | ≥1 held_out attempt on answer sheet | `heldout-performance-REAL-alt.summary.json` |
| Undo 15/15 | Sidecar merge safety | Automated headless checks | `mcat_undo_integrity_check.py` → `undo-integrity-results.json` |
| Bench p50 | Dashboard refresh at scale | `make bench` on synthetic deck | `bench-50k-results.json` |

---

## Optional live demo (if time)

```bash
cd MCAT && make ci-local
```

Say: validates data, leakage, held-out synthetic demo, AI eval, and 56 unit tests — all offline.

Then product segment: [`product-ai-demo-runofshow.md`](product-ai-demo-runofshow.md) + graded MSI via [`GRADED-QUICKSTART.md`](../GRADED-QUICKSTART.md).

---

## Related docs

| Doc | Use |
|-----|-----|
| [`HOW-TO-VERIFY.md`](../HOW-TO-VERIFY.md) | Grader rubric §7a–7h, §8–10 |
| [`SUBMISSION-RESULTS.md`](../SUBMISSION-RESULTS.md) | Full command × artifact table |
| [`EVAL-WALKTHROUGH.md`](EVAL-WALKTHROUGH.md) | Short outline + links |
| [`feedback/2026-07-05-demo.md`](../feedback/2026-07-05-demo.md) | Mentor direction / post-Sunday backlog |

# MCAT Speedrun — Eval walkthrough (screen-share script)

**Visual version:** open [`eval-presentation.html`](eval-presentation.html) in browser (reviewer-facing deck) · speaker script: [`EVAL-PRESENTER-NOTES.md`](EVAL-PRESENTER-NOTES.md)

_Presenter: Gabriel · ~5 min JSON scroll + optional `make ci-local` · 2026-07-05 pass_

**Related docs:** [`HOW-TO-VERIFY.md`](../HOW-TO-VERIFY.md) · [`SUBMISSION-RESULTS.md`](../SUBMISSION-RESULTS.md) · [`feedback/2026-07-05-demo.md`](../feedback/2026-07-05-demo.md)

---

## 30-second pitch (read aloud)

> MCAT Speedrun is an Anki fork with **three separate scores** — Memory, Performance, and Readiness — and we **never blend them**. Readiness **abstains** until outline coverage is high enough; Performance needs independent held-out answers we do not have yet. Every eval artifact is labelled **REAL or SYNTHETIC**; synthetic runs prove the **pipeline**, not learning claims. **Scores and the question bank run with no AI at runtime** — AI is optional post-answer help only, gated by offline eval.

---

## What we measured vs what we didn't

| Measured (with label) | Not measured / abstained | Why |
|------------------------|---------------------------|-----|
| Bank split integrity (REAL static scan) | Real pooled held-out Performance headline | Need frozen answer sheets, not in-app dev practice |
| Memory FSRS calibration — builder + alt tester (REAL, small n) | Strict Memory **score** on dashboard | Alt n=38 &lt;200 gate; builder immature deck |
| Held-out **scoring pipeline** (SYNTHETIC 3×105 Q) | Study interleaved vs blocked win | Synthetic p=**0.057** — fails §8 criterion |
| Paraphrase gap instrument (SYNTHETIC n=28) | Real recall + reworded attempts | No `--recall` + attempts export yet |
| Step 2 prediction harness (SYNTHETIC) | Fit on live mastery snapshots | Mock features only |
| AI explainer vs baselines (REAL harness; offline + live) | Card generation / runtime LLM scoring | Curated bank; no AI in score path |
| Undo integrity (REAL 15/15) | 20-kill GUI crash test | Not recorded |
| Bench mastery + dashboard (SYNTHETIC scale) | §10 dashboard at full ~50k | Historical p50 **~2.9 s** — miss vs target |
| Rust mastery query (4/4) | AnkiDroid pylib in this shell | `anki.buildinfo` needs full fork build |

---

## Results at a glance

_All numbers from `docs/artifacts/*.summary.json` + [`SUBMISSION-RESULTS.md`](../SUBMISSION-RESULTS.md). **Bold** = say these aloud._

### Split & bank (REAL)

| Metric | Value |
|--------|-------|
| Question bank | **170** Q (**65** dev / **105** held_out) |
| Leakage issues | **0** |
| Max paraphrase Jaccard | **0.563** (threshold **0.70**) |

### Memory calibration

| Run | Label | Brier | Log-loss | ECE | n_test |
|-----|-------|-------|----------|-----|--------|
| Synthetic demo | SYNTHETIC | **0.1407** | **0.4496** | **0.0324** | **1472** |
| Participant **alt** | **REAL** | **0.0028** | **0.0546** | **0.0532** | **38** (135 total reviews) |

_Say:_ alt calibration is REAL but strict Memory score still **withheld** (n &lt;200; default FSRS weights).

### Performance / held-out

| Run | Label | Headline | Notes |
|-----|-------|----------|-------|
| Pooled synthetic | SYNTHETIC | **55.9%** acc (**176**/315), Wilson **[0.504, 0.613]** | 3 testers × 105 Q — **pipeline demo only** |
| Participant **alt** | **REAL** | **`scorable: false`** | **0** held_out attempts; dev practice **72.7%** — **do not** report as held-out |

### Paraphrase gap (SYNTHETIC)

| Metric | Value |
|--------|-------|
| Concepts | **28** |
| Mean recall − question acc | **+0.16** (recall **0.83**, acc **0.67**) |

### Step 2 prediction (SYNTHETIC)

| Metric | Value |
|--------|-------|
| Brier | **0.219** |
| Log-loss | **0.624** |
| acc@0.5 | **66.7%** (70/105), Wilson **[0.572, 0.750]** |

### Study feature — 3-build ablation (SYNTHETIC, equal time)

| Arm | Accuracy |
|-----|----------|
| Interleaved | **71.7%** |
| Blocked | **60.0%** |
| Plain Anki | **50.0%** |

| Contrast | Δ | p |
|----------|---|---|
| Interleaved − blocked | **+11.7 pts** | **0.057** — **not significant** (§8 fail) |
| Interleaved − plain Anki | **+21.7 pts** | **0.001** * |

\* Secondary contrast only; headline interleaved−blocked does **not** pass pre-registered win.

### AI explainer eval (REAL harness, held_out wrong paths n=**315**)

| Provider | choice_specificity (AI vs static) | Pass cutoff |
|----------|-----------------------------------|-------------|
| **Offline** deterministic | AI **1.000** vs static **0.000** | **PASS** |
| **Live** gpt-4o-mini | AI **0.860** vs static **0.000** | **PASS** |

_QA gold set (semantic judge, n=60): AI **90.7%** vs static **59.6%** — see [`QA-BASELINE-COMPARISON.md`](../QA-BASELINE-COMPARISON.md)._

### Undo & bench

| Check | Result |
|-------|--------|
| Undo integrity | **15/15** PASS |
| Bench @ ~5k cards (latest) | mastery p50 **~19 ms**; dashboard p50 **~140 ms** |
| Bench @ ~50k (historical row) | dashboard p50 **~2893 ms**, p95 **~5189 ms** — **gap vs §10** |

### Unit tests (this pass)

| Target | Result |
|--------|--------|
| `make test` | **33/33** |
| `make test-eval-step2` | **8/8** |
| `cargo test -p anki mcat` | **4/4** |
| `make test-ai-proxy` | **23/23** (on proxy branch) |

---

## Honest GAPS (say these out loud — do not skip)

1. **Performance ABSTAIN:** [`heldout-performance-REAL-alt.summary.json`](../artifacts/heldout-performance-REAL-alt.summary.json) → **`scorable: false`**, **0** held_out attempts. Synthetic pooled file is **not** a real learning claim.
2. **Study inconclusive:** interleaved vs blocked **p = 0.057** — pre-registered §8 headline **fails**; no real multi-arm data.
3. **Readiness:** app abstains below **~50%** outline coverage — show coverage bar + abstain copy in product demo, not in JSON scroll.
4. **MSI may be stale:** graded installer rebuild may lag merged fork — verify commit in [`GRADED-QUICKSTART.md`](../GRADED-QUICKSTART.md) before claiming “latest build.”
5. **50k dashboard:** mastery query fast; full-scale dashboard refresh **slow** (~2.9 s historical) — not hidden.

---

## 5-minute live demo path

**Terminal (optional, ~2 min):**

```bash
cd MCAT && make ci-local
```

_Say:_ validates data, leakage, held-out synthetic demo, AI eval, **56** unit tests — all offline.

**Then open these five JSON files in order** (`docs/artifacts/`):

| # | File | One line while scrolling |
|---|------|--------------------------|
| 1 | [`leakage-check.summary.json`](../artifacts/leakage-check.summary.json) | “REAL — **0** issues, max Jaccard **0.563**.” |
| 2 | [`ai-explainer-eval.summary.json`](../artifacts/ai-explainer-eval.summary.json) | “Offline harness — choice-spec **1.0 vs 0.0**, cutoff **PASS**.” |
| 3 | [`heldout-performance-SYNTHETIC.summary.json`](../artifacts/heldout-performance-SYNTHETIC.summary.json) | “SYNTHETIC — pipeline works, **55.9%** pooled — **not** real Performance.” |
| 4 | [`memory-calibration-alt.summary.json`](../artifacts/memory-calibration-alt.summary.json) | “**REAL** alt tester — Brier **0.0028**, n_test **38**.” |
| 5 | [`heldout-performance-REAL-alt.summary.json`](../artifacts/heldout-performance-REAL-alt.summary.json) | “Same tester — **`scorable: false`** — why Performance abstains.” |

**Optional 30 s:** [`undo-integrity-results.json`](../artifacts/undo-integrity-results.json) → **15/15**; [`study-feature.summary.json`](../artifacts/study-feature.summary.json) → p=**0.057**.

**Product segment (separate run-of-show):** [`product-ai-demo-runofshow.md`](product-ai-demo-runofshow.md) + graded MSI via [`GRADED-QUICKSTART.md`](../GRADED-QUICKSTART.md).

---

## Post-Sunday — what else to measure

_From [`feedback/2026-07-05-demo.md`](../feedback/2026-07-05-demo.md) + [`LOOSE-ENDS.md`](../LOOSE-ENDS.md):_

| Theme | Next step |
|-------|-----------|
| **Binary UX** | Low-friction yes/no checkpoints vs probe → 3-bucket confirm stack |
| **Research citations** | `RESEARCH.md` + primary sources; separate calibration vs error-type self-diagnosis claims |
| **Difficulty scaffolding** | Author `difficulty` 1–5; on miss → 2 easier diagnostic MCQs (not application pool) |
| **Real held_out sheet** | Blank template → `pool_heldout.py` → replace SYNTHETIC Performance row |
| **Gold set** | ~20–30 think-aloud held_out items → inference accuracy / override rate |
| **Sync recording** | Two-device 10+10 offline reviews + same-card conflict winner on video |
| **Study feature** | Real equal-time 3-build manifest — re-test interleaved vs blocked |
| **Paraphrase gap** | Real `--recall` JSON + held_out attempts |
| **Step 2** | Real attempts + mastery snapshots at attempt time |
| **Bench / MSI** | Fresh ~50k bench after perf fixes; rebuild + record clean-machine install |

---

## Quick links

| Doc | Use |
|-----|-----|
| [`HOW-TO-VERIFY.md`](../HOW-TO-VERIFY.md) | Grader rubric map (§7a–7h, §8–10) |
| [`SUBMISSION-RESULTS.md`](../SUBMISSION-RESULTS.md) | Full command × artifact table |
| [`feedback/2026-07-05-demo.md`](../feedback/2026-07-05-demo.md) | Mentor direction (post-Sunday backlog) |
| [`LOOSE-ENDS.md`](../LOOSE-ENDS.md) | Open research / validation threads |
| [`STUDY-FEATURE-RESULTS.md`](../STUDY-FEATURE-RESULTS.md) | §8 criterion detail |
| [`QA-BASELINE-COMPARISON.md`](../QA-BASELINE-COMPARISON.md) | Semantic judge vs token baseline |

---

_Reproduce builder battery: `cd MCAT && make eval-all-synthetic && make test && make test-eval-step2`_

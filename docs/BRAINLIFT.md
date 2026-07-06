# BrainLift — MCAT Speedrun (submission)

> **Grader verification:** see [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md) — claim → evidence table, 5-minute `make ci-local` path, and explicit GAPS.

**Owner:** Gabriel Xiong  
**Product:** MCAT Speedrun — Anki fork + measurement layer (AGPL-3.0-or-later)  
**Exam:** MCAT (472–528 total; sections 118–132 each)

---

## 1. Purpose and scope

This BrainLift asks how MCAT students build **exam-ready performance** and where study tools — including Anki — fail to bridge recall, application, and readiness.

**In scope:** MCAT structure and scoring; the typical prep funnel; where methods break down between **recall**, **application**, and **readiness**. **Out of scope:** generic productivity advice; LLM card-generation architecture; deep content dives (e.g., Krebs cycle mechanisms).

**Product thesis ([`PRD.md`](PRD.md)):** Students use Anki for recall but lack a **live, honest signal** of exam-ready **performance** and **readiness**. MCAT Speedrun forks Anki and AnkiDroid, adds **performance mode** on memory-mode reviews, and displays **three separate scores** with ranges and abstention — without faking a single “% ready.”

This is **not a full MCAT prep course.** Version 1 covers ~15–25 outline topics, a modest deck, and ~30–100 **curated** performance questions from named open sources (primarily OpenStax). The prototype proves **measurement honesty and architecture**, not curriculum completeness.

---

## 2. Spiky Points of View (SPOV 1–3)

### SPOV 1: Readiness is a continuous signal, not an end state

Under the standard funnel — content review → question banks → full-lengths in the final weeks — students spend months without an early readiness signal, then discover gaps when AAMC practice arrives. Readiness measurement must move from the finish line to a **live signal with explicit uncertainty**. MCAT Speedrun expresses this as a **Readiness score** mapped to 472–528, widened when data is thin, and **withheld** when outline coverage falls below ~50%.

### SPOV 2: Recall and application are distinct

Students pair Anki with practice QBanks assuming both cover the exam. Declarative and procedural knowledge do not automatically transfer. Science sections: ~**35%** Skill 1 (content), ~**65%** Skills 2–4 (application, research, data). Anki optimizes recall; the exam tests application. Need one feedback loop, **measured separately**.

### SPOV 3: Tools record *what*, not *why*

Misread, reasoning error, and content gap carry different information but collapse to “missed topic X.” **Error typing** routes targeted drills instead of “study more topic X.” MCAT Speedrun infers error type and surfaces **one next action**.

---

## 3. Key insights

Insights **4**, **6**, and **8** (from the original BrainLift tree, referenced in [`PRD.md`](PRD.md) user journeys) drive product design.

**Insight 4 — readiness emerges at the end.** Months without a gauge, then late discovery via full-lengths. MCAT Speedrun: dashboard updates continuously with **abstention** when thresholds aren't met. PRD Journey 1 (first week, no false readiness).

**Insight 6 — blocked study hides transfer gaps.** The MCAT is structurally interleaved. MCAT Speedrun ships a **3-build ablation** at equal study time (interleaved vs blocked vs plain Anki) on the same held_out set. Hypothesis pre-registered in [`STUDY-FEATURE-RESULTS.md`](STUDY-FEATURE-RESULTS.md); null outcomes reported honestly.

**Insight 8 — card metrics poorly predict passage reasoning.** MCAT Speedrun shows memory, performance, and readiness **separately** and refuses headline readiness without range, coverage %, and missing-data note. PRD Journey 2 (memory strong, performance weaker).

**Insight 6 ↔ SPOV 2:** **paraphrase-gap instrument** ([`PARAPHRASE-TEST.md`](PARAPHRASE-TEST.md)): `paraphrase_gap = card_recall_rate − question_accuracy` on reworded held_out questions tests **transfer**, not memory echo.

---

## 4. Product embodiment

MCAT Speedrun is an **Anki fork + AnkiDroid companion** with a shared Rust mastery query, stock Anki sync for the collection, and performance data in a local sidecar (`mcat_perf.db`) synced via a uuid-deduped export/import bundle (DECISIONS §22). AI is optional and **off at runtime** for the Wednesday core; the performance bank is fully local and curated.

### Three scores (never blended)

| Score | Measures | Abstains when (strict profile) |
|-------|----------|--------------------------------|
| **Memory** | FSRS retrievability × card maturity; calibration harness separate | &lt;200 graded reviews (+ maturity rules) |
| **Performance** | First-attempt accuracy on topic-gated MCQs | &lt;30 attempts or no unlocked topics |
| **Readiness** | Section performance → 472–528 range, **coverage-penalized** | Coverage &lt;50% or other give-up rules (DECISIONS §14) |

Each score shows **range/CI**, **coverage %**, **confidence**, missing-data note, and **one next action**. No headline number without those fields — automatic fail for fake readiness (PRD §5 principle 1). Implementation: `anki-MCAT/pylib/anki/mcat_scores.py`, home-screen dashboard in `qt/aqt/deckbrowser.py`, thresholds in `data/scoring-config.json`.

### Two modes, one loop

- **Memory mode:** standard Anki review loop (FSRS); cards tagged with `topic_id`.
- **Performance mode:** separate UI/session; curated MCQs from local bank; **no live LLM at runtime**; never immediately after flipping the backing card (PRD §5 principle 3).

**Topic gate (moderate, locked):**

```
performance_unlocked(topic) :=
  distinct_cards_reviewed(topic) >= 3
  AND good_or_easy_count(topic) >= 5
```

**CARS exception:** performance always unlocked for CARS items (~23% of exam that flashcards cannot train); CARS uses skill-archetype + pacing, not the science error-typing engine ([`ERROR-DIAGNOSIS-SPEC.md`](ERROR-DIAGNOSIS-SPEC.md) → CARS diagnosis).

### Why-you-missed diagnosis (summary)

On a **science performance miss**, the app **infers** an error type rather than asking open self-diagnosis. The v2 taxonomy: **`content_gap`**, **`application`** (passage-mapping and reasoning sub-modes), **`misread`**. CARS misses are hard-guarded to `unresolved`.

**Mechanism:** (1) signals at attempt — `choice_diagnosis`, FSRS-R `M`, `cognitive_demand`, timing; (2) first-match decision order → `content_gap` / `application` / `misread` / `unresolved`; (3) optional re-check probe (FAIL = strong content_gap); (4) confirm-the-hypothesis UX with one-tap override. Focus area maps diagnosis → one next action. IDK excluded from performance accuracy (DECISIONS §30).

### Architecture and sync

Desktop (`anki-MCAT`) and mobile (`anki-android-MCAT`) share the Rust engine (`rslib/src/mcat/`) via `proto/anki/mcat.proto → get_topic_mastery()`. Memory lives in `collection.anki2` (stock Anki sync); performance in sidecar `collection.mcat_perf.db` (uuid-deduped bundle, DECISIONS §22). Headless proof: 15/15 undo + perf-sync checks (`anki-MCAT/tools/mcat_undo_integrity_check.py`, [`UNDO-INTEGRITY-PROOF.md`](UNDO-INTEGRITY-PROOF.md)).

### Question bank

170 curated items (65 `dev` / 105 `held_out`, 18 topics). Every item carries `source_name`, `source_url`, `topic_id`, `split`, and a required static `explanation` (AI-off fallback). OpenStax primary for science; CC0 for CARS. Validated by `scripts/validate_data.py`.

---

## 5. Eval infrastructure and instruments

All eval is offline unless a live AI key is supplied. Paths are wired in the `Makefile` and documented in [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md).

### One-command verifier path

```bash
cd MCAT && make ci-local    # validate + leakage + held-out demo + AI eval + unit tests
cd ../anki-MCAT && cargo test -p anki mcat   # 4/4 Rust mastery tests
```

Key artifacts under `docs/artifacts/` (each labelled REAL or SYNTHETIC): `leakage-check.summary.json` (0 contamination, max Jaccard 0.563); `paraphrase-gap.summary.json` (28 concepts); `memory-calibration*.summary.json`; `study-feature.summary.json`; `bench-50k-results.json`; `ai-explainer-eval.summary.json`; `heldout-performance-*.summary.json`.

### Paraphrase-gap instrument (§7d)

28 anchor concepts × two reworded held_out questions each. `paraphrase_gap = card_recall_rate − question_accuracy`. Run: `make eval-performance` with `--recall` and `--attempts` for real data. Synthetic demo: gap **+0.16** — instrument works; real-data gap open.

### Study feature (§8)

Three builds at equal study seconds on the same `held_out` set: interleaved (71.7%), blocked (60.0%), plain Anki (50.0%). Interleaved − plain **+21.7 pt, p = 0.001**; interleaved − blocked **+11.7 pt, p = 0.057** (honest null at demo n). Pre-registered in [`STUDY-FEATURE-RESULTS.md`](STUDY-FEATURE-RESULTS.md).

### Memory calibration and Step 2 (§9 Steps 1–2)

Real calibration at small n: builder Brier **0.0082** (n_test=39); alt Brier **0.0028** (n_test=38). Strict Memory **score** may still abstain (n&lt;200). Step 2 synthetic harness: Brier **0.219**, acc@0.5 **66.7%** — pipeline proof; real snapshots pending.

### Held-out performance (§9 Step 3)

Synthetic pipeline works (`heldout-performance-SYNTHETIC`). Real alt bundle: **`scorable: false`** (no held_out answer sheet) — primary external-validation gap.

### AI eval gates (§7f)

Opt-in, env-gated (`MCAT_LLM_PROVIDER` unset → AI OFF). Explainer: choice-specificity **1.000** vs static **0.000** offline. Follow-up Q&A: semantic judge **90.7%** vs static **59.6%** on 60-item gold set ([`QA-BASELINE-COMPARISON.md`](QA-BASELINE-COMPARISON.md)). Neither runs during review.

### Latency and integrity

Undo + perf-sync: **15/15** REAL. Dashboard @ ~50k cards: **5.2 s p95** — misses §10 &lt;1 s target. Two-device memory-sync recording: pending.

---

## 6. Honest limits

Speedrun grades **measurement honesty**, not a validated MCAT score predictor. Limits are explicit in repo docs and eval artifacts.

**Abstention and give-up rules.** Readiness **withholds** at coverage &lt;50% and until memory reviews (≥200 strict), performance attempts (≥30 strict), and per-section minimums are met. Individual scores abstain at their own thresholds. An empty profile abstains on all three — gates never fabricate numbers. A tester profile lowers gates for friend demos; strict profile governs graded claims (DECISIONS §31).

**Synthetic vs real eval labels.** Many harness outputs are labelled **SYNTHETIC** (`heldout-performance-SYNTHETIC`, `step2-prediction-SYNTHETIC`, paraphrase-gap demo, study-feature arms). Real memory calibration exists at small n (builder n_test=39, alt n_test=38) but strict Memory **score** may still abstain. Performance on independent held_out answers remains a **gap**: real alt bundle received, **`scorable: false`**.

**Held_out gap.** A premed friend was planned to complete one frozen held_out set (~45 min) for independent performance accuracy. Solo builder n=1–2 is documented throughout; friend held_out is the intended external validator, not yet a graded outcome.

**Inference limits.** ~78% of science distractors were untagged at one audit point; `M` imputation and the content_gap ↔ application boundary remain the least-tested pieces (DECISIONS §21). CARS error-type confirm is omitted in demo scope.

**Scale and speed.** Dashboard latency at ~50k cards misses §10 p95 &lt;1 s target in historical bench runs — documented as partial pass in HOW-TO-VERIFY.

**Not validated against real MCAT outcomes.** Mapping performance accuracy → 472–528 is a **monotonic direction** tuned on dev questions, reported on held_out — external validation against actual MCAT scores is bonus only (PRD §3.2 non-goal).

**Two-device memory sync.** Perf bundle merge is proven headlessly; stock Anki memory-sync rule is documented ([`SYNC-CONFLICT-RULE.md`](SYNC-CONFLICT-RULE.md)) but the on-camera two-device recording is pending ([`RECORDING-RUNBOOK.md`](RECORDING-RUNBOOK.md)).

**Single next action for eval completeness:** collect real held_out performance answers + sustained flashcard reviews; rerun `make eval-memory`, `make eval-performance` (with `--recall` and `--attempts`), and paraphrase scoring on real data.

---

## 7. Attribution

| Item | Detail |
|------|--------|
| **BrainLift author** | Gabriel Xiong |
| **Product** | MCAT Speedrun — fork of [Anki](https://github.com/ankitects/anki) and [AnkiDroid](https://github.com/ankidroid/Anki-Android) |
| **License** | AGPL-3.0-or-later; credit upstream Anki and AnkiDroid |
| **Course deliverable** | Speedrun Desktop + Mobile Study App Built on Anki |
| **Spec cross-links** | [`PRD.md`](PRD.md), [`DECISIONS.md`](DECISIONS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ERROR-DIAGNOSIS-SPEC.md`](ERROR-DIAGNOSIS-SPEC.md), [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md) |
| **Repos** | [`gabriel-xiong/MCAT`](https://github.com/gabriel-xiong/MCAT) (docs, content, eval) · [`gabriel-xiong/anki-MCAT`](https://github.com/gabriel-xiong/anki-MCAT) (desktop fork) |

---

*This document synthesizes the BrainLift knowledge tree, PRD, decision log, and eval artifacts in the MCAT Speedrun repository. It is the submission BrainLift deliverable; verification evidence lives in HOW-TO-VERIFY and `docs/artifacts/`.*

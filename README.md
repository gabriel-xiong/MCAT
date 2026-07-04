# MCAT Speedrun — Anki Measurement Layer

**Exam:** MCAT (472–528 total; sections 118–132 each)
**Owner:** Gabriel Xiong
**License:** AGPL-3.0-or-later (Anki fork — credit [Anki](https://github.com/ankitects/anki) and [AnkiDroid](https://github.com/ankidroid/Anki-Android))

A **desktop Anki fork** and an **Android (AnkiDroid) companion** that share one Rust engine and surface **three separate scores that are never blended** — **memory**, **performance**, and **readiness** — instead of one flattering “% ready.”

> **Scope:** This is a **prototype measurement product** over a **subset of MCAT topics** (18 in the v1 outline; the design target is ~15–25), **not** a full prep course. It demonstrates the recall → application → readiness bridge with honest uncertainty and abstention when the data is thin.

This README is written to be **verifiable**: every claim below is backed by a file, test, script, or committed artifact in one of the three repos. Where something is designed but not yet fully demonstrated, it is marked **Planned / In progress** rather than stated as done.

**Repos**

| Repo | Role |
|------|------|
| `MCAT/` (this repo) | Product docs, curated content, eval scripts, artifacts |
| `anki-MCAT/` | Desktop Anki fork (Rust mastery query, performance mode, three-score dashboard) |
| `anki-android-MCAT/` | AnkiDroid fork (shared forked Rust engine; mobile dashboard) |

---

## The problem (BrainLift)

MCAT students spend months on content review (often in Anki) with **no live readiness signal**, then discover gaps only during late full-length practice exams. **Recall ≠ exam performance:** MCAT science sections are roughly one-third recall-like (Skill 1) and two-thirds application / research reasoning / data interpretation (Skills 2–4). Tools that only track card completion create **false readiness**, and a missed question usually collapses to “topic X” without capturing **why** it was missed.

This app measures that gap explicitly, and refuses to invent a readiness number when it doesn’t have the data to justify one.

---

## The three scores (honest definitions)

The three scores are computed in `anki-MCAT/pylib/anki/mcat_scores.py` and rendered on Anki’s home screen (`anki-MCAT/qt/aqt/deckbrowser.py`). They are **never combined into a single number.** Thresholds mirror `data/scoring-config.json`.

### 1. Memory — an activity / consistency signal (not a proficiency %)

- **What it is:** the **count of graded FSRS reviews** logged (`select count() from revlog`), with the average FSRS retrievability and the number of topics studied/unlocked surfaced alongside it. It is deliberately **not** a “you know 78% of the material” proficiency score.
- **Abstains** below **200 graded reviews** (`MIN_MEMORY_REVIEWS`).
- A full FSRS calibration layer (Brier / log-loss / reliability diagram) exists as a separate harness — see *Evaluation* below — but the on-dashboard memory score is the review-activity signal + abstain rule.

### 2. Performance — accuracy with a Wilson 95% confidence band

- **What it is:** `correct / attempts` on eligible topics, shown with a **Wilson score 95% confidence interval** (`_wilson`, `z = 1.96`; configured in `scoring-config.json → performance.interval`). The interval widens automatically at low `n`, and the dashboard renders it as `95% CI lo–hi%`.
- **Abstains** below **30 attempts** (`MIN_PERF_ATTEMPTS`) or when no topic is unlocked.
- **Not** derived as `memory × k` — it is measured on separate exam-style attempts.

### 3. Readiness — a mapped 472–528 range that abstains aggressively

- **What it is:** section accuracy → section band (118–132) → summed total (472–528), returned as a **range** with `confidence: "low"`. The mapping is an explicitly **provisional** placeholder (`_provisional_range`; coefficients deferred — see `docs/DECISIONS.md §8`, `docs/PRD.md §10`).
- **Abstains unless ALL of** these hold (not just coverage): ≥200 reviews, ≥30 performance attempts, ≥50% outline coverage, ≥5 attempts in **each** science section (CP/BB/PS), and ≥5 CARS attempts.
- **Coverage** = measured outline topics / **18** (`coverage_summary` over the v1 outline denominator).

The dashboard also shows a **focus area** — the single highest-impact next action, derived from the most common diagnosed weakness × topic (`focus_area`) — plus a per-topic **Topic Mastery** view that exposes exactly why each topic is or isn’t unlocked.

---

## Two modes + gating

| Mode | What it is |
|------|------------|
| **Memory mode** | Normal Anki reviews (FSRS). Unchanged review loop. |
| **Performance mode** | A **separate** session that only serves a topic’s curated MCQs once that topic is **unlocked**. |

**Topic unlock gate** (`performance_eligibility` in `scoring-config.json`; constants in `mcat_perf.py`):

```
performance_unlocked(topic) := distinct_cards_reviewed >= 3 AND good_or_easy_count >= 5
```

- **CARS** is **performance-only** — it bypasses the memory gate (`cars_bypasses_memory_gate: true`).
- The app **never** flips a flashcard straight into a scored performance question. Performance sessions are distinct from reviews by design.

---

## Question bank + sources + AI-off-at-runtime

- **170 curated questions** — **65 `dev` / 105 `held_out`** across the **18** v1 topics. This is the authoritative count in `data/curation-status.json` and matches `data/questions.json` exactly.
- **Named sources.** Every item stores `source_name`, `source_url`, `source_location`, `topic_id`, `section`, and `split` (**OpenStax** is the primary science source; CARS uses CC0 passages). Human-entered from source answer keys — not authored from scratch, no scraped QBanks.
- **Required static explanation.** Every question carries a non-empty, source-grounded `explanation` (why the correct answer is correct), enforced by `scripts/validate_data.py`. It is shown after answering and is the **AI-off fallback**.
- **Additive schema for diagnosis:** optional `cognitive_demand` (`recall`/`application`/`synthesis`) and per-choice `choice_diagnosis` (content axis) power error typing and the AI explainer.
- **AI is OFF at runtime.** Performance mode reads the **local** bank; there is **no live LLM call during review**. The Wednesday build contains **zero** AI.

---

## AI features (opt-in, Friday deliverable — additive, gated, source-traced)

Two AI features live **outside** the frozen review path as pure-Python harnesses plus a documented UI seam. Both are **opt-in**, **source-grounded** (ungrounded output is blocked/dropped), and evaluated **before** any student sees output. With the provider unset the app shows the static AI-off panel and **still produces all three scores**.

**Runtime provider is env-driven** (`scripts/ai_explain.py`, `scripts/ai_qa.py`):

| Variable | Meaning |
|----------|---------|
| `MCAT_LLM_PROVIDER` | `openai` or `anthropic`. **Unset → AI OFF** (static fallback). |
| `MCAT_LLM_MODEL` | Optional model id (defaults: `gpt-4o-mini` / `claude-3-5-sonnet-latest`). |
| `MCAT_LLM_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Key, read only from the environment; never committed (`.env`/`.env.*` gitignored). |

### (1) Post-answer per-choice explainer

When a student **misses**, it explains why the **specific distractor they chose** is wrong (something the static explanation and a keyword/vector baseline structurally cannot do), grounded in the item’s named source.

- **Pre-registered cutoff, committed in code** before results (`scripts/ai_eval_explanations.py`): accuracy ≥ 0.90, wrong-answer-rate ≤ 0.05, grounding = 1.00, choice-specificity ≥ 0.80. A per-item safety gate replaces any ungrounded / wrong-choice output with the static explanation; an aggregate failure disables the AI path entirely.
- **Offline held_out result** (105 held_out Q × 3 distractors = **315 paths**, deterministic offline provider): AI choice-specificity **1.000** vs static **0.000** vs TF-IDF **0.010**; wrong-answer-rate 0.000 vs TF-IDF 0.203 → differentiation gap ≈ **+0.99**. These numbers are **by construction** (the offline provider reads ground truth) — their role is to prove the baselines can’t differentiate and to set the safety floor a live model must clear. See `docs/AI-FEATURE.md`.
- **Live-model numbers: not yet run.** No API key was present in the build environment, so live explainer numbers are deliberately left blank rather than fabricated (`docs/AI-FEATURE.md §10`). The seam is wired (`build_live_call_model_from_env`, mocked-LLM tests in `scripts/test_ai_explain_live.py`).

### (2) Follow-up Q&A (“Ask more”)

After a miss, the student can ask an open-ended follow-up (“what if I doubled both concentrations?”) and get a source-grounded answer (`scripts/ai_qa.py`); ungrounded answers are dropped.

- **60-item human-validated gold set** (`data/qa-goldset.json`, `g001`–`g060`, all validated: `g001`–`g030` on 2026-07-02, `g031`–`g060` on 2026-07-03). Authored by a **non-OpenAI** model on purpose + human validation to break circularity (`docs/QA-GOLDSET.md`). 9 parity / 51 differentiation (30 of which are hard cross-question/counterfactual/synthesis items `g031`–`g060`).
- **Committed ship gate** (`scripts/ai_eval_qa.py`): accuracy floor `GATE_MIN_ATOM_COVERAGE = 0.60`, wrong-answer ceiling `GATE_MAX_MUST_NOT_SAY_RATE = 0.10`. Wrong-answer rate is judged by a **cross-model semantic judge** (a different model family grading the OpenAI answers), because the reproducible token scorer over-flags via negation. Non-zero exit on FAIL so it can block shipping.
- **Beats-a-simpler-baseline result** (`docs/QA-BASELINE-COMPARISON.md`, rendered from `data/qa-goldset-semantic-judge.json`). Under the **fair cross-model semantic judge** (Anthropic Claude grading live `openai:gpt-4o-mini` answers), the AI beats **both** AI-off baselines overall — **90.7%** vs static **59.6%** vs keyword **45.0%** — and decisively on the hard subset — **84.2%** vs **20.8%** vs **16.7%**. The **honest exception** is the parity bucket (AI **90.8%** vs static **94.4%**, −3.7), where the purpose-built static per-choice feedback wins. Forbidden-claim assertion under the semantic judge: exactly **1 of 60** AI answers (1.7%, the g060 Arrhenius reversal) vs static/keyword 0%.
- **Caveats (stated, not hidden):** small-n (n=60, one topic trio, one answer model, one answer per item); directional evidence on a hand-built set, not a powered benchmark. A directional-reasoning prompt guardrail was added (`docs/AI-FEATURE.md §12`) but the frozen n=60 proof was **not** re-run against it.

> **Note on numbers.** The follow-up figures above come from `docs/QA-BASELINE-COMPARISON.md` / `data/qa-goldset-semantic-judge.json`, which are consistent with the committed ship-gate comments in `scripts/ai_eval_qa.py`. (An older summary in `docs/AI-FEATURE.md §11` quotes different figures; the data-file-backed numbers here are the ones to trust.)

---

## Error typing (BrainLift differentiator)

On a performance miss, the app captures **why** it was missed and routes a specific next action (`content_gap` → review the backing concept; `passage_mapping` → passage drills; `reasoning` → interleaved hard set; `misread` → timed retry, no new content).

- **Shipped (Wednesday, frozen):** four **self-report** buttons — `content_gap`, `passage_mapping`, `reasoning`, `misread` (`scoring-config.json → error_types`). This drives the dashboard next action / focus area today.
- **v2 direction (implemented in the engine; UX partly deferred):** a **3-bucket inferred taxonomy** (`content_gap` / `application` / `misread`) computed from distractor role + a cross-system per-card FSRS-R `M` signal + timing (`infer_error_type` in `mcat_perf.py`, with tests). Design: an objective **re-check probe** settles whether the content was held, then the student **confirms or overrides** a specific, evidence-backed hypothesis in one tap — not blind self-report, not a silent auto-label. `application` is the moderate-confidence default for a content-presumed-held miss; CARS misses are hard-guarded to `unresolved`. **Deferred honestly:** the dialog does not yet fire the re-check probe, so probe outcomes and first-choice churn are captured as NULL (`docs/DECISIONS.md §9, §12, §19, §21`; `docs/ERROR-DIAGNOSIS-SPEC.md`).

---

## Sync + conflict resolution (two independent channels)

Per `docs/SYNC-CONFLICT-RULE.md` and `docs/DECISIONS.md §5/§22`, a “review” travels over **two channels** that merge by **different rules**. The demo uses a **self-hosted local Anki `--syncserver`** (no AnkiWeb account needed).

### Channel (a) — Memory data rides **stock Anki sync**

`revlog`, `cards`, and the rest of the collection sync through the **shared Anki Rust sync engine** unchanged. Both forks call the same backend, so the merge is identical on both ends:

- **`revlog` (history):** append-only, `INSERT OR IGNORE` keyed by the review’s epoch-ms id. Two reviews (even of the same card on two devices) get distinct ids → **both preserved**; re-syncing a known review is a no-op → **never double-counted**. The memory count equals the union (10 + 10 = 20, each once).
- **`cards` (scheduling state):** **last-review-wins by `mtime`** — the surviving row is the later review (`max(mtime)`), order-independent; the winner **replaces** the loser (`reps`/`due`/`ivl` are not summed), so a dual-reviewed card advances **once**.

### Channel (b) — Performance data syncs via a **custom uuid-deduped bundle**

Performance lives in a **local sidecar** `collection.mcat_perf.db` (next to `collection.anki2`), which **deliberately does not ride stock Anki sync** — a full sync would silently wipe custom tables embedded in the collection. Instead it syncs via a portable **export/import bundle** (`format: "mcat_perf_bundle"`, `format_version: 1`):

- **Append-only UNION merge**, deduped by a stable per-attempt **`uuid`** (`log_attempt` stamps `uuid4`; a UNIQUE-indexed additive column backfills legacy rows). The merge is **idempotent** and **order-independent**, so after each device imports the other’s bundle both converge to the exact union of attempts.

**Proven vs. pending:**
- **Perf channel — PROVEN headlessly.** `anki-MCAT/tools/mcat_undo_integrity_check.py` asserts append-only, idempotent re-import (adds 0 / skips K), and two-device convergence (**15/15 checks pass** — `docs/UNDO-INTEGRITY-PROOF.md`, `docs/artifacts/undo-integrity-results.json`).
- **Memory channel — rule documented + inherited from stock Anki, but the two-device live demo is not yet recorded.** The winner rule is exactly stock collection-sync semantics; the on-camera 10-phone/10-desktop + same-card §7b recording remains a human step (`docs/RECORDING-RUNBOOK.md`).

---

## Architecture (shared Rust engine, sidecar perf DB)

```
Desktop (anki-MCAT, Python/Qt)  ─┐
                                 ├─►  Shared Anki Rust engine (rslib) + MCAT mastery query (rslib/src/mcat/)
Mobile   (anki-android-MCAT)    ─┘        │  proto/anki/mcat.proto  →  get_topic_mastery()
                                          │
      collection.anki2  ◄── stock Anki sync ──►   (memory: cards, revlog, FSRS)
      collection.mcat_perf.db  ◄── custom bundle ──►  (performance: perf_questions, perf_attempts)
```

- **Rust change (desktop) — DEFINITIVE.** A per-topic **mastery query** in `rslib/src/mcat/{mod,service,topic_mastery}.rs`, exposed via `proto/anki/mcat.proto` and `pylib/anki/collection.py::get_topic_mastery`. **4 Rust unit tests + 1 Python integration test pass** (`docs`/`SHARED-ENGINE-PROOF.md`). Fork is anki `26.05`, HEAD `a2500a9`.
- **Shared modified engine (mobile) — DEFINITIVE as of 2026-07-03.** The APK links a locally cross-compiled **forked** `rsdroid`/`librsdroid.so` (anki `26.05`, all **4 ABIs**, **49** `Lanki/mcat/*` proto classes). `McatDashboardRepository.topicMastery()` **prefers the Rust query** — `col.backend.getTopicMastery()` (dispatch service `41`/method `0`) — and falls back to a Kotlin re-implementation, running the Kotlin path on every success as an on-device numeric cross-check (emulator log: `RUST and KOTLIN agree on all 3 topic(s)`, and an independent SQL check matches). Verify with `anki-android-MCAT/tools/verify_backend_provenance.sh`. **Caveats:** only `cards_seen` / `good_or_easy` are consumed today; the Rust path requires the forked AAR (`local_backend=true`); mobile performance/readiness still need the sidecar (absent on the test device → those scores abstain).
- **Storage.** Memory in `collection.anki2`; performance in the sidecar `collection.mcat_perf.db` (`sidecar_path()` in `mcat_perf.py`). No external/cloud DB — local-first by design.

Full specs: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/DECISIONS.md`](docs/DECISIONS.md), [`docs/PRD.md`](docs/PRD.md), [`docs/MASTERY-QUERY-SPEC.md`](docs/MASTERY-QUERY-SPEC.md).

---

## Build & run

### Desktop — `anki-MCAT`

Anki builds with its own toolchain (Rust + a bundled Python env driven by `ninja`). **`just` is not required.** The working launcher wraps `ninja pylib qt` → `tools/run.py`:

```bash
cd anki-MCAT
./run            # macOS/Linux/Git-Bash: build pylib + qt, then launch
run.bat          # Windows cmd equivalent
```

**Tests:**

```bash
cd anki-MCAT
cargo test -p anki mcat                                  # 4 Rust mastery-query unit tests
export PYTHONPATH="$(pwd)/out/pylib:$(pwd)/pylib"        # on Windows cmd use ';' as the path separator
python -m pytest pylib/tests/test_mcat_mastery.py \
                 pylib/tests/test_mcat_perf.py \
                 pylib/tests/test_mcat_scores.py
```

> **Windows PYTHONPATH caveat:** Windows uses `;` (not `:`) as the path separator, e.g. `set PYTHONPATH=%CD%\out\pylib;%CD%\pylib`.

**Load content:** import `data/flashcards-dev-cloze.csv` + `data/flashcards-dev-basic.csv` (tag `topic:{id}`), then **Tools → MCAT: Load question bank…** → `data/questions.json`. Start from the home-screen dashboard or **Tools → MCAT: Performance session**.

### Mobile — `anki-android-MCAT`

To build the APK that links the **forked** Rust engine (not the stock published backend), set `local_backend=true` in `local.properties` with a locally built `../Anki-Android-Backend` AAR (exact cross-compile steps for all 4 ABIs in `anki-android-MCAT/docs/SHARED-ENGINE-PROOF.md §5`), then:

```bash
cd anki-android-MCAT
./gradlew :AnkiDroid:assembleFullDebug
bash tools/verify_backend_provenance.sh        # -> VERDICT: FORKED engine on mobile
```

> The current APK is **debug-signed** (`CN=Android Debug`). A **release-signed** APK is **not** yet built (see status).

### Desktop installer

A packaged Windows installer exists: `anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi` (~636 MB, valid MSI, sha256 pinned in `docs/CLEAN-INSTALL-PROOF.md`). Rebuild with `./ninja installer:package`. Note it predates the latest UI (built 2026-06-30); a clean-Windows-VM install run is a documented human step.

---

## Evaluation & reproduction

All eval is offline / no-network unless a live AI key is supplied. Targets live in the `Makefile` (Python 3.12 via `py -3.12`):

```bash
make validate-data          # schema + required-explanation validation of the bank
make eval-leakage           # dev/held_out train-test contamination scan
make eval-memory            # FSRS calibration; synthetic demo unless MCAT_COLLECTION=/path/collection.anki2
make eval-performance       # paraphrase gap (card recall vs reworded-question accuracy)
make study                  # study-feature 3-build ablation (synthetic; MCAT_STUDY_MANIFEST=/path for real data)
make eval-ai                # AI explainer vs static + TF-IDF baselines (offline, reproducible)
make eval-ai-live           # explainer against a real provider (needs a key)
make eval-qa-goldset        # follow-up Q&A ship gate, token scorer (dry-run, no key)
make eval-qa-goldset-judge  # live OpenAI answers graded by cross-model Claude judge (needs both keys)
make eval-qa-baseline       # regenerate docs/QA-BASELINE-COMPARISON.md (token scorer, no API)
make test                   # AI-harness unit tests (mocked LLM, no network)
```

**Latency / integrity (real modified backend, small-n, dev hardware):**

```bash
cd anki-MCAT
./out/pyenv/Scripts/python.exe tools/mcat_latency_bench.py       # mastery ~1 ms median @ ~200 cards
./out/pyenv/Scripts/python.exe tools/mcat_undo_integrity_check.py # 15/15 undo + integrity + perf-sync checks
```

- Latency numbers + honesty caveats: `docs/LATENCY-RELIABILITY.md` (`docs/artifacts/latency-results.json`).
- 50k-scale benchmark (`make bench` → `tools/mcat_bench_50k.py`): mastery **~304 ms p50** / dashboard **~2.9 s p50, 5.2 s p95** at ~50k cards — a **known scale limitation** (not yet optimized); `docs/LATENCY-RELIABILITY.md` (`docs/artifacts/bench-50k-results.json`).
- Memory calibration currently ships a **synthetic** demo only (`docs/artifacts/memory-calibration.summary.json` → `"mode": "synthetic"`, injected miscalibration, Brier ≈ 0.14 / ECE ≈ 0.03). **Real** calibration needs a real collection/tester bundles (`docs/TESTER-HANDOFF.md`, `scripts/revlog_from_bundle.py`).

---

## Current deliverable status (honest)

### ✅ Wednesday — core, no AI (DONE)

- Anki fork builds from source; **Rust mastery query + 4 Rust tests + 1 Python integration test** pass.
- Memory review loop; **three-score dashboard** (memory / performance / readiness + coverage + focus area) on Anki’s home screen.
- Performance mode + **170-question curated bank** + **4-type self-report error typing**. **Zero AI.**

### 🟡 Friday — AI + sync + MVP evidence (reviewer verdict: PASS)

- **Shared modified Rust engine on mobile — DEFINITIVE** (Rust query preferred, Kotlin fallback + cross-check; `SHARED-ENGINE-PROOF.md`).
- **Undo + collection integrity — PROVEN** (15/15; `UNDO-INTEGRITY-PROOF.md`).
- **Clean install — mobile PROVEN (automated)**; **desktop `.msi` artifact verified**, clean-VM run is a human step (`CLEAN-INSTALL-PROOF.md`).
- **Latency/reliability — MEASURED** (small-n, dev hardware; `LATENCY-RELIABILITY.md`).
- **AI explainer + follow-up Q&A — implemented with committed gates and a beats-baseline comparison** (offline explainer + cross-model-judged follow-up; explainer live run pending a key).
- **Perf-data cross-device sync — PROVEN headlessly**; **two-device memory-sync live recording — pending** (rule documented).

### 🔴 Sunday — prove + ship (IN PROGRESS / PLANNED)

- **Study-feature 3-build ablation (interleaved vs blocked vs plain Anki) — BUILT (synthetic pipeline; real 3-build data pending).** `scripts/eval_study_feature.py` + `make study` + [`docs/STUDY-FEATURE-RESULTS.md`](docs/STUDY-FEATURE-RESULTS.md) + `docs/artifacts/study-feature.{png,summary.json,arms.csv}` compare the three arms on the **same `held_out` performance test at equal study TIME**, with Wilson/Newcombe 95% CIs + a two-proportion z-test, a documented fixed-seed `--synthetic` generator, and a real-data `--manifest` seam. **The reported numbers are SYNTHETIC** (assumed effect sizes; seed `20260703`, equal 1800 s budget, n=120/arm): interleaved **71.7%** vs blocked **60.0%** vs plain Anki **50.0%**; interleaved − plain **+21.7 pt (p=0.001, significant)**, interleaved − blocked **+11.7 pt (p=0.057, not significant — underpowered)**. This is a pipeline proof pending real 3-build tester data, **not** a product claim (`docs/DECISIONS.md §11`).
- **50k `make bench` — IMPLEMENTED (real benchmark; known scale limitation).** `make bench` + `anki-MCAT/tools/mcat_bench_50k.py` run a real ~50k-card benchmark against the built fork backend ([`docs/LATENCY-RELIABILITY.md`](docs/LATENCY-RELIABILITY.md), `docs/artifacts/bench-50k-results.json`): at 49,986 cards the mastery query is **~304 ms p50** and the 3-score dashboard is **~2.9 s p50 / 5.2 s p95** — i.e. **~O(cards)** and **not interactive** at scale, confirming scale risk "RS" is real. Two low-risk fixes (cache the mastery result once per dashboard render; a grouped single-pass SQL aggregation in the Rust query) are **identified but deliberately not applied** in-session.
- **Real (non-synthetic) memory calibration — pending** tester/builder data (harness ready).
- **Release-signed APK — NOT built** (current APK is debug-signed).
- **Phone-review / two-device demo video — NOT recorded.** No demo/screen-recording of the deliverable exists — the only video files in the repos are **upstream Anki/AnkiDroid test fixtures** (e.g. `AnkiDroid/src/androidTest/assets/anki-15872-*`), not product recordings; `docs/RECORDING-RUNBOOK.md` is the shot-list only. (The mobile **clean-install screenshot does exist** — `anki-android-MCAT/docs/artifacts/clean_install_launch.png`; the one outstanding recording is the on-camera two-device memory-sync / phone-review video.)
- **Live AI (explainer) numbers — pending** a provider key; readiness mapping coefficients — deferred.

---

## Honesty rule (non-negotiable)

No readiness score without: evidence behind the number, what data is missing, a **range** (not a point estimate), coverage % on the full outline, and the single best next action. A confident number with none of that is a guess in a nice font — and the readiness function abstains rather than fake it.

---

## Documentation map

- Product: [`docs/PRD.md`](docs/PRD.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · [`docs/DECISIONS.md`](docs/DECISIONS.md) · [`docs/MODELS.md`](docs/MODELS.md)
- AI: [`docs/AI-FEATURE.md`](docs/AI-FEATURE.md) · [`docs/QA-GOLDSET.md`](docs/QA-GOLDSET.md) · [`docs/QA-BASELINE-COMPARISON.md`](docs/QA-BASELINE-COMPARISON.md)
- Sync & error typing: [`docs/SYNC-CONFLICT-RULE.md`](docs/SYNC-CONFLICT-RULE.md) · [`docs/ERROR-DIAGNOSIS-SPEC.md`](docs/ERROR-DIAGNOSIS-SPEC.md)
- MVP evidence: [`anki-android-MCAT/docs/SHARED-ENGINE-PROOF.md`](../anki-android-MCAT/docs/SHARED-ENGINE-PROOF.md) · [`docs/CLEAN-INSTALL-PROOF.md`](docs/CLEAN-INSTALL-PROOF.md) · [`docs/UNDO-INTEGRITY-PROOF.md`](docs/UNDO-INTEGRITY-PROOF.md) · [`docs/LATENCY-RELIABILITY.md`](docs/LATENCY-RELIABILITY.md) · [`docs/TESTER-HANDOFF.md`](docs/TESTER-HANDOFF.md) · [`docs/FEEDBACK-2026-07-03.md`](docs/FEEDBACK-2026-07-03.md)

---

## License

**MCAT Speedrun is licensed under the GNU AGPL-3.0-or-later.** It is built as a fork of two upstream projects:

- **Anki** (desktop) — [`ankitects/anki`](https://github.com/ankitects/anki), AGPL-3.0-or-later
- **AnkiDroid** (Android) — [`ankidroid/Anki-Android`](https://github.com/ankidroid/Anki-Android), AGPL-3.0-or-later (some components GPL/LGPL-3.0)

All upstream copyright remains with the original Anki and AnkiDroid authors; the MCAT Speedrun additions are contributed under the same AGPL-3.0-or-later license, and the complete corresponding source is published with any distribution (AGPL §13). This is an independent project, **not affiliated with or endorsed by** Ankitects Pty Ltd or the AnkiDroid team.

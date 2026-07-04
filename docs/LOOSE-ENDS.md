# Loose ends — open items to address

Running list of unresolved threads, research gaps, and deferred design work.
Not build tasks (those live in `WEDNESDAY-CHECKLIST.md` / specs) — this is the
"we know this isn't settled yet" list. Newest / highest-priority at top.

## Research

- [ ] **More research on students' poor ability to self-diagnose.** Keep two
  claims separate — we've conflated them once already:
  - **Established:** students **overestimate their own performance** (poor
    calibration — Dunning-Kruger, Ehrlinger, calibration-of-comprehension). This
    is about judging *right/wrong*, not error categories.
  - **Our inference (needs support):** that they *also* can't reliably
    categorize *why* they missed (reasoning slip vs content gap). This is an
    extrapolation, not a direct finding, and it's **load-bearing** for the whole
    error-diagnosis design (`ERROR-DIAGNOSIS-SPEC.md`).
  To firm up: find primary sources with effect sizes (not our BrainLift
  restatement); look specifically for evidence on *error-type* self-classification,
  not just performance overestimation; and distinguish *diagnostic* self-report
  (likely unreliable) from *observational* self-report ("did you see the EXCEPT?"
  — likely fine).
  - Implication if the inference is weaker than assumed: the confirm button could
    be promoted back toward a real signal. If stronger: lean harder on the
    objective re-check probe + gold set.

## UI / polish

- [ ] **Pixel-level UI cleanup — dedicated perfectionist-critic pass.** Do a
  full-app visual QA pass acting as a ruthless design critic: align to the pixel,
  and hunt spacing/padding inconsistencies, typography hierarchy, color/contrast,
  hover/focus states, empty/loading states, and any residual clipping or
  compression across the dashboard (three score cards + focus area + coverage
  bar), performance mode (passage/stem/choices + docked AI panel), the
  remediation/mastery/error-report dialogs, and the reviewer. This is a
  polish/consistency sweep, not a functional gap — treat every off-by-a-pixel or
  inconsistent margin as a defect. (Lean on the design-critique / polish skills.)
- [x] **Move the "Show Answer" button to center.** In the review UI the
  Show Answer button should be horizontally centered (currently not). Small
  UI/CSS fix in the reviewer bottom bar.
  Fixed in `anki-MCAT/qt/aqt/data/web/css/reviewer-bottom.scss`: added `width: 25%`
  to `.stat` so the Edit/More side columns are equal, centering the `#middle` column
  (rebuild required to regenerate `qt/_aqt/data/web/css/reviewer-bottom.css`).

## Design — not yet settled

- [ ] **"Not sure" (IDK) — richer version deferred; keep it a DIAGNOSTIC-only
  tool that must NEVER leak into Readiness (demo decision, 2026-07-03).** For the
  demo the "Not sure" opt-out is intentionally minimal: a non-CARS IDK maps
  **immediately** to `content_gap` (CARS → `unresolved`), is **excluded** from
  Performance accuracy + mastery-unlock, and is tracked as a plain `idk_count`
  (no confidence weighting, no lucky-guess detection). See DECISIONS §30.
  **Deferred richer version:** confidence-weighted scoring — treat a
  **correct-but-low-confidence** answer as a *lucky-guess* signal (don't award
  full mastery credit) and a **wrong-but-high-confidence** answer as a
  *misconception* flag — plus distinguishing a true "no idea" from a "narrowed it
  to two." **Real-MCAT caveat (load-bearing):** the actual MCAT has **NO guessing
  penalty** — on test day you should **always** guess and never leave a blank. So
  IDK here is deliberately a **diagnostic / mastery** instrument only: it must
  **not** be trained into, rewarded by, or leak into the **Readiness** score
  (which estimates the real 472–528 outcome). Any future IDK-derived signal stays
  gated to the study/diagnostics view, not Readiness. **Also open (scores
  worker):** the direct `perf_attempts` reads in `mcat_scores.py`
  (`_section_attempt_counts`, `_provisional_range`, the coverage attempt branch)
  still need an `idk = 0` filter so IDK rows can't slip into the Readiness range /
  section gates / coverage; the `accuracy()`-based paths already exclude them.
  Cross-refs: DECISIONS §30; `mcat_perf.py` (`accuracy()`, `idk_count()`,
  `PerformanceSession.not_sure()`).
- [ ] **Probe-confirmed IDK labeling — deferred Sunday refinement (2026-07-03).**
  Today an IDK is *assumed* to be a `content_gap` (non-CARS route) and the
  user-facing copy is deliberately hedged to "flagging a knowledge gap" precisely
  because "I don't know" is ambiguous — it could be a genuine content gap OR an
  application/reasoning gap (they know the facts but can't apply them). **Deferred
  refinement:** optionally run the existing content re-check probe on an IDK to
  *objectively* resolve which it is instead of assuming — probe **FAIL** → keep
  `content_gap` (they truly lacked the content); probe **PASS** → they had the
  content, so relabel to an application/reasoning gap and route accordingly. This
  reuses the probe machinery already built for missed science items. Cross-refs:
  DECISIONS §30 (refinement note); re-check probe items above;
  `mcat_perf.py` (`resolve_probe_target`, `record_probe_outcome`).
- [ ] **CARS misses skip the error-type confirm / self-diagnosis step (demo
  decision, 2026-07-03).** For CARS **performance** questions the app does **not**
  ask the user to pick or confirm an error type on a miss — the error-type
  confirmation / self-diagnosis prompt is omitted for CARS specifically (a CARS
  miss routes only to its objective skill-archetype + pacing track, not to the
  error-type self-report fallback). **Why:** asking a CARS misser to confirm
  *their own* error type partially undercuts this project's core premise that
  users generally **can't reliably self-diagnose** *why* they missed — surfacing a
  self-report step there quietly contradicts the thesis the whole error-diagnosis
  design rests on. So for the demo we omit it. This is an **accepted temporary
  gap** ("hole"), not a settled design. **Revisit later:** decide either (a) give
  CARS a **different, non-self-report diagnosis path** (lean harder on the
  objective skill-archetype + pacing signals, since CARS has no content oracle),
  or (b) justify keeping an error-type confirm on the grounds that a **scaffolded
  single-hypothesis confirmation** ("looks like X — right?") is materially
  different from **open self-diagnosis** and may be reliable enough — the very
  distinction DECISIONS §9 already draws for the science track. Cross-refs:
  `ERROR-DIAGNOSIS-SPEC.md` → "CARS diagnosis" (demo note); DECISIONS §9
  (confirm-a-hypothesis vs open self-report).
- [x] **Application-practice bank exists AND is wired into the `application`
  remediation channel (done 2026-07-02).** The curated pool
  (`data/application-practice.json` — 45 science integration items, 3 per topic,
  each `pool: application_practice`, `split: remediation`, with a `concept` slug)
  is now the concrete destination for the two-channel routing
  (`ERROR-DIAGNOSIS-SPEC.md` → "Two-channel remediation routing"). On a resolved
  `application` miss the performance dialog launches a **real short practice set**
  selected by `select_application_practice` (topic filter → exclude just-missed
  concept, same-concept fallback → exclude seen ids → variety rank → **N = 2**),
  shown in a separate, clearly-unscored `RemediationDialog`. **Isolated from
  scoring:** items live in their own `remediation_items` table (DB
  `CHECK (split = 'remediation')`) and practice attempts log to a separate
  `remediation_attempts` channel — never `perf_questions` / `perf_attempts` — so
  they can never enter the Performance/Readiness scores or the held_out eval.
  Degradation preserved: no eligible pool items → the generic "practice more
  applied items in [topic]" message. Load via Tools → "MCAT: Load
  application-practice pool…". Files: `pylib/anki/mcat_perf.py`,
  `qt/aqt/mcat/performance_dialog.py`, `qt/aqt/mcat/remediation_dialog.py`,
  `qt/aqt/mcat/__init__.py`, `pylib/tests/test_mcat_perf.py`.
- [~] **Component-card granularity expansion — trio decomposed, rest tracked
  (2026-07-02).** Per the "Component cards, not answer cards" principle, **every
  question's prerequisites should each be individually carded** (granular
  component facts, never an answer-encoding card). **Eval trio done:** **+24
  atomic Cloze cards** decompose `bb_enzymes` / `cp_acids_bases` / `cp_kinetics`
  to per-prerequisite granularity (trio 42→66 cards), with a no-answer-encoding
  guardrail (three too-close drafts reframed/dropped). This sharpens per-card `M`
  and lets the re-check probe localize the *specific* failed prerequisite. **Still
  open:** topics beyond the trio still guarantee only **≥1 backing card per
  question**, not one-per-prerequisite — the prioritized next-pass list
  (`bb_citric_acid`, `bb_glycolysis`, `cp_electrochem`, `cp_thermo`,
  `bb_genetics`, then single-fact PS/`bb_*` topics) is tracked in
  `docs/COMPONENT-CARD-GRANULARITY.md`. Authoring lives in `build_flashcards.py`;
  DECISIONS §28.
- [ ] **`w_mis` override strength under the finalized tagging still needs
  empirical data.** How much a *distinctive-misconception* `content_gap`
  distractor pick should override high `M` (the `w_mis` weight) is set by judgment
  only. With the finalized 3-axis tags (71 content_gap / 12 trap / 7 null), the
  content axis now carries a cleaner signal, but the *magnitude* of the override
  is unvalidated — it must be tuned against real attempt data and re-check-probe
  outcomes (probe FAIL should correlate with the distinctive-misconception picks
  we let contest `application`). *(Complements the `w_mis` threads in the
  choice-axis and tunable-params items below — same weight, framed here for the
  finalized tag set.)* **Update (2026-07-02):** the re-check probe now ships
  (IMMEDIATE variant) and logs `recheck_correct`, so the objective label needed
  to calibrate `w_mis` is now being collected — a probe FAIL on a
  distinctive-misconception pick is the confirmation signal `w_mis` should track.
- [~] **Choice-axis discrimination + shallow-mastery capture.** *Addressed in the
  draft (2026-07-01):* the `choice_diagnosis` tags in
  `SYNTHESIS-QUESTIONS-DRAFT.md` were re-tagged so the content axis actually
  discriminates — `content_gap` now means a *specific, distinct* misconception,
  with bare `null` near-misses and `trap: <type>` execution landings (finalized
  enum {`negation`, `unit`, `inverse`, `scaling`, `transpose`, `partial`}; a trap
  is its own axis on `maps_to: null`, not a `content_gap`) introduced where
  honest. Finalized bank counts: **71 content_gap / 12 trap / 7 null** (see that
  file's "Choice-axis re-tag pass"). The spec
  gained a **"Choice tagging methodology"** subsection and a **"Discriminating
  shallow mastery"** mechanism: a distinctive-misconception distractor pick is
  independent content-gap evidence, so high `M` no longer *unconditionally*
  downranks `content_gap` (new `w_mis·g` term) — this is what catches the
  high-`M`-but-shallow (`application_gap`) student instead of mislabeling them
  `application`. See `ERROR-DIAGNOSIS-SPEC.md` → those two sections.
  **Residual (needs empirical tuning):** the weight `w_mis` — *how much* a
  distinctive-misconception distractor pick should override high `M` — is set by
  judgment right now. It must be tuned once real attempt data exists, validated
  against **re-check-probe outcomes** (probe FAIL should correlate with the
  distinctive-misconception picks we let contest `application`) and the gold set.
  Too high → we over-call `content_gap` on strong students (undoing the 505→510
  applied-reasoning signal); too low → shallow mastery is silently absorbed into
  `application` (the named residual risk below). Also open: whether `w_mis`
  should scale with *how distinctive* the misconception is (per-distractor)
  rather than a single global weight.
- [ ] **Residual content↔application boundary risk (from the 3-bucket rename;
  ELEVATED by the abstention rebalance).** *Named (2026-07-01):* collapsing the
  science taxonomy to `content_gap` / `application` / `misread` **moves** the
  hardest boundary rather than removing it — the whole split now hinges on the
  `content_gap`↔`application` line, which rests on the two least-tested pieces:
  the content-held score `M` and the content re-check probe. If the probe is
  contaminated (PASS is priming-inflated) or `M` is mis-estimated (stale cards,
  uncovered prerequisites), **`application` will silently absorb real content
  gaps** → student sent to applied practice instead of the flashcards they need.
  **Rebalance update (2026-07-01, DECISIONS §21):** `infer_error_type` now makes
  **`application` the DEFAULT** for a content-presumed-held miss (committing
  mid/ambiguous/imputed-`M` and fast-but-no-trap misses at moderate confidence
  0.55–0.60 instead of abstaining). This is the right product call (commit +
  honest confidence beats over-abstaining), but it **raises exposure** to this
  boundary risk: more misses land in `application` by construction, so `M`
  quality and tag coverage carry more weight. Mitigations in place: authored
  `content_gap` tag and low `M` pre-empt `application` (engine branches 1–2);
  the default fires at moderate confidence (probe candidate, not settled fact);
  asymmetric probe (FAIL strong, PASS weak); and **persistent
  `application`→`content_gap` student overrides are the measurable audit signal**
  that the default is over-firing.   *To firm up:* validate `M` calibration and
  probe contamination on the gold set, and watch the override rate, before
  trusting the `application` label on the dashboard. See `ERROR-DIAGNOSIS-SPEC.md`
  → "Residual risk — the boundary moved" and DECISIONS §21.
  **Update (2026-07-02):** the content re-check probe now ships (IMMEDIATE
  variant), so `recheck_correct` gives an **objective label stream** to validate
  this exact boundary — a probe FAIL objectively confirms `content_gap` (probe
  overrides `M`/tag), and PASS objectively rules it out. Collect probe outcomes
  vs `M`/tag to measure how often `application` was silently absorbing real gaps.
- [x] **`M` uses topic-level retrievability, not per-card FSRS-R (v2 slice
  limitation).** *Named (2026-07-01):* `content_held_score` (`M`) in
  `mcat_perf.py` currently uses the **topic-level** `avg_retrievability` from the
  mastery proto, not the current FSRS-R of the **specific** `supports_question`
  backing cards. The spec's ideal is per-card. Topic-level averaging **hides
  per-card gaps** (7/8 cards mastered but the one the question needs is weak →
  reads "mastered" → real `content_gap` mislabeled `application`) and **destroys
  localization** (which prerequisite failed) — worst for the new synthesis items
  whose prerequisites differ within a topic. The build agent used the coarse
  fallback believing per-card R needs a Rust/proto rebuild that would risk the
  frozen build.
  **RESOLVED — implemented (2026-07-01): per-card R now computed in pure Python,
  no Rust/proto rebuild.** In Anki 26.05 (fsrs 5.2.0) each card's FSRS memory
  state is exposed on the Python `Card` object, so `M` is built from the specific
  backing cards without touching the backend. Shipped in `pylib/anki/mcat_perf.py`:
  `fsrs_retrievability()` (pure math, unit-tested — R=0.9 at t=S, sign-robust),
  `card_retrievability(col, cid)`, and `backing_card_ids_for_question(col, qid)`;
  `_mastery_for` now feeds per-card R into `content_held_score` and only falls
  back to topic-level R when a question has no discoverable backing cards. The
  stale "needs backend change" note in `content_held_score` was removed. What was
  implemented (matches the plan below):
  - **Reach the backing cards.** Add `backing_card_ids_for_question()` to
    `pylib/anki/mcat_perf.py`: invert `supports_question` (question → notes) via
    `col.find_notes(...)`, then expand each note to its cards with
    `col.card_ids_of_note(nid)`.
  - **Per-card R helper.** Add `card_retrievability(col, cid)` computing R in
    pure Python from `Card.memory_state` (stability `S`), `Card.decay` (default
    `0.5`), and elapsed days since `Card.last_review_time`:
    `R = (1 + FACTOR·(t_days)/S)^(-decay)`, with
    `FACTOR = 0.9^(1/-decay) − 1`. *(Alternative:
    `col.card_stats_data(cid).fsrs_retrievability`, but that can backfill
    `last_review_time` to the DB — prefer the pure-Python read path to stay
    read-only.)*
  - **Rewrite `_mastery_for`** (`mcat_perf.py:595`) to feed the per-card R list
    into the already-card-ready `content_held_score` (`mcat_perf.py:404`),
    replacing the topic-level fallback. **Delete** the stale "needs backend
    change" note at `mcat_perf.py:417-420`.
  - **Edge cases:** new/unreviewed or SM-2 cards with no `memory_state` → return
    `None` so `content_held_score` imputes `UNCOVERED_R0 = 0.5`.
  - **Re-check probe** remains a *complementary* backstop for probe-based
    contamination checks, **not** a required fallback for `M`.
  - **Refs:** `cards.py:49-52` / `102-110` (memory state, decay, last review),
    `collection.py:567` (`find_notes`) / `1015-1022` (`card_ids_of_note`),
    `rslib/src/stats/card.rs:51` (R formula parity).
- [x] **Diagnosis → next-action mapping.** *Resolved / specced (2026-07-01):*
  `content_gap` → "Review N flashcards in [topic]" (filtered memory review);
  `application` → "Practice N applied questions in [topic]" (performance session
  filtered to application/synthesis items); `misread` → "Careful-reading / pacing
  drill". Surfaces as a prominent **"Focus area"** dashboard card (same weight as
  the three scores) that launches the matching practice in one click. Logic in
  `mcat_scores.py`, tile in `deckbrowser.py`. See `ERROR-DIAGNOSIS-SPEC.md` →
  "Next-action mapping".
- [~] **Deferred v2 UX (build later, not in the current slice):** re-check probe
  UI (pre-reveal micro-probe + delayed natural check), select-then-confirm churn
  logging (`first_choice_index` / `answer_changes`), sparing observation-confirm
  prompts, and bulk `choice_diagnosis` authoring for all questions. Also the
  Wednesday 4-button → 3-button enum migration (rename `reasoning`→`application`,
  fold `passage_mapping`), done when v2 ships.
  - **Done (2026-07-01): `feature_json` capture.** Every attempt (correct *and*
    incorrect) now writes the full observed signal vector to a `feature_json`
    column (schema `mcat_perf_features_v1`; see DECISIONS §19 for the key list) plus
    the objective label columns. This is the labeled-data pipeline substrate; an
    actual ML *model* is still deferred (small-n — see "Small-n honesty" below).
  - **Done (2026-07-02): content re-check probe (IMMEDIATE variant) →
    `recheck_card_id` / `recheck_correct` now POPULATED.** The performance dialog
    fires an immediate recall probe on a science miss (before the explanation/
    diagnosis) and feeds the objective outcome into `infer_error_type`
    (`recheck_correct` branch 0): probe **FAIL** → `content_gap` @0.9 (strongest
    gap signal); probe **PASS** → suppress `content_gap`, route to
    `application`/`misread` at raised confidence; `error_source = inference+recheck`
    when the probe-informed call is confirmed. Target resolution prefers a real
    backing `card_id` (weakest-link, lowest FSRS-R first), falls back to a
    concept prompt (`card_id` NULL), or skips (CARS/unmapped). Shipped in
    `pylib/anki/mcat_perf.py` (`resolve_probe_target`,
    `PerformanceSession.probe_target` / `record_probe_outcome`) +
    `qt/aqt/mcat/performance_dialog.py`; tests in `pylib/tests/test_mcat_perf.py`.
    **This gives us an OBJECTIVE label stream** (not self-report) that can later
    calibrate `w_mis` and validate the `content_gap`↔`application` boundary (see
    the two items below). Accepted tradeoff: the immediate probe's PASS carries a
    mild MCQ-priming bias, accepted for the demo (PASS treated as solid; FAIL
    remains strongest).
  - **Still NULL (needs dialog wiring, NOT faked): `first_choice_index`,
    `answer_changes`, `recheck_timing`.** The dialog is still single-submit (no
    churn logging) and only the *immediate* probe placement is built, so
    `recheck_timing` (`immediate` \| `delayed`) has no `delayed` branch yet. Left
    NULL by design; the code path is commented accordingly (`mcat_perf.py`).
- [ ] **Attempt-data collection relies on export, not sync (sidecar ⟂ AGENTS
  lock).** *Named (2026-07-01):* `AGENTS.md` still lists "perf tables in the
  collection DB + stock Anki sync" as locked, but the implementation uses a
  **non-syncing sidecar** (`collection.mcat_perf.db`; revised in DECISIONS §5 for
  durability). Stock Anki sync only reaches **AnkiWeb**, not a queryable analytics
  DB — even the original in-collection plan would only have produced AnkiWeb rows,
  not something we can pull for eval. So attempt-data **collection for eval goes
  through the read-only export path** (`tools/mcat_export_perf.py` / Tools →
  "MCAT: Export performance data…"), and an external telemetry backend is
  **deferred**. *AGENTS lock reconciled (2026-07-03):* `AGENTS.md` (Locked
  decisions), `ARCHITECTURE.md §7`, `PRD.md` S-2, and `.cursor/rules/anki-rust.mdc`
  were updated to the sidecar + custom uuid-deduped JSON bundle model per
  DECISIONS §22 — no doc still asserts "perf tables in the collection DB."
  Still open: an external telemetry backend (only if cloud features are adopted)
  remains deferred; cross-device perf sync ships via the export/import bundle
  (DECISIONS §22, build step 7).
- [x] **CARS track has no objective oracle.** *Resolved (2026-07-01):* CARS
  doesn't use the error-typing engine at all — generic types collapse there.
  Instead it uses **skill-archetype accuracy** (group by existing CARS
  `topic_id`: comprehension / within / beyond) + a **pacing flag** from timing.
  Both objective, no oracle needed. See `ERROR-DIAGNOSIS-SPEC.md` → "CARS
  diagnosis". *Remaining:* finalize the pacing thresholds and whether to report
  finer question archetypes (inference / tone / strengthen-weaken) beyond the 3
  AAMC skills.
- [~] **Cold-start behavior — earlier "stay `unresolved`" stance SUPERSEDED
  (2026-07-01).** Before per-item / per-student timing baselines and item
  p-values exist, the process axis is near-useless. The **original** spec answer
  was "with no baselines, most misses go `unresolved` → self-report" (and,
  relatedly, "fast alone is weak → `unresolved`"). *Decided (2026-07-01,
  DECISIONS §21):* that stance is **reversed** — over-abstaining defeated the
  "infer, don't ask" goal (cold-start `M` sits in the ambiguous band, most
  distractors are untagged, most items are recall-demand), so `infer_error_type`
  now **commits `application` as the default** for these cold-start misses at
  **moderate confidence (0.55–0.60)**, carrying honesty in the confidence rather
  than abstaining. `unresolved` is reserved for the truly-dark miss (`M`
  unavailable + recall/unknown demand + no tag + no trap). The confidence (not
  the branch choice) is what sharpens as baselines accumulate. *Remaining:* how
  fast to transition to learned per-item/per-student baselines, and whether the
  moderate cold-start confidences (0.55/0.60) are well-calibrated once gold-set
  data exists. See `ERROR-DIAGNOSIS-SPEC.md` → "Cold-start honesty (superseded)"
  and "Inference rule".
- [~] **Re-check probe placement + fatigue.** *Partly resolved (2026-07-02):* the
  **IMMEDIATE pre-reveal micro-probe** is built (fires before the post-answer
  explanation, so no explanation contamination) and treats PASS as solid per the
  accepted immediate-variant tradeoff. *Still open:* the **delayed natural-review**
  variant (read the backing card's next memory-session outcome to remove the
  immediate-priming bias on PASS), and **fatigue/trigger budgeting** — it
  currently fires on every science miss with a resolvable sub-concept rather than
  sampling / gating on ambiguous `M`. Add confidence-gated + rate-limited
  triggering once the demo need is met.
- [ ] **Tunable params** (`ERROR-DIAGNOSIS-SPEC.md`): demand factor `d`,
  uncovered-prerequisite prior `R0`, the misconception weight `w_mis` (how much a
  distinctive-misconception distractor pick keeps `content_gap` in play against
  high `M` — see the choice-axis item above), and aggregation choice (geometric
  mean vs min). Set on dev, validated against gold set / re-check-probe outcomes.

## Validation / data

- [x] **Paraphrase-gap instrument built (§7d, 2026-07-02).** The memory ⟂
  performance validation tool now exists: for the eval trio (`cp_acids_bases`,
  `bb_enzymes`, `cp_kinetics`, 28 anchor concepts) it pins two reworded questions
  per concept and reports `paraphrase_gap = card_recall_rate − question_accuracy`
  (per-topic + overall), so we can show the performance score measures **transfer,
  not parroted recall**. **30 new held_out MCQs** authored (`q_ho_061`–`q_ho_090`;
  bank now 170 Q, 65 dev / 105 held_out); second stem of every pair is always
  freshly `held_out` (leakage-guarded by `validate_data.py`). No AI/network —
  `scripts/eval_paraphrase.py` (`make eval-performance`) runs a real-data path or
  a deterministic labelled synthetic demo. Deliberately deferred: the
  `supports_question` deck edges for the new probes (manifest `card_ref` is the
  authoritative link for now). See `docs/PARAPHRASE-TEST.md`, DECISIONS §27.
  *Remaining:* feed real recall/attempts once collected (still small-n — see
  below).
- [ ] **Gold set doesn't exist yet.** Need ~20–30 held_out items with think-aloud
  labels (friend) to get a real accuracy/calibration number for the inference.
- [ ] **Small-n honesty.** Solo builder + one friend → training a real ML
  classifier is likely post-prototype. Be explicit that v1's deliverable is
  *calibrated rules + a clean labeled pipeline*, not a trained model.

## Carried over (from build checklist)

- [ ] Commit hash + clean-build recording (work currently uncommitted).
- [ ] Clean-machine installer run + recording.
- [ ] Desktop memory-review screen recording.

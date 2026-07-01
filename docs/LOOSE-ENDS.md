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

## Design — not yet settled

- [ ] **Application-practice bank does not exist yet (required for the
  `application` remediation channel).** The two-channel routing
  (`ERROR-DIAGNOSIS-SPEC.md` → "Two-channel remediation routing") sends an
  `application` / shallow-mastery miss to **targeted practice on similar
  integration items**, explicitly **not** a flashcard. But no such curated
  application-practice bank (topic-filtered integration items sized for a short
  remediation set) exists today — the `application` "next action" currently has
  nothing concrete to launch. Needed: a small per-topic pool of
  application/synthesis items reserved for remediation (distinct from the
  held_out eval set to avoid leakage). Until it exists, the `application` focus
  action must degrade gracefully (generic "practice more applied items in
  [topic]") rather than promise a bank that isn't there.
- [ ] **Component-card granularity expansion is ongoing.** Per the
  "Component cards, not answer cards" principle, **every question's prerequisites
  should each be individually carded** (granular component facts, never an
  answer-encoding card). This is not done — coverage today guarantees only
  **≥1 backing card per question**, not one card per *prerequisite component*.
  Expanding granularity both improves prerequisite coverage and sharpens per-card
  `M` (cleaner content-held signal / better localization of which prerequisite
  failed). Ongoing authoring task in `build_flashcards.py`; track which questions
  still have under-decomposed prerequisites.
- [ ] **`w_mis` override strength under the finalized tagging still needs
  empirical data.** How much a *distinctive-misconception* `content_gap`
  distractor pick should override high `M` (the `w_mis` weight) is set by judgment
  only. With the finalized 3-axis tags (71 content_gap / 12 trap / 7 null), the
  content axis now carries a cleaner signal, but the *magnitude* of the override
  is unvalidated — it must be tuned against real attempt data and re-check-probe
  outcomes (probe FAIL should correlate with the distinctive-misconception picks
  we let contest `application`). *(Complements the `w_mis` threads in the
  choice-axis and tunable-params items below — same weight, framed here for the
  finalized tag set.)*
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
- [ ] **Residual content↔application boundary risk (from the 3-bucket rename).**
  *Named (2026-07-01):* collapsing the science taxonomy to `content_gap` /
  `application` / `misread` **moves** the hardest boundary rather than removing
  it — the whole split now hinges on the `content_gap`↔`application` line, which
  rests on the two least-tested pieces: the content-held score `M` and the
  content re-check probe. If the probe is contaminated (PASS is priming-inflated)
  or `M` is mis-estimated (stale cards, uncovered prerequisites), **`application`
  will silently absorb real content gaps** → student sent to applied practice
  instead of the flashcards they need. Mitigations in place: asymmetric probe
  (FAIL strong, PASS weak) + content-presence honesty gate (no `application`
  without established content). *To firm up:* validate `M` calibration and probe
  contamination on the gold set before trusting the `application` label on the
  dashboard. See `ERROR-DIAGNOSIS-SPEC.md` → "Residual risk — the boundary moved".
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
- [ ] **Deferred v2 UX (build later, not in the current slice):** re-check probe
  UI (pre-reveal micro-probe + delayed natural check), select-then-confirm churn
  logging (`first_choice_index` / `answer_changes`), sparing observation-confirm
  prompts, bulk `choice_diagnosis` authoring for all questions, and
  `feature_json`/ML training. Also the Wednesday 4-button → 3-button enum
  migration (rename `reasoning`→`application`, fold `passage_mapping`), done when
  v2 ships.
- [x] **CARS track has no objective oracle.** *Resolved (2026-07-01):* CARS
  doesn't use the error-typing engine at all — generic types collapse there.
  Instead it uses **skill-archetype accuracy** (group by existing CARS
  `topic_id`: comprehension / within / beyond) + a **pacing flag** from timing.
  Both objective, no oracle needed. See `ERROR-DIAGNOSIS-SPEC.md` → "CARS
  diagnosis". *Remaining:* finalize the pacing thresholds and whether to report
  finer question archetypes (inference / tone / strengthen-weaken) beyond the 3
  AAMC skills.
- [ ] **Cold-start behavior.** Before per-item / per-student timing baselines and
  item p-values exist, the process axis is near-useless. Decide defaults
  (conservative absolutes vs mostly `unresolved`) and how fast we transition to
  learned baselines.
- [ ] **Re-check probe placement + fatigue.** Pre-reveal micro-probe vs delayed
  natural review; how often to trigger without annoying the user; contamination
  from the post-answer explanation.
- [ ] **Tunable params** (`ERROR-DIAGNOSIS-SPEC.md`): demand factor `d`,
  uncovered-prerequisite prior `R0`, the misconception weight `w_mis` (how much a
  distinctive-misconception distractor pick keeps `content_gap` in play against
  high `M` — see the choice-axis item above), and aggregation choice (geometric
  mean vs min). Set on dev, validated against gold set / re-check-probe outcomes.

## Validation / data

- [ ] **Gold set doesn't exist yet.** Need ~20–30 held_out items with think-aloud
  labels (friend) to get a real accuracy/calibration number for the inference.
- [ ] **Small-n honesty.** Solo builder + one friend → training a real ML
  classifier is likely post-prototype. Be explicit that v1's deliverable is
  *calibrated rules + a clean labeled pipeline*, not a trained model.

## Carried over (from build checklist)

- [ ] Commit hash + clean-build recording (work currently uncommitted).
- [ ] Clean-machine installer run + recording.
- [ ] Desktop memory-review screen recording.

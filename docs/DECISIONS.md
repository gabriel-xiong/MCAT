# Design Decision Log — MCAT Speedrun

**Last updated:** 2026-07-02  
**Status:** Locked for v1 implementation

---

## Summary table

| # | Decision | Choice |
|---|----------|--------|
| 1 | Product shape | Anki fork + measurement layer |
| 2 | Exam | MCAT (472–528) |
| 3 | Course scope | Subset of topics (~15–25); not full prep course |
| 4 | Rust change | Per-topic **mastery query** |
| 5 | Mobile | **Android only** — AnkiDroid fork |
| 6 | Sync / perf storage | **Stock Anki sync**; perf data in **local sidecar `mcat_perf.db`** (revised — see §5); no external/cloud DB in v1 |
| 7 | Modes | Memory (FSRS) + Performance (curated MCQs), **separate sessions** |
| 8 | Performance gate | **Moderate:** ≥3 cards seen + ≥5 Good/Easy per topic |
| 9 | CARS | Performance-only; no memory gate |
| 10 | Scores | **Three separate** with ranges + abstain |
| 11 | Readiness | Section map + **coverage penalty**; abstain if coverage &lt; ~50% |
| 12 | Error typing | Wed: **4 self-report types** (frozen). v2: **3-bucket science taxonomy** (`content_gap`, `application`, `misread`; `reasoning`→`application`, `passage_mapping` folds in) **inferred from distractor role + cross-system `M` + timing**, then **re-check probe + student *confirms a hypothesis*** (probe settles the objective content axis; confirm captures the un-inferable misread↔application axis, correctable not a verdict; self-report demoted to confirmation + validation signal) — see §9, `ERROR-DIAGNOSIS-SPEC.md` |
| 13 | Question bank | **Curated OpenStax** (named sources); AI off at runtime |
| 14 | Study feature | **Interleaved vs blocked performance sessions** |
| 15 | Memory model | FSRS + calibration (not custom ML) |
| 16 | Performance model | Attempt accuracy (not memory × constant) |
| 17 | Builder | Solo; friend = held-out performance participant |
| 18 | AI (Friday) | Optional; not on critical path for Q bank |
| 19 | `M` signal source | **Per-card FSRS-R** (pure Python) replaces topic-level fallback; question schema extended with `cognitive_demand` + `choice_diagnosis` (additive) |
| 20 | Attempt data collection | **Local sidecar is source of truth**; full `feature_json` captured per attempt; **export script** (`tools/mcat_export_perf.py`) is the eval collection path; external telemetry backend **deferred** |
| 21 | Inference abstention balance | **Commit, don't over-abstain:** `infer_error_type` commits a diagnosis in the common miss — **`application` is the DEFAULT** for a content-presumed-held miss; honesty carried by **moderate confidence (0.55–0.60)**, not abstention. `unresolved` reserved for the truly-dark miss; CARS misses hard-guarded to `unresolved`. **Supersedes** the spec's "cold-start / fast-alone → unresolved" stance |
| 22 | Cross-device perf sync | **Export/import file bundle** (portable, versioned JSON), **append-only UNION merge** deduped by a stable per-attempt **`uuid`**; idempotent + order-independent → both devices converge. **Supersedes** the older "perf tables in the collection DB + stock Anki sync" assumption (§5/§19; AGENTS.md lock) |
| 23 | Correct-answer explanations | **Every performance question carries a required, non-empty static (NO-AI) `explanation`** — a source-grounded rationale for why the correct answer is correct, shown after answering. Doubles as the **AI-off fallback** and the **baseline** for the AI explainer. Authored in `build_question_bank.py`, enforced by `validate_data.py`, stored via an additive `explanation` column in `perf_questions` (2026-07-02) |

---

## 1. Product shape

**Decision:** Fork Anki; add measurement layer — not standalone app or add-on-only.

**Rationale:** Speedrun requires real Rust change + shared mobile engine. BrainLift targets recall–application gap in tools students already use.

**Rejected:** Add-on only (50% cap); greenfield app without shared engine.

---

## 2. Scope — not a full prep course

**Decision:** Demo on ~15–25 outline topics, ~200–500 cards, ~30–100 performance questions.

**Rationale:** Speedrun grades measurement honesty and architecture, not curriculum completeness. Coverage map uses **full outline as denominator** to show partial coverage.

---

## 3. Rust change — mastery query

**Decision:** Backend per-topic mastery/recall stats; fast at 50k cards.

**Rationale:** Powers eligibility, dashboard, Speedrun bench story. Lower risk than reschedule rewrite.

**Rejected:** Points-at-stake queue (v1 scope); topic-aware scheduling (undo/FSRS complexity).

---

## 4. Mobile — Android only

**Decision:** AnkiDroid fork; no iOS in v1.

**Rationale:** Solo schedule; one platform done well beats two broken builds.

**Phone scope:** Memory + sync + scores required; performance UI optional/slim.

---

## 5. Sync / performance storage

**Decision:** Stock Anki sync for memory data. Performance data (`perf_questions`, `perf_attempts`) lives in a **local sidecar SQLite file `mcat_perf.db`**, created next to `collection.anki2` in the profile folder. **No external/cloud database in v1.**

**Revised 2026-06-30** (was: "perf tables in same collection DB"). Reasons the sidecar wins:
- **Check Database** (Tools menu) can flag/drop tables it doesn't recognize in `collection.anki2`.
- A **full sync** replaces the entire `collection.anki2` from the server → tables embedded there would be **silently wiped**. The sidecar makes durability explicit instead of falsely "synced."
- Anki's Rust layer owns the collection schema; a sidecar gives us clean schema ownership and easy inspection/backup (`sqlite3 mcat_perf.db`).

**Why no external DB:** Anki is **local-first** — each user runs the app on their own device with their own local data; there is no central multi-tenant DB we operate. "Deploy" = ship the app. A cloud backend (Postgres/Firebase/etc.) is only needed for cloud-only features (web dashboard, cohort/leaderboard analytics, us ingesting user data) and is **deliberately deferred** — not part of the prototype and against the offline/no-runtime-network ethos.

**Open detail (cross-device perf sync, build step 7):** ~~stock Anki sync is schema-aware and won't propagate custom tables, so multi-device perf sync needs its own design — export/import, a self-hosted sync path, or (only if cloud features are later adopted) a backend.~~ **RESOLVED 2026-07-02 → see §22:** cross-device perf sync uses a portable **export/import bundle** with an append-only UNION merge (chosen over a self-hosted sync path or backend). Memory revlog conflict rule still TBD before Sunday (union + recompute FSRS).

---

## 6. Memory vs performance modes

**Decision:** Separate modes, separate sessions, topic-level gate.

**Gate:**
```
distinct_cards_reviewed >= 3 AND good_or_easy_count >= 5
```

**Rejected:** Performance immediately after flashcard reveal (collapses measurement).

**BrainLift alignment:** SPOV 2 — integrated **loop**, not blended **score**.

---

## 7. Three scores

**Decision:** Memory, performance, readiness always separate with ranges.

**Rejected:** Single “mastery %” or blended readiness.

**References:** Bransford transfer; AMEE declarative vs procedural; Speedrun honesty rule.

---

## 8. Readiness formula direction

**Decision:** Section performance → section band (118–132) → total with range; **no total if coverage &lt; 50%**.

**Open detail:** Exact mapping coefficients — tune on dev only, eval on held_out.

**Honesty:** AAMC FLs remain gold standard externally.

---

## 9. Error typing

**Decision (Wednesday):** Ship 4 types — `content_gap`, `passage_mapping`, `reasoning`, `misread`.

**Rationale:** BrainLift SPOV 3 differentiator; drives next action.

**Revised direction (v2 — 2026-07-01):** Self-report is a *weak* signal. The
research (Artino et al.: ~95–98% overestimate in medical-training contexts)
establishes that students overestimate their **performance** — poor calibration.
From that we *infer* (extrapolation, flagged for research in `LOOSE-ENDS.md`,
not a direct finding) that self-*categorizing* the reason for a miss (applied-
reasoning slip vs content gap) is likewise unreliable. So the diagnostic engine
should not be built on self-diagnosis. Instead:

- **3-bucket science taxonomy (renamed + collapsed):** `content_gap`,
  **`application`** ("Applied reasoning"), `misread`. The Wednesday `reasoning`
  type is **renamed to `application`**, and `passage_mapping` **folds under
  `application`** as a documented sub-mode (along with the earlier
  "application_gap" middle-state idea — all subsumed into the single coarse
  `application` bucket). `application` is intentionally coarse; split its
  sub-modes later only if data volume + a genuinely different remedy justify it.
- **Infer** the error type from the **role of the chosen distractor** (authored
  per option in `questions.json`), the **cross-system `M` signal** (FSRS-R of
  backing cards × `cognitive_demand`), and **timing** (fast alone is weak).
- **Honesty gate:** only label `application` when content presence is actually
  established (high `M` or a re-check probe PASS); otherwise it stays
  `content_gap` / `unresolved`. FSRS-R is a historical *signal* of
  retrievability, not proof content was available; the re-check probe is
  asymmetric (FAIL strong, PASS weak/priming-inflated).
- The student only **confirms** a concrete hypothesis in one tap
  (*"looks like applied reasoning — is that right?"*), never self-diagnoses from
  scratch. Confirmation is low-noise **and** yields labeled data.
- We **log agreement** (`confirmed` vs `override`) so we can report
  **inference-vs-confirmation agreement per type/topic with n** — and only let
  the dashboard lean on inferred types once the objective (Tier-2) signal clears
  a bar (else abstain / label "self-reported"), consistent with the readiness
  honesty rule.
- On no distractor role or conflicting signals → `unresolved`, fall back to the
  **3-button** science self-report rather than assert a shaky label.

**Residual risk of the rename:** the 3-bucket scheme *moves* rather than removes
the hard boundary — everything now hinges on the `content_gap`↔`application`
line, which rests on `M` + the re-check probe (the least-tested pieces). See
`LOOSE-ENDS.md`. The Wednesday 4-button enum stays frozen; the v2 rename/fold
migration happens when v2 is built.

**Abstention rebalance (2026-07-01) — see §21:** the inference engine was later
retuned to **commit** a diagnosis in the common miss (`application` as the
default for a content-presumed-held miss) rather than over-abstaining, carrying
honesty in **moderate confidence (0.55–0.60)** instead of `unresolved`. This
supersedes the spec's earlier cold-start/fast-alone "stay unresolved" guidance
and *elevates* the residual `content_gap`↔`application` boundary risk above.

**Rationale — why "probe + confirm the hypothesis" replaced pure 4-button
self-report (2026-07-02):** the Wednesday design was *4 self-report buttons after
a miss* (frozen enum above). v2 evolves this into a two-part flow — an objective
**re-check probe** (the recall oracle for whether the content was actually held)
followed by a one-tap **confirm** of a *specific, evidence-backed hypothesis*
about the error type, which the student can override. This sits deliberately
between two rejected extremes — **blind self-report** (unreliable; students
can't cleanly self-categorize *why* they missed) and a **silently-applied
auto-label** (presumptuous and un-correctable). Five reasons:

- **Targets only the unobservable axis.** The probe objectively settles whether
  the student held the content; the confirm step does **not** re-ask that. It
  asks only about the one axis no signal can observe — given the content was
  held, was the miss a careless *misread* vs. a genuine *reasoning/application*
  error — by presenting a specific, evidence-backed hypothesis (*"Looks like you
  knew the concept but misread — right?"*).
- **Confirming a scaffolded guess ≫ open self-diagnosis.** Reacting to a
  concrete, correct-most-of-the-time hypothesis is far more reliable than
  generating a label from scratch. It sidesteps the well-known "students can't
  reliably self-identify their errors" problem while still capturing the private
  information only the student has.
- **It corrects our inference so the next action routes correctly.** The
  dashboard's recommendation forks on error type (re-study content vs.
  slow-down-and-read vs. drill application). A silently-wrong auto-label sends
  the student to the wrong fix; the one-tap confirm prevents mis-routing.
- **Honesty + trust.** Showing our guess and letting the student override it is
  more honest than declaring *"you were careless,"* which is presumptuous and
  erodes trust when we're wrong (ties to the Speedrun honesty rule).
- **It is itself metacognitive training.** Naming/confirming your own error type
  is a learning act — the self-monitoring skill the BrainLift argues current
  tools never build.

**Framing:** *The probe measures what's objective; the confirm captures what's
private and un-inferable — presented as a correctable hypothesis, not a verdict.*

Full mechanism, schema, and validation metric: [`ERROR-DIAGNOSIS-SPEC.md`](ERROR-DIAGNOSIS-SPEC.md).

---

## 10. Performance question bank

**Decision:** Curated from OpenStax (primary) with source metadata; local bank at runtime.

**Evolution:** Initially considered public-only import; rejected heavy AI multi-agent pipeline as too complex for solo.

**Rejected:** Live LLM during performance sessions; scraping unlicensed QBanks.

**Eval:** `dev` vs `held_out` split frozen before tuning; friend answers held_out.

---

## 11. Study feature

**Decision:** Interleaved vs blocked **performance** sessions; 3-build test vs plain Anki.

**Hypothesis:** Interleaving improves mixed-topic question accuracy at equal time.

**Reference:** Kornell & Bjork 2008 (BrainLift 3.3).

---

## 12. AI

**Decision:** Optional Friday feature; performance bank independent of live AI.

**Minimal scope if shipped:** Flashcard generation from one OpenStax section + gold set eval.

**Wednesday:** zero AI.

---

## 13. Evaluation

**Decision:**

| Data | Source | Split |
|------|--------|-------|
| Memory | Builder reviews | Time 70/30 |
| Performance | Friend + builder | Frozen held_out IDs |
| Paraphrase | 30 cards × 2 topic Qs | Separate sessions |

Document n=1–2 limitations honestly.

---

## 14. Give-up thresholds (draft — finalize before Sunday)

| Rule | Threshold |
|------|-----------|
| Total readiness | 200 reviews, 30 perf attempts, 50% coverage, 5/section + CARS |
| Memory abstain | &lt; 200 reviews |
| Performance abstain | &lt; 30 attempts |

---

## 15. Deferred (hold for now)

- Which OpenStax book first  
- Exact dev/held_out ID assignment strategy  
- CARS passage count and source  
- Readiness mapping coefficients  
- Installer OS targets (Win-only vs multi)  
- Friday AI exact feature scope  

---

## 17. Per-card FSRS-R for `M`; question-schema extension (2026-07-01)

**Decision (a) — per-card FSRS-R for the content-held score `M`:** `M` will use
the **current per-card FSRS-R of the specific `supports_question` backing cards**,
replacing the coarse **topic-level** `avg_retrievability` fallback. Investigation
(2026-07-01) confirmed this is **feasible in pure Python** in Anki 26.05 (fsrs
5.2.0) — R is computed from each card's FSRS memory state (stability + days
elapsed, `decay` default 0.5) with **no Rust/proto rebuild** and no risk to the
frozen build.

**Rationale:** topic-level averaging hides per-card gaps and destroys
localization (which prerequisite failed), which silently mislabels real
`content_gap` as `application` — the exact failure mode the 3-bucket rename
depends on getting right (§9). Per-card R restores the spec's ideal signal.

**Decision (b) — question-schema extension:** the question schema is extended
with **`cognitive_demand`** (`recall` | `application` | `synthesis`, question
level) and **`choice_diagnosis[]`** (1:1 with `choices`, content axis only).
Both are **additive / non-breaking** (optional, only emitted when present;
existing 110 items stay byte-compatible), so the validator gains optional checks
only when the keys exist.

**Rationale:** these fields are required for the synthesis/application items to
exercise the `application`↔`content_gap` split; they are the authoring surface
the inference engine reads (see §9).

**References:** [`ERROR-DIAGNOSIS-SPEC.md`](ERROR-DIAGNOSIS-SPEC.md),
[`LOOSE-ENDS.md`](LOOSE-ENDS.md) (coarse-`M` item, now RESOLVED),
[`SYNTHESIS-QUESTIONS-DRAFT.md`](SYNTHESIS-QUESTIONS-DRAFT.md).

---

## 19. Performance attempt data collection + export (2026-07-01)

**Decision (a) — the local sidecar is the source of truth for attempt data.**
Every performance attempt (correct *and* incorrect) records the full observable
signal vector as a `feature_json` blob on `perf_attempts` (added via the additive
ALTER-if-missing migration), plus the objective label columns (`chosen_index`,
`mastery_snapshot`, `inferred_error_type`, `inferred_confidence`, `error_source`).
`feature_json` is stored with `ensure_ascii=False` and stamped with
`FEATURE_SCHEMA_VERSION` (`mcat_perf_features_v1`).

**feature_json schema (v1)** — captured at classify time in
`PerformanceSession._feature_vector`:
`schema`, `question_id`, `topic_id`, `section`, `split`, `chosen_index`,
`correct`, `time_seconds`, `mastery_snapshot`, `cognitive_demand`, `is_trap`,
`trap_type`, `has_content_tag`, `maps_to`, `misconception`,
`inferred_error_type`, `inferred_confidence`, `error_source`,
`self_report_error_type`, `interleaved`.

**Decision (b) — export is the collection path for eval.** A read-only export
(`tools/mcat_export_perf.py` → `anki.mcat_perf.export_attempts`, also wired as
Tools → **"MCAT: Export performance data…"**) dumps `perf_attempts` joined with
`perf_questions` to CSV and/or JSON (`--format csv|json|both`). No AI, no network.

**Decision (c) — external telemetry backend deferred.** No cloud/telemetry sink
in v1 (consistent with §5's local-first ethos). Eval happens by exporting the
sidecar and analyzing offline.

**Tension with the AGENTS.md lock (flagged honestly):** `AGENTS.md` still lists
"perf tables in the collection DB + stock Anki sync" as a locked decision. The
implementation instead uses a **non-syncing sidecar** (`collection.mcat_perf.db`),
revised in §5 for durability (a full sync would silently wipe embedded custom
tables). The consequence for *collection*: **stock Anki sync only reaches
AnkiWeb, not a queryable DB we can pull attempt data from** — even the original
"tables in the collection DB" plan would not have produced a queryable analytics
store, only AnkiWeb-synced rows. So attempt-data collection for eval relies on
the **export path**, not sync. Cross-device perf sync remains the open item in §5
(build step 7).

**Deferred capture (NOT faked):** `first_choice_index`, `answer_changes`, and the
re-check probe outcomes (`recheck_card_id` / `recheck_correct` / `recheck_timing`)
are left NULL — they need select-then-confirm churn logging + a re-check probe the
dialog does not provide yet. We capture only what is genuinely observed. See
`LOOSE-ENDS.md` ("Deferred v2 UX").

**References:** `pylib/anki/mcat_perf.py`, `tools/mcat_export_perf.py`,
`qt/aqt/mcat/__init__.py`, `pylib/tests/test_mcat_perf.py`.

---

## 21. Inference abstention rebalance — commit, don't over-abstain (2026-07-01)

**Decision:** retune `infer_error_type` (`pylib/anki/mcat_perf.py`) to **commit a
diagnosis in the common miss** instead of falling through to `unresolved` /
self-report, and make **`application` the DEFAULT** diagnosis for a
content-presumed-held miss. **Honesty is now carried by moderate CONFIDENCE
(0.55–0.60), not by abstaining.**

**Problem it fixes:** the previous engine over-abstained. Cold-start / gate-imputed
`M` lands in the ambiguous `[LOW_M, HIGH_M)` band, ~78% of science distractors are
untagged, and ~67% of items are recall-demand — so the old "ambiguous-`M`" and
"fast-alone" fall-throughs sent the *majority* of misses to `unresolved`,
defeating the product's core "infer, don't ask" goal (SPOV-3).

**The rebalanced decision order (first match wins):**
1. Chosen distractor carries a `content_gap` tag → `content_gap` (M-independent;
   0.75 if low `M` corroborates, else 0.65).
2. Low `M` → `content_gap` (≥0.6).
3. Predictable-trap landing → `misread` (0.75 fast+high-`M` / 0.6 fast-or-high-`M`
   / 0.55 otherwise).
4. **Content presumed held → `application` (the DEFAULT):** high `M` + applied
   demand ≥0.7 (strongest, cross-system divergence); high `M` any demand 0.6;
   applied demand with ambiguous/unknown/mid `M` 0.6; mid `M` 0.55.
5. **Truly-dark miss only** (`M` unavailable **and** recall/unknown demand
   **and** no tag **and** no trap, *including* fast-but-no-trap) → `unresolved` →
   self-report.

Plus a **CARS guard:** `PerformanceSession.answer` hard-forces every CARS miss to
`unresolved` (0.0) before the science engine runs, so the science default can
never mislabel a CARS miss (CARS is a separate skill-archetype + pacing track).

**Rationale (why `application` as default is honest):** the performance gate
(≥3 seen, ≥5 Good/Easy) supplies a content baseline *by construction*, so gated
misses lean `application` by design (the "gate-defines-content confound" already
in the spec). Committing those to `application` at *moderate* confidence — rather
than abstaining — is more useful and no less honest, because the confidence
transparently reflects the weak signal, and a real content gap is still caught
first by branches 1–2 (authored tag or low `M`).

**Deliberate divergence from the prior spec (now reconciled):** this **supersedes**
`ERROR-DIAGNOSIS-SPEC.md`'s "Cold-start honesty" (ambiguous-`M` → `unresolved`)
and "fast alone is weak → `unresolved`" guidance. Both cases now commit
`application` at moderate confidence. The spec was updated (2026-07-01) to match:
the "In one paragraph", "Inference rule", "Cold-start honesty", process-axis
disambiguation table, confidence table, and residual-risk sections were rewritten;
the honest content_gap↔application boundary caveat is retained and, because
`application` is now the default, explicitly **elevated** (more misses land in
`application`, so the boundary carries more weight — audited via student overrides).

**Residual risk (tracked in `LOOSE-ENDS.md`):** making `application` the default
raises exposure to the `content_gap`↔`application` mislabel if `M` is
mis-estimated or tag coverage is thin. Mitigations: branches 1–2 pre-empt with
`content_gap`; moderate confidence flags probe candidates; persistent
`application`→`content_gap` overrides are the audit signal.

**References:** `pylib/anki/mcat_perf.py` (`infer_error_type`,
`PerformanceSession.answer` CARS guard),
[`ERROR-DIAGNOSIS-SPEC.md`](ERROR-DIAGNOSIS-SPEC.md), [`LOOSE-ENDS.md`](LOOSE-ENDS.md).

---

## 22. Cross-device performance sync — export/import bundle (2026-07-02)

**Decision:** cross-device sync of performance data uses a **portable
export/import file bundle**, union-merged on import — **NOT** moving the perf
tables into `collection.anki2` to ride stock Anki sync.

**Supersedes** the earlier "perf tables in the same collection DB + stock Anki
sync" assumption (the original AGENTS.md lock, and the still-open item flagged in
§5/§19). That approach does not actually work for our data:
- Stock Anki sync is **schema-aware** — it syncs the collection's known tables,
  not arbitrary custom tables, so `perf_questions` / `perf_attempts` embedded in
  `collection.anki2` would **not propagate** (and a full sync would silently
  **wipe** them — the §5 durability reason we moved to a sidecar in the first
  place).

**Why the bundle wins (and is conflict-light):** `perf_attempts` is
**append-only truth** — each device only ever adds attempts, never edits or
deletes another device's rows. So a portable bundle that gets **UNION-MERGED**
on import needs no conflict resolution beyond de-duplication.

**Bundle format** (`anki.mcat_perf`, `tools/mcat_export_bundle.py`): a versioned
JSON envelope — `format: "mcat_perf_bundle"`, `format_version: 1`, `exported_at`,
plus `questions` (the full bank, verbatim) and `attempts` (every
`perf_attempts` column, including the raw `feature_json` string preserved
byte-for-byte). Import intersects columns, so devices with slightly different
additive-migration state still interoperate.

**Stable attempt key (`uuid`):** the `perf_attempts` autoincrement `id` is
**device-local and NOT portable**, so an additive migration (same
ALTER-if-missing pattern as `choice_diagnosis`) adds a **`uuid`** column,
backfilled once for legacy rows and **UNIQUE-indexed**. `log_attempt` stamps a
fresh `uuid4` per attempt. The merge dedups on `uuid` (with a deterministic
content-hash fallback only for pre-`uuid` legacy bundles).

**Merge semantics:** questions inserted by `id` when missing (the bank is
deterministic from the curated OpenStax source, so existing local rows are never
overwritten by a device-local copy); attempts inserted when their `uuid` is
absent, dropping the source `id` (a new local one is assigned). The merge is
**idempotent** (re-importing the same bundle adds nothing) and
**order-independent** (import order cannot change the result) → after each device
imports the other's bundle, **both converge to the exact union of attempts**
(verified in `pylib/tests/test_mcat_perf.py`).

**Local / no-AI / no-network:** the bundle is a plain file the user copies
between devices (or via any file transport). No cloud DB, no telemetry, no
runtime AI — consistent with §5's local-first ethos and the product's
no-AI-at-runtime lock.

**UI + CLI:** Tools → **"MCAT: Export sync bundle…"** / **"MCAT: Import sync
bundle…"** (`qt/aqt/mcat/__init__.py`); headless
`tools/mcat_export_bundle.py` + `tools/mcat_import_perf.py` for scripted /
recorded sync.

**References:** `pylib/anki/mcat_perf.py` (`export_bundle`, `import_bundle`,
`merge_bundle`, `_backfill_attempt_uuids`), `qt/aqt/mcat/__init__.py`,
`tools/mcat_export_bundle.py`, `tools/mcat_import_perf.py`,
`pylib/tests/test_mcat_perf.py`.

---

## 23. Correct-answer explanations (static, NO-AI)

**2026-07-02 —** Every performance question now carries a required, non-empty
**`explanation`**: a concise (1–4 sentence) written rationale for **why the
correct answer is correct**, grounded in that item's named source (OpenStax for
science; the original CC0 passage for CARS). It is shown to the student **after**
they answer, alongside the existing error-diagnosis UI.

**No AI at runtime:** the explanation is fully static content authored ahead of
time in `scripts/build_question_bank.py` (keyed by question id in the
`EXPLANATIONS` dict) and emitted into `data/questions.json`. It therefore also
serves as the app's **AI-off fallback** rationale and the **baseline** the AI
"explain why you were wrong" feature will read from and fall back to (that
feature only READs the field; the field name `explanation` is kept stable for
it). No per-distractor breakdown is required here — that remains the optional
`choice_diagnosis` content axis.

**Enforcement + storage:** `scripts/validate_data.py` fails validation if any
question's `explanation` is missing or blank. Storage adds an additive
`explanation TEXT` column to `perf_questions` (same ALTER-if-missing migration
pattern as `choice_diagnosis`), round-tripped through
`upsert_questions`/`_row_to_question` and the sync bundle import.

**References:** `scripts/build_question_bank.py` (`EXPLANATIONS`,
`_attach_explanation`), `scripts/validate_data.py`,
`data/questions.json`, `pylib/anki/mcat_perf.py`,
`qt/aqt/mcat/performance_dialog.py`, `pylib/tests/test_mcat_perf.py`.

---

## 24. AI post-answer explainer (per-choice, offline-reproducible)

**2026-07-02 —** Friday graded "AI" deliverable. When a student **misses** a
performance question, an AI explainer says **why the SPECIFIC distractor they
chose is wrong** and what the correct solution is, grounded in that item's named
source. The justification is **differentiation**: choice B produces materially
different feedback than choice C on the same question — something the static
`explanation` (entry 23) and a keyword/vector baseline structurally cannot do.

**Design (maps to the rubric):**
- **Attribution:** every output cites `source_name` (+ `source_url`/
  `source_location`). Ungrounded outputs are blocked (would score zero).
- **Per-choice differentiation:** driven by `choice_diagnosis` ground truth —
  `content_gap` names+corrects the misconception (remediation = the specific
  backing memory concept); `trap:<enum>` names the execution error
  (negation/unit/inverse/scaling/transpose/partial) + how to avoid it
  (remediation = interleaved practice); `null` = honest near-miss (no
  over-diagnosis); CARS = passage-mapping.
- **Provider seam:** `LLMProvider` is the documented plug-in point for a real
  model; because live calls aren't assumed here, the default is a
  **deterministic offline generator** so eval/baseline/AI-off are fully runnable
  with **AI OFF and no network**. All reported numbers use the offline provider
  and are labelled as such.

**Pre-registered cutoff** (declared in code before results): accuracy ≥ 0.90,
wrong-answer-rate ≤ 0.05, grounding = 1.00, choice-specificity ≥ 0.80. A per-item
safety gate blocks any explanation that is ungrounded or names the wrong choice
and **replaces it with the static explanation**; if the aggregate fails the
cutoff the whole AI path is disabled (fall back to static). Gate self-test PASS.

**Results (held_out, 75 Q / 225 distractor paths, offline):** AI acc=1.000,
wrong=0.000, grounded=1.000, **choice-specificity=1.000**; static baseline
choice-specificity=0.000; TF-IDF baseline choice-specificity=0.009 (and
wrong=0.160). **Differentiation gap = +0.991** — the headline "AI beats
baseline". Goldset 9/9 (dev). Leakage check: OK (eval = project `held_out`;
goldset is dev-only, no id/stem leak).

**AI-off:** the app serves the static `explanation` (entry 23) and still scores.

**Files:** `scripts/ai_explain.py`, `scripts/ai_eval_explanations.py`,
`data/ai-explainer-goldset.json`, `docs/AI-FEATURE.md`. READs (does not modify)
`data/questions.json` `explanation`/`choice_diagnosis`. Reuses
`scripts/eval_leakage.py`. No frozen-build rebuild.

---

## 25. Calibration export (probe-aware)

**2026-07-02 —** The error-diagnosis engine now records an OBJECTIVE label: an
immediate content re-check probe fires after a miss and stores `recheck_correct`
(probe PASS/FAIL) next to the heuristic `inferred_error_type` /
`inferred_confidence` / `error_source` and the full `feature_json` vector
(entry 5 sidecar, `perf_attempts`). This decision makes it **turnkey** to answer
"how often does the heuristic diagnosis agree with the objective probe?" for
honest accuracy reporting (Sunday proof) and to calibrate the hand-set weights
(`w_mis`, confidence bands, `HIGH_M` / `LOW_M`) against that label. **Not ML** —
a flat labeled view + a single agreement metric over hand-tuned thresholds.

**Design:**
- A `--calibration` flag on `tools/mcat_export_perf.py` (reusing the existing
  read-only export path) filters to **probe-labeled rows only**
  (`recheck_correct IS NOT NULL`) and emits one **flat, analysis-ready row per
  attempt** (CSV + JSON, `anki.mcat_perf.CALIBRATION_COLUMNS`): attempt `uuid`,
  `question_id`, `topic_id`, `cognitive_demand`, `chosen_index`, `correct`,
  `time_seconds`, `mastery_snapshot`, derived `high_m` / `low_m` threshold
  flags, `is_trap` / `trap_type` / `has_content_tag` / `maps_to` (flattened from
  `feature_json`, tolerant of legacy/missing keys), `recheck_card_id`,
  **`recheck_correct` (the objective label)**, the recomputed **pre-probe**
  `heuristic_error_type` / `heuristic_confidence`, the stored (probe-informed)
  `inferred_error_type` / `inferred_confidence`, and `error_source`.
- **Agreement metric (the headline honest number):** a decision-relevant 2×2
  tally — probe **FAIL** should map to engine `content_gap`; probe **PASS** to
  engine NOT-`content_gap` (application/misread). Agreement % =
  (FAIL&content_gap + PASS&not-content_gap) / probe-labeled rows. It is scored
  against the **pre-probe heuristic** diagnosis (recomputed with
  `recheck_correct=None`), NOT the stored `inferred_error_type` — the latter is
  probe-informed (the probe is evaluated first in `infer_error_type`), so
  comparing it to the probe would be tautological. Empty input → rate `None`
  (honest abstain, no fake 0/1).

**Files:** `tools/mcat_export_perf.py` (`--calibration`), `pylib/anki/mcat_perf.py`
(`CALIBRATION_COLUMNS`, `build_calibration_rows`, `calibration_agreement`,
`write_calibration`), `pylib/tests/test_mcat_perf.py` (synthetic probe-labeled
rows → flat export + agreement tally + legacy-tolerant flatten). Read-only on
the sidecar; no AI, no network; no frozen-build rebuild.

---

## 26. Application next-action → wired remediation pool (isolated)

**2026-07-02 —** The `application` ("Applied reasoning") diagnosis now routes to
a **real, launchable practice set** instead of a generic message. The
application-practice pool authored earlier (`data/application-practice.json` — 45
science integration items, 3 per topic) is loaded into an **isolated** sidecar
store and served after a resolved `application` miss.

**Selection** (`select_application_practice`, `pylib/anki/mcat_perf.py`):
deterministic, AI-off — filter to `topic_id == T` + `pool == application_practice`
→ exclude the just-missed `concept` (same-concept fallback if that empties) →
exclude already-seen pool ids → rank for concept variety → take **N = 2**
(`N_APPLICATION_PRACTICE`). No eligible items → the generic *"practice more
applied items in \[topic]"* fallback (degradation contract kept).

**Isolation from scored state (the load-bearing guarantee).** Remediation items
live in their own table `remediation_items` with a DB `CHECK (split =
'remediation')`; practice attempts log to a separate `remediation_attempts`
channel via `PerfStore.log_remediation_attempt`. Neither table is read by
`accuracy()`, `eligible_questions()`, or the sync bundle
(`_read_bundle_from_conn`), so a remediation item can **never** enter the
Performance/Readiness scores or a held_out/dev scored session. Scope is the
`application` channel only — `content_gap` and `misread` routing are unchanged.

**UI.** `performance_dialog.py` surfaces the next-action (label + "Practice N
similar items →" button) on an `application` resolution; the button opens a
visibly-distinct, unscored `RemediationDialog`. Load the pool via Tools →
"MCAT: Load application-practice pool…".

**Files:** `pylib/anki/mcat_perf.py` (store + selection),
`qt/aqt/mcat/performance_dialog.py`, `qt/aqt/mcat/remediation_dialog.py`,
`qt/aqt/mcat/__init__.py`, `pylib/tests/test_mcat_perf.py` (13 new tests). Pure
Python + pytest; no frozen-build rebuild.

---

## 27. §7d paraphrase-gap instrument (memory ⟂ performance proof)

**2026-07-02 —** Added a dedicated instrument that measures — and reports
honestly — the **gap between flashcard recall and accuracy on reworded
questions of the same idea**, so the performance score is demonstrably
**transfer**, not parroted memory. For each anchor concept it pins **two
exam-style questions in genuinely different wording** (never a numeric clone)
and compares card recall vs mean accuracy across the pair.

**Scope (locked eval trio):** `cp_acids_bases`, `bb_enzymes`, `cp_kinetics` —
28 anchor concepts. Within-topic anchors only (a concept, its card, and both
questions share one topic).

**Split discipline:** the **second** stem of every pair is always a freshly
authored `held_out` probe (a volunteer cannot have seen it in a dev session);
`validate_data.py` fails if any second stem is not `held_out`. **30 new curated
MCQs authored** (ids `q_ho_061`–`q_ho_090`), all `held_out`, all OpenStax-grounded
with full schema parity (stem, 4 choices, correct index, `cognitive_demand`,
3-axis `choice_diagnosis`, non-empty static `explanation`, source metadata). Bank
is now **170 questions (65 dev / 105 held_out)**.

**Gap metric:** `paraphrase_gap = card_recall_rate − question_accuracy`, meaned
per topic and overall. gap ≈ 0 at high recall → warn performance may be echoing
memory; large positive gap → performance is measuring transfer. Concepts missing
data are listed and excluded (no fake zero-fill).

**No AI / no network:** `scripts/eval_paraphrase.py` scores a real-data path
(`--recall`/`--attempts`) or a deterministic md5-seeded synthetic demo (labelled
as such). The card→question `supports_question` edge in `build_flashcards.py` was
**deliberately not touched** (parallel-write avoidance); the manifest's
`card_ref`/`card_front` is the authoritative backing-card link for the instrument
and reconciles into the deck CSV later — so the 30 new probes intentionally show
no backing card in `QUESTION-CARD-MAP.md` yet.

**Files:** `data/paraphrase-test.json` (28-row manifest), `scripts/eval_paraphrase.py`,
`Makefile` (`eval-performance`), `scripts/build_question_bank.py`,
`scripts/validate_data.py`, `scripts/eval_leakage.py`, `docs/PARAPHRASE-TEST.md`.

---

## 28. Component-card granularity (component cards, not answer cards)

**2026-07-02 —** Advanced the "one atomic backing card per prerequisite
sub-concept" principle (not merely ≥1 backing card per question). Finer,
correctly-linked component cards sharpen per-card `M` (FSRS-R) so the re-check
probe (which inverts `supports_question`) can localize the **specific** failed
prerequisite.

**What was done:** **+24 atomic Cloze cards** across the eval trio
(`bb_enzymes` 18→29, `cp_acids_bases` 15→23, `cp_kinetics` 9→14; trio 42→66),
each a within-topic link. **Guardrail — no answer-encoding:** every card teaches
a foundational prerequisite fact, never the item's own integrated answer; three
drafts that sat too close to an answer were reframed (`q_dev_005`, `q_syn_004`)
or dropped (`q_dev_016`).

**Coverage:** all 127 science questions still have ≥1 backing card. Topics
**beyond the trio** remain guaranteed only ≥1-per-question (not
one-per-prerequisite) and are tracked as a prioritized next-pass list.

**Files:** `scripts/build_flashcards.py`, `data/flashcards-dev.csv`,
`data/flashcards-dev-cloze.csv`, regenerated `docs/QUESTION-CARD-MAP.md`; full
per-card log in `docs/COMPONENT-CARD-GRANULARITY.md`.

---

## 29. Live LLM provider wired at the AI-explainer seam (env-driven, gated)

**2026-07-02 —** Plugged a **real, provider-agnostic LLM** into the documented
`LLMProvider` seam (entry 24) so the held_out eval can produce **honest,
non-by-construction** numbers, without lowering the offline floor.

**What changed:**
- `scripts/ai_explain.py`: `LLMProvider` now sends the prompt contract (name the
  correct letter, explain why the *chosen* distractor is wrong using the passed
  `choice_diagnosis`, give the correct solution, stay tied to `source_name`) and
  `parse`s **structured JSON** back into an `Explanation`. A provider client is
  built from env by `build_live_call_model_from_env`: `MCAT_LLM_PROVIDER`
  (`openai`|`anthropic`), `MCAT_LLM_MODEL`, key from `MCAT_LLM_API_KEY` or the
  provider-standard var. **SDKs are lazy-imported**; **AI-off (unset provider)
  serves the static explanation** and the whole app still works.
- The canonical `safety_block` gate moved into `ai_explain.py` and now guards a
  new `serve_explanation` path: live → gate → static fallback on block/error, so
  a live model can never misinform (ungrounded / wrong-choice → static).
- `scripts/ai_eval_explanations.py`: `--provider offline|live`. Offline stays the
  default (reproducible, no network). Live scores the **real** provider through
  the same gate/cutoff; provider errors count as blocked→static.
- `scripts/test_ai_explain_live.py`: 16 mocked-LLM tests (no network) covering
  dispatch, parse, gate blocks, AI-off fallback, and eval-against-live — green.
- `requirements.txt`: optional `openai`/`anthropic` (lazy at import).

**Secrets:** key read **only** from `os.environ`, never hardcoded/printed/logged;
`.env`/`.env.*` gitignored (`!.env.example`). **Nothing committed.**

**Status:** implementation complete + offline eval unchanged (105 held_out Q /
315 paths, AI choice-spec 1.000 vs static 0.000 / TF-IDF 0.010). **No live run
yet** — no key in the build env; live numbers deliberately left blank in
`AI-FEATURE.md` §10 rather than fabricated. Run `make eval-ai-live` (or
`py -3.12 scripts/ai_eval_explanations.py --provider live`) with a key to fill.

**Files:** `scripts/ai_explain.py`, `scripts/ai_eval_explanations.py`,
`scripts/test_ai_explain_live.py`, `requirements.txt`, `docs/AI-FEATURE.md`,
`Makefile` (`eval-ai`, `eval-ai-live`, `test`).

---

## 30. "Not sure" (IDK) anti-guessing option — demo

**2026-07-03 —** Added a minimal **"Not sure"** opt-out to the performance
answering UI (a secondary button beneath the choices, distinct from the answer
choices). It is **not** a choice submission and **not scored right or wrong**: it
reveals the correct answer + explanation (still a learning moment; the AI "Ask
more" panel stays available), then proceeds to Next like a normal post-answer
state.

**Behavior:**
- **Non-CARS →** the IDK maps **directly** to error type `content_gap` (no recall
  probe, no error-type confirm step) and routes to the same content_gap
  next-action / remediation a diagnosed content-gap miss would.
- **CARS →** logs as `unresolved` (CARS already skips error typing).

**Scoring / honesty (the whole point):**
- **Excluded from accuracy** — the row is flagged `idk = 1` and is neither a
  correct nor an attempt in the Performance accuracy numerator/denominator (raw
  **and** the Bayesian shrinkage headline, which reads `accuracy()`).
- **Not a mastery/unlock "correct"**, and **not** counted as a scored
  performance attempt.
- Because Readiness's attempt gate reads `accuracy()`, IDK stays out of that path
  naturally.
- **Tracked** via a separate `idk_count` (per item/topic) so we can honestly show
  how often the student opted out — no confidence weighting, no lucky-guess
  detection (deferred; see LOOSE-ENDS).

**Rationale:** a guessed-correct answer gives no mastery signal and **inflates**
Performance; abstaining removes that noise honestly — the item-level mirror of
the system-level readiness abstention rule. Kept deliberately minimal for the
demo ("IDK = content_gap immediately").

**Coordination (scores worker) — DONE (verified 2026-07-05):** full Readiness
isolation additionally needs an `idk = 0` filter on the **direct** `perf_attempts`
reads in `mcat_scores.py` (`_section_attempt_counts`, `_provisional_range`, and
the coverage attempt branch in `coverage_summary`); those now all carry
`AND a.idk = 0` (the `accuracy()`-derived paths already excluded IDK). See the
**Refinement** note below and its regression test
`test_idk_rows_are_invisible_to_readiness` — leave those filters sealed.

**Files:** `anki-MCAT/pylib/anki/mcat_perf.py` (idk column + migration,
`log_attempt(idk=…)`, `accuracy()` exclusion, `idk_count()`,
`PerformanceSession.not_sure()`), `anki-MCAT/qt/aqt/mcat/performance_dialog.py`
("Not sure" button + `_on_not_sure` + neutral reveal), and
`anki-MCAT/pylib/tests/test_mcat_perf.py` (3 tests).

**Refinement (2026-07-03, final agreed framing):** locking the intended shape of
the three effects so they don't drift:
- **Error typing:** IDK is still tagged `content_gap` (non-CARS route unchanged).
- **Accuracy:** untouched — IDK stays out of the accuracy numerator **and**
  denominator (no change to the exclusion).
- **Readiness harm is PASSIVE, not active.** IDK earns **no coverage credit**: a
  topic answered *only* with IDK does not count as "covered", which keeps
  Readiness low / abstaining. This is enforced by the `AND a.idk = 0` filters on
  the coverage / section-count / provisional-range queries in
  `pylib/anki/mcat_scores.py` (regression test
  `test_idk_rows_are_invisible_to_readiness`). There is **no** active readiness
  penalty, and "no coverage credit" is the same intended behavior as "invisible
  to readiness scoring" — leave those filters sealed and the test green.
- **User-facing copy:** softened to say we're **flagging this topic as a
  knowledge gap to review** and that it doesn't count for or against accuracy. It
  deliberately does **not** claim "this is not a reasoning error" or assert any
  definitive diagnosis, because "I don't know" is genuinely ambiguous — it can be
  a content gap OR an application/reasoning gap (they know the facts but can't
  apply them). Overclaiming a content-gap diagnosis would be dishonest.
- **Deferred (Sunday refinement):** optionally run the content re-check probe on
  an IDK to *objectively* confirm content-gap vs application instead of assuming
  — fail the probe → genuine `content_gap`; pass the probe → they had the
  content, so it's an application/reasoning gap. Tracked in LOOSE-ENDS.

---

## 31. Friend-tester ENGAGEMENT thresholds — NOT the graded methodology (2026-07-04)

**Label:** *friend-tester engagement thresholds — NOT used for graded readiness
claims.* These are a **separate, pre-registered on-device profile** that lowers
the score abstain gates so a casual friend who studies for a **single ~15–20 min
sitting** (≈10–20 cards reviewed, ≈8–12 questions across 1–2 topics) still sees
all three **PROVISIONAL** scores populate — so the build "feels alive" for
testers. The **graded** readiness claims continue to use the strict full-course
gates in §14 (200 reviews, 30 attempts, 21-day maturity). Both profiles ship in
`anki-MCAT/pylib/anki/mcat_scores.py` (`SCORE_PROFILE`); this build ships
`"tester"`. See [`EVAL-THRESHOLDS.md`](EVAL-THRESHOLDS.md) for the full table +
rationale.

**Pre-registered cutoffs (tester profile):**

| Gate | Strict (§14, graded) | Tester (this build) |
|------|----------------------|---------------------|
| Memory — graded reviews | ≥ 200 | **≥ 10** |
| Memory — card maturity | ≥ 1 card at interval ≥ 21d | **not required** |
| Memory — started-card floor | (governed by maturity) | **≥ 10 cards** |
| Performance — attempts | ≥ 30 | **≥ 8** |
| Readiness — coverage | ≥ 50% | ≥ 50% (unchanged) |
| Readiness — science section attempts | ≥ 5 / section | **≥ 3 / section** |
| Readiness — CARS attempts | ≥ 5 | **≥ 3** |

**Memory basis change (tester only):** 21-day maturity is unreachable in a
weekend, so the tester Memory headline is **EARLY RECALL STRENGTH = FSRS
retrievability only** (score = R × 100, maturity factor forced to 1.0) — "how
well you'd recall right now what you've reviewed", explicitly **not** long-term
durability. Gated on the ≥10 reviewed-card floor so the average is not from 1–2
cards. Strict Memory (R × maturity, needs a mature card) is unchanged.

**Honesty safeguards (what makes the low gates defensible):**
- **A truly empty profile (0 data) STILL abstains** on all three — the gates
  never fabricate a number (regression: `test_empty_profile_still_abstains_*`).
- **Confidence intervals stay VERY WIDE at small n.** Memory uses a boundary-safe
  **Wilson** interval (the plain normal SE collapses to ±0 at R≈1.0 right after a
  review — false precision — so it was replaced). Performance keeps its Wilson/
  Bayesian credible band. Readiness **widens its range at small n** (base ±6, up
  to ~±24 at the tester attempt count) via `_readiness_half_width`.
  Measured short-session example: Memory 100 → CI **82–100**; Accuracy 57 → CI
  **32–82**; Readiness range width **34** points.
- Every computed score carries a **`provisional`** flag (UI shows a `provisional`
  badge, not `measured`), coverage %, a missing-data/next-action note, and the
  three scores are **never blended**.
- The earlier accuracy-card honesty fix is preserved: a number **XOR** "not
  enough data", never both.

**Not graded:** nothing here changes the graded evaluation in §13/§14 — graded
claims must use the strict profile. This profile exists solely for tester
engagement and is labeled as such in-app (provisional) and in code/docs.

**Files:** `anki-MCAT/pylib/anki/mcat_scores.py` (profile block + Memory/Readiness
logic + Wilson Memory band), `anki-MCAT/qt/aqt/deckbrowser.py` (provisional badge
+ profile-aware copy), `anki-MCAT/tools/mcat_seed_tester.py` (enable FSRS + v3 so
retrievability exists), tests in `pylib/tests/test_mcat_scores.py` +
`qt/tests/test_mcat_dashboard_render.py`, and [`EVAL-THRESHOLDS.md`](EVAL-THRESHOLDS.md).

---

## 32. Hosted AI proxy — keyless live AI for the graded build

**2026-07-04 —** Added a **server-side proxy** path so the in-app AI assistant
can run on **graders' own machines with NO API key entered by them**. This is a
**user-directed decision for the GRADED build only**: it intentionally enables
live AI at runtime, overriding the earlier "AI off at runtime / no key bundled"
default (DECISIONS §29, tester build). The friend build is unchanged.

**Why.** Graders won't have (and shouldn't need) an LLM key. A proxy that holds
the key server-side lets the app do live, per-choice explanations + follow-up
Q&A without shipping or asking for any key. Scores/questions/flashcards remain
**fully local** — only the AI call touches the network.

**Architecture (config-driven).**
- **Proxy** (`MCAT/proxy/`): a thin authenticated relay to OpenAI chat
  completions. It receives the SAME `system`+`user` messages the app already
  builds (`ai_explain.LLM_SYSTEM_PROMPT` / `ai_qa.QA_SYSTEM_PROMPT` +
  `build_prompt`), so responses render identically (`LLMProvider.parse` /
  `parse_followup` unchanged). Two implementations, one wire contract:
  `worker.js` (**Cloudflare Worker — recommended host**) and `mcat_ai_proxy.py`
  (Python stdlib reference + `--mock` for keyless local verification / optional
  self-host).
- **Contract:** `POST <url>` with header `X-MCAT-Bundle-Token`, body
  `{model, messages}` → `200 {content, model}`; any non-200 → client falls back.
  `GET /health` for deploy verification.
- **Client** (`scripts/ai_explain.py`): a new **proxy provider** selected by
  `build_live_call_model_from_env` when no direct provider is set but a proxy is
  configured (`load_proxy_config` reads `MCAT_AI_PROXY_URL/TOKEN` **or** a
  `mcat-ai-proxy.json` bundle file). Label `proxy:<model>`; needs **no user key**.
  The existing 15s client timeout + safety gate + graceful static fallback all
  still apply (unreachable/timeout/error/blocked → source-based explanation;
  never hangs/crashes). The `mcat_ai_enabled` toggle semantics are preserved.
- **Config, not compiled:** the URL + token live in `mcat-ai-proxy.json` shipped
  **next to the launcher** (placeholder until filled). The launcher exports
  `MCAT_ROOT` + `MCAT_AI_PROXY_CONFIG`, so the URL can be set/changed **without
  an MSI rebuild** (`mcat_seed_tester.py --with-ai-proxy` assembles this).

**Security posture (endpoint is internet-reachable).** Enforced in the proxy:
shared **bundle-token** header (constant-time), **per-IP rate limiting** (20/60s),
upstream **model allowlist** (`gpt-4o-mini`), **oversized-prompt rejection**,
bounded upstream timeout, forced `temperature=0`+`max_tokens`, minimal key-safe
logging. Human-side (mandatory, documented in `docs/AI-PROXY-SETUP.md`): a
**hard monthly spend cap** + a **throwaway/scoped** upstream key. The key is
**server-side only** — never in the app, bundle, config, or git. Residual abuse
risk (token ships to graders → constrained relay) is bounded by the spend cap +
rate limit + token rotation / taking the Worker down after grading.

**Honesty / UI.** `ai_bridge.ai_provider_configured()` (toggle-independent,
network-free config check) drives an honest header pill: **"AI: On"** only when
a backend is actually configured, **"AI: Not set up"** when the toggle is on but
nothing is configured, **"AI: Off"** when toggled off — fixing the earlier
cosmetic mismatch (pill "On" while the panel said "not configured"). The
status/fallback notes are now key-agnostic (no "add an API key", since the
graded build is keyless).

**Scope guardrails.** No scheduler / three-score changes. **`SCORE_PROFILE` is
untouched** — the proxy is orthogonal to the score profile and works under
either; the graded build still needs `SCORE_PROFILE=strict` set + a rebuild as a
**separate** assembly step (not part of this change). Adding the capability is
**harmless/dormant** for friends: with the placeholder config the app behaves
exactly like the friend build (offline, source-grounded).

**MSI note.** The proxy *provider code* is a source change in the compiled app
(`ai_explain.py` proxy provider is delegated to by the compiled `ai_bridge.py`;
plus the pill/status honesty in `performance_dialog.py`), so shipping the
**capability** required **one** MSI rebuild. After that rebuild the **URL/token
stay config-driven** (no further rebuilds to set/change them).

**Files.** `MCAT/proxy/{worker.js,wrangler.toml,mcat_ai_proxy.py,README.md,
mcat-ai-proxy.example.json,test_mcat_ai_proxy.py}`, `MCAT/scripts/ai_explain.py`
(proxy provider + `load_proxy_config`), `MCAT/scripts/test_ai_proxy_client.py`,
`MCAT/.env.example`, `MCAT/docs/AI-PROXY-SETUP.md`, `MCAT/docs/TESTER-QUICKSTART.md`
(graded-build note); `anki-MCAT/qt/aqt/mcat/ai_bridge.py`
(`ai_provider_configured`), `anki-MCAT/qt/aqt/mcat/performance_dialog.py` (honest
pill/status), `anki-MCAT/tools/mcat_seed_tester.py` (`--with-ai-proxy`).

**Verification.** 12 proxy unit tests + 11 app-side provider tests (mocked
upstream / real local mock server), incl. app→proxy→rendered explanation,
follow-up Q&A, and unreachable/bad-token→static fallback — all green; existing
33 AI tests unaffected. No secrets committed.

---

## 33. Engineering workflow — feature branches → PRs → green CI

**2026-07-04 —** The final-submission work is landed as **feature-scoped
branches → one PR per feature → a green `mcat-ci` check**, not a single squashed
dump, so the history reads as a real engineering workflow for the grader.

- **Branches (`MCAT`):** `feat/honest-eval-artifacts`, `feat/ai-keyless-proxy`,
  `feat/graded-strict-build`, `ci/github-actions`, `docs/final-submission`. The
  two app-touching features open **paired** branches of the same name in
  `anki-MCAT` (`feat/ai-keyless-proxy`, `feat/graded-strict-build`);
  `feat/android-three-scores` lives in `anki-android-MCAT`.
- **Disjoint file sets** per branch. Files touched by more than one concern
  (`Makefile`, `docs/DECISIONS.md`) are assigned **whole** to their single
  most-relevant branch to avoid merge conflicts — see the branch→files map in
  `docs/pr-drafts/README.md`.
- **Ordering / CI dependency:** `.github/workflows/mcat-ci.yml` runs the proxy
  tests (`proxy.test_mcat_ai_proxy`, `scripts.test_ai_proxy_client`), so
  `ci/github-actions` must merge **after** `feat/ai-keyless-proxy` (and the eval
  PR) or its two proxy steps fail with `ModuleNotFoundError`.
- **Non-destructive discipline:** every commit was staged by explicit path with
  `git diff --cached --name-only` verified clean of `.env*`/keys/build artifacts;
  no history rewrite, no force; publishing is done by the maintainer via the
  VSCode GitHub extension.

---

## 18. References

- [`PRD.md`](PRD.md)  
- [`ARCHITECTURE.md`](ARCHITECTURE.md)  
- BrainLift — Gabriel Xiong  
- Speedrun PDF in repo root  

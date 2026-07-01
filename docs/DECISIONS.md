# Design Decision Log — MCAT Speedrun

**Last updated:** 2026-07-01  
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
| 12 | Error typing | Wed: **4 self-report types** (frozen). v2: **3-bucket science taxonomy** (`content_gap`, `application`, `misread`; `reasoning`→`application`, `passage_mapping` folds in) **inferred from distractor role + cross-system `M` + timing, student *confirms*** (self-report demoted to confirmation + validation signal) — see `ERROR-DIAGNOSIS-SPEC.md` |
| 13 | Question bank | **Curated OpenStax** (named sources); AI off at runtime |
| 14 | Study feature | **Interleaved vs blocked performance sessions** |
| 15 | Memory model | FSRS + calibration (not custom ML) |
| 16 | Performance model | Attempt accuracy (not memory × constant) |
| 17 | Builder | Solo; friend = held-out performance participant |
| 18 | AI (Friday) | Optional; not on critical path for Q bank |
| 19 | `M` signal source | **Per-card FSRS-R** (pure Python) replaces topic-level fallback; question schema extended with `cognitive_demand` + `choice_diagnosis` (additive) |
| 20 | Attempt data collection | **Local sidecar is source of truth**; full `feature_json` captured per attempt; **export script** (`tools/mcat_export_perf.py`) is the eval collection path; external telemetry backend **deferred** |
| 21 | Inference abstention balance | **Commit, don't over-abstain:** `infer_error_type` commits a diagnosis in the common miss — **`application` is the DEFAULT** for a content-presumed-held miss; honesty carried by **moderate confidence (0.55–0.60)**, not abstention. `unresolved` reserved for the truly-dark miss; CARS misses hard-guarded to `unresolved`. **Supersedes** the spec's "cold-start / fast-alone → unresolved" stance |

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

**Open detail (cross-device perf sync, build step 7):** stock Anki sync is schema-aware and won't propagate custom tables, so multi-device perf sync needs its own design — export/import, a self-hosted sync path, or (only if cloud features are later adopted) a backend. Memory revlog conflict rule still TBD before Sunday (union + recompute FSRS).

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

## 18. References

- [`PRD.md`](PRD.md)  
- [`ARCHITECTURE.md`](ARCHITECTURE.md)  
- BrainLift — Gabriel Xiong  
- Speedrun PDF in repo root  

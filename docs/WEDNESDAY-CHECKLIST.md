# Wednesday checklist (Speedrun)

_Last updated: 2026-07-01. Engineering + content are done; what's left is
committing, and capturing the two desktop recordings. See
`docs/RECORDING-RUNBOOK.md` for the "hit record and follow" shot-lists._

## Proof artifacts to capture

- [ ] Commit hash of `anki-MCAT` — **blocked: work is still uncommitted** (see
      `docs/RELEASE-INSTALLER.md`; needs your go-ahead to commit + push)
- [ ] Screen recording: desktop memory review + performance/diagnosis demo —
      **you record** (shot-list A in `docs/RECORDING-RUNBOOK.md`)
- [x] Screen recording: phone review session (AnkiDroid) — captured to
      `assets/` during the mobile track (import + graded review on emulator)
- [ ] Clean-machine install recording — installer **already built** locally
      (`anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`); run the existing
      `.msi` on a clean VM and record (shot-list B in
      `docs/RECORDING-RUNBOOK.md`). Note: the `.msi` predates today's UI changes.
- [x] Rust test output — 4 mastery unit tests pass (`cargo test -p anki mcat`);
      re-run and screen-capture for the proof packet
- [x] **No AI** in build or runtime — verified: MCAT runtime modules contain no
      network/LLM calls (only SQLite + AGPL header URLs)

## Engineering

- [x] `./run` succeeds; Anki opens (Anki 26.05, Qt 6.11)
- [x] Mastery query implemented in `rslib` (`rslib/src/mcat/`; see
      `docs/MASTERY-QUERY-SPEC.md`)
- [x] ≥3 Rust unit tests + 1 Python integration test (4 Rust + Python tests in
      `pylib/tests/test_mcat_*.py`)
- [x] Performance mode reads `data/questions.json` (loader + sidecar DB)
- [x] Error typing UI on performance miss — **v2 confidence-gated diagnosis
      panel**: shows the *inferred* type + confidence ("Looks like: <type> ·
      NN%") with one-tap **Confirm** and an **"Actually, something else"**
      override (which excludes the suggested type); a 3-button
      content_gap / applied-reasoning / misread self-report is the low-confidence
      fallback. (Inferred, not blank self-report.)
- [x] Memory score + range + give-up on dashboard (three-score home screen)
- [x] Topic tags on deck (`data/deck-tagging.md`)
- [x] Tools-menu MCAT actions: Load question bank, Export performance data,
      Reset performance data; plus **auto-reset of performance/readiness when an
      MCAT-tagged deck is deleted** (dashboard falls back to "not enough data")

## Content (parallel — you)

- [x] ≥30 questions in `data/questions.json` (`split: dev`) — **65 dev** now
      (**170 total: 65 dev / 105 held_out** across all **18 topics**; 157 science
      + 13 CARS). Science-question coverage **127/157** (the 30 new §7d paraphrase
      probes `q_ho_061`–`q_ho_090` have no dedicated backing card yet — see
      DECISIONS §27) and choice-tag coverage (287 content_gap / 18 trap / 76 null
      distractors, as of the pre-§27 bank — recompute for the current 170).
- [x] Update `data/curation-status.json` counts (auto-refreshed by builder)
- [x] `python scripts/validate_data.py` passes
- [x] Flashcards regenerated: **133 cards (106 cloze / 27 basic)** in
      `data/flashcards-dev-cloze.csv` + `data/flashcards-dev-basic.csv`. CSVs now
      carry Anki import directives (`#notetype` / `#columns` / `#tags column`) →
      **one-click import**, no header note to delete.
- [x] Small test deck tagged across ≥5 topics — 133-card deck across 18 topics

## Docs

- [x] Fork README states MCAT exam + AGPL credit (`anki-MCAT/README.md`)
- [x] Rust change note (`docs/RUST-CHANGE-NOTE.md`)

## Remaining for the morning (needs your decision / action)

1. **Commit** the `anki-MCAT` changes (see `docs/RELEASE-INSTALLER.md`) — I did
   not commit/push overnight without explicit approval.
2. **Installer**: already built locally
   (`anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`) — just run it on a
   clean VM and record. (CI path documented as a fallback in
   `docs/RELEASE-INSTALLER.md`.)
3. **Recordings**: desktop memory-review + performance/diagnosis demo, and the
   clean-machine install of the existing `.msi` (phone review already captured).
   Follow `docs/RECORDING-RUNBOOK.md` for both shot-lists.

## Friday deliverables

Three Friday workstreams, ordered by dependency: **(1)** the GRADED-CORE
collection review sync + §7b test (unblocks the 70% cap), **(2)** the phone
three-score dashboard, and **(3)** the performance-data bundle side-channel.
Sub-parts (1) and (3) are **different sync channels** — (1) syncs memory reviews
(revlog + card scheduling) over the shared engine; (3) syncs MCAT
performance-attempt data as a portable bundle. Shot-lists in
`docs/RECORDING-RUNBOOK.md`: (1) = §D, (2) = §F, (3) = §E.

### (1) GRADED CORE — collection review sync + §7b test (desktop ↔ AnkiDroid)

_Set up + documented 2026-07-02. Server verified; client wiring + recording are
manual GUI/emulator steps (can't be scripted from the shell)._

Spec: "review on the phone, see it on the desktop, and the reverse, with no lost
or double-counted reviews" + "offline review works, then syncs when the connection
returns" + the §7b sync test. Load-bearing ("No phone companion that shares the
engine and syncs: 70% maximum").

- [x] **Approach decided + documented: self-hosted local `--syncserver`** (not
      AnkiWeb) — no credentials, offline-friendly on the LAN, same build serves
      both forks. Rationale in `docs/SYNC-CONFLICT-RULE.md §5`.
- [x] **Server verified from the FROZEN build** (no `./run` rebuild):
      `out/installer/build/anki/windows/app/src/Anki.exe --syncserver` with
      `SYNC_USER1=mcat:mcat` → `GET /health` = **200**, `/sync/*` route live
      (2026-07-02). Command in `docs/RECORDING-RUNBOOK.md §D.1`.
- [x] **Conflict/winner rule written down** (required §7b artifact) —
      `docs/SYNC-CONFLICT-RULE.md`: revlog append-only keyed by review ms-id
      (`INSERT OR IGNORE`; none lost/doubled) + card scheduling
      **last-review-wins by `mtime`** (shared Rust engine, both forks).
- [x] **§7b click-by-click runbook** — `docs/RECORDING-RUNBOOK.md §D` (start
      server, point clients, baseline, 10+10 offline reviews, same-card conflict,
      phone→desktop proof).
- [ ] **Point desktop client at server** — Preferences → Syncing → *Self-hosted
      sync server* = `http://127.0.0.1:8080/` (runbook §D.2). **Needs you (GUI).**
- [ ] **Point AnkiDroid at server** — Settings → Sync → *Custom sync server* →
      *Sync URL* = `http://10.0.2.2:8080/`; log in `mcat`/`mcat` (§D.3). **Needs
      you (emulator).**
- [ ] **Recording:** phone review appears on desktop after sync + 20-review
      no-loss/no-dup + same-card conflict winner (§D.4–D.5). **You record.**

### (2) Phone three-score dashboard (AnkiDroid)

_Implemented 2026-07-02. Satisfies the Friday spec item: "The phone shows the
three scores with ranges and follows the give-up rule."_

Mirrors the desktop scoring on-device: the AnkiDroid dashboard replicates the
Rust mastery query + `mcat_scores.py` thresholds in Kotlin against the SAME
`data/scoring-config.json` values, so **phone and desktop agree**.

- [x] **Dashboard screen** in the AnkiDroid fork
      (`AnkiDroid/src/main/java/com/ichi2/anki/mcat/`): `McatDashboardFragment`
      (UI) + `McatScores` (pure scoring port) + `McatDashboardRepository` (real
      data feeds). Hosted by `SingleFragmentActivity`.
- [x] **Entry point:** DeckPicker overflow menu → **"MCAT: Dashboard"**
      (`res/menu/deck_picker.xml` + `DeckPicker.onOptionsItemSelected`).
- [x] **Three scores with ranges, never blended:** Memory (reviews · topics ·
      unlocked), Performance (accuracy · correct/attempts), Readiness (472–528
      range), plus coverage bar + single next action + focus area.
- [x] **Readiness honesty / give-up rule** matches `scoring-config.json`
      (coverage < 50%, attempts < 30, reviews < 200, per-section + CARS minimums):
      below threshold the phone shows **NO readiness number** (abstain), with the
      coverage %, missing-data reason, and next action. When eligible it shows the
      range + confidence + last-updated + next action.
- [x] **Data feeds — honest about scope:**
      - **Memory = REAL** (live collection: revlog count + topic-tagged mastery).
      - **Performance / Readiness = REAL when the perf sidecar
        `collection.mcat_perf.db` is present on-device** (read read-only, same file
        the desktop writes / the sync bundle carries). If absent, Performance shows
        "no data yet" and Readiness abstains — never fabricated. UI lights up
        automatically once the sidecar lands.
- [x] **AI-off-safe:** dashboard renders from local SQLite only — no network/AI.
- [x] **Builds:** `./gradlew :AnkiDroid:compilePlayDebugKotlin` compiles clean
      (JDK 17 via `JAVA_HOME`). Full APK: `./gradlew :AnkiDroid:assemblePlayDebug`.
- [ ] **Recording:** open the phone dashboard + show abstain/give-up state —
      **you record** (shot-list **F** in `docs/RECORDING-RUNBOOK.md`).
- [ ] **Commit** the AnkiDroid changes (uncommitted, per the no-commit-without-
      approval rule).

### (3) Performance-data bundle sync (side-channel)

_Implemented 2026-07-02. Engineering done; what's left is recording the two demos._

- [x] **Export/import bundle sync** for performance data — portable, versioned
      JSON bundle (`format: mcat_perf_bundle`, `format_version: 1`) with an
      **append-only UNION merge** deduped by a stable per-attempt **`uuid`**
      (additive migration, same pattern as `choice_diagnosis`). Idempotent +
      order-independent → two devices converge. See `docs/DECISIONS.md §22`.
- [x] **Tools-menu actions:** "MCAT: Export sync bundle…" and "MCAT: Import sync
      bundle…" (`anki-MCAT/qt/aqt/mcat/__init__.py`).
- [x] **Headless CLIs:** `tools/mcat_export_bundle.py` + `tools/mcat_import_perf.py`
      (mirror the existing `tools/mcat_export_perf.py`).
- [x] **Tests green:** round-trip, disjoint union + convergence, idempotent
      re-import, order-independence, uuid migration/backfill — in
      `pylib/tests/test_mcat_perf.py` (52 passed).
- [ ] **Recordings:** "Two-way sync verified" + "Offline review → sync" —
      **you record** (shot-list **E** in `docs/RECORDING-RUNBOOK.md`).
- [ ] **Commit** the sync changes (still uncommitted, per the no-commit-without-
      approval rule).

> Scope note: the bundle in sub-part (3) syncs **MCAT performance-attempt data**
> as a portable side-channel. It is **separate from** the GRADED-CORE deliverable
> in sub-part (1) above, which is the actual **memory-review sync** (revlog + card
> scheduling) between the desktop and AnkiDroid forks over the shared engine —
> that is what the spec's "phone companion that shares the engine and syncs" and
> §7b measure.

## Explicitly not Wednesday

- ~~Two-way sync (Friday)~~ — **done**, see the Friday sections above
- AI features (Friday)
- Readiness calibration / Sunday eval scripts
- AnkiDroid full parity

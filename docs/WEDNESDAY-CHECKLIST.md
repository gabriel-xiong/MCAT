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
      (**140 total: 65 dev / 75 held_out** across all **18 topics**; 127 science
      + 13 CARS). Science-question coverage **127/127** and choice-tag coverage
      **127/127** (287 content_gap / 18 trap / 76 null distractors).
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

## Explicitly not Wednesday

- Two-way sync (Friday)
- AI features (Friday)
- Readiness calibration / Sunday eval scripts
- AnkiDroid full parity

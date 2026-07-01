# Wednesday checklist (Speedrun)

_Status as of 2026-06-30 (overnight build). Engineering + content are done;
what's left is committing, the installer build, and capturing recordings._

## Proof artifacts to capture

- [ ] Commit hash of `anki-MCAT` — **blocked: work is still uncommitted** (see
      `docs/RELEASE-INSTALLER.md`; needs your go-ahead to commit + push)
- [ ] Screen recording: memory review session (desktop) — **you record**
- [x] Screen recording: phone review session (AnkiDroid) — captured to
      `assets/` during the mobile track (import + graded review on emulator)
- [ ] Clean-machine install recording — installer **built** locally
      (`anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`); run on a clean VM
      and record
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
- [x] Error typing UI on performance miss (4 buttons)
- [x] Memory score + range + give-up on dashboard (three-score home screen)
- [x] Topic tags on deck (`data/deck-tagging.md`)

## Content (parallel — you)

- [x] ≥30 questions in `data/questions.json` (`split: dev`) — **50 dev** now
      (110 total: 50 dev / 60 held_out across all 18 topics)
- [x] Update `data/curation-status.json` counts (auto-refreshed by builder)
- [x] `python scripts/validate_data.py` passes
- [x] Small test deck tagged across ≥5 topics — **79 notes across 15 topics**

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
3. **Recordings**: desktop memory review + clean-machine install (phone review
   already captured).

## Explicitly not Wednesday

- Two-way sync (Friday)
- AI features (Friday)
- Readiness calibration / Sunday eval scripts
- AnkiDroid full parity

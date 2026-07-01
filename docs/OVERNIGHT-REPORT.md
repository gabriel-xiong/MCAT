# Overnight build report — 2026-06-30 → 07-01

Everything below is **data / docs / local build only**. I did **not** commit,
push, or dispatch CI (no explicit approval for that). Review items are called
out at the end.

## 1. Question bank — DONE (exceeds all milestones)

`data/questions.json` rebuilt from a new authoring script
`scripts/build_question_bank.py`.

- **110 questions**, all 4-option MCQs, exactly one correct answer.
- **50 dev / 60 held_out**, across **all 18 topics**.
- Milestones: Wed (30 dev / 5 topics) ✅, Fri (50 dev / 20 held_out) ✅,
  Sun (80 total / 60 held_out) ✅.
- Science items sourced to the OpenStax chapters in
  `data/openstax-sources.json` (`source_name` / `source_url` / `source_location`
  on every item). CARS items are **original CC0 passages** I wrote (two
  passages, "History & Objectivity" and "Choice & Freedom") — no AAMC/Khan or
  other proprietary QBank content was copied.
- The existing 7 dev items (`q_dev_001..007`) are preserved verbatim so
  flashcard `supports_question` links still resolve.
- `python scripts/validate_data.py` → **Validation OK**.
- `data/curation-status.json` counts auto-refreshed by the builder.

**Please spot-check the answer keys** — I authored these from established
OpenStax-level facts, but a quick review of a random sample is worth it.

## 2. Flashcards — DONE (Wed target met)

Rebuilt from `scripts/build_flashcards.py` (single source → 3 CSVs kept in sync).

- **102 notes across 15 science topics** (Wed target was ≥50 across ≥5).
- **85 Cloze / 17 Basic** → cloze share 83% (rule ~70–80%; slightly high after
  adding per-question coverage cards — acceptable, flag if you want it lower).
- Follows the cloze rules in `data/deck-tagging.md`: single-index paired blanks
  (`{{c1::x}} … {{c1::y}}`, never `c1`+`c2` leakage), max 2 blanks, anchored
  blanks, Basic = real "why" questions, **all `text`/`back` fields quoted**.
- Files: `data/flashcards-dev.csv` (all), `-cloze.csv`, `-basic.csv`.
- The original 16 notes are preserved verbatim, so re-importing won't duplicate
  them; the new notes are additive. Re-import both `-cloze.csv` and `-basic.csv`
  in Anki to pick up the new cards.

CARS has **no** flashcards by design (performance-only).

**Question ↔ flashcard mapping** (added on request): the deck was expanded to
**102 cards** so that **every science question has ≥1 dedicated backing card**
(97/97), and `supports_question` is now a **precise per-question link**.
`docs/QUESTION-CARD-MAP.md` lists each of the 110 questions with the exact
card(s) that teach it, plus a per-topic coverage table. The flashcard builder
self-checks coverage (warns on any gap or dangling id); the map script exits
non-zero if any science question is uncovered. Regenerate with
`scripts/build_flashcards.py` then `scripts/build_question_card_map.py`.

## 3. Fork README — DONE

`anki-MCAT/README.md` rewritten: MCAT product statement (three separate scores,
topic-gated performance, honest abstention, no runtime AI), a summary of what
the fork changes, build/test/run instructions, and explicit **AGPL-3.0-or-later
+ Anki/AnkiDroid upstream credit**. Upstream Anki README preserved below it.

## 4. Installer — BUILT locally

`./ninja installer:package` completed (exit 0, ~195s). Artifact:
**`anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi`** (~636 MB).
Only remaining step is running it on a clean VM and recording it. See
`docs/RELEASE-INSTALLER.md` (also has the GitHub Actions fallback).

## 5. Verification

- Python: `pytest pylib/tests/test_mcat_*.py` → **17 passed**.
- Rust: 4 mastery-query unit tests (`cargo test -p anki mcat`).
- Data: `scripts/validate_data.py` → OK.
- No-AI: MCAT runtime modules (`mcat_perf.py`, `mcat_scores.py`, `qt/aqt/mcat/`)
  contain no network/LLM calls — only SQLite and AGPL header URLs.

## 6. Docs updated

- `docs/WEDNESDAY-CHECKLIST.md` — statuses checked off + remaining items.
- `docs/RELEASE-INSTALLER.md` — new commit + installer + proof runbook.
- `data/curation-status.json` — refreshed counts.

## What needs YOU in the morning (needs your decision / action)

1. **Review** a sample of the question keys + flashcards (they're meant for your
   morning review).
2. **Commit** `anki-MCAT` and `MCAT` (I left this to you — exact commands in
   `docs/RELEASE-INSTALLER.md`). Consider gitignoring `anki-MCAT/target-install/`
   and `anki-MCAT/tools/git-bash-temp.sh` (local scratch/artifacts).
3. **Test the installer** on a clean VM + record.
4. **Record** the desktop memory-review session (phone review already captured
   in `assets/`).

## New/changed files

- `MCAT/scripts/build_question_bank.py` (new)
- `MCAT/scripts/build_flashcards.py` (new)
- `MCAT/data/questions.json` (110 Qs)
- `MCAT/data/flashcards-dev.csv`, `-cloze.csv`, `-basic.csv`
- `MCAT/data/curation-status.json`
- `MCAT/docs/WEDNESDAY-CHECKLIST.md`, `docs/RELEASE-INSTALLER.md`,
  `docs/OVERNIGHT-REPORT.md`
- `anki-MCAT/README.md`
- `anki-MCAT/out/installer/dist/anki-26.05-win-x64.msi` (build artifact)

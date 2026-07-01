---
name: mcat-speedrun-dev
description: >-
  Guide development of the MCAT Speedrun Anki fork — mastery query Rust change,
  memory/performance modes, three-score dashboard, AnkiDroid sync, curated OpenStax
  question bank, error typing, coverage map, and Speedrun Wed/Fri/Sun milestones.
  Use when editing this repo, forking Anki/AnkiDroid, or implementing eligibility,
  scoring, eval scripts, or performance mode.
---

# MCAT Speedrun Dev

## Start here

1. Read `AGENTS.md`, then `docs/PRD.md` and `docs/DECISIONS.md`.
2. Confirm which milestone is active (Wed = no AI; Fri = sync + AI optional; Sun = eval + ship).
3. Prefer minimal diffs; match Anki upstream patterns.

## Milestone gates

| Day | Must have | Must not |
|-----|-----------|----------|
| **Wed** | Anki builds; mastery query + tests; memory + perf demo; error typing; installer; AnkiDroid review | AI calls |
| **Fri** | Two-way sync; 3 scores on phone; offline → sync | — |
| **Sun** | eval scripts; calibration; APK + installer; demo proof | Fake readiness |

## Architecture checklist

- [ ] Shared Rust engine (desktop + AnkiDroid)
- [ ] Mastery query → topic eligibility
- [ ] Memory mode (FSRS) + Performance mode (separate session)
- [ ] Gate: ≥3 cards seen + ≥5 Good/Easy per topic
- [ ] CARS performance-only
- [ ] Three scores with ranges + give-up rules
- [ ] Coverage map; readiness abstain < ~50%
- [ ] Curated questions with source metadata + dev/held_out split
- [ ] Error types → next action on dashboard

## Question bank workflow

1. Pull from OpenStax end-of-chapter / review MCQs with answer keys
2. Tag `topic_id`, `section`, `source_*`, `split`
3. Freeze `held_out` before tuning thresholds
4. Friend answers held-out set once for eval

Do not: live LLM during performance mode; unlicensed QBank scrapes.

## Scoring rules

- **Memory:** FSRS + calibration on held-out reviews — not custom ML
- **Performance:** attempt accuracy — NOT `memory × constant`
- **Readiness:** section map + coverage penalty; wide ranges when n is small

## Study feature

Interleaved vs blocked **performance** sessions. Three builds: on / off / plain Anki. Same time, same questions.

## Eval commands (Makefile)

- `make bench` — latency on 50k deck
- `make eval-memory` — Brier/log loss + calibration chart
- `make eval-performance` — held-out accuracy + paraphrase gap
- `make eval-leakage` — train/test overlap

## Common mistakes

- Blending three scores into one "readiness %"
- Performance questions right after flashcard reveal
- Showing readiness with low outline coverage
- Building mobile before desktop Anki compiles
- Tuning on held-out questions then reporting on same set

## BrainLift alignment

- SPOV 1: readiness as continuous signal with abstention
- SPOV 2: memory + performance in one loop, separate measurement
- SPOV 3: error typing, not just missed topic

## References

- `docs/ARCHITECTURE.md` — data model and sync
- `data/mcat-outline.example.json` — topic IDs
- `data/questions.example.json` — question schema
- Speedrun PDF in repo root — grading rubric

# AGENTS.md — MCAT Speedrun

Read this before making changes. Full specs: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`.

## Product in one sentence

Anki fork + AnkiDroid companion with **three separate scores** (memory, performance, readiness), topic-gated performance mode, and honest abstention — **not** a full MCAT prep course.

## Build order (do not skip)

1. Anki builds from source
2. Rust **mastery query** + tests
3. AnkiDroid builds with same engine
4. Topic tags + outline JSON + eligibility gates
5. Performance mode + curated question bank (OpenStax) + error typing
6. Dashboard (3 scores, coverage, next action)
7. Sync proof + eval scripts + packaging

## Locked decisions

- **Exam:** MCAT (472–528)
- **Rust change:** per-topic mastery query
- **Mobile:** Android / AnkiDroid only
- **Sync:** stock Anki sync; perf tables in same collection DB
- **Performance gate:** ≥3 cards seen + ≥5 Good/Easy per topic
- **CARS:** performance-only (no memory gate)
- **Questions:** curated named sources; **AI off at runtime**
- **Study feature:** interleaved vs blocked performance sessions
- **Scores:** never blend memory + performance + readiness

## What not to do

- Do not rewrite scheduler in JS/Swift/Kotlin
- Do not show performance immediately after flashcard reveal
- Do not invent readiness without range, coverage, and give-up rules
- Do not scrape unlicensed QBanks
- Do not scope-creep into full MileDown-scale content
- Do not add AI calls to Wednesday deliverable

## Key paths

```
docs/PRD.md              — requirements
docs/ARCHITECTURE.md     — system design
docs/DECISIONS.md        — decision log
data/mcat-outline.example.json
data/questions.example.json
Makefile                 — bench + eval targets
```

## Eval (solo)

- Memory data: builder reviews (time-split train/test)
- Performance data: friend on frozen `held_out` questions
- Document small n honestly

## Suggested development loops

Use Cursor `/loop` for long builds:

```
/loop 5m check if anki ./tools/build finished and report errors
/loop 10m run make test and summarize failing tests
```

## After code changes

- Run relevant Rust tests for mastery query changes
- Run `make test` when wired
- Update README build section when fork paths are known

## License

AGPL-3.0-or-later fork. Credit Anki and AnkiDroid upstream.

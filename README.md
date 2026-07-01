# MCAT Speedrun — Anki Measurement Layer

**Exam:** MCAT (472–528 total; sections 118–132 each)  
**Owner:** Gabriel Xiong  
**License:** AGPL-3.0-or-later (Anki fork — credit [Anki](https://github.com/ankitects/anki) and [AnkiDroid](https://github.com/ankidroid/Anki-Android))

A **desktop Anki fork** and **Android companion** that share one Rust engine and surface **three honest scores** — **memory**, **performance**, and **readiness** — not one blended “% ready.”

> **Scope:** This is a **prototype measurement product** on a **subset of MCAT topics**, not a full prep course. We demonstrate the recall → application → readiness bridge with honest uncertainty and abstention when data is thin.

---

## The problem (BrainLift)

MCAT students spend months on content review (often Anki) without a live readiness signal, then discover gaps only during late full-length practice exams. **Recall ≠ exam performance:** ~35% of science questions are Skill 1 (recall-like); ~65% require application, research reasoning, or data interpretation. Tools that only track card completion create **false readiness**.

This app measures that gap explicitly.

---

## What it does

| Mode / layer | Measures | How |
|--------------|----------|-----|
| **Memory mode** | Declarative recall | Normal Anki reviews (FSRS) |
| **Performance mode** | Procedural / exam-style accuracy | Curated MCQs from named sources (OpenStax, etc.) on **unlocked topics only** |
| **Readiness** | Continuous score proxy | Section performance + outline **coverage** → 472–528 **range**; abstains when coverage &lt; ~50% |

**Integrated loop:** performance misses include **error typing** (content gap / passage mapping / reasoning / misread) → dashboard **next action** — not disjoint Anki + QBank tabs.

---

## Architecture (locked)

| Area | Decision |
|------|----------|
| Engine | Shared **Anki Rust** core + **per-topic mastery query** |
| Desktop | Anki fork (Python/Qt UI) |
| Mobile | **AnkiDroid fork** (Android only) |
| Sync | **Stock Anki sync**; performance tables in same collection DB |
| Questions | **Curated** from OpenStax / named sources; **AI off at runtime** |
| Study feature | **Interleaved vs blocked performance sessions** (3-build ablation) |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/DECISIONS.md`](docs/DECISIONS.md).

---

## Topic eligibility (memory → performance)

Performance mode unlocks per topic when:

- ≥ **3** distinct cards reviewed at least once  
- ≥ **5** Good or Easy reviews in that topic  

**CARS:** performance-only lane (no flashcard gate).

Performance sessions are **separate** from flashcard reviews — not “flip card → instant quiz.”

---

## Give-up rules (draft)

Scores are withheld when data is insufficient. **Total readiness** requires all of:

- ≥ **200** memory reviews  
- ≥ **30** performance attempts  
- ≥ **50%** outline coverage (topics with ≥1 card reviewed)  
- ≥ **5** performance attempts per science section + CARS  

Individual scores may abstain with lower thresholds. See [`docs/PRD.md`](docs/PRD.md) §7.

---

## Content scope (not a full course)

| Enough for speedrun | Not required |
|---------------------|--------------|
| ~**15–25** outline topics with deck tags | Full AAMC content map filled |
| ~**200–500** flashcards | MileDown / AnKing scale |
| ~**30–100** curated performance questions | Full QBank |
| Coverage % shown honestly (e.g. “38% of outline”) | 100% coverage |

Question bank: copy from **OpenStax** end-of-chapter / review questions with `source_name`, `source_url`, and `topic_id`. See [`data/questions.example.json`](data/questions.example.json).

---

## Repository layout

```
MCAT/
├── README.md                 # This file
├── AGENTS.md                 # Agent / developer workflow
├── docs/
│   ├── PRD.md                # Full product requirements
│   ├── ARCHITECTURE.md       # System design
│   └── DECISIONS.md          # Locked design decisions
├── data/
│   ├── mcat-outline.v1.json      # 18-topic v1 subset (coverage denominator)
│   ├── openstax-sources.json     # where to pull curated MCQs
│   ├── questions.json            # performance bank (you fill from OpenStax)
│   ├── curation-status.json      # progress tracker
│   ├── scoring-config.json       # gates, give-up rules, error types
│   └── deck-tagging.md
├── scripts/
│   ├── validate_data.py
│   ├── eval_leakage.py
│   ├── sync_curation_status.py
│   └── setup-anki-build.sh
├── .cursor/
│   ├── rules/                # Cursor project rules
│   └── skills/mcat-speedrun-dev/  # Project skill for AI assistants
├── Makefile                  # bench + eval targets (stubs until implemented)
└── Speedrun_ ... .pdf        # Course spec
```

---

## Build order (do this first)

1. **Get Anki building from source** — nothing else matters until this works  
2. **One tiny Rust change visible end-to-end** (mastery query)  
3. **Same engine on AnkiDroid**  
4. Memory mode + topic tags + eligibility gates  
5. Performance mode + curated question bank + error typing  
6. Dashboard (three scores, coverage, next action)  
7. Sync + eval scripts + packaged builds  

> Teams that delay Rust build or mobile until late in the week will not finish. Solo: **Android only**, slim phone scope (memory + sync + scores).

---

## Build instructions

> **Environment setup:** see [`docs/SETUP.md`](docs/SETUP.md) for installed tools (Git, Rust MSVC, Python 3.12, Node).

> **Status:** Pre-implementation. Fill in commit hashes and paths after fork is cloned.

### Prerequisites

- Rust toolchain (Anki’s pinned version — see upstream `docs/build.md`)
- Python 3.x + Qt dependencies (Anki desktop)
- Android SDK / JDK (AnkiDroid)
- ~50 GB disk for full Anki + AnkiDroid trees (recommended: git submodules or side-by-side clones)

### Desktop (Anki fork)

```bash
# After forking anki/anki and applying changes:
cd anki
./tools/build
# Run tests including Rust mastery query + Python integration test
```

### Android (AnkiDroid fork)

```bash
cd Anki-Android
./gradlew assembleDebug
# Install APK on device/emulator; verify same collection opens and reviews work
```

### Eval (Sunday deliverables)

```bash
make bench              # 50k-card latency report
make eval-memory        # FSRS calibration on held-out reviews
make eval-performance   # Held-out question accuracy + paraphrase gap
make eval-leakage       # Train/test overlap check
```

---

## Evaluation (solo-friendly)

| Data | Who | Split |
|------|-----|-------|
| Memory reviews | You (daily Anki use) | Time-based 70/30 train vs test |
| Performance questions | Premed friend (held-out set) | Frozen `held_out` IDs before tuning |
| Paraphrase test | 30 cards × 2 topic-linked Qs | Friend; separate session from cards |

Document small **n** and low confidence honestly — beats a fake precise readiness score.

---

## Milestones (Speedrun)

| Deadline | Goal |
|----------|------|
| **Wednesday** | Both apps review same deck; Rust change; memory score; installer; phone recording. **No AI.** |
| **Friday** | AI checked (if shipped); two-way sync; three scores on phone |
| **Sunday 10:59 PM CT** | Calibrated models; study-feature test; APK + installer; demo video; BrainLift |

---

## Documentation

- [`docs/PRD.md`](docs/PRD.md) — full product requirements (§4 personas, user stories, journeys)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, data model, sync  
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decision log  
- `Speedrun_ A Desktop + Mobile Study App Built on Anki (1).pdf` — course grading spec  

---

## Honesty rule (non-negotiable)

No readiness score without:

- evidence behind the number  
- what data is missing  
- a **range**, not a point estimate alone  
- coverage % on the full outline  
- the **single best next thing to study**  

A confident number with none of that is a guess in a nice font.

---

## License

This project forks Anki (AGPL-3.0-or-later). Some Anki components use BSD-3-Clause. Maintain upstream attribution and publish source on distribution.

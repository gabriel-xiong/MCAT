# Deck tagging convention

Anki notes use a **single topic tag** per card for mastery query + eligibility.

## Format

```
topic:{topic_id}
```

Examples:

| Card content | Tag |
|--------------|-----|
| PEP → pyruvate kinase | `topic:bb_glycolysis` |
| Nernst equation | `topic:cp_electrochem` |
| Working memory | `topic:ps_memory` |

`topic_id` must match an entry in `data/mcat-outline.v1.json`.

## CARS

Do **not** tag CARS content on flashcards. CARS uses performance-only items (`section: CARS`).

## Optional section tag (dashboard)

```
section:BB
section:CP
section:PS
```

Derived from topic if omitted.

## Memory deck style (`flashcards-dev.csv`)

Memory mode should **not** feel like performance mode (no MCQ stems on cards).

| Style | Share | Use for |
|--------|-------|---------|
| **Cloze** | ~70–80% | High-yield facts, pairs, labels-in-context |
| **Basic Q/A** | ~15–25% | Mechanisms and **why** (one short paragraph max) |

**Cloze rules:** max **2 blanks** per note; sentence gives context (not a bare term). Blanks must be **constrained** — avoid `[weaker]` / `[stronger]` alone where any word fits; anchor with named examples or fixed vocabulary (e.g. equilibrium lies to the `left`).

**No answer leak:** In Anki, `{{c1::…}}` + `{{c2::…}}` on one note → **two cards**; each card shows the other blank’s answer. Use instead:
- **Same number** (`{{c1::Positive}} … {{c1::negative}}`) → one card, both hidden together (pairs/opposites).
- **Separate notes** when facts should be recalled independently (e.g. “enzymes lower Ea” vs “enzymes don’t change ΔG”).

**CSV quoting (required):** Always wrap the `text` and `back` fields in double quotes. Cloze sentences often contain commas (e.g. "…activation energy, not ΔG"); an unquoted comma splits the row, dumping the cloze into the wrong column (front goes blank, raw `{{c1::}}` shows on the back).

**Avoid bad stems:**
- **Don’t hide what the stem gives away** — e.g. hiding `Positive` while showing `endergonic` (flip: show ΔG sign, hide label).
- **No trivial `{{c1::not}}` cards** — use a full sentence or a Basic “why”.
- **One blank when two aren’t needed** — e.g. one product per Le Chatelier card, not `product` + `reactants` with no anchor.
- **Hide the hard word, not the grammar cue** — e.g. Brønsted: hide `donate`/`accept`, not `acids`/`bases`.

**Basic rules:** real question on the front; avoid “Which of the following…” or four-option patterns.

Import (**one step — no manual setup**): in Anki, *File → Import* the split files `data/flashcards-dev-cloze.csv` (Cloze) and `data/flashcards-dev-basic.csv` (Basic), then Import. Each file starts with Anki import directives (leading `#` lines) that Anki parses as config and never imports as notes, so **there is no header/junk note to delete and no "first row is field names" or separator toggle to flip**. The directives set the comma separator, the notetype (Cloze / Basic), and map columns automatically: `text`→Text (Cloze) / `text`→Front + `back`→Back (Basic), `tags` (col 4) → tags `topic:{id}`; the `note_type` and `supports_question` columns are left unmapped/ignored. The combined `data/flashcards-dev.csv` imports too (it uses `#notetype column:` to pick Cloze/Basic per row). Source of record: `scripts/build_flashcards.py`.

**`supports_question` column (metadata, not imported into Anki):** a **precise per-question link** — the id(s) of the performance question(s) whose tested fact the card teaches (pipe-separated, e.g. `q_dev_020|q_ho_021`). Every science question in `questions.json` has ≥1 backing card (the builder self-checks this and warns on gaps or dangling ids); some cards are extra concept cards with an empty link. For the full readable mapping (each question → the cards that teach it, plus a per-topic coverage table), see `docs/QUESTION-CARD-MAP.md` (regenerate with `scripts/build_question_card_map.py`). CARS questions have no cards by design.

## Milestone targets

| When | Cards tagged |
|------|----------------|
| Wed demo | ≥50 cards across ≥5 topics |
| Sunday | ≥200 cards across ≥10 topics |

## Performance bank (`questions.json`)

- **Canonical file:** `data/questions.json` — stems, four choices, correct letter, topic, source metadata.
- **Progress:** `data/curation-status.json` — dev / held_out counts per topic.
- **Schema example:** `data/questions.example.json`
- **Source map:** `data/openstax-sources.json` — chapter URLs used for curation.

**Format rule (v1):** deterministic 4-option MCQ only — exactly one correct answer (`A`–`D`). No open-ended, multi-select, or AI-graded items.

**`explanation` field (required):** every question carries a non-empty `explanation` — a concise (1–4 sentence) static, **NO-AI** rationale for **why the correct answer is correct**, grounded in that item's named source (OpenStax for science; the original CC0 passage for CARS). It is authored in `scripts/build_question_bank.py` (keyed by question id in the `EXPLANATIONS` dict), shown to the student **after** they answer, and reused as the app's AI-off fallback and the baseline for the AI "explain your miss" feature. It complements — never replaces — `source_name`/`source_url`. `scripts/validate_data.py` fails if any question's `explanation` is missing or blank. Per-choice/distractor breakdown is **not** part of this field (that lives in the optional `choice_diagnosis`).

**Difficulty rule (v1):** prefer **pathway / regulation / equilibrium** items (e.g. Ch. 7 Review Q9, Q16) over definition recall (e.g. “energy currency is ATP”). Skip items that duplicate flashcard stems. Tag `skill: "2"` for application-style items.

**MCAT calibration:** OpenStax review/exercise items are **not equated to AAMC difficulty**. They are intro-college content; the real MCAT adds passage context, multi-step reasoning, and experimental framing. v1 performance score = accuracy on this curated bank only — **not** a calibrated 118–132 section score. Readiness abstains below 50% topic coverage (`scoring-config.json`). Sunday milestone: friend held-out set + optional AAMC-style items for sanity check.

Each entry includes `source_url` + `source_location` so you can open the OpenStax page and compare (e.g. `Ch. 7 Review Q9`). Chemistry items from exercises are marked `4-choice MCQ` when options were normalized from (a)(b)(c) lists.

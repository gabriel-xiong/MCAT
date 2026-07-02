# §7d Paraphrase-Gap Instrument

_The measurement tool that proves the app scores **performance (transfer)**, not
just **memory (recall)**._ (Spec §7d / PRD §8.3.)

## Why this exists

The performance score is only meaningful if answering a question requires more
than reciting the backing flashcard. If a student's flashcard **recall** and
their **accuracy on the linked questions** are ~equal, the "performance" number
is just parroting memory. This instrument measures — and reports honestly — the
**gap** between the two.

For each anchor flashcard concept we pin **two exam-style questions** that test
the **same idea in genuinely different wording** (never a numeric clone). We then
compare recall of the card against mean accuracy on its two reworded questions.

## Scope (locked eval core)

Three topics only — the confirmed eval trio:

| Topic | Anchor concepts | Question slots |
|-------|----------------:|---------------:|
| `cp_acids_bases` | 10 | 20 |
| `bb_enzymes` | 10 | 20 |
| `cp_kinetics` | 8 | 16 |
| **total** | **28** | **56** |

Within-topic anchors **only** — a concept, its card, and both of its questions
always share one topic (no cross-topic `supports_question`-style links).

## Files

| Path | Role | Owner here |
|------|------|-----------|
| `scripts/build_question_bank.py` | authors/promotes the reworded MCQs; source of record | ✎ edited |
| `data/questions.json` | emitted bank (170 items) | ✎ regenerated |
| `data/paraphrase-test.json` | the instrument manifest (28 rows) | ✎ new |
| `scripts/eval_paraphrase.py` | the gap scorer + synthetic demo | ✎ new |
| `Makefile` (`eval-performance`) | runs the scorer | ✎ edited |
| `scripts/validate_data.py` | validates the manifest + new questions | ✎ edited |
| `scripts/eval_leakage.py` | proves pairs are genuinely reworded | ✎ edited |

Deliberately **not** touched (owned by a concurrent worker): the `anki-MCAT`
repo, `qt/aqt/mcat/performance_dialog.py`, `pylib/anki/mcat_perf.py`,
`data/application-practice.json`, and the shared docs `docs/DECISIONS.md`,
`docs/LOOSE-ENDS.md`, `docs/ERROR-DIAGNOSIS-SPEC.md`.

## Manifest schema (`data/paraphrase-test.json`)

Top-level object: `schema_version`, `description`, `trio`,
`session_order_default`, `gap_metric`, `notes`, and `concepts` (the rows).

Each row in `concepts`:

```json
{
  "topic_id": "bb_enzymes",
  "concept": "vmax_saturation",
  "card_ref": "enzymes_vmax_saturation",
  "card_front": "An enzyme reaches Vmax when its active sites are saturated with substrate.",
  "question_ids": ["q_dev_024", "q_ho_075"],
  "new_question_ids": ["q_ho_075"],
  "pair_type": "reused_authored",
  "session_order": "memory_first"
}
```

- `concept` — unique slug (the memorized idea).
- `card_ref` / `card_front` — the **backing-card link**. `card_front` is the
  de-clozed front of a real flashcard in `data/flashcards-dev.csv`, in the SAME
  topic; `validate_data.py` confirms the match, so the link is verifiable.
- `question_ids` — exactly two ids `[q_a, q_b]`, distinct, both within the row's
  topic, each used in at most one pair.
- `new_question_ids` — which of the pair were authored fresh for this instrument.
- `pair_type` — `reused_authored` (one existing + one fresh) or
  `authored_authored` (both fresh, both held_out).
- `session_order` — `memory_first` (flashcard recall first, then the questions),
  so a reveal never immediately precedes the matching question.

### Split discipline (leakage)

`q_b` (the **second** stem) is **always a freshly authored `held_out` probe**, so
a volunteer cannot have seen it in a dev performance session. `validate_data.py`
fails if any second stem is not `held_out`. `authored_authored` pairs put **both**
stems in `held_out`.

## Authoring log

30 new curated MCQs authored (ids `q_ho_061`–`q_ho_090`), all `held_out`, all
grounded in OpenStax (CC-BY) with full schema parity: stem, 4 choices, correct
index, `topic_id`, `cognitive_demand`, per-choice 3-axis `choice_diagnosis`
(content_gap misconception / trap enum / null on the correct choice), a non-empty
static `explanation`, and `source_name`/`source_url`/`source_location`.

| Topic | Anchor concepts | Reused existing | Newly authored (held_out) |
|-------|----------------:|----------------:|--------------------------:|
| `cp_acids_bases` | 10 | 9 | 11 (`q_ho_061`–`q_ho_071`) |
| `bb_enzymes` | 10 | 9 | 11 (`q_ho_072`–`q_ho_082`) |
| `cp_kinetics` | 8 | 8 | 8 (`q_ho_083`–`q_ho_090`) |
| **total** | **28** | **26** | **30** |

Notes on reuse and the flagged data issues:

- The existing bank was not built as paraphrase pairs, so most concepts had only
  **one** clean standalone question; the second stem was authored fresh.
- **Passage-set clones are not paraphrases.** The `bb_enzymes` synthesis block
  `q_syn_001`–`q_syn_004` share one `P_ENZYME` passage, so two of them are never
  paired with each other. Where a passage item is reused (`q_syn_002`,
  `q_syn_004` for enzymes; `q_syn_009` for acids; `q_syn_020` for kinetics), it
  is paired with a **fresh standalone** stem, never with a passage sibling — and
  the fresh standalone re-tests the idea in crisp, passage-free wording (e.g.
  `q_syn_004`'s Km/Keq idea is rewritten standalone as `q_ho_080`).
- `card_ref` links stay **within topic**, avoiding the cross-topic hazard (e.g. a
  `cp_kinetics` card pointing at a thermo question).

The card→question `supports_question` edge inside `build_flashcards.py` was left
untouched to avoid a parallel-write collision; the manifest's `card_ref` /
`card_front` is the authoritative backing-card link for this instrument and can
be reconciled into the deck CSV later.

## The gap metric

Per concept:

```
card_recall_rate    = fraction of successful flashcard recalls for the card
question_accuracy   = mean accuracy across the concept's two linked questions
paraphrase_gap      = card_recall_rate - question_accuracy
```

Aggregated as the mean per topic and overall. Interpretation:

- **gap ≈ 0** with high recall → question accuracy tracks recall; warn that
  performance may be **echoing memory**.
- **gap large & positive** → the student recalls the fact but cannot apply it in
  new words → performance is measuring **transfer**, not parroting.

## How to run

```bash
# validate the bank + the manifest (well-formed, within-trio, valid pairs,
# held_out second stem, card_front resolves to a real within-topic card)
py -3.12 scripts/validate_data.py

# prove pairs are genuinely reworded (not near-identical) + split leakage
py -3.12 scripts/eval_leakage.py

# the gap report (synthetic, deterministic demo when no real data is supplied)
make eval-performance
#   └─ equivalently: py -3.12 scripts/eval_paraphrase.py
```

`make eval-performance` prints a reproducible sample report: a per-concept table
(recall − q_acc = gap), a per-topic summary, and the aggregate paraphrase gap.
The demo signals are derived deterministically from the manifest (md5-seeded), so
the numbers are stable across runs and machines; they are clearly labelled
`synthetic demo`.

## Real-data path

When real study data exists, pass two JSON files (no AI, no network):

```bash
py -3.12 scripts/eval_paraphrase.py --recall recall.json --attempts attempts.json
```

**`recall.json`** — memory recall per concept, keyed by the manifest `concept`
slug (or its `card_ref`). Either a rate map or raw revlog-style events the scorer
aggregates:

```json
{ "vmax_saturation": 0.83, "active_site": 0.71 }
```
```json
[ { "concept": "vmax_saturation", "recalled": true },
  { "concept": "vmax_saturation", "recalled": false } ]
```

Source: the builder's own FSRS/revlog recalls (memory mode), reduced to a
per-card success rate over the evaluation window.

**`attempts.json`** — a performance-mode attempts export, keyed by `question_id`.
Either an accuracy map or raw attempts the scorer aggregates:

```json
{ "q_dev_024": 0.80, "q_ho_075": 0.50 }
```
```json
[ { "question_id": "q_ho_075", "correct": false },
  { "question_id": "q_ho_075", "correct": true } ]
```

Source: performance-mode sessions on the frozen `held_out` split (e.g. a friend
attempting the reworded probes). Report the small sample size honestly.

Concepts missing recall or attempt data are listed and excluded from the
aggregate rather than silently zero-filled.

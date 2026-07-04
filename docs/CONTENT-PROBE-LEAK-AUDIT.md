# Content re-check probe — answer-leak audit (2026-07-03)

Audit + fix of the **"Quick check — recall before the explanation"** probe that
fires on a science miss in performance mode. The probe is supposed to be a
**recall check**: show a prompt, hide the answer, reveal it only after the
student responds. Two probes were leaking the answer in the pre-reveal prompt.

## How a probe is rendered (schema + render contract)

The probe is resolved by `resolve_probe_target()` in
`anki-MCAT/pylib/anki/mcat_perf.py` and rendered by
`anki-MCAT/qt/aqt/mcat/performance_dialog.py` (`_start_probe`, `_on_probe_reveal`).
The probe descriptor has two fields:

| Field | Role | Rendered | Source |
|-------|------|----------|--------|
| `front` | **PROMPT** (recall cue) | shown immediately, pre-reveal | a backing flashcard front |
| `back`  | **REVEAL** (answer) | shown only after "Reveal answer" | card back, or the question's `explanation` in the map-fallback path |

`resolve_probe_target` resolves the `front`/`back` in this order:

1. **Real backing card** (`_card_probe_text`) — renders the actual collection
   card. A **Cloze** card renders with its blank (`[...]`) shown → a *proper*
   recall cue (no leak). `back` = the card's answer.
2. **Map-backed fallback** (`_probe_from_question_card_map`) — used when no
   collection card renders (the demo/loaded-bank path). Picks a front via
   `_pick_probe_front` (**prefers the first non-cloze front**, else `fronts[0]`)
   and **`_decloze_front`s it** (fills `{{c1::X}}` → `X`). `back` = the
   question's `explanation`.
3. **Generic fallback** — a topic-free "state the underlying rule…" prompt
   (does not leak). Used by the 30 held-out questions with no backing card.
4. **CARS / unmapped** → probe skipped.

**Where probe content lives (data repo):** the prompt (`front`) is the backing
flashcard's `text`, authored in `scripts/build_flashcards.py` (the source of
record) → generated into `data/flashcards-dev*.csv` → surfaced through the
generated `data/question-card-map.json` (`fronts[]`). The reveal (`back`, in the
fallback path) is the question's `explanation` in `data/questions.json`.
`questions.json` has **no** dedicated probe-prompt field — the ~110 `recall`
hits in it are the `cognitive_demand` tag, not a probe prompt.

## Two kinds of leak found

The screenshots (and the demo) exercise the **map-fallback** path. Auditing all
157 science questions' resolved fallback prompts:

| Class | Count | Cause | Fix owner |
|-------|-------|-------|-----------|
| No backing card → generic prompt | 30 | n/a (does not leak) | — |
| **Non-cloze (Basic) front states the answer** | **2** | **content** — the flashcard front itself contains the answer | **content (this repo) — DONE** |
| Other Basic fronts (clean recall questions) | 26 | n/a (proper "why/how/what" prompts) | — |
| **Cloze-only → prompt de-clozed** | **99** | **render** — `_decloze_front` fills the blank instead of showing it | **UI/engine worker (see below)** |

### (A) Content leak — fixed here (2 probes)

A **Basic** backing card whose front literally states the item's answer. These
leak in **every** render path (real-card *and* fallback), so they are genuine
content bugs. Fixed in `scripts/build_flashcards.py` (then regenerated the CSVs
+ map); the answer now lives on the card `back`, and the reveal `explanation`
already held it.

| id | topic | before (leaking prompt) | after (recall prompt) |
|----|-------|-------------------------|-----------------------|
| `q_dev_004` | `bb_enzymes` | *"Why compare reaction rates (not ΔG) to judge activation energy?"* — states the answer ("Compare their reaction rates.") | *"What is the best way to judge the relative activation energies of two reactions?"* |
| `q_dev_002` | `bb_citric_acid` | *"When ADP is high, why do metabolic pathways generally speed up?"* — asserts the answer ("increase the activity of specific enzymes") | *"When ADP levels rise, what happens to the activity of the cell's rate-limiting respiratory enzymes, and why?"* |

The MCQ stem, choices, `correct`, scoring, and `choice_diagnosis` were **not**
touched — only the probe prompt/reveal split.

### (B) Systemic render leak — route to the UI/engine worker (99 probes)

Every **cloze-only-backed** question leaks in the **map-fallback** path because
`_probe_from_question_card_map` calls `_decloze_front`, which **fills** the cloze
deletion (`{{c1::3:1}}` → `3:1`) instead of showing a blank. The **screenshot-1
genetics** probe is this class:

- `q_dev_030` / `q_ho_037` / `q_syn_013` fallback prompt (leaking):
  *"A monohybrid cross Aa × Aa gives a phenotypic ratio of 3:1 and a genotypic
  ratio of 1:2:1."* — the ratios are the answer.

This is **not** a per-item content bug: the same cloze card renders as a correct,
answer-hidden recall cue in the **real-card** path (`_card_probe_text` shows
`… phenotypic ratio of [...] and a genotypic ratio of [...]`). The defect is that
the fallback fills the blank rather than preserving it.

**Recommended render fix (in `mcat_perf.py`, owned by the UI/engine worker):**
in `_probe_from_question_card_map` (and the generic fallback), replace the cloze
deletion with a blank marker instead of de-clozing — mirror `_card_probe_text`.
e.g. `re.sub(r"\{\{c\d+::(.*?)\}\}", "[…]", front)` rather than
`_decloze_front(front)`. That makes all 99 cloze probes proper recall cues
(answer hidden) in the fallback too, matching the real-card path; the reveal
(`explanation`) already carries the answer. No `questions.json` change needed.

(Alternative content-only mitigation — authoring a non-cloze "recall question"
Basic card for each cloze-only question so `_pick_probe_front` selects it — was
**not** taken: it would add ~99 cards to the memory deck and shift the mastery
gate/card counts, i.e. change the memory-mode surface for a defect that belongs
in the render layer.)

## Verification

- `python scripts/build_flashcards.py` + `python scripts/build_question_card_map.py`
  regenerate the CSVs and `question-card-map.json` from the edited source.
- `python scripts/validate_data.py` → **OK**.
- Re-audit: the two Basic prompts no longer contain the answer; the cloze-only
  count is unchanged (99), confirming that class is untouched and pending the
  render fix.

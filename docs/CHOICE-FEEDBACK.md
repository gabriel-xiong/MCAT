# Per-choice feedback (`choice_feedback`)

Static, pre-seeded, source-grounded rationale for **every** choice of every
performance question. This is the no-AI product's per-choice explainer, the
AI-off fallback, and the baseline the AI "explain your miss" feature must beat.
No AI runs at runtime — the strings are baked into `data/questions.json` by the
builder.

## What it is

Each question carries a `choice_feedback` array aligned **1:1** with `choices`
(same length and order):

- **Correct choice** — a terse "why this is correct" line (begins `Correct —`).
- **Each distractor** — the *specific* reason that choice fails (begins
  `Incorrect —`): the named misconception, the execution error for a trap
  (e.g. "this inverts the area ratio"), or briefly why a near-miss is tempting
  but wrong.

This is separate from and additional to the single correct-answer
`explanation`. It is also distinct from `choice_diagnosis`: those content-axis
tags were used only as **hints** while authoring — the feedback states the real
reason, never a restatement of the choice, and it exists for the correct choice
and for CARS items too.

## Where it lives (source of truth)

- Authored in `scripts/build_question_bank.py` in the `CHOICE_FEEDBACK` dict,
  keyed by stable question id (mirrors the `EXPLANATIONS` pattern).
- `_attach_choice_feedback()` attaches it during the build and fails loudly on a
  missing id, a length mismatch, or a blank entry.
- Regenerate with `python scripts/build_question_bank.py` — never hand-edit
  `data/questions.json`.
- `data/questions.example.json` is hand-maintained and carries a well-formed
  example array to stay valid.

## Validation

`scripts/validate_data.py` (`_validate_choice_feedback`) requires, on every
question in `questions.json` and `questions.example.json`:

- `choice_feedback` is a list,
- its length equals the number of `choices`,
- every entry is a non-empty string.

Coverage: all ~170 questions (dev=65, held_out=105) carry a full-length,
all-non-empty array; the `Correct —` line lands on the stored correct index for
every item. Priority eval trio (`cp_acids_bases`, `bb_enzymes`, `cp_kinetics`)
authored at the highest specificity.

## Deferred wiring (later coordinated pass — NOT done here)

This pass produces the **data + validator only**. Still to do, in the storage/UI
pass:

1. Add a `choice_feedback` storage column in `pylib/anki/mcat_perf.py`,
   mirroring the existing `explanation` / `choice_diagnosis` migration, and
   round-trip it (persist + reload).
2. In `qt/aqt/mcat/performance_dialog.py`, display the **chosen distractor's**
   `choice_feedback` line after the student answers (alongside/atop the
   correct-answer `explanation`).

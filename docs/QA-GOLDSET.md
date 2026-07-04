# QA Gold Set — AI Follow-up Q&A Evaluation

This document describes `data/qa-goldset.json` and its validation sheet
`data/qa-goldset-validation.TEMPLATE.json`: the draft ground truth for evaluating
the MCAT Speedrun **AI follow-up Q&A** feature.

## What the feature under test does

After a student misses a performance-mode question and sees the static feedback, the
AI feature answers **open-ended follow-up questions** such as:

- "Why doesn't C work?"
- "Where does the 8.25 come from?"
- "What's the difference between competitive and allosteric inhibition here?"
- "Why n=2 and not n=1?"

We evaluate the AI's answers for **accuracy**, **wrong-answer rate**, and **grounding**,
against a **baseline** (the static per-choice feedback / keyword retrieval).

## Why this gold set breaks circularity (read this first)

The feature under test uses **OpenAI**. If the ground truth were also authored by
OpenAI, the evaluation would be circular — the judge and the judged would share the
same blind spots and phrasing biases, inflating measured accuracy.

**This gold set was authored by a non-OpenAI model (Anthropic Claude), on purpose, to
break that circularity.** It is *draft* ground truth. A **human validates every
`fact_atom` before the gold set is used** (see the validation workflow below). The
combination — non-OpenAI drafting + human validation + fact-atom scoring — gives an
independent yardstick the OpenAI feature cannot trivially game.

## Method

1. **Non-OpenAI draft.** A non-OpenAI model read each held-out trio question (stem,
   choices, correct answer, `explanation`, `choice_feedback`, `choice_diagnosis`) and
   hand-authored, per follow-up, a short list of **`fact_atoms`**: checkable, atomic
   facts the correct answer must contain.
2. **Grounded, not invented.** Every atom is **derivable from the question's own
   curated content**, with OpenStax as the upstream authority. See the honest caveat
   below. Each item records `grounding_source` naming the exact field(s) it draws on.
3. **Human validation.** A human approves / edits / rejects each atom via the
   validation template. Only then is an item marked `validated: true`.
4. **Cross-model, fact-atom scoring.** Downstream, the AI feature's answer to each
   `followup_question` is scored against the validated atoms (see scoring below). A
   different model family authored the key than the one being graded.

## Honest grounding caveat

The `fact_atoms` are **"consistent with / derivable from" the curated source
material — not quoted verbatim.** They restate and, in the differentiation bucket,
*combine* multiple curated statements (e.g., applying Henderson–Hasselbalch, or reading
a rate from an initial-rates table). This is intentional: the follow-ups are open-ended,
so the answers must be *entailed by* the curated content rather than copied from a
single sentence. Where an atom depends on a specific number stated in the passage
(e.g., `pKa = 4.74`) or on multi-step arithmetic, it is listed under
`flagged_for_attention` in the validation template for extra human scrutiny.

## Two-bucket composition

| Bucket | What it tests | Why included | Count |
|---|---|---|---|
| **parity** | "Why is choice X wrong?" — the static per-choice `choice_feedback` already answers this | Shows the baseline *does* perform here; the AI shouldn't lose to it on easy cases | 9 |
| **differentiation** | Open-ended: multi-step "where does this number come from?", conceptual contrasts, "what if X changed?", "why this formula/value?" — structurally **beyond** a fixed per-choice blurb or keyword retrieval | Where the AI's marginal value is proven | 51 |

The set is deliberately weighted (~85%) toward differentiation. Within it, the
**hard-differentiation** subset `g031`–`g060` (30 items) is authored so a static
`explanation` + `choice_feedback` dump structurally cannot answer it — the needed
facts are absent from the anchor question's own curated content (cross-question /
counterfactual / synthesis / transfer), yet every atom remains traceable to the
named OpenStax source.

## Counts

- **Total: 60 gold items.** All 60 (`g001`–`g060`) are human-validated (`g001`–`g030` on 2026-07-02; `g031`–`g060` on 2026-07-03).
- By topic: `cp_acids_bases` 24, `bb_enzymes` 20, `cp_kinetics` 16.
- By bucket: parity 9, differentiation 51 (of which `g031`–`g060` are the 30 hard-differentiation items).
- Source: **held-out (frozen eval) split only** of the three trio topics in
  `data/questions.json`. Read-only; the question bank is not modified.

## Gold item schema

Each item in `data/qa-goldset.json` under `items[]`:

- `id` — gold item id (`g001`…`g060`).
- `topic_id` — one of the trio topics.
- `question_id` — a held-out trio question in `data/questions.json`.
- `chosen_distractor_index` — 0-based index of the wrong choice the follow-up is about,
  or `null` if the follow-up isn't tied to one specific distractor.
- `followup_question` — the student's natural-language question.
- `bucket` — `"parity"` or `"differentiation"`.
- `fact_atoms` — **the objective scoring key**: short, atomic, checkable required facts.
- `must_not_say` — (optional) contradicting/wrong claims that count as a wrong answer.
- `grounding_source` — which curated field(s) / OpenStax concept the atoms derive from.
- `draft_reference_answer` — 1–3 sentence reference for human context only (atoms are
  the real key).
- `validated` — `false` until a human flips it.

## How the downstream eval scores

For each gold item, feed `followup_question` (with its question context) to the AI
feature (and, as baseline, the static per-choice feedback), then score the response.
**Scoring is partial-credit, not all-or-nothing** — an earlier all-atom-required rule
was too rigid (an answer that nailed 3 of 4 atoms scored the same as one that missed
everything). There are two scorers:

### Headline metric — partial credit

- **Accuracy = mean atom coverage.** The fraction of `fact_atoms` an answer conveys,
  averaged across items. This is the headline number.
- **Pass rate.** Per-item pass/fail at a configurable `--pass-threshold` (default
  **0.75**): an item passes if coverage ≥ threshold **and** it asserts no `must_not_say`
  claim.
- **`full_correct` (strict, secondary).** All validated atoms covered **and** no
  forbidden claim. Kept for continuity, but no longer the headline.
- **Wrong-answer = contradiction.** Asserting any `must_not_say` claim counts as a wrong
  answer regardless of coverage; tracked separately (`any_must_not_say_rate`).
- **Grounding.** The answer is "grounded" if its facts trace to the item's
  `grounding_source` (curated `explanation` / `choice_feedback` / `choice_diagnosis`,
  ultimately OpenStax). Ungrounded answers are blocked upstream by `serve_followup`.

### Two scorers

1. **Token-overlap (default baseline, offline, no LLM).** Content-token overlap +
   numeric agreement per atom; `must_not_say` matched by phrase/overlap. It is
   deliberately kept as the reproducible baseline and was hardened in two ways:
   - **Negation-aware `must_not_say`:** a forbidden phrase is *not* flagged when a
     negation cue (`not` / `isn't` / `rather than` / `no` / `never` / `instead` …) sits
     in the window around where the claim's words land — so "12.0 is the pOH, **not** the
     pH" no longer reads as asserting "the pH is 12.0". (Cues are scanned on a
     stopword-preserving stream, since `not`/`no`/`than` are themselves stopwords.)
   - **Numeric robustness:** numbers are canonicalized preserving **sign and exponent**
     (`10^-2` → `1e-2`, `1.0x10^-3` → `1e-3`), so an atom like `pH = -log(10^-2) = 2.0`
     is not flattened to bare digits `{10, 2}` and a right vs. wrong exponent no longer
     look identical.

   Token overlap still cannot resolve claims that are *semantically opposite but share
   vocabulary* (e.g. "activation energy **equals** ΔG" vs. an answer distinguishing
   them). That residual rigidity is precisely what motivates the judge.

2. **Cross-model LLM judge (`--judge`).** See below.

### Cross-model LLM-as-judge (`--judge`)

The feature under test generates answers with **OpenAI**. To grade with a model's
understanding of paraphrase and negation *without reintroducing circularity*, the judge
**must be a different model family** — by default **Anthropic Claude**
(`MCAT_JUDGE_PROVIDER` / `MCAT_JUDGE_MODEL`, default `anthropic` /
`claude-3-5-sonnet-latest`; key `MCAT_JUDGE_API_KEY` or `ANTHROPIC_API_KEY`).

- **Answer generator = OpenAI** (`MCAT_LLM_PROVIDER`). **Judge = Claude.** The eval
  **refuses** to run if the judge family equals the answer-generator family (prints a
  circularity note and falls back to token overlap).
- The judge does **not** author or alter the rubric — the **human-validated `fact_atoms`
  remain the rubric**. The judge only maps an answer onto those fixed atoms, returning
  `{atoms_covered: [bool…], must_not_say_violated: [bool…], coverage_fraction: float,
  notes: str}`. It is instructed to accept **paraphrase** and to treat a **correct
  negation** of a `must_not_say` phrase as *not* a violation.
- If no judge key is configured, the eval prints a clear message and **falls back to the
  token-overlap scorer**.

**Why cross-model breaks circularity.** OpenAI wrote the answer; a *different* family
(Claude) grades it; and the yardstick (`fact_atoms`) was itself drafted by a non-OpenAI
model and **human-validated**. No single model both writes and grades against a rubric
it authored, so shared blind spots / phrasing biases cannot inflate the score. (The gold
set's own `fact_atoms` were likewise authored by a non-OpenAI model on purpose — see
"Why this gold set breaks circularity" above.)

Expected pattern: baseline and AI both do well on the **parity** bucket; the AI should
open a clear margin on the **differentiation** bucket, where a fixed per-choice blurb or
keyword retrieval cannot produce the multi-step or contrastive answer.

## Human validation workflow

1. Open `data/qa-goldset.json` and `data/qa-goldset-validation.TEMPLATE.json` side by
   side (ids match, e.g. `g001`).
2. Start with `flagged_for_attention` in the template — these atoms (specific passage
   numbers and multi-step arithmetic) most need a careful human check.
3. For each gold item, open its `question_id` in `data/questions.json` and read the
   stem, choices, correct answer, `explanation`, and `choice_feedback`.
4. For each `fact_atom`, set `atom_status` to `approve`, `edit` (put the corrected
   wording in `atom_fix`), or `reject`. Optionally review `must_not_say`.
5. Set the item's `item_decision` to `approved` once all its atoms are approve/edit,
   then flip that item's `validated` to `true` in `qa-goldset.json`.
6. (Recommended) Save the filled sheet as `data/qa-goldset-validation.json` (drop
   `.TEMPLATE`) so the template stays pristine.

## Provenance / integrity

- **Author:** non-OpenAI model (Anthropic Claude), by design, to avoid evaluating an
  OpenAI feature with an OpenAI-authored key.
- **Inputs:** read-only from `data/questions.json` (held-out trio questions only).
- **Status:** all items `validated: false` until a human validates. Do not use for
  reported metrics before validation.

## Running the eval

`scripts/ai_eval_qa.py` batch-scores follow-up answers against `fact_atoms` and
`must_not_say`, reporting mean atom coverage (headline), pass rate, wrong-answer hits,
and parity vs differentiation buckets.

| Command | Answers | Scorer | Keys |
|---|---|---|---|
| `make eval-qa-goldset` | `draft_reference_answer` (dry-run) | token overlap | none |
| `py … --dry-run --all --judge-mock` | draft (dry-run) | offline mock judge (plumbing test) | none |
| `make eval-qa-goldset-live` | live OpenAI | token overlap | `OPENAI_API_KEY` |
| `make eval-qa-goldset-judge` | live OpenAI | **cross-model Claude judge** | `OPENAI_API_KEY` + `ANTHROPIC_API_KEY` |

The full cross-model run (OpenAI answers, Claude judges) is:

```
py -3.12 scripts/ai_eval_qa.py --live --all --judge
```

With `.env` set to:

```
MCAT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
# optional overrides (defaults shown):
# MCAT_JUDGE_PROVIDER=anthropic
# MCAT_JUDGE_MODEL=claude-3-5-sonnet-latest
```

Other flags: `--pass-threshold F` (default 0.75), `--item g007`, `--limit N`, `--all`
(include draft items before validation), `--verbose`. If `--judge` is set but no judge
key is present, the eval prints a note and falls back to token overlap. `--judge-mock`
exercises the judge parse/aggregation plumbing fully offline (no key, no network).

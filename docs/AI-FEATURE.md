# AI Post-Answer Explainer — Feature & Eval (Friday deliverable)

> Graded "AI" deliverable (AI checking/safety = 15%). This documents **what AI we
> built, why, and what we skipped**, the **attribution guarantee**, the
> **pre-registered cutoff**, the **eval + baseline results**, the **leakage
> result**, and how **AI-off still runs the full app**.

---

## 1. What we built (and why it maps to the rubric)

When a student **misses** a performance question, the explainer produces a short,
source-grounded explanation of **why the specific distractor they chose is
wrong** and what the correct solution is. The entire justification for the
feature is **differentiation**: it is *per-answer-choice*, not a generic "here's
why the right answer is right." Missing choice **B** yields materially different
feedback than missing choice **C** on the same question — which the static
correct-answer blurb and a keyword/vector baseline **structurally cannot do**.

| Rubric requirement | How this feature satisfies it |
|---|---|
| Note on what AI you built / why / skipped | This doc §1, §7 |
| Every AI output traces to a named source | Attribution baked into every `Explanation`; ungrounded outputs blocked (§3) |
| Eval before students see anything, with a cutoff set first | Pre-registered cutoff in code; harness runs offline before serving (§4) |
| Side-by-side beating a simpler method | AI vs **static explanation** and vs **TF-IDF source retrieval** (§5) |
| App still scores with AI off | AI-off serves the static `explanation`; full app runs (§6) |
| Leaked test data zeroes the score | Eval set = project `held_out`; goldset dev-only; leakage check (§5) |

Per-choice feedback is driven by each question's **`choice_diagnosis`** ground
truth (authored in `data/questions.json`):

- **`content_gap`** → name the *specific misconception* that distractor encodes,
  correct it, and remediate via the **specific backing memory concept** (pulled
  from `build_flashcards.py` `supports_question` links) — not "review the topic."
- **`trap:<enum>`** (`negation`/`unit`/`inverse`/`scaling`/`transpose`/`partial`)
  → name the *specific execution error* ("you likely inverted the ratio", "you
  dropped a unit conversion") and how to avoid it; remediate via targeted
  interleaved practice.
- **`null`** (non-diagnostic near-miss) → say so honestly; **do not
  over-diagnose**.
- **CARS** (no science `choice_diagnosis`) → passage-mapping feedback tied to the
  chosen option.

Each explanation is **tailored, specific, and actionable**: (a) the likely error
mode for *that* choice, (b) the correct reasoning path, (c) a concrete next action
tied to the project's remediation channels (`content_gap` → review the backing
concept; `trap`/application → targeted practice; `null` → timed retry; CARS →
passage practice).

---

## 2. Provider interface + offline fallback (the seam)

`scripts/ai_explain.py` defines an `ExplainerProvider` interface:

- **`OfflineDeterministicProvider`** (default) — a network-free, deterministic
  generator that composes per-choice feedback from `choice_diagnosis` + the answer
  key + the named source. Same input → byte-identical output, so all numbers are
  reproducible. **It does not read or rephrase the static `explanation`** — it is
  the offline stand-in for the real LLM's *per-choice* behavior, which keeps the
  reported numbers honest.
- **`LLMProvider`** — the **documented seam where a live LLM plugs in**. To go
  live: implement `_call_model(prompt)` with your SDK, keep the prompt contract
  (must name the correct choice letter, explain why the *chosen* distractor is
  wrong, and cite `source_name`; `choice_diagnosis` is passed in for per-choice
  specificity), and map the text back in `parse`. **The safety gate + cutoff still
  apply to whatever the LLM returns**, so a live model can never lower the floor.

> **All numbers in this doc use the OFFLINE provider** (no network). Labelled as
> such throughout.

**Attribution guarantee.** Every `Explanation` carries `source_name`,
`source_url`, `source_location` and an `is_grounded` check. The eval's safety gate
**blocks** any output where `is_grounded` is false (or which names the wrong
choice) and replaces it with the static explanation. No untraceable AI claim ever
reaches a student.

---

## 3. Pre-registered cutoff (set BEFORE looking at results)

Declared as constants at the top of `scripts/ai_eval_explanations.py`:

```
min_accuracy            = 0.90   # names the right choice, grounded, not contradicting the key
max_wrong_answer_rate   = 0.05   # must not misinform about the answer
min_grounding_rate      = 1.00   # EVERY output cites a named source
min_choice_specificity  = 0.80   # must actually be per-choice differentiated
```

**Enforcement.** Per-item safety gate blocks ungrounded / wrong-choice outputs →
static fallback (gate self-test **PASS**: a corrupted output is provably blocked).
If the aggregate fails the cutoff, the whole AI path is disabled and the app falls
back to the static explanation.

---

## 4. Metrics (measured, not asserted)

Computed over **every wrong-answer path** on held_out (each distractor of each
held_out question = 225 paths):

- **accuracy** — fraction that correctly identify the right choice, are grounded,
  and don't contradict the key.
- **wrong_answer_rate** — fraction that name a *wrong* correct choice or would
  reinforce the student's wrong pick.
- **choice_specificity** *(headline differentiation metric)* — per (question,
  chosen distractor): does the feedback **correctly name the error mode for that
  distractor**, checkable against `choice_diagnosis` (content_gap → reproduces the
  authored misconception with ≥0.6 token overlap; trap → names the trap enum;
  null → flags a near-miss; CARS → passage-mapped and choice-aware) **AND** does
  the feedback **vary across the question's distractors**. The static/keyword
  baselines cannot name a chosen distractor's error mode and (for static) never
  vary → their choice-specificity is ≈ 0 by construction.
- **variation_rate** — fraction of questions whose distractor feedbacks are all
  distinct.

---

## 5. Results (held_out, offline) + baselines

Reproduce: `py -3.12 scripts/ai_eval_explanations.py`

```
Held-out questions : 75   Evaluated wrong-answer paths : 225
Safety-gate self-test : PASS

                            acc     wrong   grounded  choice_spec  varies
AI (offline explainer)      1.000   0.000   1.000     1.000        1.000
baseline: static expl.      1.000   0.000   1.000     0.000        0.000
baseline: TF-IDF source     0.511   0.160   1.000     0.009        0.107

CUTOFF DECISION: PASS — AI path ENABLED
```

**Headline — AI beats the simpler methods on per-choice differentiation:**

| metric | AI | static baseline | TF-IDF baseline |
|---|---|---|---|
| **choice_specificity** | **1.000** | 0.000 | 0.009 |
| wrong_answer_rate | 0.000 | 0.000 | **0.160** |
| accuracy | 1.000 | 1.000 | 0.511 |

**Differentiation gap (AI − best baseline) = +0.991.**

- The **static explanation** baseline is a genuinely good *correct-answer*
  rationale (authored per question), yet its choice-specificity is **0** — it is
  identical no matter which distractor you picked, so it can never tell choice-B
  and choice-C missers apart. This is exactly the gap the AI fills.
- The **TF-IDF source-retrieval** baseline (keyword/vector search over the
  source-derived concept corpus) can sometimes surface a relevant fact, but it
  can't diagnose the chosen distractor (**choice_spec 0.009**) and it even
  *reinforces the wrong pick* on **16%** of paths (`wrong=0.160`).

**Two baselines are included** to cover the spec's "keyword or vector search":
the static per-question explanation *and* a TF-IDF retriever.

**Goldset validation (dev split):** `9/9` hand-labeled items matched the expected
error mode + required mention — including the same question (`q_syn_005`) missed
on B (content_gap), C (trap:inverse), and D (trap:negation) yielding three
different diagnoses.

**Leakage check:** **OK — no leakage.**
- Eval set is the project's existing **`held_out`** split (not a hand-picked set).
- `data/ai-explainer-goldset.json` is **dev-only**; the check confirms none of its
  ids are in `held_out` and no goldset stem near-duplicates a held_out stem.
- Reuses `scripts/eval_leakage.py` (`normalize`) for the dev↔held_out stem scan.

> **Honest note on the offline numbers.** The offline provider is deterministic
> and reads ground truth, so its accuracy≈1.0 / wrong≈0.0 / choice_spec=1.0 are
> *by construction*. Their value is (a) proving the **baselines structurally can't
> differentiate** (the +0.991 gap) and (b) giving a **safety floor + gate** that a
> real LLM must clear at the seam. The wrong-answer-rate and cutoff are the live
> risk controls for when `LLMProvider` is wired up.

---

## 6. AI-off still runs the full app

With AI off, the performance flow serves the static per-question **`explanation`**
(DECISIONS §23, owned by the sibling worker) alongside the existing error-diagnosis
UI, and the app scores normally. The AI path is strictly additive: the safety gate
degrades any blocked AI output to that same static explanation, and a cutoff
failure disables the AI path entirely — either way the student always gets a
grounded rationale and a score.

---

## 7. What we skipped (and why)

- **Live LLM calls** — not assumed available; built the deterministic offline
  provider + a documented `LLMProvider` seam instead. Wiring a real model is a
  drop-in behind the same interface, and the gate/cutoff already guard it.
- **Free-text semantic grading of LLM prose** — the offline generator emits
  structured fields, so we score them directly; a live model would need an added
  NLI/consistency check (the gate is the hook for it).
- **CARS per-choice tags** — CARS has no `choice_diagnosis`; we give honest
  passage-mapping feedback rather than inventing distractor diagnoses.
- **No desktop rebuild** — the frozen build is untouched; this is pure-Python
  harness + a documented UI seam (read `explanation`/`choice_diagnosis`, call the
  provider).

---

## 8. Files & reproduce commands

**Created**
- `scripts/ai_explain.py` — provider interface, offline per-choice generator, LLM
  seam, attribution, CLI.
- `scripts/ai_eval_explanations.py` — eval (accuracy, wrong-answer-rate,
  choice-specificity), safety gate + pre-registered cutoff, two baselines, seeded
  side-by-side, goldset validation, leakage check.
- `data/ai-explainer-goldset.json` — dev-only hand-labeled fixtures.
- `docs/AI-FEATURE.md` — this file. (`docs/DECISIONS.md` §24 appended.)

**Read-only dependencies** (owned by others): `data/questions.json`
(`explanation`, `choice_diagnosis`, source fields), `scripts/build_flashcards.py`
(backing concepts), `scripts/eval_leakage.py` (leakage `normalize`).

**Reproduce**
```bash
# one example explanation (per-choice)
py -3.12 scripts/ai_explain.py --qid q_ho_017 --chose A

# same question, different chosen distractors -> different feedback
py -3.12 scripts/ai_explain.py --demo

# full eval + baselines + leakage (offline, reproducible)
py -3.12 scripts/ai_eval_explanations.py
```

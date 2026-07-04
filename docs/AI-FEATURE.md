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
- **`LLMProvider`** — the **live-LLM seam, now wired to a real, provider-agnostic
  backend** (OpenAI or Anthropic). It is selected purely by environment config
  (see §9), builds a `call_model(prompt) -> str` callable with **lazy SDK
  imports**, sends the prompt contract (name the correct choice letter, explain
  why the *chosen* distractor is wrong — informed by the passed `choice_diagnosis`
  — give the correct solution, stay tied to `source_name`), and `parse`s the
  model's **structured JSON** back into an `Explanation`. The question's own
  `source_*` fields are attached for attribution, and the model's asserted correct
  letter is preserved so the gate can catch a wrong-answer output. **The safety
  gate + cutoff still run in front of whatever the LLM returns**, so a live model
  can never lower the floor.

> **Offline vs live.** The default provider is `OfflineDeterministicProvider`
> (no network, reproducible). The numbers in §5 are from that offline provider
> and are labelled as such — they are *by construction* (see the honest note).
> **Live-model numbers are produced by running against a real key** (§9); the
> real `openai:gpt-4o-mini` results are now in §10.

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
held_out question — currently **105 held_out Q × 3 distractors = 315 paths**):

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

Reproduce: `py -3.12 scripts/ai_eval_explanations.py` (writes the machine-readable
artifact `docs/artifacts/ai-explainer-eval.summary.json` + `.baselines.csv`).

```
Held-out questions : 105   Evaluated wrong-answer paths : 315
Safety-gate self-test : PASS

                            acc     wrong   grounded  choice_spec  varies
AI (offline explainer)      1.000   0.000   1.000     1.000        1.000
baseline: static expl.      1.000   0.000   1.000     0.000        0.000
baseline: TF-IDF source     0.476   0.210   1.000     0.010        0.133

CUTOFF DECISION: PASS — AI path ENABLED
```

**Headline — AI beats the simpler methods on per-choice differentiation:**

| metric | AI | static baseline | TF-IDF baseline |
|---|---|---|---|
| **choice_specificity** | **1.000** | 0.000 | 0.010 |
| wrong_answer_rate | 0.000 | 0.000 | **0.210** |
| accuracy | 1.000 | 1.000 | 0.476 |

**Differentiation gap (AI − best baseline) = +0.990.**

**Machine-readable artifact.** The full run (per-method metrics, the
pre-registered cutoff decision, source-traceability coverage, leakage, goldset,
and gate self-test) is written to
[`docs/artifacts/ai-explainer-eval.summary.json`](artifacts/ai-explainer-eval.summary.json)
and a flat [`docs/artifacts/ai-explainer-eval.baselines.csv`](artifacts/ai-explainer-eval.baselines.csv)
every run — mirroring the memory-calibration / study-feature artifacts. Numbers
above are copied from that artifact (offline provider, so labelled
`numbers_are: offline_deterministic_by_construction`).

**Source traceability on held_out (spec: "every AI output traces to a named
source").** Measured by the harness over all 105 held_out questions:

| field | coverage | note |
|---|---|---|
| `source_name` (named source) | **105/105 = 100%** | the hard grounding rule — the safety gate blocks any output with an empty `source_name` |
| `source_location` (page/§) | 105/105 = 100% | every item is locatable to a page/section |
| `source_url` | 98/105 = 93.3% | the 7 without a URL (`q_ho_053`–`q_ho_060`) are the CARS passage items, which are named + located but have no external OpenStax URL |
| fully grounded (`name` + `url`/`loc`) | **105/105 = 100%** | every served explanation is attributable |

- The **static explanation** baseline is a genuinely good *correct-answer*
  rationale (authored per question), yet its choice-specificity is **0** — it is
  identical no matter which distractor you picked, so it can never tell choice-B
  and choice-C missers apart. This is exactly the gap the AI fills.
- The **TF-IDF source-retrieval** baseline (keyword/vector search over the
  source-derived concept corpus) can sometimes surface a relevant fact, but it
  can't diagnose the chosen distractor (**choice_spec 0.010**) and it even
  *reinforces the wrong pick* on **~20%** of paths (`wrong=0.203`).

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
> differentiate** (the +0.990 gap) and (b) giving a **safety floor + gate** that a
> real LLM must clear at the seam. The wrong-answer-rate and cutoff are the live
> risk controls now that `LLMProvider` **is** wired up (§9). Real, non-by-
> construction numbers from `--provider live` (`openai:gpt-4o-mini`) are in §10:
> the live model clears the same cutoff (choice_specificity **0.860**, gap
> **+0.851**) with 0 gate blocks and 0 errors.

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

- **Live LLM calls are now wired** (OpenAI + Anthropic) behind the same
  `LLMProvider` seam, selected by env config (§9). They are **optional**: the
  SDKs are lazy-imported, the offline provider stays the default, and AI-off
  still serves the static explanation, so nothing breaks without a key.
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

**Created / updated**
- `scripts/ai_explain.py` — provider interface, offline per-choice generator,
  **live `LLMProvider` (OpenAI/Anthropic, env-driven, lazy imports)**, canonical
  `safety_block` gate, `serve_explanation` (gate + static fallback), attribution,
  CLI (`--live`).
- `scripts/ai_eval_explanations.py` — eval (accuracy, wrong-answer-rate,
  choice-specificity), safety gate + pre-registered cutoff, two baselines, seeded
  side-by-side, goldset validation, leakage check; **`--provider offline|live`**.
- `scripts/test_ai_explain_live.py` — mocked-LLM tests (no network) for provider
  dispatch, parse, gate, AI-off fallback, and eval-against-live.
- `requirements.txt` — **optional** `openai` / `anthropic` SDKs (lazy-imported).
- `data/ai-explainer-goldset.json` — dev-only hand-labeled fixtures.
- `docs/AI-FEATURE.md` — this file. (`docs/DECISIONS.md` §24 / new dated note.)

**Read-only dependencies** (owned by others): `data/questions.json`
(`explanation`, `choice_diagnosis`, source fields), `scripts/build_flashcards.py`
(backing concepts), `scripts/eval_leakage.py` (leakage `normalize`).

**Reproduce (offline, no key, reproducible)**
```bash
# one example explanation (per-choice)
py -3.12 scripts/ai_explain.py --qid q_ho_017 --chose A

# same question, different chosen distractors -> different feedback
py -3.12 scripts/ai_explain.py --demo

# full eval + baselines + leakage (offline, reproducible)
py -3.12 scripts/ai_eval_explanations.py

# mocked-LLM tests (no network)
py -3.12 -m unittest scripts.test_ai_explain_live -v
```

---

## 9. Live provider — env config & run commands

The `LLMProvider` seam is now backed by a real, **provider-agnostic** client
selected entirely by environment variables. SDKs are **lazy-imported**, so the
module, the offline eval, and AI-off all work whether or not the SDKs are
installed.

**Environment contract**

| Variable | Meaning |
|---|---|
| `MCAT_LLM_PROVIDER` | `openai` or `anthropic`. **Unset → AI OFF** (static fallback). |
| `MCAT_LLM_MODEL` | Model id (optional). Defaults: `gpt-4o-mini` / `claude-3-5-sonnet-latest`. |
| `MCAT_LLM_API_KEY` | Generic key (takes precedence), **or** the provider-standard var below. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Provider-standard key var. |

**Secrets handling (strict).** The key is read **only** from the environment
(`os.environ`) inside `ai_explain.py`; it is **never** hardcoded, printed, or
logged. Supply it via a **gitignored `.env`** (see `.env.example`; `.env` and
`.env.*` are gitignored) or by exporting it in your shell. Never commit a real
key. `pip install -r requirements.txt` adds the optional SDKs.

**Install the optional SDKs**
```bash
pip install -r requirements.txt        # openai + anthropic (optional)
```

**Run the LIVE held_out eval (produces real, non-by-construction numbers)**
```bash
# Git Bash on Windows — set env for this shell only (key never printed):
export MCAT_LLM_PROVIDER=openai            # or: anthropic
export MCAT_LLM_MODEL=gpt-4o-mini          # or your chosen model id
export OPENAI_API_KEY=...                  # paste your key (or ANTHROPIC_API_KEY / MCAT_LLM_API_KEY)

# real eval on held_out (gated; falls back to static on any failure):
py -3.12 scripts/ai_eval_explanations.py --provider live
#   make eval-ai-live

# single live example (gated serving path):
py -3.12 scripts/ai_explain.py --qid q_ho_017 --chose A --live
```

Prefer not to export in the shell? Put the same lines (without `export`) in a
local **`.env`** (gitignored) and load it before running, e.g.
`set -a; source .env; set +a` in Git Bash.

**Cost / scale note.** The live eval issues **one model call per wrong-answer
path** = **held_out questions × 3 distractors** (currently **105 × 3 = 315
calls**) per run, at `temperature=0`, ~1 short JSON response each. Multiply by
your model's per-call price to estimate cost; there is no caching layer, so each
run re-issues all 315 calls. Use a cheaper/faster model for iteration.

---

## 10. Live-model results (real LLM run)

> **Run.** Executed against a real key via `py -3.12 scripts/ai_eval_explanations.py
> --provider live` (`make eval-ai-live`). These are **live-measured**, not
> by-construction: every one of the 315 wrong-answer paths issued a real model
> call at `temperature=0`, then passed through the same safety gate + pre-registered
> cutoff (§3). Machine-readable evidence:
> [`docs/artifacts/ai-explainer-eval-live.summary.json`](artifacts/ai-explainer-eval-live.summary.json)
> + [`docs/artifacts/ai-explainer-eval-live.baselines.csv`](artifacts/ai-explainer-eval-live.baselines.csv)
> (`provider_mode: live`, `numbers_are: live_measured`).

| metric | AI (live) | static baseline | TF-IDF baseline |
|---|---|---|---|
| accuracy | **1.000** | 1.000 | 0.476 |
| wrong_answer_rate | **0.000** | 0.000 | 0.210 |
| grounding_rate | **1.000** | 1.000 | 1.000 |
| choice_specificity | **0.860** | 0.000 | 0.010 |
| variation_rate | 0.962 | 0.000 | 0.133 |
| outputs blocked → static | 0 / 315 | — | — |
| provider errors → static | 0 / 315 | — | — |

**Headline (live) — AI beats both simpler baselines on per-choice
differentiation:** choice_specificity **0.860** vs static **0.000** vs TF-IDF
**0.010** → **differentiation gap (AI − best baseline) = +0.851**. The live model
also stayed grounded (1.000) and never named a wrong choice (wrong_answer_rate
0.000), so it does **not** reinforce a student's wrong pick — unlike the TF-IDF
baseline (0.210).

Provider/model used: **openai : gpt-4o-mini** · Date: **2026-07-04 (UTC)** ·
Held_out questions: **105** · Held_out paths: **315** · Calls issued: **315**
(0 blocked by gate → static, 0 provider errors) ·
**CUTOFF decision: PASS — AI path ENABLED** (accuracy ≥ 0.90, wrong ≤ 0.05,
grounding = 1.00, choice_specificity ≥ 0.80 all cleared).

> **Live vs offline.** The offline §5 numbers are deterministic and *by
> construction* (choice_spec 1.000); the live run above is the honest,
> non-by-construction measurement. The live choice_specificity (0.860) is lower
> than the offline 1.000 — expected, since the live model must independently
> reproduce each authored misconception's key terms (≥0.6 token overlap) rather
> than emit them verbatim — yet it still clears the pre-registered 0.80 floor and
> beats both baselines by a wide margin, all with zero gate blocks and zero
> errors on this run.

---

## 11. Second AI feature — follow-up Q&A ("Ask more") is first-class

Beyond the per-choice explainer above, the **opt-in post-miss follow-up Q&A** is a
first-class AI feature in its own right: after a miss a student can ask an
open-ended question ("what if I doubled both concentrations?") and get a
**source-grounded** answer (`scripts/ai_qa.py`; ungrounded answers are dropped, so
AI-off simply shows the static explanation). It has its **own** human-validated gold
set (`data/qa-goldset.json`, 60 items across the acids/bases · enzymes · kinetics
trio — 9 parity / 51 differentiation, incl. 30 hard cross-question/counterfactual/synthesis items g031–g060), its
own **committed ship gate** in `scripts/ai_eval_qa.py`
(`GATE_MIN_ATOM_COVERAGE = 0.60` accuracy floor on the token scorer;
`GATE_MAX_MUST_NOT_SAY_RATE = 0.10` wrong-answer ceiling measured by the
cross-model semantic judge — the token must_not_say check over-flags via negation
and is shown only for transparency), and a live-answer proof in
`docs/QA-BASELINE-COMPARISON.md`. Crucially, this feature answers the "does AI beat
a simpler method?" question where the explainer's *differentiation* argument is
strongest: a static explanation dump or keyword retrieval **structurally cannot**
answer a synthesis/counterfactual follow-up. Under the **fair cross-model semantic
judge** (Anthropic Claude grading the live `openai:gpt-4o-mini` answers against the
human-validated `fact_atoms`) the AI beats **both** baselines overall (**90.7%** vs
static 59.6% vs keyword 45.0%) and decisively on the hard subset (**84.2%** vs
static 20.8% vs keyword 16.7%, **+63.3 pts**), while the honest exception is the
**parity** bucket (AI 90.8% vs static 94.4%, **−3.7**), where the static per-choice
feedback is purpose-built. The reproducible token scorer alone is confounded (it
rewards the static baseline for dumping the very paragraph the atoms were derived
from), which is exactly why the cross-model semantic judge is the honest
adjudicator — see `docs/QA-GOLDSET.md` and `docs/QA-BASELINE-COMPARISON.md`.

---

## 12. Directional-reasoning guardrail (follow-up Q&A prompt hardening)

**Failure it addresses.** The n=60 gold-set review found the follow-up model's
main residual weakness is **directional / relationship-reversal** errors: it keeps
the right framework but **flips the direction** of a cause→effect link or a role
assignment. Examples the review surfaced: naming the *wrong* buffer species as the
one that neutralizes added acid vs. added base (a reversed role assignment), and
dropping the explicit **contrast** a "compare A vs. B" question asks for.

**The guardrail (general, not item-specific).** `build_followup_prompt` in
`scripts/ai_qa.py` now injects a short `DIRECTION CHECK` block (constant
`DIRECTIONAL_GUARDRAIL`) into every follow-up prompt, after the full anchor
context. It tells the model to (a) verify the direction of every cause→effect and
every role assignment before answering (which species does which job, which
quantity rises vs. falls, which of two options is larger / more sensitive), (b)
for counterfactual "what if X changed" questions, state the direction of the
change and re-derive it from the underlying relationship, (c) answer **both sides**
explicitly when a contrast is requested, and (d) never assert a claim that
reverses the true relationship. It hardcodes **no** item facts and leaks no gold
answers, so it generalizes. All existing behavior is preserved: the prompt still
injects the full anchor context (stem, choices, per-choice feedback, static
explanation, source), the feature stays **opt-in**, ungrounded answers are still
dropped, and every answer remains traceable to the named source.

**What a spot-check showed (scratch only).** On a small check set
(`build/prompt-fix-check.json`, `openai:gpt-4o-mini`), the reversed-role case is
**fixed** (the buffer answer now correctly assigns the weak base to added acid and
the conjugate acid to added base), a forward/reverse-barrier contrast that the old
answer omitted is now stated correctly, and the previously-correct guard items did
not regress at the ship-gate level. One residual remains: an
Arrhenius **temperature-sensitivity** comparison is a genuine model-level
misconception (it conflates a larger rate constant with greater temperature
sensitivity) that a *general* guardrail does not reliably fix without hardcoding
the fact — which we deliberately did not do.

**Re-eval is a separate decision.** The frozen n=60 proof
(`data/qa-goldset-live-answers.json`, `data/qa-goldset-semantic-judge.json`, and
the `docs/` eval artifacts) is **untouched** and was **not** regenerated for this
prompt change. A full n=60 re-eval on the new prompt would be a **separate,
explicit decision** and must be written to fresh files (not silently overwritten
onto the frozen artifacts), since re-freezing the passing proof is a deliberate
act, not a side effect of hardening the prompt.

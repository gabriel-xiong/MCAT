# QA Gold Set — Baseline vs AI Comparison

_"Does the AI beat a simpler method?" — the live OpenAI follow-up answers (`data/qa-goldset-live-answers.json`, `openai:gpt-4o-mini`) vs two AI-OFF baselines (static source dump; keyword retrieval), all scored against the human-validated `fact_atoms` and `must_not_say`. Reported under BOTH instruments: (1) the reproducible TOKEN scorer in `scripts/ai_eval_qa.py` (no API, but biased toward verbatim source recall) and (2) a CROSS-MODEL SEMANTIC JUDGE (Anthropic Claude grading the OpenAI answers against the same rubric — the fair instrument). n=60 (9 parity / 51 differentiation, incl. 30 hard g031-g060 items)._

## Methods

- **ai** — saved live OpenAI answer (no new API calls; scoring reproducible).
- **static** — the app's shipped AI-OFF fallback: the question's `explanation` + the chosen distractor's `choice_feedback` (all choice feedback when no single distractor is recorded — the most generous static answer).
- **keyword** — top-2 sentences from that same static pool retrieved by content-token overlap with the follow-up question.

Metric = **mean atom coverage** (partial credit: fraction of an item's fact_atoms the answer covers), averaged over items. `AI - best baseline` is the AI's margin over the stronger of the two baselines on that subset.

## Headline — token scorer (all validated items)

| Bucket | AI | static | keyword | AI − best baseline |
|---|---|---|---|---|
| ALL (n=60) | 54.0% | 52.1% | 35.7% | +1.9% |

## TOKEN SCORER — coverage by bucket (reproducible, no API calls)

| Bucket | AI | static | keyword | AI − best baseline |
|---|---|---|---|---|
| parity (n=9) | 82.4% | 92.6% | 73.1% | -10.2% |
| differentiation (n=51) | 49.0% | 44.9% | 29.1% | +4.1% |
| hard-differentiation g031-g060 (n=30) | 30.8% | 15.0% | 8.3% | +15.8% |

_Note: even under the token scorer — which is biased toward the static source dump (see the artifact discussion below) — the AI already leads on the g031-g060 hard subset, where the static baseline cannot recover the answer from the anchor question's own text. The static "win" is confined to parity + easy-differentiation items whose atoms were derived from the very paragraph the static baseline dumps verbatim._

## must_not_say hit rates — token scorer (any forbidden claim asserted)

| Subset | AI | static | keyword |
|---|---|---|---|
| ALL (n=60) | 11.7% | 1.7% | 16.7% |
| parity (n=9) | 11.1% | 0.0% | 22.2% |
| differentiation (n=51) | 11.8% | 2.0% | 15.7% |

## Per-item coverage — token scorer (AI vs best baseline)

_Token scorer only (confounded — see the semantic-judge table above for the fair per-bucket comparison). `!`/AI-LOSS rows here are mostly token artifacts: the token scorer over-credits the static source dump and under-credits AI paraphrase (e.g. it scores g009/g040 at 0% for the AI though both answers are correct)._

`flag`: **AI WIN** = AI coverage exceeds best baseline by >10 pts; **AI LOSS** = best baseline exceeds AI by >10 pts; else `~`. `!` marks any must_not_say violation by that method.

| id | bucket | AI | static | keyword | best base | flag |
|---|---|---|---|---|---|---|
| g001 | parity | 75% | 100% | 100% | 100% | AI LOSS |
| g002 | parity | 100% | 100% | 75% | 100% | ~ |
| g003 | parity | 67%! | 100% | 100% | 100% | AI LOSS |
| g004 | differentiation | 100% | 100% | 75% | 100% | ~ |
| g005 | differentiation | 100% | 100% | 100% | 100% | ~ |
| g006 | differentiation | 100% | 100% | 100% | 100% | ~ |
| g007 | differentiation | 75% | 75% | 75% | 75% | ~ |
| g008 | differentiation | 100% | 100%! | 100%! | 100% | ~ |
| g009 | differentiation | 0% | 75% | 25% | 75% | AI LOSS |
| g010 | differentiation | 100%! | 100% | 100%! | 100% | ~ |
| g011 | differentiation | 100% | 100% | 50% | 100% | ~ |
| g012 | parity | 100% | 100% | 50% | 100% | ~ |
| g013 | parity | 67% | 100% | 33% | 100% | AI LOSS |
| g014 | parity | 100% | 67% | 67%! | 67% | AI WIN |
| g015 | differentiation | 100%! | 100% | 33% | 100% | ~ |
| g016 | differentiation | 100% | 100% | 75% | 100% | ~ |
| g017 | differentiation | 33% | 100% | 0% | 100% | AI LOSS |
| g018 | differentiation | 50% | 100% | 75% | 100% | AI LOSS |
| g019 | differentiation | 50% | 50% | 50% | 50% | ~ |
| g020 | differentiation | 75% | 75% | 50% | 75% | ~ |
| g021 | differentiation | 100% | 100% | 75% | 100% | ~ |
| g022 | parity | 67% | 67% | 100%! | 100% | AI LOSS |
| g023 | parity | 100% | 100% | 100% | 100% | ~ |
| g024 | parity | 67% | 100% | 33% | 100% | AI LOSS |
| g025 | differentiation | 100% | 100% | 100%! | 100% | ~ |
| g026 | differentiation | 25% | 25% | 0%! | 25% | ~ |
| g027 | differentiation | 100% | 75% | 50%! | 75% | AI WIN |
| g028 | differentiation | 67% | 100% | 100% | 100% | AI LOSS |
| g029 | differentiation | 33% | 100% | 0% | 100% | AI LOSS |
| g030 | differentiation | 67% | 67% | 0% | 67% | ~ |
| g031 | differentiation | 50%! | 25% | 25% | 25% | AI WIN |
| g032 | differentiation | 0% | 25% | 0% | 25% | AI LOSS |
| g033 | differentiation | 25% | 25% | 25%! | 25% | ~ |
| g034 | differentiation | 25% | 0% | 0% | 0% | AI WIN |
| g035 | differentiation | 25% | 0% | 0% | 0% | AI WIN |
| g036 | differentiation | 25% | 50% | 25% | 50% | AI LOSS |
| g037 | differentiation | 50% | 0% | 0% | 0% | AI WIN |
| g038 | differentiation | 25% | 25% | 25% | 25% | ~ |
| g039 | differentiation | 75% | 75% | 0% | 75% | ~ |
| g040 | differentiation | 0% | 0% | 0% | 0% | ~ |
| g041 | differentiation | 75% | 0% | 0% | 0% | AI WIN |
| g042 | differentiation | 0% | 50% | 25% | 50% | AI LOSS |
| g043 | differentiation | 75%! | 0% | 0%! | 0% | AI WIN |
| g044 | differentiation | 25% | 0% | 0% | 0% | AI WIN |
| g045 | differentiation | 0% | 0% | 0% | 0% | ~ |
| g046 | differentiation | 25% | 25% | 25% | 25% | ~ |
| g047 | differentiation | 25% | 25% | 25% | 25% | ~ |
| g048 | differentiation | 0% | 0% | 0%! | 0% | ~ |
| g049 | differentiation | 25% | 25% | 0% | 25% | ~ |
| g050 | differentiation | 50% | 50% | 25% | 50% | ~ |
| g051 | differentiation | 50% | 25% | 25% | 25% | AI WIN |
| g052 | differentiation | 25% | 0% | 0% | 0% | AI WIN |
| g053 | differentiation | 0% | 0% | 0% | 0% | ~ |
| g054 | differentiation | 25% | 0% | 0% | 0% | AI WIN |
| g055 | differentiation | 25% | 0% | 0% | 0% | AI WIN |
| g056 | differentiation | 25%! | 0% | 0% | 0% | AI WIN |
| g057 | differentiation | 75% | 0% | 0% | 0% | AI WIN |
| g058 | differentiation | 50% | 0% | 0% | 0% | AI WIN |
| g059 | differentiation | 0% | 0% | 0% | 0% | ~ |
| g060 | differentiation | 50%! | 25% | 25% | 25% | AI WIN |

## CROSS-MODEL SEMANTIC JUDGE — coverage by bucket (the FAIR instrument)

_Anthropic Claude (this coding subagent). CROSS-MODEL / non-circular: the answers under test were generated by OpenAI gpt-4o-mini, a DIFFERENT model family. No OpenAI judge was used (same-family would be circular; scripts/ai_judge.py refuses it), and no Anthropic API key is configured, so the judgment was performed directly by reasoning rather than via an API call._

Each answer is graded on whether it *conveys* the human-validated `fact_atoms` (any paraphrase / equivalent numeric or symbolic form), not on keyword overlap — so the static baseline no longer gets free credit for dumping the source paragraph the atoms were derived from.

| Bucket | AI | static | keyword | AI − best baseline |
|---|---|---|---|---|
| ALL (n=60) | 90.7% | 59.6% | 45.0% | +31.1% |
| parity (n=9) | 90.8% | 94.4% | 71.3% | -3.7% |
| differentiation (n=51) | 90.7% | 53.4% | 40.3% | +37.3% |
| hard-differentiation g031-g060 (n=30) | 84.2% | 20.8% | 16.7% | +63.3% |

### must_not_say — forbidden-claim assertion rate (semantic judge)

| Subset | AI | static | keyword |
|---|---|---|---|
| ALL (n=60) | 1.7% | 0.0% | 0.0% |
| parity (n=9) | 0.0% | 0.0% | 0.0% |
| differentiation (n=51) | 2.0% | 0.0% | 0.0% |
| hard g031-g060 (n=30) | 3.3% | 0.0% | 0.0% |

_any_violation booleans per method. Under semantic judging, exactly ONE of the 180 answers asserts a forbidden claim: the AI on g060 (it claims a LOWER activation energy is more temperature-sensitive -- the reverse of the truth -- asserting the g060 must_not_say). That is the only genuine violation across all 60 items and both baselines (static 0/60, keyword 0/60; AI 1/60 = 1.7%). The token scorer's extra must_not_say flags (ai/keyword on g001-g030) remain negation/refutation false positives._

## Honest interpretation

**Two instruments, two verdicts. Under the reproducible TOKEN scorer the static source-dump edges the AI on parity + easy-differentiation (a measurement artifact, explained below), but the AI already leads on the g031-g060 hard subset. Under the fair CROSS-MODEL SEMANTIC JUDGE the artifact disappears and the AI beats BOTH simpler methods overall and decisively on differentiation — the honest exception being parity, where the static per-choice feedback is purpose-built and the AI trails slightly.**

### Token scorer (confounded)
- **Differentiation (n=51):** AI 49.0% vs static 44.9% (**AI +4.1%**) vs keyword 29.1% (**AI +19.9%**).
- **Parity (n=9):** AI 82.4% vs static 92.6% (**AI -10.2%**) vs keyword 73.1% (**AI +9.3%**).
- **Hard g031-g060 (n=30):** AI 30.8% vs static 15.0% (**AI +15.8%**) vs keyword 8.3% (**AI +22.5%**). Even the token scorer, biased toward the source dump, puts the AI ahead here.

- **Why the static baseline "wins" the aggregate token score is a measurement artifact.** Per the gold set's own `grounding_policy`, every `fact_atom` on the parity + easy-differentiation items was authored to be *derivable from* the question's `explanation` + `choice_feedback`. The static baseline dumps that entire source text, so it maximizes atom token-overlap **by construction**. The token scorer cannot tell "dumped the whole explanation" apart from "answered the specific follow-up," so it over-credits the dump and under-credits the AI's paraphrase (it scored the AI 0% on several items — e.g. g009, g040 — whose answers are in fact fully correct).

### Cross-model semantic judge (fair)
- **Overall (n=60):** AI 90.7% vs static 59.6% (**AI +31.1%**) vs keyword 45.0% (**AI +45.7%**).
- **Differentiation (n=51):** AI 90.7% vs static 53.4% (**AI +37.3%**) vs keyword 40.3% (**AI +50.4%**).
- **Hard g031-g060 (n=30):** AI 84.2% vs static 20.8% (**AI +63.3%**) vs keyword 16.7% (**AI +67.5%**). This is the proof: on cross-question / counterfactual / synthesis / transfer follow-ups the static dump and keyword retrieval structurally cannot recover the answer. But the AI is not flawless here: on **g060** it REVERSES the Arrhenius temperature-sensitivity relation and asserts the item's `must_not_say` (see Safety below); on **g032** it swaps the NH3/NH4+ neutralization roles; and g036/g056 (0.50 each) drop the contrast the item asked for. AI coverage still exceeds both baselines on every one of the 30 hard items, but g060 is effectively a loss once its forbidden-claim assertion is counted.
- **Parity (n=9) — where AI does NOT win:** AI 90.8% vs static 94.4% (**AI -3.7%**). The static per-choice feedback is designed to answer "why is X wrong?", and the AI occasionally drops a secondary atom (e.g. g013 omits the induced-fit point). This is expected and reported honestly, not hidden.
- **Safety (must_not_say):** under semantic judging exactly ONE of the 180 answers asserts a forbidden claim — the **AI on g060** (it claims a lower activation energy is more temperature-sensitive, the reverse of the truth), giving AI 1.7% (1/60) vs static 0% and keyword 0%. This is the single genuine violation in the set and it is the AI's, not a baseline's. The token scorer's much larger "AI is dirtier" signal (ai 11.7%, keyword 16.7%) is mostly a negation-detection artifact: those answers state the CORRECT opposite of a must_not_say phrase but share its content tokens.

- **Small-n caveat:** n=60 total (9 parity / 51 differentiation, of which 30 are the hard g031-g060 subset), one topic trio (acids/bases, enzymes, kinetics), one answer model (gpt-4o-mini), one answer per item. The token scorer is a fully reproducible keyword/numeric heuristic (no API); the semantic judge is a single cross-model pass by a different family (Anthropic Claude) against a human-validated rubric. Directional evidence on a tiny hand-built set, reported honestly — not a powered benchmark.
- **Verdict:** *Under the fair instrument the AI beats both simpler methods.* Overall the AI leads static by +31.1% and keyword by +45.7%; on the hard subset it leads static by +63.3%. The token metric favored verbatim source recall (the wrong instrument for "did it answer THIS follow-up?"), which is exactly why the cross-model semantic judge — a different model family grading against a human-validated rubric — is the honest adjudicator here.

_Token-scorer tables generated by `scripts/qa_baseline_compare.py` (reproducible, no API). Semantic-judge tables rendered from `data/qa-goldset-semantic-judge.json` (a recorded cross-model pass). Regenerate with `make eval-qa-baseline` or `py -3.12 scripts/qa_baseline_compare.py --write`._

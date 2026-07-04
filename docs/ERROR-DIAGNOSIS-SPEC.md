# Error diagnosis spec — inference + confirmation

**Status:** Design locked (2026-07-01). Wednesday build keeps 4-button
self-report (Decision §9). This spec is the v2 mechanism.

**Rebalance (2026-07-01):** the live engine (`infer_error_type` in
`pylib/anki/mcat_perf.py`) was retuned to stop over-abstaining and then made
**demand-aware** to stop over-applying `application`. It **commits a diagnosis
in the common miss** but the content-presumed-held default now branches on
`cognitive_demand`: an `application`/`synthesis` miss → `application`; a
**`recall` miss → `content_gap`** (a recall item has no reasoning step to fail,
so `application` is a category error there); an un-typed miss leans
`content_gap`. `unresolved` is reserved for the truly-dark miss. Honesty is
carried by **confidence that varies with signal strength** (strong when `M` is
clearly high/low or a tag/trap is authored; weaker when `M` is imputed/
ambiguous) — **not** by a single flat number and **not** by abstaining. This
**supersedes** the earlier "Cold-start honesty", the "fast alone is weak →
`unresolved`", and the first-rebalance "`application` is the default for any
content-presumed-held miss / moderate 0.55–0.60" guidance in the sections below
(all now reframed inline). See Decision §21 and `LOOSE-ENDS.md`.

## In one paragraph (the mechanism)

**We infer the likely cause of a miss from independent signals — what the item
tests, how the student behaved, and whether the memory system says they hold the
content — validate content availability with a targeted recall probe when it's
decision-relevant, and commit a diagnosis at a confidence that reflects how much
signal we actually have.** In the common case we **do commit** (a content-tagged
or low-`M` miss → `content_gap`; a trap landing → `misread`; otherwise a
**demand-aware** default — an `application`/`synthesis` miss → `application`, a
`recall` miss → `content_gap`, an un-typed miss leans `content_gap`), carrying
honesty in a *confidence that varies with signal strength* rather than
abstaining; we fall back to `unresolved` / self-report only for the genuinely
no-signal miss (and, as a separate track, for every CARS miss). Everything below is that sentence plus the honesty guards that
keep it from over-claiming. (The rigor / caveats are for internal architecture;
for demo/team framing, lead with this paragraph.)

## Problem

The whole BrainLift SPOV-3 differentiator ("*why* a student missed, not just
*what*") rides on one signal — and the v1 signal is a weak one: **student
self-report**. What the research actually establishes (Dunning-Kruger /
calibration literature) is that students **systematically overestimate their own
performance** — poor self-calibration. From that we *infer* (our extrapolation,
not a direct finding) that asking them to finely categorize *why* they missed —
a reasoning slip vs a content gap — is even more fraught than judging right/wrong.
That inferred claim is load-bearing here, so it's flagged for more research in
`LOOSE-ENDS.md`. Either way, self-labeling the "why" is a shaky foundation for
the diagnostic engine.

## Principle

**Move the judgment from the student's introspection to (a) the item,
(b) observable behavior, and (c) objective cross-system measurement. The model
*infers* a hypothesis. Never assert an unconfirmed or conflicted diagnosis.**

## The ground-truth problem (read this first)

There is a **circularity** to confront honestly: we infer error types *because*
students can't reliably diagnose their own failures — so their **confirmation
cannot be treated as ground truth either.** You can't launder noisy self-report
into truth by phrasing it as yes/no. This reframes what confirmation is for and
where real labels come from.

**A. Ask for checkable facts, not diagnoses.** The calibration research is about
overestimating *performance*; we extend it to argue that *unprompted
introspective categorization* ("reasoning slip vs content gap?") is also
unreliable. Whatever its strength, that is **not** the same as reporting a
concrete, low-inference observation. The confirm step must collect
**observations we map to types ourselves**, never the category label:

- ❌ "Was this a reasoning error?" (asks for the diagnosis we said they can't do)
- ✅ "The question asked for the EXCEPT — did you notice that?" (checkable fact)
- ✅ "Did you run out of time / guess?" (reliable)

These prompts are **used sparingly** — triggered by a salient behavioral signal
(e.g. an abnormally fast answer) and rate-limited, never shown on every miss
(see UX → "Prompt sparingly").

**B. Real ground truth is objective, not opinion:**
- **FSRS-R of backing cards** — an objective *historical signal of
  retrievability*, independent of belief. It is **not proof the content was
  available at that moment**: a student can have high card retrievability yet
  fail because the card was shallow, the cue didn't match the question's
  context, or the concept was memorized but not flexibly usable. Treat it as a
  strong prior on content availability, not a verdict.
- **Behavioral logs** — timing, answer changes, chosen distractor are facts.
- **Content re-check probe (the key one):** right after a miss, show a *plain
  recall probe* of the exact sub-concept(s) the question needed (via
  `supports_question`). Interpretation is **asymmetric**: probe **FAIL** =
  strong evidence of `content_gap` (can't recall it even when cued now); probe
  **PASS** = **weak** evidence, because the question itself (stem, choices, a
  priming distractor) may have cued recall. This uses **memory mode as an
  objective oracle for performance-mode error typing** — no self-diagnosis
  required — but only the FAIL direction is strong.
- **Gold set:** a small think-aloud sample (e.g., held_out friend on ~20–30
  items) for high-quality labels. We don't need truth on every item — just a
  trustworthy sample to measure inference quality.

**C. The confirm button is a weak signal, not the validator.** Its honest role:
student **agency** (override + we log it) and a cheap **consistency monitor**
(systematic inference↔confirm disagreement flags a problem). It is **not** the
ML training label — labels come from B (re-check probe + gold set).

**Honest stance for the prototype (small n):** inferred types are *hypotheses
reported with explicit uncertainty*, validated on a small gold set — we do not
claim per-user ground truth. Consistent with the project's abstain-and-report
ethos.

## Two tracks (science vs CARS)

Our science questions (BB/CP/PS) are **standalone stems** (no passage; verified
in `questions.json`). CARS questions embed the passage inline in the stem and
have **no flashcards/mastery**. That splits diagnosis into two tracks whose
item-encoded types are **mutually exclusive**:

| Track | Passage | Mastery/flashcards | Diagnosis approach |
|-------|---------|--------------------|--------------------|
| **Science** (BB/CP/PS) | No | Yes | error-typing engine: `content_gap`, `application`, `misread` |
| **CARS** | Yes (in stem) | No | **skill-archetype accuracy + pacing flag** (see below) — *not* generic error-typing |

- `content_gap` is **science-only** — CARS is by definition *no outside
  knowledge*, so a content gap on passage-supplied material is impossible.
- The **cross-system signal (memory ⟂ performance)** and the **content re-check
  probe** are **science-only** — CARS has no mastery/flashcards, so no oracle.
- **CARS does not use the inference/confirm error-typing machinery** (see
  "CARS diagnosis" below); the generic taxonomy collapses there.
- **CARS-abstains rule (engine guard):** `PerformanceSession.answer` hard-guards
  every CARS miss to `unresolved` (confidence 0.0) *before* the science engine
  runs — so the rebalanced science default (which now commits `application` on a
  content-presumed-held miss, below) can never mislabel a CARS miss. CARS routes
  to its own skill-archetype + pacing track and to the self-report fallback,
  never to `content_gap` / `application` / `misread`.

### CARS diagnosis (separate, simpler, objective)

The generic science error-typing engine doesn't fit CARS: `content_gap` can't
occur (no outside knowledge), and the process buckets don't map cleanly onto
what makes CARS remedies differ. But CARS remedies **do** differ — just along a
different axis. The actionable dimensions are the **skill archetype** that
failed (main idea / structure, evidence retrieval, inference, author attitude,
beyond-the-text reasoning), plus **pacing/timing** and **trap-answer
susceptibility**. The coarse skill grouping we **already tag** via `topic_id`
is the entry point:

| CARS `topic_id` | AAMC skill |
|-----------------|-----------|
| `cars_comprehension` | Foundations of Comprehension |
| `cars_reasoning_within` | Reasoning Within the Text |
| `cars_reasoning_beyond` | Reasoning Beyond the Text |

CARS diagnosis = two objective signals, **no inference, no self-diagnosis, no
oracle**:
1. **Skill-archetype accuracy** — group attempt accuracy by CARS `topic_id`.
   Drives the differentiated next action ("weak area: Reasoning Beyond the Text
   52% vs Comprehension 81% → drill beyond-text items").
2. **Pacing flag** — from timing (CARS is time-pressured): missing **fast** →
   rushing/misread → pacing advice; **slow + missing** → genuine skill
   difficulty → the skill breakdown says which.

This sidesteps CARS having no content oracle: its actionable axis was never
content. The science error buckets don't apply to CARS — "which skill archetype"
(plus pacing and trap susceptibility) *is* the CARS diagnosis. The remedy is
skill-specific (e.g. weak beyond-the-text reasoning → drill beyond-text items;
frequent trap picks under time → trap-recognition + pacing drill), **not** a
generic "just practice CARS."

**Demo note (2026-07-03).** For the Friday demo a CARS miss **omits the
error-type confirm / self-diagnosis step**: it routes only to the two objective
signals above and does **not** surface the error-type self-report prompt.
Rationale (a self-report step for CARS would undercut the "users can't reliably
self-diagnose" premise) and the "revisit later" options are tracked as an
accepted temporary gap in `LOOSE-ENDS.md` ("CARS misses skip the error-type
confirm / self-diagnosis step"). The normative CARS flow above is unchanged; this
records only a demo-scope omission.

## The types are on two different axes (do NOT tag one-per-choice)

Within a track, a distractor still cannot be mapped to exactly one error type —
that is category-confused. One item-encoded type sits on the **content axis**;
the process types are properties of the **student's process** and are not
encoded in the choice at all:

The error-typing engine below is **science-track only** (CARS uses skill
accuracy + pacing, above). Within science:

| Type | Axis | Where it comes from |
|------|------|---------------------|
| `content_gap` | **Content (item)** | The chosen distractor encodes a specific factual misconception |
| `misread` | **Process (behavior)** | Fast + high `M` + trap-option pick on an otherwise-easy item; lands on a *predictable* trap |
| `application` ("Applied reasoning") | **Process (behavior)** | Had the content (high `M`) on an application/synthesis item but missed; long dwell and/or correct→wrong change reinforce it; lands on *any* option |

**`application` is a deliberately COARSE bucket.** It subsumes several related
failure modes that share one remedy family (do more applied practice, not more
flashcards): application/transfer failure, multi-step integration failure, and
**passage-to-concept mapping** (knowing a concept but failing to map given data
onto it). These are documented **sub-modes**, not separate live bins in v1 — we
split them later **only if** data volume *and* a genuinely different remedy
justify it. Splitting now costs signal at small n. In particular,
**`passage_mapping`** lives here as the science passage-mapping sub-mode (e.g.
knows Michaelis–Menten but can't map a passage's inhibitor data onto competitive
inhibition); it is dormant in the current dev bank (standalone stems) but is a
real, reserved failure mode under `application`, **not** a retired type.

**Honesty constraint (content presence gate) — demand-aware:** the *strong*
`application` call (high confidence, ≥0.7) still requires content presence
*actually established* — high `M` **and** applied/synthesis demand
(cross-system divergence), or a re-check probe PASS. `application` is also the
**default coarse bucket** for a content-presumed-held miss where content
presence is only *presumed* — **but only on an `application`/`synthesis`
item** (mid `M`, or ambiguous/imputed `M`): those commit `application` at
**lower confidence** (rising with `M`·`d`) rather than abstaining, justified by
the gate-defines-content confound (gated applied misses lean `application` by
construction — see that section). A **`recall` miss is never `application`** —
it has no reasoning step to fail, so a presumed-held recall miss routes to
`content_gap` (the fact itself) at confidence that varies with `M` (low when
`M` is high — contradictory). The honesty is carried by the **varying
confidence**, not by staying `unresolved`. What still protects against silently
absorbing a real gap: a low `M` or an authored content tag routes to
`content_gap` first (branches 1–2 below), the demand split keeps recall misses
out of `application`, and the moderate confidence flags applied cases for the
re-check probe. We never fire *high-confidence* `application` without
established content.

**An applied-reasoning slip can land on any distractor** (and a misread often,
but not always, lands on a *predictable* trap) — so "the process-error option"
is not reliably one choice. We therefore only author the **content axis** on the
choice, and detect the **process axis** from behavior. A distractor may also
carry **more than one** candidate content misconception, or **none** (a merely
plausible trap).

## Signals (ranked by reliability)

| # | Signal | Reliability | Role |
|---|--------|-------------|------|
| 1 | **Cross-system divergence** — high card retrievability (current FSRS-R) yet missed a synthesis item | High (two independent measurements; FSRS-R is a signal, not proof of momentary availability) | Strongest `application` vs `content_gap` discriminator (science) |
| 2 | **Content re-check probe** — post-miss recall of the backing sub-concept | **FAIL** = high (objective `content_gap`); **PASS** = weak (priming-inflated) | Settles `content_gap` vs process (asymmetrically); the validation label |
| 3 | **Distractor content tag** — the misconception a wrong option encodes (authored) | Medium-high (expert-labeled), **content axis only** | Prior weight toward `content_gap` |
| 4 | **Timing** relative to a per-item/per-student baseline | Medium (confounded) | Process axis — fast **alone (no trap) is weak** (→ the demand-aware default, not `misread`); fast+high `M`+trap→misread (highest conf); a bare trap landing still commits `misread` at moderate conf |
| 5 | **Answer changes / churn** (needs select-then-confirm UI) | Medium | Process axis — correct→wrong switch signals `application` |
| 6 | **Student confirmation** (observation prompt) | Low (self-report) | Agency + cheap consistency check — **not** ground truth (see ground-truth problem) |

Self-report is demoted from *driver* to a weak *consistency channel*. No single
signal is forced to yield a unique type; inference produces a **ranked
hypothesis** and prefers `unresolved` over a shaky guess.

## Detecting the process axis (`misread` vs `application`)

These are **not** authored on choices — they're inferred from behavior, and
it's the most confounded signal we have. No single input is trusted; we combine
several. **Rebalanced (2026-07-01, demand-aware):** rather than abstaining when
the behavioral signal is weak or conflicting, the engine now commits — a trap
landing → a (moderate) `misread`, and everything else content-presumed-held → a
**demand-aware default** (an `application`/`synthesis` miss → `application`; a
`recall` miss → `content_gap`, since a recall item has no reasoning step to
fail; an un-typed miss leans `content_gap`) — and carries the honesty in a
confidence that **varies with signal strength**. `unresolved` is reserved for
the truly no-signal miss (see "Inference rule").

### Strongest signal: cross-system divergence (memory ⟂ performance)

The most trustworthy discriminator between `application` and `content_gap` is
**not** behavioral — it's the **divergence between the two score systems**,
which only this architecture can measure:

```
all prerequisite concepts mastered  AND  item demand = application/synthesis
   AND  missed
        -> application   (they HAD the pieces; the integration/transfer step failed)

any prerequisite concept NOT mastered  AND  missed
        -> content_gap on that prerequisite   (do NOT call it application)
```

Why it's strong: memory (FSRS/mastery) and performance (attempt accuracy) are
**independent measurements**. Their disagreement — "the memory system says you
know every piece, the performance system says you missed the synthesis" — is
much harder to fake than a timing threshold, and it's exactly the SPOV-3 case
(strong students whose misses are applied-reasoning/mapping, not content).

**Operationalized from data we already have:**
- **Prerequisite concepts** = invert the `supports_question` links (cards →
  question) into (question → backing cards/topics); check each backing topic's
  mastery / FSRS retrievability.
- **Item demand** = a question-level `cognitive_demand` tag
  (`recall | application | synthesis`). The signal only fires for
  `application`/`synthesis`; a missed *recall* item you've "mastered" is more
  likely a misread or a stale card, not an applied-reasoning failure.

**Honesty guard (rebalanced 2026-07-01):** fire `application` with **high
confidence (≥0.7)** only when *every* prerequisite is mastered (high `M`) **and**
demand is application/synthesis. If a prerequisite is clearly weak (low `M`) or
the chosen distractor carries a content tag, route to `content_gap` instead — we
can't tell "applied it wrong" from "was missing piece 3." The change from the
old stance: a merely *ambiguous* or mid-`M` miss **on an application/synthesis
item** no longer stays `unresolved`; it still commits `application`, but at
**lower confidence** (rising with `M`·`d`), with the honesty carried by that
number and the case flagged for the re-check probe. A **`recall` miss is not
governed by this at all** — it commits `content_gap`, never `application`
(no reasoning step to fail). So the content-presence gate governs the
**confidence of an applied `application`**, not whether we commit it — and the
demand tag governs *which* type we commit; only the truly-dark miss abstains.

### The gate-defines-content confound (important)

Because performance mode is **unlocked by flashcard mastery**, students arrive
with a content baseline *by construction* — so gated misses will **lean toward
`application`**. That direction is **by design** (it's the 505→510 shift: strong
students miss on applied-reasoning/mapping, not content) — but it becomes an
*issue* if we treat "passed the gate" as "no content gap." They are not the
same:

- The gate (≥3 seen, ≥5 Good/Easy) is a **low bar**; FSRS-R may have **decayed**
  since unlock ("unlocked" ≠ "knows it now").
- **Recall ≠ application** — the gap the product exists to measure; real content
  weakness can persist in a "mastered" topic.
- **Coverage gaps** — a needed sub-concept may have **no backing card**, so its
  mastery is unknown.

**Two distinct notions of "mastery" — do not conflate:**

| | Performance **gate** (eligibility) | **Content-mastered** (diagnosis) |
|---|---|---|
| Rule | ≥3 seen + ≥5 Good/Easy | current FSRS-R of backing cards, per card, at attempt time |
| Purpose | may you *see* perf questions on this topic | is a miss `application` vs `content_gap` |
| When | one-time unlock | recomputed every attempt (decay-aware) |
| Status | **unchanged** | new, stricter |

**"Content-mastered" is a continuous quantity computed from the raw FSRS-R
values — not tiers/thresholds** (banding is just thresholds in disguise and
reintroduces all-for-one rigidity). For a missed question with backing cards
`i=1..n` at current retrievability `R_i ∈ [0,1]`:

```
content-held score   M = ( Π R_i )^(1/n)          # geometric mean:
                                                   #  - weakest-link sensitive
                                                   #  - stable across prereq counts
                                                   #  (strict alt: M = min_i R_i)

uncovered prerequisite -> impute R_i = R0          # conservative prior (topic avg
                                                   # or ~0.5); drags M down smoothly

type affinities (continuous in M):
   application   ∝ M · d              # d = demand factor from cognitive_demand
                                      #     (recall≈0 → no application; synthesis≈1)
   content_gap   ∝ (1 − M) + w_mis·g  # g = 1 if the CHOSEN distractor is a
                                      #     distinctive-misconception content_gap,
                                      #     else 0 (see "Discriminating shallow
                                      #     mastery" below). w_mis keeps a real
                                      #     misconception in contention even at high M.
   misread       ∝ b                  # behavioral term (fast + high M + trap; low churn)

normalize the three -> distribution; confidence = p_top, margin = p_top − p_2nd
```

The application↔content_gap split is thus a smooth dial on `M`: high `M` →
mostly `application`, low `M` → mostly `content_gap`, blended in between;
confidence falls out of the same numbers. **Exception (not a pure dial on `M`):**
when the chosen distractor is a *distinctive-misconception* `content_gap`, the
`w_mis·g` term keeps `content_gap` in play even at high `M` — high mastery no
longer *unconditionally* downranks `content_gap`. See "Discriminating shallow
mastery" below. Free params: the demand factor
`d`, the uncovered prior `R0`, and the misconception weight `w_mis` — all
**tunable on dev, validated against confirmation agreement** (and, for `w_mis`,
against re-check-probe outcomes; see LOOSE-ENDS). Sparse-history cards yield
noisy `R_i` → naturally widen the distribution (lower confidence) without
special-casing.
- **Persistently low agreement on `application`** (student overrides to
  content_gap) is the measurable signal that the gate is too lax or coverage too
  thin — the confound is audited, not hidden.
- A tentative-`application` miss with weak/ambiguous `M` is a prime **trigger for
  the content re-check probe** (see that section) to settle it objectively.

#### Discriminating shallow mastery (why the misconception term exists)

The dangerous middle state the product must catch: a student whose flashcard
mastery `M` is **high** but who **doesn't truly understand** — content is
recallable in isolation but not flexibly usable (call it *shallow mastery* /
`application_gap`). On a pure `M` dial, high `M` sends every miss toward
`application`, so a shallow-mastery student who picks a distractor encoding a
*specific* misconception gets mis-explained as an applied-reasoning slip and
routed to applied practice — when the honest signal is that they hold a concrete
wrong belief and need the flashcards.

**The mechanism:** a distractor tagged `content_gap` with a *distinctive*
misconception is **independent content-gap evidence that does not come from `M`**
— it comes from *which wrong belief the student acted on*. So a distinctive-
misconception distractor pick **must not be fully suppressed by high `M`**: the
`w_mis·g` term above keeps `content_gap` in contention even when `M` is high.
This is exactly what captures the shallow-mastery / `application_gap` middle
state — the two signals *diverge* (memory says "knows it," the chosen
misconception says "holds a specific wrong belief"), and that divergence is the
diagnostic, not `M` alone.

**Kept consistent with the probabilistic, confidence-gated framing:** the choice
tag is a **weighted prior, not a verdict** (see "Distractor priors, not hard
tags"). `w_mis·g` *raises* the `content_gap` weight; it does not force the label.
When high `M` and a distinctive-misconception pick both fire, the distribution is
genuinely **contested** (lower `p_top`, smaller margin) → medium confidence →
this is precisely the case that should **trigger the content re-check probe**,
which remains the objective disambiguator. Probe **FAIL** confirms the
`content_gap` (shallow mastery — the card was hollow); probe **PASS** (weak, per
the asymmetry) leans it back toward `application`. So the misconception term
*surfaces* the shallow-mastery hypothesis for objective checking; it never
silently overrides `M`.

**How the live engine realizes this (rebalanced 2026-07-01):** rather than
computing a normalized contested distribution, `infer_error_type` collapses the
`w_mis` idea into its **first branch** — an authored `content_gap` tag on the
chosen distractor commits `content_gap` outright, **independent of `M`**, at
confidence 0.65 (or 0.75 when low `M` corroborates). That moderate 0.65 *is* the
"contested, medium-confidence" state: high enough to route the shallow-mastery
student to the flashcards they actually need instead of the `application`
default, low enough to flag the case for the re-check probe. The engine does not
emit a blended `content_gap`/`application` distribution; it prioritizes the tag
and carries the contest in the confidence.

### Behavioral axis (splits application vs misread once content_gap is ruled out)

**Fingerprints**

| | `misread` | `application` |
|---|-----------|-------------|
| Timing (vs baseline) | **fast** — confident, didn't deliberate (**fast alone is weak**; see below) | **slow / long dwell** — worked at it |
| Knowledge | should get it (high mastery / FSRS R) | has the pieces but chained/transferred them wrong |
| Answer churn | low — one confident pick | high — switches, esp. correct→wrong |
| Landing option | a *predictable* trap (negation/unit) — the trigger for a `misread` call | any option |

**`misread` rides on a *predictable-trap landing*, and its confidence scales
with the behavioral evidence (rebalanced 2026-07-01).** Once content is ruled
in/out (branches 1–2), a trap-option pick commits `misread`: **strongest (0.75)
when fast + high `M`** (confident, didn't deliberate, on an item they should
get), **moderate (0.6) when fast *or* high `M`**, and **committed but low-
confidence (0.55)** for a bare trap landing otherwise. **Fast *alone* (no trap)
is still not `misread`** — a fast wrong answer with no trap can be a blind
guess, time pressure, or fatigue, so it falls through to the demand-aware
default (`application` on an applied/synthesis item, `content_gap` on a recall
item — not `misread`, and no longer `unresolved` unless the miss is truly
dark). This diverges from the earlier "fast + high `M` + trap *required* for any
misread call" stance: a trap landing now commits `misread` at moderate
confidence even when slow / mid-`M`, because the predictable-trap option is
itself the execution-slip signal.

**Three inputs, combined**

1. **Timing vs baseline** — never an absolute threshold (confounded by reading
   load, fatigue, CARS vs science). Compare to a **per-item median** (once
   attempts accumulate) and a **per-student** pace; bucket CARS separately.
2. **Answer churn** — needs a **select-then-confirm** interaction (tap to
   select, tap again to submit) to log `first_choice_index` + `answer_changes`.
   Correct→wrong switch is the strongest `application` tell.
3. **"Should they have known it?"** — the content-held score `M` from the
   cross-system section above (already computed; don't restate the logic here).
   The behavioral axis only splits `misread` vs `application` **after** `M` has
   ruled `content_gap` in or out — high `M` (knows it) makes fast+trap→misread,
   slow/churn→application; low `M` pulls toward `content_gap` regardless.

Rough disambiguation (given `M`; content tag takes precedence — see "Inference
rule"). Cells show the committed type; parentheses note confidence:

| | trap landing | no trap, applied/synth demand | no trap, recall demand | no trap, unknown/missing demand |
|---|------|------|--------------|--------------|
| **high `M` (knows it)** | misread (0.75 if fast, else 0.6) | **application** (≥0.7) | **content_gap** (~0.40, contradictory) | **content_gap** (~0.40) |
| **mid `M`** | misread (0.6 if fast, else 0.55) | **application** (0.50–0.68) | **content_gap** (~0.60) | **content_gap** (~0.60) |
| **ambiguous / imputed `M`** (`None`) | misread (0.55, or 0.6 if fast) | **application** (0.55) | **content_gap** (~0.45) | **`unresolved`** (truly dark) |
| **low `M`** | content_gap | content_gap | content_gap | content_gap |

Read the shift from the earlier (demand-blind) table here: the
`recall`/`unknown`-demand column no longer commits `application` — a recall miss
has no reasoning step to fail, so it routes to `content_gap` (the fact itself),
and confidence *varies* (higher as `M` drops; deliberately low ~0.40 for a
high-`M` recall miss, which is contradictory and a probe candidate). The one
surviving `unresolved` cell is the bottom-right — `M` unavailable, no trap, no
tag, and **unknown/missing** demand: the truly-dark miss. (A `recall`-demand
miss with `M` unavailable is *not* dark: the demand alone routes it to
`content_gap` at ~0.45.)

**Partial item encoding for misread:** negation/`EXCEPT`/`LEAST` stems and
unit-swap distractors have a predictable misread landing spot. Optional
distractor flag `trap: "negation"` \| `"unit"` **raises the misread prior** when
that option is picked quickly — bridging the axes without pretending every
misread is item-encoded.

**Cold-start honesty (superseded 2026-07-01 — commit, but demand-aware, and
vary the confidence):** the *original* stance here was that with no baselines
the process axis is weak, so **most misses should go `unresolved`** → 3-button
self-report. The live engine **no longer does this.** In practice cold-start
`M` is imputed by the gate to the `UNCOVERED_R0` prior (~0.5, landing in the
ambiguous `[LOW_M, HIGH_M)` band) for nearly every attempt with no review
history, and ~78% of science distractors are untagged. The *first* rebalance
committed all such misses to `application` @ 0.55 — but that emitted a **single
constant label at a single constant confidence** across every miss, including
the ~61% `recall`-demand items where `application` is a category error (no
reasoning step exists to fail). The demand-aware fix keeps "commit, don't
abstain" but routes by demand: a cold-start **`recall`** miss → `content_gap`
(they likely don't truly hold the fact), an **applied/synthesis** miss →
`application`, an un-typed miss leans `content_gap` — and **confidence varies**
(moderate ~0.6 at the imputed mid-`M`, low ~0.40 when `M` is high yet a recall
fact was missed, strong when `M` is clearly high/low or a tag/trap is authored).
`unresolved` is reserved for the truly-dark miss (`M` unavailable **and**
unknown/missing demand **and** no tag **and** no trap). As per-item / per-student
baselines accumulate the *confidence* sharpens; the agreement metric still says
when to trust the label.

## Content re-check probe (objective disambiguator)

**Status: IMPLEMENTED — IMMEDIATE variant (2026-07-02).** Shipped in
`pylib/anki/mcat_perf.py` (`resolve_probe_target`, `card_retrievability`
weakest-link selection, `infer_error_type(recheck_correct=...)` branch 0,
`PerformanceSession.probe_target` / `record_probe_outcome`) and wired into the Qt
dialog (`qt/aqt/mcat/performance_dialog.py`): on a SCIENCE miss the probe fires
**immediately**, before the explanation/diagnosis panels — plain recall of the
backing sub-concept → reveal → "I knew it" / "I didn't" self-grade → the
probe-informed diagnosis. Outcomes persist to `recheck_card_id` /
`recheck_correct` and travel in the sync bundle.

**Accepted tradeoff (team decision).** Because the probe fires **immediately**
after the miss (not delayed), a PASS carries a mild "the MCQ just cued recall"
priming bias. The team has **chosen to accept this for the demo** and treats a
PASS as **solid evidence** that content was available (it is *not* heavily
discounted for priming). The asymmetry that is kept is only that **FAIL is the
single strongest content signal** (committed at high confidence ~0.9); a PASS
suppresses `content_gap` and routes to `application`/`misread` at *raised*
confidence. The delayed natural-review variant (read the backing card's next
memory-session outcome) remains a future refinement to remove the priming bias
entirely, but is out of scope for this slice.

> **Probe-branch confidence varies (2026-07-03 fix).** The probe branch is what
> the live UI shows (`record_probe_outcome` re-runs the inference with the
> outcome set), so it must obey the same **"confidence varies with signal
> strength — continuous values, not tiers"** rule as the rest of the engine.
> An earlier implementation returned per-outcome *constants* (FAIL → 0.9, PASS
> non-applied → 0.65, trap → 0.8); because the app fires a probe on essentially
> every miss, the probe branch was the *only* branch users ever saw and the
> on-screen confidence collapsed to those two/three numbers regardless of `M`,
> timing, tag, or demand (the `M`-varying ladder only runs in the offline eval
> replay where `recheck_correct is None`). The probe branch now folds those same
> signals into a **bounded** confidence — FAIL ∈ [0.85, 0.97] (modulated by `M`
> magnitude / authored misconception / speed, so low `M` corroborates and high
> `M` mildly contradicts) and PASS ∈ [0.6, 0.9] (modulated by demand match / `M`
> / speed) — preserving the FAIL-is-strongest and PASS-≥-moderate semantics
> while no longer emitting a single flat constant. Still honestly bounded (a
> thin, cold-start-imputed signal never fabricates near-certainty).

The strongest way to separate `content_gap` from `application`/`misread` without
self-diagnosis: after a miss, objectively test whether the required content was
actually retrievable, using the backing cards (`supports_question`). This turns
memory mode into an **oracle** for performance-mode error typing — but an
**asymmetric** one (FAIL is strong, PASS is weak in principle; per the accepted
tradeoff above the IMMEDIATE build treats PASS as solid, keeping only the FAIL-is-
strongest asymmetry).

**Placement (avoid contamination):**
- **Pre-reveal micro-probe** — probe the atomic prerequisite immediately after
  the answer but **before** showing the explanation (otherwise they just read
  it). Clean signal.
- **Delayed natural check** — the backing card resurfaces in the next memory
  session anyway; read that outcome too. Removes priming, zero extra UX.

**Interpretation is asymmetric (honesty) — this is the crux:**
- Probe **FAIL** → **strong** evidence of `content_gap` (can't recall the fact
  even when cued now).
- Probe **PASS** → **weak** evidence toward `application`/`misread` — the
  question itself (stem, choices, a priming distractor) may have cued recall, so
  immediate recall is priming-inflated. Do not treat a PASS as "content was
  definitely there"; the delayed natural review is the cleaner confirmation.

**Card selection + localization:** for a synthesis miss with several backing
cards, probe each prerequisite (lowest-R first). **One** prereq fails → content
gap **localized to that specific card** → precise next action + handoff to
memory mode. **All** pass → *lean* toward `application` (weakly, per the
asymmetry above), corroborated by high `M` and the delayed review.

**Trigger policy:** the design intent is to fire only when decision-relevant
(ambiguous `M`) and sampled to avoid fatigue. **As implemented (IMMEDIATE
variant, 2026-07-02) the probe fires on every SCIENCE miss with a resolvable
backing sub-concept** (CARS and unmapped misses skip it and use the inference
path unchanged) — kept simple and demo-reliable; confidence-gated / budgeted
triggering is a later refinement. Never reveal the MCQ answer via the probe (the
probe shows a backing *component* card, not the answer).

**Probe target resolution (as implemented):** `resolve_probe_target` inverts
`supports_question` → backing card ids and probes the **weakest link first**
(lowest current per-card FSRS-R; a card with no memory state sorts first). The
resolved **real collection `card_id`** is stored in `recheck_card_id`. If no card
can be cleanly resolved/rendered at runtime it **falls back** to a plain
concept-recall prompt derived from the question's backing topic (recorded with
`recheck_card_id = NULL`, `fallback = true`). CARS or a genuinely unmapped item
returns `None` → the probe is **skipped** and the existing inference path runs
unchanged.

Logged: `recheck_card_id`, `recheck_correct`, `recheck_timing`
(`immediate` | `delayed`), `recheck_latency`. These are **objective labels**
(not self-report) — the training/validation target.

## Data model

### `questions.json` — author the *content axis only*

Tag each distractor with the content misconception(s) it encodes — **not** an
error type per choice, and **never** `misread`/`application` (those aren't
choice-encoded).

```json
"choice_diagnosis": [
  {"maps_to": "content_gap", "misconception": "forgot Le Chatelier shift direction"},
  null,
  {"maps_to": "content_gap", "misconception": "used total pressure, not partial"},
  {"maps_to": null, "trap": "negation"}
]
```

Optional `trap` (one of `negation`, `unit`, `inverse`, `scaling`, `transpose`,
`partial`) marks a predictable **execution/misread** landing spot; it raises the
misread prior when that option is picked quickly (see process-axis section). It
is a *prior nudge*, not a hard label, and rides on `maps_to: null` with **no**
`misconception` (a content confusion is `content_gap`, never a trap).

**Question-level `cognitive_demand`** (`recall` \| `application` \| `synthesis`)
— required for the cross-system signal. Only `application`/`synthesis`
items can fire a high-confidence `application` diagnosis. Prerequisite concepts
are read from the inverted `supports_question` links, so no extra authoring is
needed beyond the demand tag. (Note: `cognitive_demand` is a **question-level
difficulty axis**; the `application` **error type** is a separate diagnosis — an
`application`-demand item can still be missed for a `content_gap`.)

`choice_diagnosis` is **science-only** (CARS uses skill-archetype accuracy, not
distractor tags). Aligned 1:1 with `choices`; `null` for the correct option.
`maps_to` ∈ `content_gap` | `null` (may be a **list** if a distractor reflects
more than one plausible misconception). `misconception` is free text used to
make the confirm prompt concrete and to guide authoring. Validator (when
present): length == choices, the correct index is `null`, `maps_to` is
`content_gap`/`null` only, and `choice_diagnosis` does not appear on CARS
questions. Questions without it degrade gracefully (content axis = none → lean
on process/behavior and the demand-aware default — `application` on an
applied/synthesis item, `content_gap` on a recall or un-typed item; `unresolved`
only for the truly-dark miss).

#### Choice tagging methodology

The choice axis only discriminates if tags actually **distinguish** landings.
Tagging every distractor `content_gap` gives zero discrimination — the content
axis then contributes a flat prior and cannot help separate a real content gap
from a process error. **Content axis only on choices** — never tag
`misread`/`application` on a choice (those are process-axis, inferred from
behavior). Every distractor gets exactly one of **three axes**, each meaning
something different:

1. **`content_gap` (+ specific `misconception`)** — landing here requires a
   **false belief** about the science. Each `content_gap` distractor within one
   question must encode a **different** misconception (no generic "doesn't know
   X" repeated across choices). `maps_to: "content_gap"`.
   *Example — q_syn_001 B:* `content_gap`, "expects Vmax to fall — confuses
   noncompetitive (Vmax↓, Km unchanged) with the observed Vmax-unchanged /
   Km-up pattern." A student who picks it holds a nameable, specific error.

2. **`trap: <type>`** — a predictable **execution-error** landing (arithmetic /
   procedural slip by a student who *does* hold the concept). It feeds the
   behavioral/`misread` prior, **not** the content axis, so it rides on
   `maps_to: null` with **no** `misconception`. Use **only** where such a landing
   genuinely exists; never use `trap` for a content confusion.

3. **`null` (bare)** — genuinely **non-diagnostic**: an arbitrary wrong number
   with no pathway, or a plausible-but-unrelated grab. Picking it says nothing on
   the content axis. The whole entry is `null`.
   *Example — q_syn_009 D:* `null` — a numeric near-miss with no coherent
   derivation pathway.

**The six trap types** (each with a one-line draft example):

| type | meaning | draft example |
|------|---------|---------------|
| `negation` | dropped/flipped a sign or missed an `EXCEPT`/`LEAST`/`NOT` | q_syn_006 B — dropped the − in ΔG° = −nFE°cell → +212 kJ |
| `unit` | unconverted / mismatched units | q_syn_019 B — used kJ against J directly (50/150 = 0.33) |
| `inverse` | inverted a ratio or took the reciprocal | q_syn_023 B — used A₂/A₁ instead of A₁/A₂ |
| `scaling` | off by a power / factor (×10, squared, wrong order of magnitude) | q_syn_011 D — applied two log units (10²) instead of one |
| `transpose` | swapped two values / labels / positions | q_syn_020 B — swapped the reaction orders of A and B |
| `partial` | executed most of the chain but stopped one step short | q_syn_008 D — got Ecell→0 but not ΔG→0 at equilibrium |

**Aim for honest variety.** Where an item genuinely supports it, prefer a mix
(a deep-misconception `content_gap`, a `trap`, and a `null` near-miss) rather
than a uniform wall of `content_gap`. But **do not force** a tag that isn't true
to the choice: an item whose three distractors each encode a real, distinct
misconception is legitimately all-`content_gap`. (Finalized bank counts:
**71 content_gap / 12 trap / 7 null** across the 90 synthesis distractors — see
`SYNTHESIS-QUESTIONS-DRAFT.md` → "Choice-axis re-tag pass".)

### `perf_attempts` — new columns (SQLite migration, additive)

Split into **v1-essential** (build now) and **deferred** (need select-then-confirm
UI + ML infra that don't exist yet). Only the v1-essential columns are migrated
in this slice.

**v1-essential:**

| Column | Meaning |
|--------|---------|
| `chosen_index` | which option the student finally submitted (0–3) |
| `time_seconds` | *(exists)* latency — compared to per-item / per-student baseline |
| `mastery_snapshot` | content-held score `M` / FSRS retrievability at attempt time ("should they know it") |
| `inferred_error_type` | model hypothesis: content axis (distractor `maps_to`) + process axis (timing/mastery) |
| `inferred_confidence` | `p_top` of the inferred type (gates confirm vs top-2 vs unresolved) |
| `recheck_card_id` | backing card probed to disambiguate content vs application (localizes the gap) |
| `recheck_correct` | probe outcome — **objective** content-availability label (not self-report) |
| `error_source` | `inferred_confirmed` · `inference+recheck` (probe-informed + self-report agreed) · `self_report_override` · `self_report` · `unresolved` |
| `error_type` | *(exists)* **resolved** type used downstream = override → else confirmed inference |

**Deferred (until select-then-confirm UI + ML exist):**

| Column | Meaning | Why deferred |
|--------|---------|--------------|
| `first_choice_index` | first option selected (for churn) | needs select-then-confirm interaction |
| `answer_changes` | count of selection switches before submit | needs select-then-confirm interaction |
| `feature_json` | full feature vector at attempt time (timing z-score, churn, mastery/R, demand, prior, p-value) | training data for a later ML model that doesn't exist yet |
| `recheck_timing` | `immediate` (pre-reveal) \| `delayed` (next memory session) | comes with the re-check probe UI (deferred) |

*(`confirmed` / `self_report_type` are covered by today's `error_type` +
`error_source`; broken out only if the confirm UI needs them.)*

### Inference rule (v1, probabilistic, two-axis)

Inference **commits a single type + a confidence** (`p_top`) rather than
abstaining in the common case (rebalanced 2026-07-01). It is still uncertainty-
aware: the confidence, not abstention, carries the honesty, and a low-`M` or
tagged miss is still routed to `content_gap` so real gaps are not absorbed. The
branches below are the **live `infer_error_type` order — first match wins** (a
priority ladder, not a normalized distribution); they are a **bootstrap**, not
the final model (see "Confidence & ML path"). Setup:
`high_M = M ≥ 0.7`, `low_M = M < 0.4`, `mid_M` = `M` known and in `[0.4, 0.7)`,
`fast = time < 8s`, `applied_demand = demand ∈ {application, synthesis}`.

```
correct answer                         -> none            (confidence 1.0)

# 0. Content re-check probe outcome (OBJECTIVE oracle; evaluated FIRST when a
#    probe fired — recheck_correct is not None). Strongest single content signal.
wrong AND recheck FAIL (recheck_correct == False)
                                       -> content_gap     (0.9)  # strongest gap
wrong AND recheck PASS (recheck_correct == True):        # content_gap SUPPRESSED
    trap-option pick                   -> misread         (0.8)
    applied/synthesis demand           -> application     (>= 0.75)
    else (held recall/un-typed miss)   -> misread         (0.6)  # careless slip

# 1. Authored content misconception on the chosen distractor (M-INDEPENDENT):
#    acting on a specific wrong belief is direct content evidence, so this wins
#    even at high M (this is how the shallow-mastery / w_mis case is realized).
wrong AND chosen distractor has a content_gap tag
                                       -> content_gap     (0.75 if low_M else 0.65)

# 2. Low mastery: content demonstrably not held:
wrong AND low_M                        -> content_gap     (>= 0.6)

# 3. Predictable-trap landing -> misread (execution slip; content ruled out
#    above; applies regardless of demand — a trap is a slip even on recall):
wrong AND trap-option pick             -> misread         (0.75 fast+high_M
                                                           / 0.6 fast OR high_M
                                                           / 0.55 otherwise)

# 4. DEFAULT: content presumed held -> DEMAND-AWARE (what the item TESTS decides
#    the failure mode; never a demand-blind constant):
# 4a. application/synthesis demand -> application (the expected gated-miss: had
#     the pieces, deployment/transfer failed). Gate-defines-content confound.
wrong AND applied_demand AND high_M    -> application     (>= 0.7)  # strongest
wrong AND applied_demand (M mid/ambiguous/imputed/unknown)
                                       -> application     (0.55 if M None
                                                           else 0.50–0.68,
                                                           rising with M·d)
# 4b. recall demand -> content_gap (the FACT itself; a recall item has NO
#     reasoning step to fail, so NEVER application). low_M/tag/trap routed above.
wrong AND recall_demand                -> content_gap     (0.40–0.60, higher as
                                                           M drops; ~0.40 when
                                                           high_M — contradictory)
# 4c. unknown/missing demand, any M reading -> lean content_gap (honest un-typed
#     default), NOT application:
wrong AND demand unknown AND M known   -> content_gap     (0.40–0.60, as 4b)

# 5. Truly no signal: M unavailable AND unknown/missing demand AND no tag AND no
#    trap (INCLUDING fast-but-no-trap) -> abstain:
else                                   -> unresolved      (0.0) -> 3-button
                                          self-report (error_source = self_report)
```

Three things define the demand-aware rebalance. **(a) The content-presumed-held
default branches on `cognitive_demand` (branch 4)**, it is no longer a
demand-blind `application`: an `application`/`synthesis` miss commits
`application` (high-`M` + applied demand is the **strongest**, ≥0.7,
cross-system divergence; mid/ambiguous/imputed `M` commits at honestly lower
confidence via the gate-defines-content confound), while a **`recall` miss
commits `content_gap`** — a pure-recall item has no application step to fail, so
`application` there is a category error; the honest read is that the student
does not truly hold the fact. An un-typed miss leans `content_gap`. **(b)
Confidence VARIES with signal strength** rather than sitting at a flat 0.55: it
is strong when `M` is clearly high or low, when a tag/trap is authored, or when
demand strongly matches the label, and weaker (honestly) when `M` is
imputed/ambiguous — a high-`M` recall miss is deliberately *low* confidence
(FSRS says held yet a recall fact was missed → contradictory, a probe
candidate). No single constant dominates. **(c)** The distinctive-misconception
/ shallow-mastery case is realized as branch 1: an authored `content_gap` tag on
the chosen distractor commits `content_gap` directly (M-independent, 0.65,
rising to 0.8 corroborated by low `M`, 0.7 weakly opposed by high `M`) — the
concrete form of `w_mis` "keeping `content_gap` in play at high `M`." The
**exact `unresolved` condition** is narrow: `M` unavailable **and**
unknown/missing demand **and** no content tag **and** no trap (this includes a
fast-but-no-trap miss). Everything else commits. When several signals could
fire, the first matching branch wins; surface the runner-up in the confirm
prompt where useful. Confidences are conservative absolute fallbacks until
per-item baselines exist; they sharpen (not the branch choice) as data
accumulates.

**Distractor priors, not hard tags:** a distractor's `maps_to` contributes a
*prior weight* toward its content type (e.g. 0.7 `content_gap`, 0.3 nothing),
not a certainty — so tagging is never "all-for-one." Priors combine with the
other signals; confidence falls out of the combination.

## Confidence scoring & the ML path

**Now (bootstrap, rule-based):** the weighted rules above produce
`(error_type, confidence)`. Confidence sets *what* we'd ask; the salient-trigger
+ budget rules (see UX) set *whether* we ask at all — so most misses get no
prompt:

| Confidence | Behavior (if a prompt is triggered + budget allows) |
|-----------|----------|
| High (`p_top` ≥ ~0.7, clear margin — corroborated cross-system `application`, a clearly-low-`M` or low-`M`-corroborated-tag `content_gap`) | assert silently; **confirm only** if a salient signal makes it worth one tap |
| Moderate (~0.5–0.68 — the committed demand-aware default: mid/ambiguous-`M` `application` on an applied item, a mid-`M` recall `content_gap`, a bare-trap `misread`, an uncorroborated content tag) | **still commit** the type (this is where the honesty lives); optionally show **top-2** or a one-tap confirm, and prefer the re-check probe when content vs application is what's uncertain |
| Low-but-committed (~0.40–0.45 — a *contradictory* signal, e.g. a high-`M` recall miss routed to `content_gap`, or a recall/un-typed miss with `M` unavailable) | commit the type but treat as a **prime re-check-probe candidate**; the low number is the honest flag, not an abstention |
| `unresolved` (0.0 — the truly-dark miss, *not* merely "low confidence") | 3-button self-report (`error_source = self_report`), or nothing |

Note the distinction the rebalance draws: **moderate/low confidence is a
committed diagnosis, not an abstention.** `unresolved` is no longer "confidence
below a threshold" — it is the specific truly-dark branch (5) above. A
moderate-`p_top` `application`, or a low-`p_top` `content_gap` on a high-`M`
recall miss, is a real, logged, actionable diagnosis carrying its own honesty in
the number (and, when low, flagging itself for the re-check probe).

**Later (learned model):** the rules are deliberately a **data generator**, not
the destination. Every attempt logs a **feature vector** + the **confirmed
label**, giving supervised training data:

- **Features:** distractor `maps_to` prior, timing z-score vs per-item/per-student
  baseline, `answer_changes`, prerequisite mastery / FSRS-R, `cognitive_demand`,
  section/track, item p-value.
- **Label:** **objective** where possible — content re-check probe outcome and
  gold-set think-aloud labels (see "ground-truth problem"). Raw student
  confirmation is a **weak/soft signal**, not a clean training target; use it
  only as a feature or noisy label, never as the sole ground truth.
- **Model:** once n is sufficient, replace the hand weights with a calibrated
  classifier that outputs `P(type)` directly. Same confidence gate, same confirm
  loop — only the weighting is learned. Per-track models (science vs CARS) since
  their feature sets differ (mastery exists only for science).

This is why confidence + confirmation are in from day one: they make the v1 data
**ML-ready** and let us report calibration (predicted confidence vs actual
agreement) honestly.

## UX (performance dialog, on a miss)

Prompts ask for **checkable observations**, not category diagnoses (see
ground-truth problem). We map the answers to types ourselves.

### Prompt sparingly — trigger on salient signals, don't tax every miss

Popping an observation prompt after *every* miss is tedious and trains users to
tap through it (which corrupts the signal anyway). Prompts fire only when
**something is worth asking about** and we're inside a small budget:

- **Salient-behavior trigger** — surface a prompt when a signal stands out, e.g.
  an **abnormally fast** answer → *"That was quick — did you read the whole
  question, or skim it?"*; a **correct→wrong switch** → *"You changed your
  answer — what made you switch?"*. Quiet, unremarkable misses get **no prompt**
  — but they are **still committed and logged** with the inferred type (the
  demand-aware default — `application` on an applied miss, `content_gap` on a
  recall/un-typed miss — at its varying confidence), *not* logged as
  `unresolved`. Only a truly-dark miss logs `unresolved`.
- **Confidence gate** — only prompt when the answer would actually move the
  diagnosis (borderline/medium), not when inference is already confident or
  hopeless.
- **Budget / rate-limit** — cap prompts per session and don't re-ask the same
  observation type repeatedly; sample rather than exhaustively ask.
- **Always skippable** — a one-tap dismiss; a skipped prompt logs `confirmed=NULL`
  and never blocks the next question.

1. Grade the choice; if wrong, compute `(inferred_error_type, confidence)`.
2. **Content re-check probe** — *(design: only when inference hinges on
   content_gap vs application and the trigger/budget allows.)* **As implemented
   (IMMEDIATE variant): fires on every science miss with a resolvable backing
   sub-concept, before the explanation/diagnosis** — plain recall → reveal →
   self-grade → objective disambiguation, logged as `recheck_card_id` /
   `recheck_correct`. FAIL is strong; PASS is treated as solid per the accepted
   immediate-variant tradeoff.
3. **Salient signal + actionable confidence:** confirm via an **observation**
   grounded in the hypothesis, e.g. misread → *"The question asked for EXCEPT —
   did you catch that?"* [Yes/No]; application → *"Did you know [sub-concept] but
   combine/apply it wrong?"*. Yes → `confirmed=1`; No → `confirmed=0` (+ optional
   override).
4. **Moderate confidence, within budget:** the type is **already committed and
   logged**; optionally ask the one discriminating observation between top-2, or
   trigger the re-check probe when content vs application is the open question.
5. **`unresolved` (truly-dark miss) or CARS:** 3-button self-report for the
   track (`error_source=self_report`), logged as weak signal only. Note this
   fires only for the narrow truly-dark branch (and every CARS miss), **not** for
   an ordinary moderate-confidence diagnosis.

## Validation — two tiers (do not confuse them)

**Tier 1 — consistency monitor (cheap, NOT truth).** Confirmation agreement:

```
inference_agreement = confirmed=1 / (confirmed=1 + confirmed=0)   # per type, per topic, with n
```

This only measures whether inference agrees with **self-report**, which is
itself unreliable — so it is a **consistency signal, not accuracy**. Use it to
flag problems (systematic disagreement on a type → likely mislabeled priors),
never to claim the engine is "X% correct."

**Tier 2 — objective validation (the real number).** Accuracy is measured
against **objective labels**, not opinion:
- **Content re-check probe** — post-miss recall of the backing sub-concept
  objectively settles content_gap vs (application/misread), asymmetrically
  (FAIL strong, PASS weak).
- **Gold set** — ~20–30 held_out items with think-aloud labels → compute true
  precision/recall of the inference, and **calibration** (does predicted
  confidence match observed correctness?).

**Gating rule (softened for small n):** early validation estimates
**directional quality** — especially `content_gap` vs non-`content_gap` (the
load-bearing split) — rather than per-type precision/recall. Per-type
precision/recall is reported **only when sample size is adequate**. The
dashboard's "next action" leans on an inferred type only when its Tier-2 signal
clears the bar available at that n; otherwise abstain or label "self-reported"
— same abstention philosophy as readiness. Honest reporting states
*"error-diagnosis accuracy = X% on gold set (n=…)"* (or, at low n, only the
directional content-vs-not signal), never dressing up self-report agreement as
ground truth.

**Upstream sanity check (memory ⟂ performance).** The §7d **paraphrase-gap
instrument** (`docs/PARAPHRASE-TEST.md`) validates the premise this whole engine
rests on — that a performance miss can be a *transfer* failure distinct from a
*recall* failure. It compares flashcard recall against accuracy on reworded
questions of the same concept (`paraphrase_gap = card_recall_rate −
question_accuracy`); a persistently near-zero gap at high recall would mean
performance is echoing memory and the `content_gap`↔`application` split has little
to separate. It is a bank-level instrument, not a per-attempt label — kept
separate from the two tiers above (don't conflate its gap with diagnosis
accuracy).

## Next-action mapping (dashboard "Focus area")

The diagnosed weakness must turn into **one concrete click**. Map the top
diagnosed weakness (`error_type` × `topic`) to a single action:

| Diagnosed type | Next action | Launches |
|----------------|-------------|----------|
| `content_gap` | **"Review N flashcards in [topic]"** | filtered **memory review** for the topic's backing cards |
| `application` ("Applied reasoning") | **"Practice N applied questions in [topic]"** | a **performance session filtered** to application/synthesis items in that topic |
| `misread` | **"Careful-reading / pacing drill"** | a short timed/careful-reading drill (or a pacing tip if no drill deck) |

This surfaces as a **prominent "Focus area" card** on the home dashboard — the
**same visual weight as the three scores** — that names the top weakness and
launches the matching practice in **one click**. Logic lives in
`mcat_scores.py` (compute the top weakness → action); the tile lives in
`deckbrowser.py` (render + wire the button). It abstains gracefully (no
diagnosed misses yet → a "start a session / study to unlock" prompt, never a
fabricated focus area).

## Deferred remediation (diagnose now, re-learn later)

Diagnosis and re-learning are **separate clocks**. The content re-check probe
(the disambiguator) may fire **immediately** after the miss — it is a *test*, not
a study event, and reading the answer explanation post-attempt is normal feedback
and fine. **Re-learning must be deferred.** On a *confirmed* `content_gap`, do
**not** re-show the backing card in the same session; instead **down-weight the
card's FSRS state** (treat the miss as a **lapse** — reduce stability / reset the
card toward a shorter interval) so it **resurfaces in a future memory-mode
session** at a spaced interval.

Why: re-showing the just-missed card immediately produces the **massed-practice
fluency illusion** — the answer is in working memory, recall feels effortless,
and the student mistakes momentary fluency for durable learning. Spacing the
re-review is what actually rebuilds the memory. So:

- **Immediate (allowed):** the re-check probe; the post-attempt answer
  explanation.
- **Deferred (required):** spaced re-learning of the card, via a lapse-style
  FSRS down-weight that schedules it into a later memory session — never an
  in-session re-drill.

## Two-channel remediation routing

The resolved error type routes to **different channels** — a content gap and an
application gap are *not* fixed the same way, and a misread is fixed by neither:

| Resolved type | Channel | Concrete remediation |
|---------------|---------|----------------------|
| `content_gap` | **Memory (spaced)** | Down-weight the **specific backing COMPONENT card**'s FSRS state (lapse) so it returns in a **future** memory-mode review — not an immediate re-show. |
| `application` (incl. shallow-mastery / `application_gap`) | **Performance (practice)** | **WIRED (2026-07-02):** launches a **real short practice set** from the isolated application-practice pool — targeted **practice on similar integration items** in that topic. The component facts are already held; the missing skill is chaining them. **Not** a flashcard. |
| `misread` (`trap`) | **Behavioral nudge** | A pacing / careful-reading nudge (watch signs, units, `EXCEPT`) — no card, no practice bank; the concept and application were both fine. |

The key asymmetry: routing an `application` miss to flashcards re-drills facts
the student already knows (false comfort, no skill gain), and routing a
`content_gap` to more integration practice asks them to chain a component they
don't yet hold. Route to the channel that fixes the *actual* failure.

### `application` channel — the wired remediation pool (2026-07-02)

The `application` next-action is no longer a generic message with nothing to
launch. On a **resolved `application`** miss the performance dialog
(`qt/aqt/mcat/performance_dialog.py`) surfaces a concrete, launchable practice
set drawn from the **application-practice pool** (`data/application-practice.json`
— 45 science integration items, 3 per topic). See
[`APPLICATION-PRACTICE-POOL.md`](APPLICATION-PRACTICE-POOL.md) for the pool and
its schema.

**Selection rule** (deterministic, AI-off — `select_application_practice` in
`pylib/anki/mcat_perf.py`): on a miss with diagnosis `application`, topic `T`,
just-missed concept `C` → (1) filter the pool to `topic_id == T` and
`pool == 'application_practice'`; (2) exclude items whose `concept == C` (fall
back to same-concept items if that empties the set); (3) exclude already-seen
pool ids (the seen-set); (4) rank for concept variety (distinct concepts first,
deterministic id order); (5) take **N = 2** (`N_APPLICATION_PRACTICE`, a config
constant). The set is served as a **separate, clearly-unscored** practice window
(`RemediationDialog`). **Degradation contract preserved:** when the pool yields
no eligible items (e.g. a topic with no pool coverage, or everything already
seen) the action falls back to the generic *"practice more applied items in
\[topic]"* message rather than promising a bank that isn't there.

**Never-scored guarantee (isolation invariant).** The pool lives in its own
sidecar table `remediation_items` (a DB `CHECK (split = 'remediation')` rejects
any scored item), and practice attempts are logged to a separate
`remediation_attempts` channel via `PerfStore.log_remediation_attempt` — **never**
`perf_questions` / `perf_attempts`. Nothing on this path is read by `accuracy()`,
`eligible_questions()`, or the sync bundle, so an `application` remediation item
can **never** enter the Performance or Readiness scores, nor a held_out/dev
scored session. This is only the **`application`** channel; `content_gap` (review
the backing concept) and `misread` (pacing nudge) routing are unchanged.

## Component cards, not answer cards

Backing cards must encode **prerequisite COMPONENTS**, never the **integrated
answer / exception** the synthesis question tests. Carding the integrated
conclusion collapses **synthesis → recall**: the student "masters" the card, `M`
reads high, yet they never practiced the chaining the question demands — a
**false mastery** that the diagnosis engine then mislabels (a real application
gap looks like "should have known it"). An answer-encoding card also **poisons
the cross-system signal**, since high `M` on the exact answer removes the
divergence that distinguishes `application` from `content_gap`.

Rules:

- **Never** author a card that states the question's integrated answer or its
  exception (e.g. *not* "Competitive inhibition: Vmax unchanged, Km↑, overcome by
  excess substrate" for an inhibition item — that *is* the answer).
- **Do** author each prerequisite as its **own granular component card** (e.g.
  "a competitive inhibitor binds the active site, competing with substrate" +
  "excess substrate outcompetes a reversible active-site binder"). The student
  chains components at question time.
- **Prescription:** keep adding **more granular component cards** so every
  question's prerequisites are each individually carded. This both improves
  prerequisite coverage *and* sharpens per-card `M` (finer-grained retrievability
  → a cleaner content-held signal) — but **never** add an answer-encoding card to
  get there.

## Residual risk — the boundary moved, not removed

Collapsing to a **3-bucket** scheme (`content_gap` / `application` / `misread`)
does **not** remove the hardest classification boundary — it **relocates** it.
The entire split now hinges on the `content_gap`↔`application` line, and that
line rests on exactly the two **least-tested** pieces of the design: the
content-held score `M` and the content re-check probe. If the probe is
contaminated (PASS inflated by priming — see the asymmetry) or `M` is
mis-estimated (stale/decayed cards, uncovered prerequisites), **`application`
will silently absorb real content gaps** — mislabeling a student who *doesn't
know it* as one who *couldn't apply it*, and sending them to applied practice
instead of the flashcards they need.

**The rebalance (2026-07-01) deliberately raises this exposure and must be
audited.** By committing `application` on a content-presumed-held **applied**
miss — including mid-`M` and ambiguous/imputed-`M` applied misses that formerly
went `unresolved` — more applied misses now land in `application` by
construction. That is the intended trade (commit + varying confidence beats
over-abstaining), but it means the `content_gap`↔`application` boundary now
carries *more* weight, not less. What holds the line: (1) an authored
`content_gap` tag or low `M` still pre-empts `application` (branches 1–2 run
first), so tag coverage and `M` quality are the real safeguards; (2) **the
demand split** keeps `recall` misses out of `application` entirely (they route
to `content_gap`), so the exposure is confined to genuinely applied/synthesis
items; (3) the applied default fires at **lower confidence** on
mid/ambiguous-`M`, which flags it as a probe candidate rather than a settled
fact; (4) persistent student overrides of `application`→`content_gap` are the
measurable audit signal that the default is over-firing. The **inverse risk**
the demand split introduces — a genuinely applied miss authored (or left) as
`recall`, or a shallow-mastery recall item — now routes to `content_gap`
instead, i.e. toward flashcards; that is the conservative direction (re-drill
the fact) and is caught by the same override/probe audit. This is the **named
residual risk** of the rename *and* the rebalance; it is mitigated (not
eliminated) by the asymmetric probe (FAIL strong), the demand split, the
varying-confidence framing, and tag/`M` coverage, and it is tracked in
`LOOSE-ENDS.md`.

## Migration from the Wednesday 4-button enum

The Wednesday-shipped self-report enum — 4 buttons: `content_gap`,
`passage_mapping`, `reasoning`, `misread` — stays **FROZEN** as the currently
shipped functionality. **This v2 spec supersedes it:** `reasoning` is renamed to
`application` ("Applied reasoning"), and `passage_mapping` **folds under
`application`** as a documented sub-mode (no longer its own live bin). Net: the
v2 science self-report fallback is **3 buttons** (`content_gap`, `application`,
`misread`). The enum migration (rename + fold, plus any `perf_attempts`
back-fill of historical `reasoning`/`passage_mapping` rows to `application`)
should happen **when v2 is built**, not before — the Wednesday build is not
touched.

## Build order

1. Add `choice_diagnosis` (content axis) + `cognitive_demand` (question level)
   to a starter subset in `questions.json` + validator rules (see mechanism
   end-to-end before tagging all 110).
2. `perf_attempts` migration (additive columns) in `PerfStore`.
3. `PerformanceSession`: compute the ranked `inferred_error_type` — **cross-system
   check first** (invert `supports_question` → prerequisite mastery × demand),
   then behavior (timing/answer-change), then content axis (`choice_diagnosis`);
   `confirm_error()` / `override_error()` wrapping today's `classify_error()`.
4. Dialog: **observation-based** confirm prompt (checkable fact, not category)
   + optional **content re-check probe** (log `recheck_correct`); keep 3-button
   fallback for `unresolved`.
5. Bulk-author `choice_diagnosis` for all 110 questions (in
   `build_question_bank.py`) — content-axis tags only.
6. **Validation:** Tier-1 consistency report (agreement by type/topic, n) **and**
   Tier-2 gold-set accuracy + calibration (the number we actually trust).

## Non-goals (v1 of this mechanism)

- **ML classifier is roadmap, not v1** — v1 is rule-based weights + confidence +
  confirmation, *designed to generate the training data* (`feature_json` +
  objective labels from re-check probe / gold set). The learned model comes once
  n is sufficient.
- No eye-tracking / keystroke forensics.
- Timing/answer-change modifiers stay optional until baselines exist.

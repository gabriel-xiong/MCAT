# Tag Validity — is `choice_diagnosis` good ground truth for the AI differentiation eval?

**Question.** The AI explainer's headline **choice-specificity** metric
(`scripts/ai_eval_explanations.py → names_error_mode`) scores whether a model
names the error mode of the chosen distractor, using each choice's
`choice_diagnosis` tag as ground truth. That is only meaningful if a
knowledgeable human, seeing *only the question + chosen distractor*, could
independently recover the same tag. If tags are ambiguous or generic, the eval
measures noise. This doc quantifies how **recoverable / distinctive** the tags
are, with emphasis on the eval trio (`cp_acids_bases`, `bb_enzymes`,
`cp_kinetics`).

**Scope / constraints.** Analysis only. New files only; nothing in
`data/questions.json` or the AI scripts/docs was modified. Not committed.

**Reproduce.**
```
py -3.12 scripts/analyze_tags.py            # distribution + distinctiveness
py -3.12 scripts/build_recoverability_sheet.py   # (re)build blind pilot instrument
py -3.12 scripts/score_tag_agreement.py     # score filled human labels vs key
```

The 3-axis scheme (per `diagnose_choice`): `content_gap` (a SPECIFIC
misconception), `trap:<enum>` (execution slip:
inverse/unit/scaling/negation/transpose/partial), `null` (non-diagnostic
near-miss). The correct slot is always `null`.

---

## 1. Distribution audit (distractors only; correct slot excluded)

**170 questions, 510 distractors.**

| map | overall | trio |
|---|---|---|
| `content_gap` | **374 (73.3%)** | **165 (88.7%)** |
| `trap:*` | 21 (4.1%) | 12 (6.5%) |
| `null` | 115 (22.5%) | 9 (4.8%) |

Trap breakdown (whole bank, n=21): partial 6, inverse 6, scaling 4, negation 3,
unit 1, transpose 1.

Per-topic (trio starred):

| topic | nQ | content_gap | trap | null | cg% |
|---|--:|--:|--:|--:|--:|
| *bb_enzymes | 22 | 62 | 0 | 4 | 93.9% |
| *cp_acids_bases | 23 | 59 | 7 | 3 | 85.5% |
| *cp_kinetics | 17 | 44 | 5 | 2 | 86.3% |
| cp_electrochem | 11 | 26 | 4 | 3 | 78.8% |
| cars_* (3 topics) | 13 | 0 | 0 | 39 | 0% |
| (others) | … | … | … | … | … |

**Takeaway — content_gap dominance.** Nearly 3 of every 4 distractors bank-wide
(and ~9 of 10 in the trio) are tagged `content_gap`. Traps — the most objectively
recoverable category — are rare (4% overall). So the eval leans almost entirely
on the *fuzziest* category for its "signal," and `bb_enzymes` in particular has
**zero traps**. CARS is 100% `null` by design (no flashcard gate), so it
contributes nothing to a misconception-recovery metric.

---

## 2. Distinctiveness audit of `content_gap` tags

For each `content_gap` distractor we judged whether the misconception encodes a
**distinctive, uniquely-identifiable** error (names an alternative concept, a
reversed relationship, or a specific category confusion — *recoverable*) vs a
**generic** "just wrong" restatement/negation of the choice (*not recoverable as
an error mode*), with **borderline** in between. Method: a transparent marker +
choice-overlap heuristic in `analyze_tags.py`, hand-verified against the full
dump.

| label | overall (n=374) | trio (n=165) |
|---|---|---|
| distinctive | 196 (52.4%) | 87 (52.7%) |
| borderline | 149 (39.8%) | 61 (37.0%) |
| generic | 29 (7.8%) | 17 (10.3%) |

Roughly **half** of content_gap tags are genuinely distinctive; ~40% are
borderline; ~8–10% are generic. Psychology topics score highest on
distinctiveness (ps_memory 87%, ps_social 87%, ps_learning 77%); the trio sits
near the middle (~48–56%).

**Distinctive examples (recoverable):**
- `q_dev_005/B` "Binds to the active site and blocks it…" → *describes
  competitive inhibition rather than allosteric* (names the alternative concept).
- `q_ho_082/B` "binds substrate more tightly (higher affinity)" → *reverses the
  relationship — treats higher Km as tighter binding* (specific relation flip).
- `q_ho_062/D` "produces OH⁻ only by dissociating" → *uses the narrower Arrhenius
  definition, not Brønsted–Lowry proton acceptor*.
- `q_ho_073/A` "exergonic and energy-releasing" (for ΔG>0) → *swaps the
  exergonic/endergonic definitions*.
- `q_ho_089/C` "bond dissociation enthalpy" → *confuses activation energy with a
  specific bond quantity*.

**Generic examples (not distinctive — just negates/restates the choice):**
- `q_dev_003/A,B` "believes it is false that endergonic reactions have +ΔG…" —
  pure restatement of a "which is false" option; carries no error mode beyond
  "picked this option."
- `q_dev_011/A` "thinks a buffer is a strong acid plus a strong base" — restates
  the distractor text.
- `q_ho_027/A` "thinks the enzyme is consumed" — echoes the choice.

**Borderline examples:** `q_dev_015/A` "thinks temperature raises ΔG and that
speeds the reaction"; `q_ho_080/D` "makes the thermodynamic outcome depend on
substrate concentration" — real ideas, but a labeler could phrase or attribute
them several ways.

---

## 3. Blind self-labeling recoverability PROXY (estimated human ceiling)

We built the blind instrument (§4), then the analyst assigned an error mode to
**40 trio cases** (12 trap, 20 content_gap spanning distinctive/borderline/
generic, 8 null) from **only** the stem + choices + chosen distractor, and scored
against the hidden key with `score_tag_agreement.py`.

> **Honesty caveat.** The analyst had already viewed the tags while doing §1–§2,
> so this is a *contaminated, optimistic* proxy — an **upper bound** on the true
> human ceiling. A real, uncontaminated human pilot (instrument in §4) should be
> expected to score **at or below** these numbers.

**Headline results (n=40):**
- Coarse (content_gap / trap / null) agreement: **0.800**; Cohen's **κ = 0.649**
  ("substantial").
- Fine agreement (trap enum must also match): **0.775**.

**By gold map:**

| gold map | n | coarse agree | notes |
|---|--:|--:|---|
| content_gap | 20 | 1.000 | but see recovery below; content_gap is the *default* guess |
| trap | 12 | 0.667 | 4 gold traps were absorbed into content_gap |
| null | 8 | 0.500 | analyst invented misconceptions for genuine near-misses |

**The number that matters for the eval — content_gap misconception recovery** at
the eval's own bar (token overlap ≥ 0.6 vs the stored misconception):
**13/20 = 0.65.** Broken down by distinctiveness:

| distinctiveness | recovery @0.6 |
|---|--:|
| distinctive | 6/10 = 0.60 |
| borderline | 4/6 = 0.67 |
| generic | 3/4 = 0.75 |

**Trap enum** exact recovery: **7/12 = 0.583** (κ=0.478). But of the 8 numeric
distractors the analyst *did* recognize as traps, enum was correct on **7/8
(0.875)** — traps are highly recoverable *when the item is an unambiguous
execution slip* (ratio inversion, doubling→halve/quadruple, ×10 per pH unit).

### What the divergences reveal (the noise sources)

1. **`content_gap` is an over-applied catch-all.** Of 28 analyst `content_gap`
   labels, only 20 were gold content_gap → **precision 0.71** (recall 1.00). The
   category vacuums up genuine `null` near-misses (C04, C24, C25, C34) and
   execution traps (C14, C23, C32, C38).

2. **The `trap` ↔ `content_gap` boundary is leaky on numeric items.** 4 of 12
   gold traps were independently labeled content_gap. Example, `q_ho_013` (order
   of `k[A][B]²`): the choice "1" is tagged **trap:partial**, "0" is **null**,
   and "2" is **content_gap** — three different maps for three wrong orders on the
   *same* question. `q_ho_088` (zero-order doubling): "quadruple" = content_gap
   but "halve" = trap:inverse. This within-question inconsistency is exactly what
   depresses inter-rater recoverability.

3. **The eval's 0.6 overlap check is *lexical*, and it is perverse.**
   Conceptually-correct independent phrasings still miss the bar ~35% of the time
   (e.g. C31: analyst wrote "confuses activation energy with bond dissociation
   enthalpy" vs gold "names bond dissociation enthalpy, a specific bond quantity,
   not the reaction's energy barrier" → <0.6 overlap, scored a MISS despite being
   right). Worse, **generic tags are recovered *more* often (0.75) than
   distinctive tags (0.60)** because a generic tag just restates the choice, so
   any on-topic sentence overlaps it. The metric partly rewards "talked about the
   right choice" over "named the specific error mode."

---

## 4. Blind human-labeling instrument (for a real pilot)

Built by `scripts/build_recoverability_sheet.py` (seeded, stratified over the
trio). Give the sheet to a knowledgeable human; keep the key hidden.

- **Sheet (tags withheld):** `data/tag-recoverability-sheet.json` — 40 cases,
  each with stem, choices, correct letter, and the chosen distractor. Labeler
  fills `content_gap|trap|null` (+ trap enum, + free-text misconception).
- **Hidden key:** `data/tag-recoverability-key.json` — gold map + trap enum +
  stored misconception + heuristic distinctiveness. **Do not show the labeler.**
- **Blank template:** `data/tag-recoverability-human.TEMPLATE.json` (copy to
  `data/tag-recoverability-human.json` and fill).
- **Scorer:** `scripts/score_tag_agreement.py` — % agreement (coarse + fine),
  **Cohen's κ**, content_gap misconception recovery @0.6, and all breakdowns by
  gold map and distinctiveness.
- A filled example (the contaminated analyst proxy of §3) is at
  `data/tag-recoverability-human.json` so the scorer runs out of the box; replace
  it with real human labels for the true ceiling.

---

## 5. Verdict + recommendations

**Is there enough distinctive, recoverable signal for the differentiation eval to
be meaningful?** **Yes — but only on a subset, and the current metric measures a
blend of real signal, noise, and a lexical artifact.**

- **Real signal exists** where it is concentrated: **traps that are clearly
  execution slips** (recovered ~0.88 enum-when-recognized) and **distinctive
  content_gaps** that name an alternative concept or a reversed relationship
  (concept-level recall 100%; κ overall 0.65 = substantial). These are legitimate
  ground truth a human can independently reproduce.
- **Weak / noisy tags** dilute it: the ~40% borderline + ~8–10% generic
  content_gaps, the leaky `trap↔content_gap` boundary on numeric items, and the
  soft `null↔content_gap` boundary (content_gap precision only 0.71).
- The **0.6 token-overlap check** is the biggest structural problem: it under-
  credits distinctive tags and over-credits generic restatements, so a high
  choice-specificity score does **not** by itself prove per-choice
  differentiation.

**Strong vs weak, by category/topic:**
- Strong: `trap:*` on unambiguous items; distinctive content_gaps; psych topics
  (ps_memory/ps_social/ps_learning) and, in the trio, most of `bb_enzymes` and
  `cp_acids_bases` conceptual items.
- Weak: generic "which-is-false" restatements (`q_dev_003`-style); numeric
  order/pH distractors sitting on the trap/content_gap/null fault line
  (`q_ho_013/014/088`, `q_ho_005/066/008`); anything tagged `null` (correctly
  non-diagnostic — should not be scored for error-mode naming).

**Recommendations (do NOT change `questions.json` here — for the AI-file owner):**
1. **Lean the headline choice-specificity metric on the high-signal subset:**
   report it over `{trap} ∪ {distinctive content_gap}` and show `{borderline,
   generic content_gap}` separately. Don't let generic tags inflate the number.
2. **Down-weight or re-tag generic content_gaps.** The ~29 bank-wide (17 trio)
   pure restatements/negations carry no error-mode signal beyond "picked wrong";
   re-tag as `null` or exclude from the choice-specificity metric. (Keeping them
   makes the metric *look* better while measuring less.)
3. **Fix the boundaries with a written rubric** so structurally identical
   distractors get consistent maps: pick one rule for numeric order/power errors
   (e.g. wrong power → `trap:scaling`; wrong sign/direction → `trap:negation`/
   `inverse`; conceptual "which order" confusion → `content_gap`) and apply it to
   all distractors of a question. `q_ho_013` currently violates this.
4. **Reform the content_gap check** from raw token overlap to a concept-level
   match — e.g. score against a short controlled misconception key / required
   concept token(s) per distractor — so distinctive vocabulary isn't penalized
   and generic restatement isn't rewarded.
5. **Run the real human pilot** (§4) to replace the contaminated proxy. Treat the
   proxy numbers (content_gap recovery **0.65**, trap-enum **0.58**, κ **0.65**)
   as **ceilings**; if a fresh human lands materially lower on the full tag set
   but stays high on the high-signal subset, that confirms restricting the metric
   is the right call.

**Bottom line:** keep the differentiation eval, but run it on **traps +
distinctive content_gaps**, exclude `null` and (at minimum down-weight) generic
content_gaps, and replace the lexical-overlap check with a concept-level match.
That converts a metric that currently scores ~human-ceiling 0.65 with a lexical
bias into one that actually measures per-choice error-mode identification.

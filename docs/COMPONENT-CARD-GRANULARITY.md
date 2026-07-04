# Component-card granularity

Status of the "component cards, not answer cards" decomposition: each performance
question should have **one atomic backing card per prerequisite sub-concept**, not
merely ≥1 backing card total. Finer, correctly-linked component cards sharpen
per-card `M` (FSRS-R) so the re-check probe (which inverts `supports_question`)
can localize the *specific* failed prerequisite.

Owner of this pass: `scripts/build_flashcards.py` + `data/flashcards-*.csv` only.

## Guardrail — no answer-encoding

Every card added here teaches a foundational prerequisite fact (OpenStax-grounded),
**never** the integrated answer to its MCQ. Three drafts that sat too close to an
item's own answer were reframed or dropped:

- `q_dev_005` (allosteric inhibitor lowers affinity) → generalized to the
  **activator-vs-inhibitor direction** so it teaches the concept, not the answer.
- `q_syn_004` (enzyme changes rate not ΔG/Keq) → reframed to the **underlying
  reason** (ΔG/Keq depend only on the reactant–product free-energy difference).
- `q_dev_016` (catalyst = alternate pathway, lower Ea) → **not re-authored**: that
  phrasing is the item's own answer, and the existing "catalyst lowers Ea, doesn't
  change ΔG/equilibrium" card already backs it.

## Answer-leak audit — probe backing cards (whole-bank pass)

The content re-check probe inverts `supports_question`: it shows a backing card's
front so the student self-tests the **prerequisite**. A card *leaks* when its
de-clozed front, on its own, states the linked question's **own answer/outcome** —
a student could then "pass" the probe by recognizing the answer rather than by
knowing the upstream concept.

**Scope of the audit.** All 127 questions that have backing cards were compared
(each card front vs. that question's correct choice + explanation). Recall items
(`q_dev_*`, most `q_ho_*`) legitimately have card ≈ tested fact — there is no
distinct upstream prerequisite, so those are *not* leaks. Leaks were found only on
**application/synthesis** items where a single card encoded the derived directional
or numeric outcome. Six cards were fixed (5 reframed, 1 unlinked); one prerequisite
card was added.

| Question(s) | Before (leaking front) | After (prerequisite front) |
|-------------|------------------------|----------------------------|
| `q_syn_007`, `q_ho_002` (electrochem) | "By the Nernst equation, raising the concentration of product ions **lowers the cell potential**." — verbatim answer (Ecell decreases) | "In the Nernst equation Ecell = E°cell − (RT/nF)ln Q, the reaction quotient is Q = **[products]/[reactants]**, so adding product ions **raises** Q." — teaches the governing equation + Q; student derives the −lnQ direction |
| `q_syn_017` (osmosis) | "In osmosis, water moves toward the hypertonic side; **a cell in a hypotonic solution swells and may lyse**." — the item's own outcome | "…water moves toward the **hypertonic** (higher-solute) side." **+ added** tonicity-vocabulary card ("lower solute ⇒ **hypotonic**, higher solute ⇒ **hypertonic**"). Student predicts swelling/lysis |
| `q_syn_024` (strong vs weak acid) | "A strong acid ionizes completely **(lower pH)**; a weak acid … only partially **(higher pH)**." — the comparative answer | "A strong acid ionizes **completely** in water, whereas a weak acid at the same concentration ionizes only **partially**." Student connects ionization → [H⁺] → pH |
| `q_syn_009` (Henderson–Hasselbalch) | "Henderson–Hasselbalch: pH = pKa + log([A⁻]/[HA]); when [A⁻] = [HA], **pH = pKa**." — equals the answer (equal ⇒ pH = pKa) | "Henderson–Hasselbalch relates buffer pH to pKa: pH = pKa + log(**[A⁻]/[HA]**)." Student applies log(1)=0 |
| `q_syn_011` (buffer ratio) | "…raising pH by 1 unit above the pKa multiplies the [A⁻]/[HA] ratio **by 10**." — the item's 10:1 answer | "Rearranging Henderson–Hasselbalch, the buffer ratio is [A⁻]/[HA] = **10^(pH − pKa)**." Student plugs pH − pKa = 1 |
| `q_syn_020` (derive rate law) | shared card "For rate = k[A][B]², the overall reaction order is 3" — front shows the exact rate law `q_syn_020` must **derive from data** | **Unlinked** from `q_syn_020` (still backs `q_ho_013` recall). `q_syn_020` keeps the order-definition, first-order-scaling, and method-of-initial-rates cards |

`data/paraphrase-test.json` anchors `card_front` for the two reworded trio
concepts (`henderson_hasselbalch`, `strong_vs_weak_ionization`) were updated to
match the reframed fronts. Coverage held: every one of the 127 previously-backed
science questions still has ≥1 backing card (`q_syn_020` → 3, `q_ho_002` → 1).

> Not flagged (deliberate): cards that teach a **governing law** an application item
> must still *apply* (e.g. Bernoulli/continuity for `q_syn_022`, `ΔG° = −nFE°cell`
> for `q_syn_006`, `E°cell = E°cathode − E°anode` for `q_syn_005`) — this is the
> guardrail-approved "teach the equation, not the outcome" pattern. `q_syn_021`
> ("thermodynamics and rate are independent") and `q_dev_016` (catalyst) remain as
> previously decided.

## Eval trio — what was decomposed

Cards added in this pass (all Cloze, all within-topic links):

| Topic | Cards before | Added | Cards after |
|-------|-------------:|------:|------------:|
| `bb_enzymes` | 18 | 11 | 29 |
| `cp_acids_bases` | 15 | 8 | 23 |
| `cp_kinetics` | 9 | 5 | 14 |
| **trio total** | 42 | 24 | 66 |

### bb_enzymes (11 added)
- `q_dev_003`: endergonic-absorbs / exergonic-releases energy; both reactions must
  cross an activation-energy barrier (the two true-statement prerequisites the
  "false comparison" item leans on).
- `q_dev_004`: activation energy is a kinetic (not thermodynamic) property — why it
  can't be read from ΔG/spontaneity.
- `q_dev_005`: allosteric activator raises vs inhibitor lowers active-site affinity.
- `q_ho_026`: the allosteric site as the named contrast to the active site.
- `q_ho_027`: enzyme is not consumed; substrate is chemically transformed (the two
  distractor prerequisites).
- `q_ho_028`: definition of denaturation (loss of 3-D shape distorting the active site).
- `q_syn_003`: controlled variable; independent-vs-dependent variable (experimental-
  design prerequisites for the "what must be held constant" item).
- `q_syn_004`: ΔG/Keq depend only on the free-energy difference (catalyst-invariant).

Example: *"Both endergonic and exergonic reactions must first overcome an
activation-energy barrier"* supports `q_dev_003` — a prerequisite, not the answer
(the item's answer is that the *speed* comparison is false).

### cp_acids_bases (8 added)
- `q_dev_006`: NH₃ + H₂O ⇌ NH₄⁺ + OH⁻ (the weak-base equilibrium the item is built on).
- `q_dev_006`/`q_syn_012`: common-ion effect (shared prerequisite).
- `q_dev_007`: explicit inverse acid ↔ conjugate-base strength relationship.
- `q_dev_011`: a strong-acid/strong-base pair cannot buffer (distractor prerequisite).
- `q_ho_007`: Kw = 1.0×10⁻¹⁴ at 25 °C; neutral solution ≡ [H⁺] = [OH⁻] (two atomic parts).
- `q_syn_011`: Henderson–Hasselbalch ratio proportionality (each pH unit above pKa ⇒ ×10).
- `q_syn_012`: suppressed ionization ⇒ lower percent dissociation.

Example: *"At 25 °C the water autoionization constant Kw = [H⁺][OH⁻] = 1.0×10⁻¹⁴"*
supports `q_ho_007`; paired with the separate *"neutral solution ≡ [H⁺] = [OH⁻]"*
card, the two prerequisites resolve independently.

### cp_kinetics (5 added)
- `q_dev_015`: raising temperature does **not** lower Ea or change ΔG (distractor prereqs).
- `q_dev_017`: the Arrhenius relationship names k's temperature dependence.
- `q_ho_016`: Ea is the transition-state barrier, not the reactant–product ΔH/ΔG.
- `q_syn_020`: method-of-initial-rates procedure (not the specific rate law).
- `q_syn_021`: thermodynamic favorability and rate are independent (prereq, not "high Ea").

Example: *"Method of initial rates: find a reactant's order by comparing experiments
in which only that reactant's concentration changes"* supports `q_syn_020` — the
procedure, never the answer `rate = k[A][B]²`.

## Coverage status

All 127 science questions still have ≥1 backing card (builder self-check passes; no
dangling `supports_question` ids).

### Trio — remaining under-decomposition (minor)
The trio is now well decomposed. Residual notes:
- `q_syn_011` / `q_ho_008` rely on quantitative H-H / log-scale relationships that are
  taught as single proportionality cards rather than fully worked steps; acceptable
  as atomic facts, flagged only for completeness.
- No trio question is missing a per-prerequisite card after this pass.

### Beyond the trio — NOT yet decomposed (tracked)
These topics still guarantee only ≥1 backing card per question, not one-per-prerequisite.
Candidates for the next granularity pass (highest-value first):
- `bb_citric_acid`, `bb_glycolysis` — multi-step pathway items (`q_dev_001`,
  `q_syn_016`, `q_ho_023`…) would benefit from per-step atomic cards.
- `cp_electrochem` — `q_syn_005`–`q_syn_008` (cell-potential sign conventions, Nernst
  vs standard, ΔG°=−nFE°) partly decomposed; distractor prereqs could be finer.
- `cp_thermo` — spontaneity sign combinations (`q_ho_009`, `q_dev_012`).
- `bb_genetics` — probability-product / dihybrid steps (`q_syn_013`, `q_syn_014`).
- `bb_membranes`, `bb_dna`, and the PS topics (`ps_memory`, `ps_learning`,
  `ps_social`, `ps_demographics`) — mostly single-fact recall items; lower priority.

## Follow-ups deliberately NOT done (for the reconciliation pass)

Per file-ownership constraints, this pass touched only `build_flashcards.py` and the
flashcard CSVs. The following still need to be run/updated by the owner:
- **`scripts/build_question_card_map.py`** — regenerate so the map reflects the 24 new
  card→question links.
- **`docs/QUESTION-CARD-MAP.md`** — regenerate from the above (per-question card lists +
  per-topic coverage table will change for the trio).
- **`scripts/validate_data.py`** — run to confirm the new cards introduce no schema/link
  violations (no `questions.json` change was made, so this is a verification, not a fix).
- **Cloze-share note:** the deck is at 83% Cloze vs the soft ~70–80% target (all 24 new
  cards are atomic Cloze facts). Non-blocking; rebalance only if desired.

`data/flashcards-dev-basic.csv` was intentionally left unchanged (no Basic cards added).

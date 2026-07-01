# Synthesis & Application Questions — REVIEW DRAFT

**Status:** Reviewed + fixed + **INTEGRATED** (2026-07-01). All three required
fixes applied (see "Fixes applied" at the end), then the 30 `q_syn_*` items and
27 new backing cards were appended (append-only) to
`scripts/build_question_bank.py` / `scripts/build_flashcards.py` and
regenerated. Bank is now 140 questions (dev 65 / held_out 75); every `q_syn_*`
has ≥1 backing card; validator + leakage check pass. This file remains the
human-readable spec of record. Written to satisfy `ERROR-DIAGNOSIS-SPEC.md`: the current bank is
recall-heavy and cannot exercise the `application`/`content_gap` split, which is
the whole differentiator. These 30 items are majority **synthesis**, the rest
**application**, each with an authored **content-axis `choice_diagnosis`** and a
list of **backing flashcards** (existing + new) so the cross-system signal
(memory ⟂ performance) can actually fire.

Author does NOT edit `data/questions.json`, `scripts/build_question_bank.py`,
`scripts/build_flashcards.py`, `data/flashcards-dev*.csv`, or
`curation-status.json` — another agent owns those right now. This file is the
reviewable spec the user approves before integration.

---

## How these differ from the existing 110

- Existing items are mostly single-fact recall (define X, which enzyme does Y).
- Every item here **integrates ≥2 concepts** (synthesis) or **applies a concept
  to novel data / a multi-step calculation** (application). None are pure recall.
- Each carries two **new** question-level/authoring fields the spec requires but
  the current schema doesn't yet emit:
  - `cognitive_demand` ∈ {`application`, `synthesis`} (question level).
  - `choice_diagnosis[]` — 1:1 with `choices`, `null` on the correct index.
    Three axes on a distractor: `content_gap` (`maps_to: "content_gap"` +
    `misconception`), `trap: <type>` (`maps_to: null`, type ∈
    {`negation`, `unit`, `inverse`, `scaling`, `transpose`, `partial`}), or a
    bare `null` (non-diagnostic). Content axis only (never `misread`/`application`
    on a choice; those are behavioral). See the finalized "Choice-axis re-tag
    pass" section below.
- 4 **multi-question science passages** (data table / described experiment in the
  stem, 3–4 questions each) introduce data-interpretation and passage→concept
  mapping — the reserved `passage_mapping` sub-mode of `application`.

---

## Summary table

| id | topic_id | sec | demand | concepts integrated | split |
|----|----------|-----|--------|---------------------|-------|
| **Passage 1 — Enzyme inhibition data (bb_enzymes)** ||||||
| q_syn_001 | bb_enzymes | BB | synthesis | Vmax/Km signature → inhibition type (enzymes × kinetics × data) | held_out |
| q_syn_002 | bb_enzymes | BB | application | surmountability of competitive inhibition at high [S] | held_out |
| q_syn_003 | bb_enzymes | BB | application | experimental design: controlled vs independent variable | held_out |
| q_syn_004 | bb_enzymes | BB | synthesis | kinetics vs thermodynamics (Km ≠ Keq; inhibitor ≠ ΔG) | held_out |
| **Passage 2 — Galvanic cell + thermo (cp_electrochem)** ||||||
| q_syn_005 | cp_electrochem | CP | application | E°cell from reduction potentials; anode/cathode assignment | dev |
| q_syn_006 | cp_electrochem | CP | synthesis | ΔG° = −nFE°cell (thermo × electrochem, find n) | dev |
| q_syn_007 | cp_electrochem | CP | application | Nernst: product ion ↑ → Ecell ↓; Ecell vs E°cell | dev |
| q_syn_008 | cp_electrochem | CP | synthesis | discharge to equilibrium: Ecell→0 and ΔG→0 | dev |
| **Passage 3 — Buffer / Henderson–Hasselbalch (cp_acids_bases)** ||||||
| q_syn_009 | cp_acids_bases | CP | application | Henderson–Hasselbalch pH at 1:1 ratio | held_out |
| q_syn_010 | cp_acids_bases | CP | synthesis | buffer mechanism on strong-acid add (equilibrium × acid-base) | held_out |
| q_syn_011 | cp_acids_bases | CP | application | HH ratio for a target pH | held_out |
| q_syn_012 | cp_acids_bases | CP | synthesis | common-ion effect (Le Chatelier × dissociation × pH) | held_out |
| **Passage 4 — Dihybrid probability (bb_genetics)** ||||||
| q_syn_013 | bb_genetics | BB | application | product rule: P(yyrr) across independent genes | dev |
| q_syn_014 | bb_genetics | BB | synthesis | combined phenotype probability (3/4 × 1/4) | dev |
| q_syn_015 | bb_genetics | BB | synthesis | infer genotype from testcross ratios (both genes) | dev |
| **Standalone science** ||||||
| q_syn_016 | bb_citric_acid | BB | synthesis | substrate-level ATP: glycolysis + 2 TCA turns (exclude ETC) | dev |
| q_syn_017 | bb_membranes | BB | application | tonicity: RBC in hypotonic solution → water movement | held_out |
| q_syn_018 | bb_dna | BB | application | base-pairing + antiparallel + 5'→3' directionality | dev |
| q_syn_019 | cp_thermo | CP | synthesis | crossover T = ΔH/ΔS with kJ/J unit handling | dev |
| q_syn_020 | cp_kinetics | CP | synthesis | derive rate law/orders from an initial-rate table | held_out |
| q_syn_021 | cp_kinetics | CP | synthesis | ΔG<0 yet slow: thermodynamics vs kinetics (Ea) | dev |
| q_syn_022 | cp_fluids | CP | synthesis | continuity + Bernoulli in a narrowing pipe | held_out |
| q_syn_023 | cp_fluids | CP | application | continuity numeric: A₁v₁ = A₂v₂ | dev |
| q_syn_024 | cp_acids_bases | CP | application | strong vs weak acid, equal conc → pH comparison | held_out |
| q_syn_025 | ps_learning | PS | application | variable-ratio schedule (gambling vignette) | dev |
| q_syn_026 | ps_learning | PS | application | negative reinforcement vs punishment (vignette) | held_out |
| q_syn_027 | ps_social | PS | synthesis | FAE vs actor–observer bias (paired vignette) | dev |
| q_syn_028 | ps_social | PS | application | cognitive dissonance reduction (vignette) | held_out |
| q_syn_029 | ps_memory | PS | application | context-dependent memory (encoding specificity) | dev |
| q_syn_030 | ps_demographics | PS | synthesis | social gradient vs threshold from a mortality table | held_out |

**Totals:** 30 items — BB 10, CP 14, PS 6. Demand: synthesis 15, application 15
(per-item table above is authoritative). Split: dev 15, held_out 15.

---

## New `topic_id`s introduced

**None.** Every item reuses an existing outline `topic_id` (see
`data/mcat-outline.v1.json`), so no outline edit is required and the validator's
`topic_id ∈ outline` check keeps passing. Notes:

- Enzyme inhibition kinetics (competitive/noncompetitive) is filed under existing
  **`bb_enzymes`** ("Enzyme Kinetics and Regulation") rather than a new
  `bb_enzyme_kinetics`. **Decision for user:** if you want inhibition-type items
  tracked as their own coverage cell, add `bb_enzyme_kinetics` to the outline and
  retag q_syn_001–004. Recommendation: keep under `bb_enzymes` for v1 (avoids a
  low-count coverage cell).
- Actor–observer bias (q_syn_027) is filed under existing **`ps_social`**.

---

## Integration plan (after review — append-only)

Runtime never runs these scripts; they emit the data files. Steps:

1. **Schema additions (small, additive).** `cognitive_demand` and
   `choice_diagnosis` are not in `REQUIRED_QUESTION_FIELDS` today, so adding them
   is non-breaking. Coordinate with the other agent since it owns
   `build_question_bank.py`:
   - The `q(...)` helper gains two optional kwargs (`demand=None`,
     `choice_diagnosis=None`) that are only emitted when present. Existing 110
     items stay byte-compatible if the keys are omitted when `None`.
   - `validate_data.py`: add optional checks (only when the key exists):
     `cognitive_demand ∈ {recall, application, synthesis}`;
     `len(choice_diagnosis) == 4`; correct index is `null`; each `maps_to ∈
     {content_gap, null}` or a list thereof; `choice_diagnosis` absent on CARS.
2. **Append the 30 items** to `build_question_bank.py` as a new `SYNTHESIS` list
   with explicit ids `q_syn_001…030` (do NOT reuse the auto `q_dev_/q_ho_` index
   loop — these need stable ids). Emit them into `questions.json` after the
   existing arrays. Ids are new → no collisions. Passages reuse a shared stem
   constant (like `P_HIST`/`P_CHOICE`) so the table text is identical across a
   passage's questions.
3. **Add the backing cards** (see appendix) to the `CARDS` list in
   `build_flashcards.py`, each with `topic:<id>` and `supports_question` linking
   to the `q_syn_*` ids. Re-run to regenerate `flashcards-dev*.csv`.
4. **Regenerate + validate:**
   - `python scripts/build_flashcards.py`
   - `python scripts/build_question_bank.py`
   - `python scripts/validate_data.py`  (expect "Validation OK", question count
     140, dev/held_out both +15)
   - coverage / linkage check: confirm every `q_syn_*` has ≥1 backing card
     (`build_flashcards.py` already self-checks this; the new synthesis items must
     appear in its "supported" set).
   - `python scripts/eval_leakage.py` — confirm no dev/held_out contamination
     (passages kept wholly within one split, so no cross-split leak).
5. **`curation-status.json`** counts refresh automatically via
   `build_question_bank.py` (the other agent's file) — no manual edit.

**Note on `choice_diagnosis` tagging discipline (spec §"Choice tagging
methodology"):** we author only the **content axis** on a choice, across three
mutually exclusive tags — `content_gap` (a false belief, with a concrete
`misconception`), `trap: <type>` (a predictable execution slip; `maps_to: null`,
no misconception; type ∈ {`negation`, `unit`, `inverse`, `scaling`, `transpose`,
`partial`}), or a bare `null` (non-diagnostic). We never tag
`misread`/`application` on a choice — those are inferred from behavior; a `trap`
merely *nudges* the behavioral misread prior (e.g., the kJ/J `unit` trap in
q_syn_019). Final counts and the per-item table are in the finalized
"Choice-axis re-tag pass" section below.

---

## New backing cards — summary

**27 new cards** needed so every synthesis item has prerequisite coverage; many
items also reuse existing cards. Breakdown by topic:

| topic_id | new cards | reused existing cards |
|----------|-----------|-----------------------|
| bb_enzymes | 5 | "enzymes lower Ea, not ΔG"; Vmax saturation |
| cp_electrochem | 5 | Nernst (q_ho_002); anode/cathode; E°cell↔spontaneous |
| cp_acids_bases | 4 | buffer = weak acid + conj. base; add-product-shifts-left; strong-acid pH |
| bb_genetics | 3 | 3:1/1:2:1 monohybrid; testcross uses hom. recessive |
| bb_citric_acid / bb_glycolysis | 2 | glycolysis net 2 ATP; TCA 1 GTP/turn |
| bb_membranes | 1 | osmosis = diffusion of water |
| bb_dna | 1 | A-T/G-C pairing; antiparallel |
| cp_thermo | 1 | ΔG=ΔH−TΔS; spontaneous-at-high-T |
| cp_kinetics | 1 | ΔG<0 ≠ fast; catalyst lowers Ea not ΔG; order card |
| cp_fluids | 0 | continuity A₁v₁=A₂v₂; Bernoulli speed↑→pressure↓ |
| ps_learning | 2 | variable-ratio; neg. reinforcement increases behavior |
| ps_social | 1 | FAE; cognitive dissonance |
| ps_memory | 0 | context-dependent memory (q_ho_042) |
| ps_demographics | 1 | social gradient (q_ho_052) |

Full CSV-ready rows in the **Backing cards appendix** at the end.

---

# Full question specifications

Legend per item: **stem / choices / correct**, then `topic_id · section ·
cognitive_demand`, a one-line **why-reasoning** justification, the
**choice_diagnosis** (per index), **source**, and **backing cards**.

---

## Passage 1 — Enzyme inhibition kinetics (`bb_enzymes`, held_out)

**Shared passage stem** (prepended to q_syn_001–004):

```
PASSAGE
An enzyme converts substrate S to product P. A researcher measures the initial
reaction velocity (v0) at several substrate concentrations, first with enzyme
alone and then with the same amount of enzyme plus a fixed concentration of
inhibitor X. Enzyme amount and temperature are identical in both runs.

  [S] (mM) | v0, enzyme only (µmol/min) | v0, enzyme + X (µmol/min)
  ---------+---------------------------+--------------------------
     1     |            33             |            14
     2     |            50             |            25
     4     |            67             |            40
     8     |            80             |            57
    16     |            89             |            73

At very high (saturating) [S], both curves approach the same maximum velocity
(Vmax ≈ 100 µmol/min). The substrate concentration giving half-maximal velocity
is about 2 mM without X and about 6 mM with X.
```

*(Data are internally consistent with Michaelis–Menten v = Vmax[S]/(Km+[S]),
Vmax = 100 for both; Km = 2 without X, apparent Km = 6 with X.)*

### q_syn_001
- **Stem:** *(passage)* "Which type of inhibition does X most likely exhibit?"
- **Choices:** A) Competitive · B) Noncompetitive · C) Uncompetitive · D) Irreversible (covalent)
- **Correct:** **A**
- `bb_enzymes · BB · synthesis` — must read the data signature (**Vmax unchanged,
  apparent Km increased**) and map it to a mechanism; integrates enzyme kinetics +
  data interpretation. Not recallable from a definition alone.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "expects Vmax to fall; confuses noncompetitive (Vmax↓, Km unchanged) with the observed Vmax-unchanged/Km-up pattern"
  - C → `content_gap`, "uncompetitive lowers both Vmax and Km; misreads the table"
  - D → `content_gap`, "assumes higher apparent Km implies irreversible/covalent inhibition"
- **Source:** OpenStax Biology 2e — Ch. 6.5 Enzymes (enzyme inhibition; Michaelis–Menten regulation). *Original data item (CC0, MCAT Speedrun) grounded in 6.5.*
- **Backing cards:** NEW-E1 (competitive inhibitor binds the active site, competing with substrate — *component*, not the Vmax/Km signature), NEW-E2 (noncompetitive: Vmax↓, Km unchanged), NEW-E3 (Km = [S] at ½Vmax). *(existing "competitive vs allosteric" card also supports.)* The student must derive the "Vmax-unchanged, apparent-Km-up" signature from the mechanism + data — no card hands it.

### q_syn_002
- **Stem:** *(passage)* "If [S] is raised to very high (saturating) levels in the presence of X, the reaction velocity will:"
- **Choices:** A) approach the same maximum as without X · B) remain below the uninhibited velocity at every [S], including saturating · C) exceed the uninhibited Vmax · D) become independent of [S] at all concentrations
- **Correct:** **A**
- `bb_enzymes · BB · application` — applies the *surmountable* property of
  competitive inhibition inferred in q_syn_001 to a new condition (high [S]).
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "does not know competitive inhibition is overcome by excess substrate"
  - C → `content_gap`, "believes adding substrate can push velocity past Vmax"
  - D → `content_gap`, "confuses saturation with zero-order independence at all [S]"
- **Source:** OpenStax Biology 2e — Ch. 6.5 Enzymes. *(CC0, MCAT Speedrun.)*
- **Backing cards:** NEW-E1 (competitive inhibitor binds the active site, competing with substrate — surmountability is derived from this), existing q_dev_024 card (Vmax at saturation).

### q_syn_003
- **Stem:** *(passage)* "Substrate concentration is the independent variable (deliberately ranged across rows) and the presence of inhibitor X is the treatment being compared. Which *other* quantity most needed to be identical in both runs so that any difference in velocity can be attributed to X?"
- **Choices:** A) the substrate concentration · B) the total amount of enzyme · C) the measured reaction velocity · D) the presence of inhibitor X
- **Correct:** **B**
- `bb_enzymes · BB · application` — experimental-design reasoning (MCAT Skill 4):
  distinguish the **controlled** variable from the **independent** variable ([S],
  deliberately varied), the **dependent** variable (velocity), and the
  **treatment** (X present/absent).
- **choice_diagnosis:**
  - A → `content_gap`, "the stem names [S] as the independent variable; selecting it ignores that [S] is varied on purpose, not a control"
  - B → `null`
  - C → `content_gap`, "names the dependent variable — the measured outcome, not a control"
  - D → `content_gap`, "X presence is the treatment being compared, so it cannot be held constant"
- **Source:** OpenStax Biology 2e — Ch. 6.5 Enzymes; experimental-design reasoning (AAMC Skill 4). *(CC0, MCAT Speedrun.)*
- **Backing cards:** NEW-E4 (assay: hold [enzyme] constant; [S] independent, velocity dependent).

### q_syn_004
- **Stem:** *(passage)* "Inhibitor X changes the *apparent* Km measured for this enzyme. Does X change the reaction's ΔG or its equilibrium constant (Keq)?"
- **Choices:** A) Yes — it makes S→P less thermodynamically favorable · B) No — it changes the rate/kinetics but not ΔG or Keq · C) Yes — raising Km lowers Keq · D) It changes ΔG only at high [S]
- **Correct:** **B**
- `bb_enzymes · BB · synthesis` — integrates enzyme kinetics with thermodynamics:
  inhibitors (like catalysts) affect the *path/rate*, not the *thermodynamics*;
  **Km ≠ Keq**. High-yield MCAT conflation.
- **choice_diagnosis:**
  - A → `content_gap`, "treats a kinetic inhibitor as changing thermodynamic favorability"
  - B → `null`
  - C → `content_gap`, "confuses Km (kinetic, [S] at ½Vmax) with Keq (thermodynamic)"
  - D → `content_gap`, "thinks ΔG depends on substrate concentration"
- **Source:** OpenStax Biology 2e — Ch. 6.5 Enzymes + Ch. 6.3 (ΔG / spontaneity). *(CC0, MCAT Speedrun.)*
- **Backing cards:** existing card "Enzymes speed a reaction by lowering activation energy, without changing ΔG" (line 10), NEW-E5 (inhibitors/catalysts change rate not ΔG/Keq).

---

## Passage 2 — Galvanic cell coupled to thermodynamics (`cp_electrochem`, dev)

**Shared passage stem** (prepended to q_syn_005–008):

```
PASSAGE
A galvanic cell is built from two standard half-cells at 25 °C:

  Cu²⁺(aq) + 2e⁻ → Cu(s)     E° = +0.34 V
  Zn²⁺(aq) + 2e⁻ → Zn(s)     E° = −0.76 V

The two metals are connected by an external wire and the half-cells by a salt
bridge. (F ≈ 96,500 C/mol.)
```

### q_syn_005
- **Stem:** *(passage)* "Which electrode is the cathode, and what is the standard cell potential E°cell?"
- **Choices:** A) Cu is the cathode; E°cell = +1.10 V · B) Zn is the cathode; E°cell = +1.10 V · C) Cu is the cathode; E°cell = +0.42 V · D) Cu is the cathode; E°cell = −1.10 V
- **Correct:** **A**
- `cp_electrochem · CP · application` — apply E°cell = E°cathode − E°anode and the
  rule that the higher reduction potential is reduced (cathode): 0.34 − (−0.76) =
  +1.10 V.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "assigns cathode to the more negative electrode (reverses anode/cathode)"
  - C → `null` — numeric near-miss: 0.42 V from combining the potentials the wrong way (|0.76| − |0.34|); no distinct conceptual misconception beyond the arithmetic
  - D → `null`, `trap: negation` — sign-flip landing: correct magnitude (1.10 V) with a dropped/flipped sign → −1.10 V (an execution slip, not a content belief)
- **Source:** OpenStax Chemistry 2e — Ch. 17.2 Galvanic Cells; Ch. 17.3 Standard Reduction Potentials.
- **Backing cards:** NEW-EC1 (E°cell = E°cathode − E°anode; higher reduction potential = cathode), existing card "oxidation at anode / reduction at cathode" (line 54).

### q_syn_006
- **Stem:** *(passage)* "Using ΔG° = −nFE°cell, what is ΔG° for this cell reaction, and is it spontaneous?"
- **Choices:** A) ≈ −212 kJ; spontaneous · B) ≈ +212 kJ; nonspontaneous · C) ≈ −106 kJ; spontaneous · D) ΔG° = 0; the cell is at equilibrium
- **Correct:** **A**
- `cp_electrochem · CP · synthesis` — couples electrochemistry to thermodynamics
  and requires extracting **n = 2** from the balanced half-reactions:
  −(2)(96,500)(1.10) ≈ −2.12×10⁵ J ≈ −212 kJ.
- **choice_diagnosis:**
  - A → `null`
  - B → `null`, `trap: negation` — dropped the negative sign in ΔG° = −nFE°cell → +212 kJ ("nonspontaneous"); an execution landing, not a content gap
  - C → `content_gap`, "used n = 1 instead of extracting n = 2 electrons from the balanced half-reactions"
  - D → `content_gap`, "assumes a standard cell is at equilibrium (confuses E°cell with Ecell = 0)"
- **Source:** OpenStax Chemistry 2e — Ch. 17.4 Potential, Free Energy, and Equilibrium.
- **Backing cards:** NEW-EC2 (ΔG° = −nFE°cell; +E°cell → −ΔG°), NEW-EC3 (finding n = mol e⁻ in the balanced redox), existing card "positive E°cell → spontaneous, ΔG°<0" (line 55).

### q_syn_007
- **Stem:** *(passage)* "If the concentration of Zn²⁺ (a product ion) is increased while Cu²⁺ is held constant, what happens to the actual cell potential Ecell?"
- **Choices:** A) Ecell decreases · B) Ecell increases · C) E°cell decreases · D) no change, because E° is fixed
- **Correct:** **A**
- `cp_electrochem · CP · application` — apply the Nernst equation qualitatively
  (raising product ion → Q↑ → Ecell↓) and distinguish **Ecell (actual)** from
  **E°cell (standard, fixed)**.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "wrong direction of the Nernst shift"
  - C → `content_gap`, "confuses Ecell with E°cell — standard potential is fixed, so this option is a category error"
  - D → `content_gap`, "believes ion concentration cannot affect the actual potential"
- **Source:** OpenStax Chemistry 2e — Ch. 17.4 (Nernst equation).
- **Backing cards:** existing card "raising product ions lowers cell potential" (line 59, q_ho_002), NEW-EC4 (Ecell varies with concentration; E°cell is fixed).

### q_syn_008
- **Stem:** *(passage)* "As the cell operates and the reaction proceeds toward equilibrium, Ecell trends toward ____ and ΔG trends toward ____."
- **Choices:** A) Ecell → 0; ΔG → 0 · B) Ecell increases; ΔG becomes more negative · C) Ecell → E°cell; ΔG → ΔG° · D) Ecell → 0; ΔG → a large negative value
- **Correct:** **A**
- `cp_electrochem · CP · synthesis` — integrates cell discharge with the
  thermodynamic equilibrium condition: a dead battery has Ecell = 0 **and** ΔG = 0.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "thinks an operating cell gains potential over time"
  - C → `content_gap`, "confuses approaching equilibrium with returning to standard conditions (Ecell→E°cell)"
  - D → `null` — partial-knowledge near-miss: right that Ecell→0 but wrong that ΔG→a large negative value (incomplete recall of "ΔG→0 at equilibrium"); no distinct misconception
- **Source:** OpenStax Chemistry 2e — Ch. 17.4; Ch. 16.4 Free Energy.
- **Backing cards:** NEW-EC5 (discharge: Ecell→0 and ΔG→0 at equilibrium), existing card "at equilibrium ΔG = 0" (line 62, q_ho_011).

---

## Passage 3 — Buffer / Henderson–Hasselbalch (`cp_acids_bases`, held_out)

**Shared passage stem** (prepended to q_syn_009–012):

```
PASSAGE
A chemist prepares an acetate buffer from acetic acid (CH₃COOH) and its
conjugate base acetate (CH₃COO⁻). For acetic acid, pKa = 4.74. The initial
buffer contains [CH₃COOH] = 0.10 M and [CH₃COO⁻] = 0.10 M. The relevant
equilibrium is:  CH₃COOH ⇌ CH₃COO⁻ + H⁺.
```

### q_syn_009
- **Stem:** *(passage)* "What is the pH of the initial buffer?"
- **Choices:** A) 4.74 · B) 7.00 · C) 9.26 · D) 2.37
- **Correct:** **A**
- `cp_acids_bases · CP · application` — apply Henderson–Hasselbalch; at
  [A⁻]=[HA], log(1)=0 → pH = pKa.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "assumes equal concentrations imply a neutral pH of 7"
  - C → `content_gap`, "used 14 − pKa (pOH/pKb confusion) or inverted the ratio"
  - D → `null` — numeric near-miss: 2.37 = pKa/2 has no coherent conceptual pathway (arbitrary manipulation)
- **Source:** OpenStax Chemistry 2e — Ch. 14.6 Buffers (Henderson–Hasselbalch).
- **Backing cards:** NEW-AB1 (HH equation; [A⁻]=[HA] → pH=pKa).

### q_syn_010
- **Stem:** *(passage)* "A small amount of strong acid (HCl) is added to the buffer. What happens to the pH, and why?"
- **Choices:** A) pH drops sharply, as it would in pure water · B) pH decreases only slightly; acetate (A⁻) reacts with the added H⁺ to form acetic acid · C) pH increases, because acetate is a base · D) pH does not change at all, because buffers hold pH perfectly constant
- **Correct:** **B**
- `cp_acids_bases · CP · synthesis` — integrates the acid-base equilibrium with
  buffer-capacity mechanism (what species consumes the added H⁺).
- **choice_diagnosis:**
  - A → `content_gap`, "does not understand buffering — treats buffer like unbuffered water"
  - B → `null`
  - C → `content_gap`, "wrong direction: adding acid cannot raise pH here"
  - D → `content_gap`, "over-generalizes buffers as infinite/perfect capacity"
- **Source:** OpenStax Chemistry 2e — Ch. 14.6 Buffers.
- **Backing cards:** NEW-AB2 (added strong acid is absorbed by A⁻ → HA; pH drops slightly), existing card "buffer = weak acid + conjugate base resists pH change" (line 48, q_dev_011).

### q_syn_011
- **Stem:** *(passage)* "To instead prepare a buffer at pH 5.74 (one unit above the pKa), what ratio of [CH₃COO⁻] to [CH₃COOH] is needed?"
- **Choices:** A) 1 : 10 · B) 10 : 1 · C) 1 : 1 · D) 100 : 1
- **Correct:** **B**
- `cp_acids_bases · CP · application` — invert Henderson–Hasselbalch:
  pH − pKa = 1 = log([A⁻]/[HA]) → ratio = 10 (base:acid).
- **choice_diagnosis:**
  - A → `content_gap`, "inverted the ratio (acid:base vs base:acid)"
  - B → `null`
  - C → `content_gap`, "assumes every buffer is 1:1 regardless of target pH"
  - D → `content_gap`, "used two log units (10²) instead of one"
- **Source:** OpenStax Chemistry 2e — Ch. 14.6 Buffers.
- **Backing cards:** NEW-AB1 (HH equation).

### q_syn_012
- **Stem:** *(passage)* "Solid sodium acetate is dissolved into a solution of pure acetic acid (adding CH₃COO⁻). What happens to the acetic-acid dissociation equilibrium, to its percent dissociation, and to the pH?"
- **Choices:** A) shifts left; percent dissociation of acetic acid decreases; pH rises · B) shifts right; more H⁺ is released; pH drops · C) no shift; acetate is only a spectator ion · D) shifts left; but pH drops
- **Correct:** **A**
- `cp_acids_bases · CP · synthesis` — integrates Le Chatelier / **common-ion
  effect** with its consequence for dissociation and pH.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "wrong Le Chatelier direction for adding a common ion"
  - C → `content_gap`, "does not recognize the common-ion effect"
  - D → `content_gap`, "gets the shift right but the pH direction wrong (less H⁺ → higher pH)"
- **Source:** OpenStax Chemistry 2e — Ch. 14.6 Buffers; Ch. 15/Le Chatelier (common-ion effect).
- **Backing cards:** NEW-AB3 (*component*: less dissociation → fewer H⁺ → higher pH), existing card "adding product shifts equilibrium toward reactants" (line 45, q_dev_006 — supplies the left-shift). The student chains left-shift → less dissociation → higher pH; no single card states all three.

---

## Passage 4 — Dihybrid probability (`bb_genetics`, dev)

**Shared passage stem** (prepended to q_syn_013–015):

```
PASSAGE
In pea plants, seed color and seed shape are controlled by two genes on
different chromosomes (they assort independently). Yellow (Y) is dominant to
green (y); round (R) is dominant to wrinkled (r). Two doubly heterozygous
plants are crossed:  YyRr × YyRr.
```

### q_syn_013
- **Stem:** *(passage)* "What is the probability that a given offspring is homozygous recessive for both genes (yyrr)?"
- **Choices:** A) 1/16 · B) 9/16 · C) 1/4 · D) 3/16
- **Correct:** **A**
- `bb_genetics · BB · application` — apply the product rule across two independent
  monohybrid crosses: P(yy)=1/4, P(rr)=1/4 → 1/16.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "reports the both-dominant phenotype fraction (9/16)"
  - C → `content_gap`, "solves one gene (1/4) but forgets to multiply the second"
  - D → `content_gap`, "confuses with a one-dominant/one-recessive class (3/16)"
- **Source:** OpenStax Biology 2e — Ch. 12.3 Laws of Inheritance (independent assortment; product rule).
- **Backing cards:** NEW-G1 (product rule across independent genes), existing card "monohybrid Aa×Aa → 3:1 / 1:2:1" (line 37).

### q_syn_014
- **Stem:** *(passage)* "What fraction of offspring are expected to be yellow **and** wrinkled (Y_ rr)?"
- **Choices:** A) 3/16 · B) 9/16 · C) 1/16 · D) 3/4
- **Correct:** **A**
- `bb_genetics · BB · synthesis` — combine per-gene phenotype probabilities:
  P(yellow)=3/4 × P(wrinkled)=1/4 = 3/16.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "gives the both-dominant 9/16 (ignores that shape is recessive)"
  - C → `content_gap`, "computes both-recessive instead of one dominant/one recessive"
  - D → `content_gap`, "reports only the yellow fraction (3/4), forgetting to multiply by wrinkled"
- **Source:** OpenStax Biology 2e — Ch. 12.3 Laws of Inheritance.
- **Backing cards:** NEW-G1 (product rule), NEW-G2 (dihybrid 9:3:3:1).

### q_syn_015
- **Stem:** *(passage)* "Separately, a yellow, round plant of unknown genotype is testcrossed with a green, wrinkled plant (yyrr). The offspring are ½ yellow : ½ green, and **all** are round. What is the unknown plant's genotype?"
- **Choices:** A) YyRR · B) YYRr · C) YyRr · D) YYRR
- **Correct:** **A**
- `bb_genetics · BB · synthesis` — reason backward from two testcross ratios: a
  1:1 color split ⇒ heterozygous Yy; all-round offspring ⇒ homozygous RR.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "maps the ratios to the wrong genes (reads color data onto shape)"
  - C → `content_gap`, "assumes both genes heterozygous, ignoring the 'all round' result"
  - D → `content_gap`, "assumes fully homozygous dominant despite the ½ green offspring"
- **Source:** OpenStax Biology 2e — Ch. 12.2 Characteristics and Traits (testcross); Ch. 12.3.
- **Backing cards:** NEW-G3 (testcross ratio → genotype inference), existing card "testcross uses homozygous recessive partner" (line 40, q_ho_039).

---

## Standalone science items

### q_syn_016
- **Stem:** "Under aerobic conditions, one glucose molecule is fully oxidized: glycolysis yields 2 pyruvate, each pyruvate is converted to acetyl-CoA, and each acetyl-CoA is oxidized in the citric acid cycle. Counting **only substrate-level phosphorylation** (not the electron transport chain), how many net ATP/GTP are produced from one glucose through the end of the citric acid cycle?"
- **Choices:** A) 2 · B) 4 · C) 36 · D) 30
- **Correct:** **B**
- `bb_citric_acid · BB · synthesis` — integrate glycolysis (net 2 ATP) with **two**
  turns of the citric acid cycle (1 GTP each) while excluding oxidative
  phosphorylation: 2 + 2 = 4.
- **choice_diagnosis:**
  - A → `content_gap`, "counts only glycolysis; forgets the 2 GTP from the two TCA turns"
  - B → `null`
  - C → `content_gap`, "gives total aerobic yield (~36) — conflates substrate-level with oxidative phosphorylation"
  - D → `null` — same total-aerobic-yield conflation as C, just the alternate ~30 ATP textbook figure; no distinct misconception (numeric variant of C)
- **Source:** OpenStax Biology 2e — Ch. 7.2 Glycolysis; Ch. 7.3 Citric Acid Cycle.
- **Backing cards:** NEW-BB1 (1 glucose → 2 acetyl-CoA → 2 TCA turns), NEW-BB2 (substrate-level total = 4; rest is ETC), existing "glycolysis net 2 ATP" (line 21), existing "TCA 1 ATP/GTP per turn" (line 4, q_dev_001).

### q_syn_017
- **Stem:** "A red blood cell with an internal solute concentration of about 300 mOsm is placed into a 100 mOsm solution. What is the net movement of water and the likely outcome?"
- **Choices:** A) water leaves the cell; it shrinks (crenates) · B) water enters the cell; it swells and may lyse · C) no net movement; the solutions are isotonic · D) solutes diffuse out of the cell to equalize concentrations
- **Correct:** **B**
- `bb_membranes · BB · application` — apply osmosis/tonicity to a novel scenario:
  the external solution is hypotonic → water enters the cell.
- **choice_diagnosis:**
  - A → `content_gap`, "reverses osmosis direction (treats the cell as if it were in a hypertonic bath)"
  - B → `null`
  - C → `content_gap`, "misjudges tonicity (300 vs 100 mOsm are not equal)"
  - D → `content_gap`, "thinks solute crosses rather than water — misunderstands osmosis"
- **Source:** OpenStax Biology 2e — Ch. 5.2 Passive Transport (osmosis, tonicity).
- **Backing cards:** NEW-M1 (water moves toward hypertonic side; cell in hypotonic solution swells), existing "osmosis = diffusion of water" (line 28, q_ho_032).

### q_syn_018
- **Stem:** "One strand of DNA reads 5'-TACGGA-3'. Written in the conventional 5'→3' direction, the newly synthesized complementary strand is:"
- **Choices:** A) 5'-TCCGTA-3' · B) 5'-ATGCCT-3' · C) 5'-TACGGA-3' · D) 5'-UCCGUA-3'
- **Correct:** **A**
- `bb_dna · BB · application` — apply base-pairing (A-T, G-C) **plus** the
  antiparallel rule and 5'→3' convention: complement of 5'-TACGGA-3' is
  3'-ATGCCT-5', which written 5'→3' is TCCGTA.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "writes the base complement but ignores antiparallel orientation (reports it 3'→5')"
  - C → `content_gap`, "copies the template instead of pairing complementary bases"
  - D → `content_gap`, "uses uracil (RNA) instead of thymine for DNA"
- **Source:** OpenStax Biology 2e — Ch. 14.2 DNA Structure (base pairing, antiparallel strands).
- **Backing cards:** NEW-D1 (write complement 5'→3': pair then reverse — strands antiparallel), existing "A-T / G-C pairing" (line 32, q_ho_033), existing "strands antiparallel" (line 33, q_ho_036).

### q_syn_019
- **Stem:** "A reaction has ΔH = +50 kJ/mol and ΔS = +150 J/(mol·K). Above approximately what temperature does the reaction become spontaneous?"
- **Choices:** A) 333 K · B) 0.33 K · C) 3.0 K · D) It is never spontaneous
- **Correct:** **A**
- `cp_thermo · CP · synthesis` — set ΔG = ΔH − TΔS = 0, solve T = ΔH/ΔS, and
  **convert kJ→J**: 50,000 / 150 ≈ 333 K.
- **choice_diagnosis:**
  - A → `null`
  - B → `null`, `trap: unit` — unconverted units: 50/150 = 0.33 (used kJ against J directly); an execution landing, not a content gap
  - C → `null` — numeric near-miss (3.0 K) with no clean single-step derivation; not a predictable unit landing
  - D → `content_gap`, "thinks ΔH>0 means never spontaneous, ignoring the TΔS term at high T"
- **Source:** OpenStax Chemistry 2e — Ch. 16.4 Free Energy (ΔG=ΔH−TΔS; temperature dependence).
- **Backing cards:** NEW-T1 (*component*: convert ΔH kJ ↔ ΔS J to the same unit before combining — not the crossover formula), existing "ΔG=ΔH−TΔS" (line 60), existing "ΔH>0,ΔS>0 spontaneous at high T" (line 65, q_ho_009). The student derives T = ΔH/ΔS by setting ΔG = 0.

### q_syn_020
- **Stem:** "Initial-rate data for A + B → products:\n\n```\nExp | [A] (M) | [B] (M) | rate (M/s)\n 1  |  0.10   |  0.10   |   2.0\n 2  |  0.20   |  0.10   |   4.0\n 3  |  0.10   |  0.20   |   8.0\n```\nWhat is the rate law?"
- **Choices:** A) rate = k[A][B]² · B) rate = k[A]²[B] · C) rate = k[A][B] · D) rate = k[A]²[B]²
- **Correct:** **A**
- `cp_kinetics · CP · synthesis` — derive orders from data: doubling [A]
  (Exp 1→2) doubles rate → 1st order in A; doubling [B] (Exp 1→3) quadruples rate
  → 2nd order in B.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "swaps the orders of A and B"
  - C → `content_gap`, "reads B as first order (misses the ×4 → square)"
  - D → `content_gap`, "misreads A as second order"
- **Source:** OpenStax Chemistry 2e — Ch. 12.3 Rate Laws (method of initial rates).
- **Backing cards:** NEW-K1 (*component*: definition of reaction order = exponent on each reactant; overall = sum), existing "overall order for k[A][B]²" (line 69, q_ho_013), existing "doubling first-order reactant doubles rate" (line 72, q_ho_014). The student runs the method of initial rates across the two comparisons themselves.

### q_syn_021
- **Stem:** "A reaction has ΔG = −100 kJ/mol yet proceeds imperceptibly slowly at room temperature. Which statement best explains this?"
- **Choices:** A) ΔG must actually be positive · B) The reaction is thermodynamically favorable but has a high activation energy, so it is kinetically slow · C) The reaction is already at equilibrium · D) A catalyst would speed it up by making ΔG more negative
- **Correct:** **B**
- `cp_kinetics · CP · synthesis` — integrates thermodynamics (spontaneity ← ΔG)
  with kinetics (rate ← activation energy); the two are independent axes.
- **choice_diagnosis:**
  - A → `content_gap`, "conflates slow with nonspontaneous (thinks rate reveals ΔG)"
  - B → `null`
  - C → `content_gap`, "confuses 'slow' with 'at equilibrium'"
  - D → `content_gap`, "believes catalysts change ΔG (they change Ea only)"
- **Source:** OpenStax Chemistry 2e — Ch. 16.4 Free Energy; Ch. 12.5 Collision Theory / 12.7 Catalysis.
- **Backing cards:** existing Basic "does a negative ΔG mean fast? No — spontaneity vs kinetics" (line 64, q_ho_010), existing "catalyst lowers Ea, not ΔG" (line 67, q_dev_016).

### q_syn_022
- **Stem:** "Water in streamline flow moves through a horizontal pipe that narrows from cross-sectional area A₁ to A₂ = A₁/2. Compared with the wide section, in the narrow section the water's speed and pressure are:"
- **Choices:** A) speed doubles; pressure decreases · B) speed halves; pressure increases · C) speed doubles; pressure increases · D) speed is unchanged; pressure decreases
- **Correct:** **A**
- `cp_fluids · CP · synthesis` — chain the continuity equation (half the area →
  double the speed) with Bernoulli (higher speed at constant height → lower
  pressure).
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "reverses continuity (smaller area → slower)"
  - C → `content_gap`, "gets continuity right but violates Bernoulli (thinks faster → higher pressure)"
  - D → `content_gap`, "ignores continuity entirely"
- **Source:** OpenStax College Physics — Ch. 12.1 Flow Rate and Continuity; Ch. 12.2 Bernoulli's Equation.
- **Backing cards:** existing "continuity A₁v₁=A₂v₂" (line 75), existing "Bernoulli: higher speed → lower pressure" (line 76, q_ho_017).

### q_syn_023
- **Stem:** "Water flows at 2.0 m/s through a pipe of cross-sectional area 6.0 cm². The pipe then narrows to 2.0 cm². What is the water's speed in the narrow section?"
- **Choices:** A) 6.0 m/s · B) 0.67 m/s · C) 2.0 m/s · D) 18 m/s
- **Correct:** **A**
- `cp_fluids · CP · application` — numeric continuity: A₁v₁ = A₂v₂ →
  (6.0)(2.0) = (2.0)(v) → v = 6.0 m/s.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "inverted the area ratio (multiplied by A₂/A₁ instead of A₁/A₂)"
  - C → `content_gap`, "assumes speed is unchanged (ignores continuity)"
  - D → `null` — numeric distractor (18 m/s) with no clean derivation; no diagnostic misconception
- **Source:** OpenStax College Physics — Ch. 12.1 Flow Rate and Continuity.
- **Backing cards:** existing "continuity A₁v₁=A₂v₂" (line 75, q_dev_018/q_dev_019).

### q_syn_024
- **Stem:** "Equal volumes of 0.10 M HCl and 0.10 M acetic acid (Ka = 1.8×10⁻⁵) are compared. Which statement about their pH is correct?"
- **Choices:** A) Both have the same pH because their concentrations are equal · B) HCl has the lower pH because it ionizes completely · C) Acetic acid has the lower pH because it is the stronger acid · D) Both are neutral (pH 7)
- **Correct:** **B**
- `cp_acids_bases · CP · application` — reason from degree of ionization to [H⁺]
  to pH: a strong acid fully ionizes (more H⁺, lower pH) than an equal-concentration
  weak acid.
- **choice_diagnosis:**
  - A → `content_gap`, "assumes equal concentration ⇒ equal pH, ignoring ionization extent"
  - B → `null`
  - C → `content_gap`, "reverses acid strength (calls acetic acid the stronger acid)"
  - D → `content_gap`, "thinks acids can be pH-neutral"
- **Source:** OpenStax Chemistry 2e — Ch. 14.3 pH and pOH; Ch. 14.2 (strong vs weak acids).
- **Backing cards:** NEW-AB4 (strong acid fully ionizes → lower pH; weak acid partial → higher pH), existing "strong acid pH = −log[H⁺]" (line 51, q_ho_005).

### q_syn_025
- **Stem:** "A slot machine pays out after an unpredictable number of plays. Gamblers keep pulling the lever at a high, steady rate, and the behavior is very resistant to extinction. This pattern best illustrates:"
- **Choices:** A) a fixed-interval schedule · B) a variable-ratio schedule · C) negative reinforcement · D) a fixed-ratio schedule
- **Correct:** **B**
- `ps_learning · PS · application` — apply reinforcement-schedule concepts to a
  vignette; the defining features (unpredictable # of responses, high steady rate,
  extinction-resistant) identify variable-ratio.
- **choice_diagnosis:**
  - A → `content_gap`, "confuses interval (time-based) with ratio (response-based) schedules"
  - B → `null`
  - C → `content_gap`, "mislabels a reinforcement schedule as negative reinforcement"
  - D → `content_gap`, "confuses fixed with variable ratio (misses 'unpredictable')"
- **Source:** OpenStax Psychology 2e — Ch. 6.3 Operant Conditioning (reinforcement schedules).
- **Backing cards:** NEW-L1 (variable-ratio → high steady, extinction-resistant, e.g. gambling), existing "variable-ratio = unpredictable # of responses" (line 93, q_ho_047).

### q_syn_026
- **Stem:** "A person takes aspirin whenever they have a headache; the relief that follows makes them more likely to take aspirin the next time. This is an example of:"
- **Choices:** A) positive reinforcement · B) negative reinforcement · C) positive punishment · D) negative punishment
- **Correct:** **B**
- `ps_learning · PS · application` — apply the operant 2×2 to a vignette: an
  **aversive** state (pain) is **removed**, which **increases** the behavior →
  negative reinforcement. High-yield confusion.
- **choice_diagnosis:**
  - A → `content_gap`, "assumes any behavior increase is positive reinforcement (adding a stimulus)"
  - B → `null`
  - C → `content_gap`, "confuses reinforcement (increases behavior) with punishment (decreases it)"
  - D → `content_gap`, "confuses negative reinforcement with negative punishment"
- **Source:** OpenStax Psychology 2e — Ch. 6.3 Operant Conditioning.
- **Backing cards:** NEW-L2 (negative reinforcement vs punishment distinction), existing "negative reinforcement increases behavior by removing aversive" (line 91, q_ho_046).

### q_syn_027
- **Stem:** "Jordan watches a classmate trip and thinks, 'How clumsy.' Later, when Jordan trips, they blame the uneven floor. The judgment of the classmate illustrates ____, and Jordan's judgment of their own stumble illustrates ____."
- **Choices:** A) the fundamental attribution error; the actor–observer bias · B) the self-serving bias; the fundamental attribution error · C) the just-world hypothesis; conformity · D) the bystander effect; obedience
- **Correct:** **A**
- `ps_social · PS · synthesis` — distinguish and correctly pair two attribution
  biases in one applied scenario (dispositional attribution for others vs
  situational for self).
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "reverses the two biases (self-serving bias + FAE instead of FAE + actor–observer)"
  - C → `null` — plausible-distractor grab of unrelated social-psych concepts (just-world / conformity); encodes no specific misconception about attribution
  - D → `null` — plausible-distractor grab of unrelated social-influence concepts (bystander / obedience); encodes no specific misconception about attribution
- **Source:** OpenStax Psychology 2e — Ch. 12.1 What Is Social Psychology? (attribution).
- **Backing cards:** existing "fundamental attribution error" (line 94, q_dev_038), NEW-S1 (actor–observer bias: own behavior → situation, others' → disposition).

### q_syn_028
- **Stem:** "A person who values their health but smokes daily feels uncomfortable, then persuades themselves that 'the health risks are exaggerated.' Resolving the discomfort by changing a belief best illustrates:"
- **Choices:** A) reduction of cognitive dissonance · B) classical conditioning · C) the bystander effect · D) negative reinforcement
- **Correct:** **A**
- `ps_social · PS · application` — apply cognitive-dissonance theory to a novel
  vignette (belief change to reduce attitude–behavior conflict).
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "confuses attitude change with associative (classical) learning"
  - C → `null` — plausible-distractor grab (bystander effect); encodes no specific misconception about dissonance
  - D → `content_gap`, "confuses a cognitive process (dissonance reduction) with operant reinforcement"
- **Source:** OpenStax Psychology 2e — Ch. 12.3 Attitudes and Persuasion (cognitive dissonance).
- **Backing cards:** existing "cognitive dissonance = discomfort from conflicting attitudes/behavior" (line 97, q_dev_043).

### q_syn_029
- **Stem:** "Students who study in a quiet room recall more when tested in a quiet room than when tested in a noisy one; those who studied with background noise show the reverse. This is best explained by:"
- **Choices:** A) the serial position effect · B) context-dependent memory (encoding specificity) · C) proactive interference · D) chunking
- **Correct:** **B**
- `ps_memory · PS · application` — apply encoding-specificity/context-dependent
  memory to a novel experiment result.
- **choice_diagnosis:**
  - A → `content_gap`, "confuses a list-position effect with context effects"
  - B → `null`
  - C → `content_gap`, "confuses interference (competing memories) with context matching"
  - D → `content_gap`, "confuses an encoding strategy with a retrieval-context effect"
- **Source:** OpenStax Psychology 2e — Ch. 8.3 Ways to Enhance Memory (context-dependent memory).
- **Backing cards:** existing "context-dependent memory: recall improves when context matches" (line 87, q_ho_042).

### q_syn_030
- **Stem:** "A study reports age-adjusted mortality by income quintile:\n\n```\nIncome quintile | deaths per 1,000/yr\n lowest         |        12\n second         |        10\n middle         |         8\n fourth         |         6\n highest         |         5\n```\nWhich concept does this pattern best illustrate, and what does it imply?"
- **Choices:** A) a social gradient in health — outcomes improve stepwise with rising SES, not only for the poorest · B) health disparities are essentially random · C) only the very poorest have worse health (a threshold effect) · D) the differences are fully explained by genetics
- **Correct:** **A**
- `ps_demographics · PS · synthesis` — interpret a data table and map the
  monotonic stepwise pattern onto the social-gradient concept, rejecting the
  threshold misreading.
- **choice_diagnosis:**
  - A → `null`
  - B → `content_gap`, "denies the clear monotonic pattern in the data"
  - C → `content_gap`, "threshold misconception — misses that risk falls at *every* step, not just at the bottom"
  - D → `content_gap`, "attributes a social-gradient pattern solely to genetics, ignoring social determinants"
- **Source:** OpenStax Psychology 2e — Ch. 14.3 Stress and Illness (SES, social determinants). *Original data item (CC0, MCAT Speedrun) grounded in 14.3.*
- **Backing cards:** existing "social gradient: outcomes improve with higher SES" (line 101, q_ho_052), NEW-DEM1 (gradient ≠ poverty threshold: improves at every step).

---

# Backing cards appendix (CSV-ready)

Columns match `flashcards-dev.csv`: `note_type,text,back,tags,supports_question`.
Cloze uses ONE index for paired blanks (never c1+c2). **NEW** rows must be added to
`build_flashcards.py`'s `CARDS` list; **EXISTING** rows already ship and are listed
only to show reuse (do not duplicate them).

### bb_enzymes (5 new)
```
Cloze,"A competitive inhibitor binds the enzyme's {{c1::active site}}, directly competing with substrate for binding.",,topic:bb_enzymes,q_syn_001|q_syn_002
Cloze,"Noncompetitive inhibition: Vmax {{c1::decreases}} while Km stays {{c1::unchanged}}.",,topic:bb_enzymes,q_syn_001
Cloze,"Km is the substrate concentration at {{c1::half of Vmax}}; a higher Km means lower substrate affinity.",,topic:bb_enzymes,q_syn_001
Basic,"In an enzyme assay comparing 'with inhibitor' vs 'without', which variable is held constant and which is deliberately varied?","Hold the total enzyme amount (and temperature) constant. Substrate concentration is the independent variable you vary; reaction velocity is the dependent variable you measure.",topic:bb_enzymes,q_syn_003
Basic,"How does Km differ in kind from Keq?","Km is a kinetic quantity — the [S] at half-Vmax, describing how the enzyme handles substrate. Keq is a thermodynamic quantity — the equilibrium ratio set by the free-energy difference between reactants and products.",topic:bb_enzymes,q_syn_004
```
Reused existing: line 10 (enzymes lower Ea, not ΔG), q_dev_024 card (Vmax saturation).

### cp_electrochem (5 new)
```
Cloze,"E°cell = E°(cathode) − E°(anode); the half-cell with the {{c1::higher (more positive)}} reduction potential is the cathode.",,topic:cp_electrochem,q_syn_005
Cloze,"ΔG° = {{c1::−nFE°cell}}, so a positive E°cell gives a {{c1::negative}} ΔG° (spontaneous).",,topic:cp_electrochem,q_syn_006
Basic,"For ΔG° = −nFE°cell, what is n?","n is the number of moles of electrons transferred in the balanced redox reaction (e.g., n = 2 for Zn(s) + Cu²⁺ → Zn²⁺ + Cu(s)).",topic:cp_electrochem,q_syn_006
Cloze,"Ecell (the actual potential) changes with ion concentrations via the Nernst equation, but E°cell (standard) is {{c1::fixed}}.",,topic:cp_electrochem,q_syn_007
Cloze,"A galvanic cell keeps doing electrical work until it reaches {{c1::equilibrium}}, at which point Ecell = {{c1::0}} (a dead battery).",,topic:cp_electrochem,q_syn_008
```
Reused existing: line 54 (anode oxidation/cathode reduction), line 55 (+E°cell → spontaneous), line 59 / q_ho_002 (Nernst product ions lower Ecell), line 62 / q_ho_011 (ΔG=0 at equilibrium).

### cp_acids_bases (4 new)
```
Cloze,"Henderson–Hasselbalch: pH = pKa + log([A⁻]/[HA]); when [A⁻] = [HA], pH = {{c1::pKa}}.",,topic:cp_acids_bases,q_syn_009|q_syn_011
Basic,"In a buffer, which species neutralizes a small amount of added strong acid (H⁺), and what does it become?","The conjugate base (A⁻) reacts with the added H⁺ and is converted into the weak acid (HA), consuming the added acid.",topic:cp_acids_bases,q_syn_010
Basic,"If something suppresses a weak acid's dissociation, what happens to [H⁺] and pH?","Less dissociation releases fewer H⁺, so [H⁺] falls and the pH rises.",topic:cp_acids_bases,q_syn_012
Cloze,"A strong acid ionizes {{c1::completely}} (lower pH); a weak acid at equal concentration ionizes only {{c1::partially}} (higher pH).",,topic:cp_acids_bases,q_syn_024
```
Reused existing: line 48 / q_dev_011 (buffer = weak acid + conjugate base), line 45 / q_dev_006 (adding product shifts toward reactants), line 51 / q_ho_005 (strong-acid pH = −log[H⁺]).

### bb_genetics (3 new)
```
Cloze,"For independent genes, the probability of a combined genotype/phenotype is the {{c1::product}} of the separate gene probabilities (e.g., 1/2 × 1/3 = 1/6).",,topic:bb_genetics,q_syn_013|q_syn_014
Cloze,"A dihybrid cross of two double heterozygotes (YyRr × YyRr) gives a phenotypic ratio of {{c1::9:3:3:1}} under independent assortment.",,topic:bb_genetics,q_syn_014
Basic,"In a testcross (× homozygous recessive), how do you read one gene's result?","A ~1:1 dominant:recessive split means the tested parent is heterozygous for that gene; offspring that are all dominant mean it is homozygous dominant.",topic:bb_genetics,q_syn_015
```
Reused existing: line 37 (monohybrid 3:1 / 1:2:1), line 40 / q_ho_039 (testcross uses homozygous recessive).

### bb_citric_acid / bb_glycolysis (2 new)
```
Cloze,"One glucose → 2 pyruvate → 2 acetyl-CoA → {{c1::2}} turns of the citric acid cycle.",,topic:bb_citric_acid,q_syn_016
Basic,"Which stages of glucose oxidation make ATP/GTP by substrate-level phosphorylation, and which supplies the much larger remainder?","Glycolysis and the citric acid cycle make ATP/GTP directly by substrate-level phosphorylation; the electron transport chain (oxidative phosphorylation) supplies the much larger remainder.",topic:bb_glycolysis,q_syn_016
```
Reused existing: line 21 (glycolysis net 2 ATP), line 4 / q_dev_001 (TCA 1 ATP/GTP per turn).

### bb_membranes (1 new)
```
Cloze,"In osmosis, water moves toward the {{c1::hypertonic}} (higher-solute) side; a cell in a hypotonic solution {{c1::swells}} and may lyse.",,topic:bb_membranes,q_syn_017
```
Reused existing: line 28 / q_ho_032 (osmosis = diffusion of water).

### bb_dna (1 new)
```
Basic,"To write the complement of a DNA strand in the 5'→3' direction, what two steps do you take?","Pair each base (A-T, G-C), then reverse the order — because the two strands are antiparallel (e.g., 5'-AATGC-3' → 5'-GCATT-3').",topic:bb_dna,q_syn_018
```
Reused existing: line 32 / q_ho_033 (A-T, G-C pairing), line 33 / q_ho_036 (antiparallel).

### cp_thermo (1 new)
```
Cloze,"When combining ΔH (in kJ) with ΔS (in J) in ΔG = ΔH − TΔS, first convert both to the {{c1::same energy unit}} (e.g., kJ → J).",,topic:cp_thermo,q_syn_019
```
Reused existing: line 60 (ΔG=ΔH−TΔS), line 65 / q_ho_009 (ΔH>0,ΔS>0 → spontaneous at high T).

### cp_kinetics (1 new)
```
Cloze,"In a rate law rate = k[A]^m[B]^n, the exponent on each reactant is its {{c1::order}}; the sum m+n is the overall order.",,topic:cp_kinetics,q_syn_020
```
Reused existing: line 69 / q_ho_013 (overall order of k[A][B]²), line 72 / q_ho_014 (first-order doubling), line 64 / q_ho_010 (ΔG<0 ≠ fast), line 67 / q_dev_016 (catalyst lowers Ea not ΔG).

### cp_fluids (0 new)
Reused existing only: line 75 (continuity A₁v₁=A₂v₂), line 76 / q_ho_017 (Bernoulli: higher speed → lower pressure).

### ps_learning (2 new)
```
Cloze,"A {{c1::variable-ratio}} schedule (e.g., gambling) produces a high, steady response rate that is highly resistant to extinction.",,topic:ps_learning,q_syn_025
Basic,"How is negative reinforcement different from punishment?","Negative reinforcement removes an aversive stimulus and thereby increases a behavior; punishment (positive or negative) decreases a behavior.",topic:ps_learning,q_syn_026
```
Reused existing: line 93 / q_ho_047 (variable-ratio = unpredictable # responses), line 91 / q_ho_046 (negative reinforcement increases behavior by removing aversive).

### ps_social (1 new)
```
Cloze,"{{c1::Actor–observer}} bias: we attribute our own behavior to the situation but others' behavior to their disposition (the latter overlaps the fundamental attribution error).",,topic:ps_social,q_syn_027
```
Reused existing: line 94 / q_dev_038 (fundamental attribution error), line 97 / q_dev_043 (cognitive dissonance).

### ps_memory (0 new)
Reused existing only: line 87 / q_ho_042 (context-dependent memory).

### ps_demographics (1 new)
```
Basic,"How does a social gradient in health differ from a simple poverty threshold?","A gradient means health improves at every step up the SES ladder — not only the poorest are worse off. A threshold would mean only those below a cutoff suffer.",topic:ps_demographics,q_syn_030
```
Reused existing: line 101 / q_ho_052 (social gradient improves with SES).

---

# Items I flagged for a second look (author uncertainty)

None of the answer keys are in doubt — each was re-derived (calculations shown
above). Judgment calls worth a reviewer's eye:

1. **q_syn_003 (controlled variable). — RESOLVED.** The original stem ("held
   constant across both runs") let a test-wise student pick A, since the same `[S]`
   series appears in both runs. The stem was reworded to name `[S]` as the
   independent variable and X as the treatment up front, then ask for the *other*
   quantity that must be identical — which uniquely selects **B** (enzyme amount).
   Temperature is already stated constant in the passage, so it isn't offered.
2. **q_syn_006 rounding.** ΔG° = −(2)(96,500)(1.10) = −212,300 J → I label it
   "≈ −212 kJ." Distractor C (−106 kJ) is the n=1 error. Fine as written; just
   keep the "≈".
3. **q_syn_016 substrate-level count.** Answer 4 assumes the common MCAT
   convention (glycolysis **net** 2 ATP + 2 GTP from two TCA turns), explicitly
   excluding the ETC. The stem states "only substrate-level phosphorylation" to
   remove ambiguity. Distractors 36/30 are the two textbook "total aerobic yield"
   figures students conflate — intentional.
4. **q_syn_027 pairing.** The classmate judgment is squarely the fundamental
   attribution error; the self-judgment is the actor–observer bias (its
   complement). If you prefer to keep PS strictly to already-carded concepts, the
   self-judgment could instead be framed as "self-serving bias," but actor–observer
   is the more precise fit and I added a backing card for it.
5. **`cognitive_demand` honesty.** A couple of items (q_syn_002, q_syn_023,
   q_syn_029) are labeled `application` rather than `synthesis` because they apply
   a single principle to new data rather than chaining two. This keeps the tag
   honest per the spec (the cross-system `application` diagnosis fires for both
   demand levels, but synthesis carries the strongest signal).

---

# Report

- **Counts by section:** BB 10, CP 14, PS 6 (30 total). No CARS (science-track
  items are where the error-typing engine matters; CARS uses skill-accuracy, not
  `choice_diagnosis`).
- **Counts by demand:** synthesis 15, application 15, recall 0.
- **Split:** dev 15 / held_out 15 (each multi-question passage kept wholly within
  one split to avoid cross-split leakage).
- **New backing cards needed:** **27** (each new synthesis/application item that
  lacked coverage now has ≥1 prerequisite card; many also reuse existing cards, so
  every `q_syn_*` has ≥1 backing card and the cross-system signal can fire).
- **New topic_ids:** **none** (all reuse existing outline topics).
- **Decisions for the user:**
  1. Approve adding `cognitive_demand` + `choice_diagnosis` to the question schema
     + validator (additive, non-breaking) — required for these items to do their
     job. Coordinate with the agent currently editing `build_question_bank.py`.
  2. Keep enzyme-inhibition items under `bb_enzymes`, or split out a new
     `bb_enzyme_kinetics` topic (I recommend keeping them under `bb_enzymes` for
     v1).
  3. Confirm the q_syn_003 wording tweak (add "besides temperature") if you find
     the controlled-variable choice too open.
  4. Confirm q_syn_027's self-judgment concept (actor–observer bias vs
     self-serving bias).

---

## Review outcome (2026-07-01)

**Status:** All 30 answer keys were independently verified as **scientifically
correct**. All three required fixes have now been **applied to this draft** (see
"Fixes applied" below). The draft is **still NOT integrated** — the next step is
appending the items/cards into the data files.

### Fix 1 (important) — some backing cards encode the *answer*, not the *components* — ✅ APPLIED

Several backing cards encode the **integrated answer** rather than the
**component** facts. This collapses "synthesis" back into recall and muddies the
`content_gap`↔`application` signal (the whole point of these items): if the
prerequisite card already states the conclusion, a strong `M` no longer
distinguishes "held the components" from "memorized the payoff." Clearest
offenders:

- **NEW-E1** (q_syn_001)
- **NEW-T1** (q_syn_019)
- **NEW-AB3** (q_syn_012)
- **NEW-K1** (q_syn_020)

**Resolution:** decompose those cards to component-level facts, **OR** honestly
relabel the affected item `application` instead of `synthesis`.

### Fix 2 — q_syn_003 has real ambiguity — ✅ APPLIED

The same `[S]` series (1, 2, 4, 8, 16) is used in **both** runs, so choice A
("substrate concentration held constant across both runs") is defensible against
the intended answer **B** (enzyme amount). Reword the stem so the control is
unambiguous, e.g. *"so that any difference in velocity is attributable to X,
which quantity must be identical in both runs?"*

### Fix 3 (minor schema) — `trap` tag over-applied — ✅ APPLIED

> **Historical.** The allowed trap enum was later expanded to
> {`negation`, `unit`, `inverse`, `scaling`, `transpose`, `partial`} and traps
> were separated from the content axis — see the finalized "Choice-axis re-tag
> pass". The two items below remain content confusions (correctly *not* traps).

At the time of this fix the `trap` tag was used beyond its then-allowed values
(`negation` | `unit`). These are content confusions, not traps, and were
stripped at integration so the validator stays clean:

- **q_syn_016 C** ("total aerobic yield") — content confusion, not a trap.
- **q_syn_018 D** ("uses uracil") — content confusion, not a trap.
- **q_syn_007 C** — uses a bare `trap` (no allowed value).

### Approved decisions

1. **Add `cognitive_demand` + `choice_diagnosis` schema** (additive,
   non-breaking).
2. **Keep enzyme items under `bb_enzymes`** — no new `topic_id`.
3. **Keep q_syn_027 as actor–observer bias** — do NOT switch to self-serving
   bias.

---

## Fixes applied (2026-07-01)

All three fixes from the review outcome are now reflected in the specs above.
Summary of exactly what changed (draft only — no data files touched yet):

**Fix 1 — decomposed the four component-vs-answer cards (kept items `synthesis`).**
Each offending card was rewritten to a *component* fact so no single backing card
states the integrated conclusion; the student must chain the components. The items
stay `synthesis` (the higher-value cross-system signal), not relabelled.

| card | was (encoded the answer) | now (component only) |
|------|--------------------------|----------------------|
| NEW-E1 (q_syn_001/002) | "Competitive: Vmax unchanged, Km↑, overcome by more substrate" | "A competitive inhibitor binds the active site, competing with substrate" |
| NEW-T1 (q_syn_019) | "crossover T = ΔH/ΔS; convert units" | "convert ΔH (kJ) and ΔS (J) to the same unit before combining in ΔG = ΔH − TΔS" |
| NEW-AB3 (q_syn_012) | "common-ion: adding A⁻ shifts left, less dissociation, higher pH" | "less dissociation → fewer H⁺ → higher pH" (left-shift comes from existing q_dev_006 card) |
| NEW-K1 (q_syn_020) | "compare experiments… doubling [X] ×4 ⇒ 2nd order" | "the exponent on each reactant is its order; overall = sum" |

Per-question **Backing cards** lines for q_syn_001/002/012/019/020 were updated to
note the derivation the student now has to perform.

**Fix 1b (second-pass sweep, 2026-07-01) — six more answer-encoding cards
decomposed.** A follow-up scan of *every* `q_syn_*`-linked card found six more
cards that still collapsed an item to single-card recall (or leaked the exact
answer text), applying the same Fix-1 rule. All were rewritten to component facts;
`supports_question` links (and therefore coverage) are unchanged, and the
appendix rows above already reflect the new text.

| card | item | was (encoded the answer) | now (component only) |
|------|------|--------------------------|----------------------|
| NEW-E5 | q_syn_004 (synth) | "inhibitors don't change ΔG or Keq" (= answer B) | "Km is kinetic ([S] at ½Vmax); Keq is thermodynamic" (Km≠Keq distinction; the *doesn't-change-thermo* half comes from the existing catalyst card) |
| NEW-EC5 | q_syn_008 (synth) | "Ecell→0 **and** ΔG→0" (= answer A) | "cell works until equilibrium, where Ecell = 0" (ΔG→0 comes from the existing "at equilibrium ΔG = 0" card, already linked to q_syn_008) |
| NEW-AB2 | q_syn_010 (synth) | "A⁻ reacts with H⁺… pH drops only slightly" (= answer B) | "A⁻ neutralizes added H⁺, becoming HA" (mechanism only; the *resists-pH-change* half comes from the existing buffer card) |
| NEW-BB2 | q_syn_016 (synth) | "4 — net 2 ATP + 2 GTP…" (= the integrated total) | "glycolysis + TCA are substrate-level; the ETC supplies the rest" (the 2+2 sum is derived from the three existing component cards) |
| NEW-D1 | q_syn_018 | example was the exact exam sequence 5'-TACGGA-3' → 5'-TCCGTA-3' | same two-step method, neutral example 5'-AATGC-3' → 5'-GCATT-3' |
| NEW-G1 | q_syn_013 | example "1/4 × 1/4 = 1/16" (= q_syn_013's exact answer) | product-rule example changed to "1/2 × 1/3 = 1/6" |

Application-only principle cards (NEW-E4, NEW-G3, NEW-L2, NEW-EC3, NEW-DEM1) and
pre-existing concept cards were intentionally left as-is: they teach a general
principle without reproducing a synthesis chain, which is expected for
`application` items.

**Fix 2 — reworded q_syn_003 stem.** The stem now names `[S]` as the independent
variable and X as the treatment, then asks for the *other* quantity that must be
identical in both runs → uniquely selects **B** (enzyme amount). choice_diagnosis A
updated to match. Flagged-item note #1 marked RESOLVED.

**Fix 3 — stripped the three invalid `trap` tags.** Removed the bare/invalid `trap`
from **q_syn_007 C**, **q_syn_016 C**, and **q_syn_018 D** (they are content
confusions → `content_gap` only). At the time of this fix the only remaining
`trap` tags were the valid `trap: negation` (q_syn_006 B) and `trap: unit`
(q_syn_019 B/C). *(Superseded by the "Choice-axis re-tag pass" below: traps now
sit on `null` distractors, and q_syn_019 C was reclassified to a plain `null`
near-miss — leaving `trap: negation` on q_syn_005 D + q_syn_006 B and
`trap: unit` on q_syn_019 B.)*

The draft is now clear to integrate (append-only) per the Integration plan above.

---

## Choice-axis re-tag pass — FINALIZED (2026-07-01)

> **This section supersedes all earlier partial tallies.** Interim numbers from
> the first re-tag draft (78/9/3, traps-carried-on-null) are obsolete; the
> finalized state below is what ships in `data/questions.json` and what
> `scripts/build_question_bank.py` emits. Where any older paragraph in this file
> conflicts, this section wins.

**Why:** the prior authoring pass tagged nearly every distractor `content_gap`,
giving **no discrimination at the choice level**. If the content axis never says
"this landing is *not* a content gap," a high-`M` student who memorized cards
shallowly (recall in isolation, no true understanding) gets mis-explained as an
`application`/`misread` error instead of what it is. This finalized pass applies
the spec's **3-axis choice tagging methodology** (`ERROR-DIAGNOSIS-SPEC.md` →
"Choice tagging methodology"). No stems, choices, or answer keys were touched —
only `choice_diagnosis`.

**The three choice axes (content axis is the *only* one authored on a choice):**

- **`content_gap`** (+ specific `misconception`): landing here requires a
  **false belief** about the science. `maps_to: "content_gap"`.
- **`trap: <type>`**: a predictable **execution-error** landing — feeds the
  behavioral/misread prior, *not* content. `maps_to: null`, no `misconception`.
  Allowed types: `negation`, `unit`, `inverse`, `scaling`, `transpose`,
  `partial`.
- **`null`**: genuinely **non-diagnostic** — an arbitrary wrong number with no
  pathway, or a plausible-but-unrelated grab. The whole entry is `null`.

**Distractor tally (90 distractors = 30 items × 3 non-correct choices; the
correct index is always `null` and is excluded):**

| axis | count | notes |
|-----|-------|-------|
| `content_gap` (specific misconception) | **71** | distinct within each question |
| `trap: <type>` (execution landing) | **12** | see trap breakdown below |
| `null` (non-diagnostic) | **7** | numeric near-miss / plausible grab |

**Trap breakdown (12):** `inverse` ×3 (q_syn_005 C, 011 A, 023 B),
`negation` ×2 (q_syn_005 D, 006 B), `partial` ×4 (q_syn_008 D, 012 D, 013 C,
014 D), `scaling` ×1 (q_syn_011 D), `transpose` ×1 (q_syn_020 B),
`unit` ×1 (q_syn_019 B).

Before this pass: **0** `null` distractors and **3** `trap` tags — all carried
redundantly as `content_gap` **+** `trap`. After: traps and nulls are their own
axes — a `trap` carries `maps_to: null` and **no** misconception (a mere content
confusion must stay `content_gap`, never a trap), and a `null` is a bare
non-diagnostic entry.

**Per-item before → after (only the 19 choices that changed):**

| item / choice | before | after |
|---------------|--------|-------|
| q_syn_005 C | `content_gap` "wrong subtraction (0.42)" | `trap: inverse` |
| q_syn_005 D | `content_gap` "sign-flipped E°cell" | `trap: negation` (sign-flip landing → −1.10 V) |
| q_syn_006 B | `content_gap` + `trap: negation` | `trap: negation` (dropped sign is execution, not content) |
| q_syn_008 D | `content_gap` "recalls Ecell→0 not ΔG→0 (partial)" | `trap: partial` |
| q_syn_011 A | `content_gap` "inverted the ratio" | `trap: inverse` |
| q_syn_011 D | `content_gap` "two log units (10²)" | `trap: scaling` |
| q_syn_012 D | `content_gap` "shift right, pH direction wrong" | `trap: partial` |
| q_syn_013 C | `content_gap` "solves one gene, forgets the 2nd" | `trap: partial` |
| q_syn_014 D | `content_gap` "only the yellow fraction (3/4)" | `trap: partial` |
| q_syn_019 B | `content_gap` + `trap: unit` | `trap: unit` (unconverted units is execution, not content) |
| q_syn_020 B | `content_gap` "swaps the orders of A and B" | `trap: transpose` |
| q_syn_023 B | `content_gap` "inverted the area ratio" | `trap: inverse` |
| q_syn_009 D | `content_gap` "strong acid / pKa÷2" | `null` (numeric near-miss, no coherent pathway) |
| q_syn_016 D | `content_gap` "~30 total-ATP" | `null` (numeric variant of C's total-yield conflation) |
| q_syn_019 C | `content_gap` + `trap: unit` "partial unit handling" | `null` (numeric near-miss; not a predictable unit landing) |
| q_syn_023 D | `content_gap` "multiplied areas" | `null` (numeric distractor, no clean derivation) |
| q_syn_027 C | `content_gap` "unrelated concepts" | `null` (plausible grab, no specific misconception) |
| q_syn_027 D | `content_gap` "unrelated concepts" | `null` (plausible grab, no specific misconception) |
| q_syn_028 C | `content_gap` "unrelated bystander concept" | `null` (plausible grab, no specific misconception) |

Items that remain all-`content_gap` (q_syn_001–004, 010, 015, 017, 018, 021,
022, 024–026, 029, 030) genuinely have three distinct misconception distractors
each — the rubric says not to force a `trap`/`null` where the choice doesn't
honestly support it.

---

## Bank-wide choice-tagging expansion — FINALIZED (2026-07-01)

> **This section extends the re-tag pass above from the 30 `q_syn_*` items to
> the *entire* science bank.** The synthesis-item counts above are unchanged
> and remain a subset of the totals below.

**Why:** the `q_syn_*` pass tagged only 30 of 127 science questions, so 291 of
381 science distractors (78%) carried **no** `choice_diagnosis` at all. That
thin coverage was the ceiling on the engine's ability to tell `content_gap`
(a real misconception) from `application` (content held, not deployed) — the
whole shallow-mastery signal. This pass applies the **same 3-axis methodology**
(`ERROR-DIAGNOSIS-SPEC.md` → "Choice tagging methodology") to the 97
recall-heavy `q_dev_*` / `q_ho_*` science items. Authoring lives in
`scripts/build_question_bank.py` (`CHOICE_DIAGNOSIS` dict, keyed by id, wired in
`main()`); `data/questions.json` was regenerated. No stems, choices, or answer
keys were touched — only `choice_diagnosis`. CARS is untouched (0 of 13 CARS
questions carry choice tags, by design).

**Science-distractor tally (381 distractors = 127 items × 3 non-correct
choices; the correct index is always `null` and excluded):**

| axis | before | after | notes |
|------|--------|-------|-------|
| `content_gap` (specific misconception) | 71 | **287** | distinct within each question |
| `trap: <type>` (execution landing) | 12 | **18** | enum-only; breakdown below |
| `null` (non-diagnostic) | 7 | **76** | arbitrary number / unrelated grab |
| untagged (no `choice_diagnosis`) | 291 | **0** | every science item now tagged |
| **science questions carrying choice tags** | 30 / 127 | **127 / 127** | |

**Trap breakdown (18 total):** `partial` ×6, `scaling` ×4, `inverse` ×4,
`negation` ×2, `unit` ×1, `transpose` ×1. The 6 *new* traps (beyond the 12 from
`q_syn_*`) are honest execution/attractor landings on the **numeric CP items**,
where an arithmetic slip by a student who holds the concept genuinely exists:

| item / choice | trap | landing |
|---------------|------|---------|
| q_dev_020 B (net glycolysis ATP = 2) | `partial` | reports gross 4 — forgot to subtract the 2 ATP invested |
| q_ho_005 B (pH of 0.010 M HCl) | `scaling` | used 0.10 M (off by one power of ten) → pH 1.0 |
| q_ho_008 B (pH 4 vs pH 6, ×100) | `scaling` | used one pH unit (10¹) instead of two (10²) |
| q_ho_013 A (overall order of k[A][B]²) | `partial` | took only [A]'s order (1); didn't sum the exponents |
| q_ho_014 B (double [A], first order) | `scaling` | squared the factor (2²) despite the stated first order |
| q_ho_014 D (double [A], first order) | `inverse` | took the reciprocal of the factor (0.5×) |

**Honesty notes — where the choices are deliberately `null`-heavy.** Traps stay
rare because this bank is recall-heavy ("which/what/define"): a wrong pick on a
conceptual recall item is almost always a genuine **content confusion**, not an
execution slip, so it is tagged `content_gap` — not manufactured into a trap.
Conversely, several recall items have distractors that are **arbitrary numbers
or unrelated term-grabs** with no nameable misconception; forcing a
`content_gap` onto those would fabricate a belief and dilute the content axis,
so they are honestly `null`:

- **All-`null` items** (all three distractors non-diagnostic): **q_ho_025**
  (NADH per acetyl-CoA — 1/2/4 are bare count near-misses) and **q_ho_051**
  (SES components — blood type / height / personality type are arbitrary
  non-SES grabs). Tagged but carry no content or trap signal.
- **`null`-heavy items** (single `content_gap` + two grabs): e.g. q_dev_019
  (continuity vs Pascal/Archimedes — only the Bernoulli near-miss is a real
  confusion), q_dev_021 (glycolysis location — only the mitochondria answer is
  diagnostic; nucleus/ER are grabs), q_dev_025 (membrane framework —
  peptidoglycan is the one nameable cell-wall confusion; cellulose repeats it,
  glycogen is a grab), q_dev_041 (social-determinant — blood type is the one
  biological-vs-social confusion; the genetic/eye-color choices repeat it).
- **Redundant-belief distractors** demoted to `null`: where two distractors
  encode the *same* underlying false belief, only one is `content_gap` (the
  rubric forbids repeating a misconception within a question), and the twin is
  `null` — e.g. q_dev_002 D ("slow the pathway" repeats B's ADP-reversal),
  q_ho_041 D (iconic memory repeats A's sensory-memory error), q_ho_044 D
  ("motor skills" repeats A's procedural-vs-explicit error).

**Result:** the content axis can now discriminate on **all** 127 science items
(was 30). Where the spec's shallow-mastery term (`w_mis·g`) needs a
distinctive-misconception distractor to keep `content_gap` in contention at high
`M`, the recall bank now supplies one on 287 distractors instead of 71.

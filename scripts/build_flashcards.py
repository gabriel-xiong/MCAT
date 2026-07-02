#!/usr/bin/env python3
"""Build the memory-deck CSVs from one authored source of record.

Emits three files (kept in sync):
  data/flashcards-dev.csv         all notes (Cloze + Basic)
  data/flashcards-dev-cloze.csv   Cloze notes only
  data/flashcards-dev-basic.csv   Basic notes only

Rules enforced by construction (see data/deck-tagging.md):
  - single topic tag per note:  topic:{topic_id}
  - Cloze uses ONE index for paired/opposite blanks ({{c1::x}} … {{c1::y}}) so
    both hide together on ONE card — never {{c1::}}+{{c2::}} (that leaks the
    other answer). Max 2 blanks; blanks are anchored, not bare terms.
  - Basic = a real question on the front; no MCQ / "which of the following".
  - text and back fields are ALWAYS double-quoted (commas are common and an
    unquoted comma splits the row).
  - no CARS flashcards (CARS is performance-only).

`supports_question` = precise per-question link: the id(s) of the performance
question(s) whose tested fact this card teaches. Every science question in
data/questions.json has >=1 backing card (self-checked below); some cards are
extra concept cards with no linked question (empty). CARS questions have no
cards by design.

Run:  python scripts/build_flashcards.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# (note_type, text, back, topic_id, supports_question)
# Basic notes put the question in `text` and the answer in `back`.
# Cloze notes leave `back` empty.  supports = "|"-joined precise question ids.
CARDS: list[tuple[str, str, str, str, str]] = [
    # ---- bb_citric_acid ----------------------------------------------------
    ("Cloze", "The citric acid cycle takes place in the {{c1::mitochondrial matrix}}.",
     "", "bb_citric_acid", ""),
    ("Cloze", "The citric acid cycle oxidizes {{c1::acetyl-CoA}} to CO₂ and transfers electrons to carriers used by the ETC.",
     "", "bb_citric_acid", ""),
    ("Cloze", "Each turn of the TCA cycle makes one {{c1::ATP or GTP}} via substrate-level phosphorylation (not via the ETC).",
     "", "bb_citric_acid", "q_syn_016"),
    ("Cloze", "In the citric acid cycle, GTP/ATP is made by substrate-level phosphorylation during the conversion of {{c1::succinyl-CoA to succinate}}.",
     "", "bb_citric_acid", "q_dev_001"),
    ("Cloze", "High {{c1::ADP}} signals low ATP and increases catabolic flux through key enzymes.",
     "", "bb_citric_acid", "q_dev_002"),
    ("Cloze", "Acetyl-CoA joins {{c1::oxaloacetate}} to form {{c1::citrate}} at the start of each cycle turn.",
     "", "bb_citric_acid", "q_dev_023"),
    ("Cloze", "Per turn, the citric acid cycle releases {{c1::2}} CO₂ and makes {{c1::3}} NADH.",
     "", "bb_citric_acid", "q_ho_023|q_ho_025"),
    ("Basic", "When ADP is high, why do metabolic pathways generally speed up?",
     "Allosteric activation of rate-limiting enzymes — the cell needs to regenerate ATP.",
     "bb_citric_acid", "q_dev_002"),
    ("Basic", "Why does the citric acid cycle itself produce little ATP directly?",
     "Most of its energy is captured as NADH and FADH₂, which feed the electron transport chain — where the bulk of ATP is actually made.",
     "bb_citric_acid", "q_ho_024"),

    # ---- bb_enzymes --------------------------------------------------------
    ("Cloze", "Enzymes speed a reaction by lowering its {{c1::activation energy}}, without changing {{c1::ΔG}}.",
     "", "bb_enzymes", "q_dev_003|q_dev_004|q_syn_004"),
    ("Cloze", "ΔG > 0 → {{c1::endergonic}}; ΔG < 0 → {{c1::exergonic}}.",
     "", "bb_enzymes", "q_dev_003"),
    ("Cloze", "Reaction rate depends on {{c1::activation energy}}, not ΔG.",
     "", "bb_enzymes", "q_dev_003"),
    ("Cloze", "{{c1::Competitive}} inhibitors bind the active site; allosteric inhibitors bind {{c1::elsewhere}} and change enzyme shape/activity.",
     "", "bb_enzymes", "q_dev_005|q_syn_001"),
    ("Cloze", "An enzyme reaches {{c1::Vmax}} when its active sites are {{c1::saturated}} with substrate.",
     "", "bb_enzymes", "q_dev_024|q_syn_002"),
    ("Basic", "Why compare reaction rates (not ΔG) to judge activation energy?",
     "ΔG reflects spontaneity/energy change; Ea sets the barrier that controls rate at a given temperature.",
     "bb_enzymes", "q_dev_004"),
    ("Basic", "How does an allosteric inhibitor differ from a competitive inhibitor?",
     "Competitive: active site, blocks substrate. Allosteric: non-active site, conformation change (often lowers affinity).",
     "bb_enzymes", "q_dev_005"),
    ("Cloze", "The {{c1::active site}} is the region of an enzyme where substrate binds and catalysis occurs.",
     "", "bb_enzymes", "q_ho_026"),
    ("Cloze", "Induced fit: when substrate binds, the enzyme's {{c1::active site}} changes shape to fit it more snugly.",
     "", "bb_enzymes", "q_ho_027"),
    ("Cloze", "Heating an enzyme far above its optimum {{c1::denatures}} it, lowering its activity.",
     "", "bb_enzymes", "q_ho_028"),

    # ---- bb_glycolysis -----------------------------------------------------
    ("Cloze", "Glycolysis takes place in the {{c1::cytoplasm}} (cytosol), not the mitochondrion.",
     "", "bb_glycolysis", "q_dev_021"),
    ("Cloze", "Net ATP yield of glycolysis per glucose is {{c1::2}} (4 produced − 2 invested).",
     "", "bb_glycolysis", "q_dev_020|q_ho_021|q_syn_016"),
    ("Cloze", "Glycolysis reduces NAD⁺ to {{c1::NADH}} and ends in two molecules of {{c1::pyruvate}}.",
     "", "bb_glycolysis", "q_dev_022|q_ho_019"),
    ("Cloze", "The committed, rate-limiting enzyme of glycolysis is {{c1::phosphofructokinase-1}} (PFK-1).",
     "", "bb_glycolysis", "q_ho_020"),
    ("Basic", "Under anaerobic conditions in muscle, what happens to pyruvate and why?",
     "It is reduced to lactate to regenerate NAD⁺, so glycolysis (and ATP output) can continue.",
     "bb_glycolysis", "q_ho_022"),

    # ---- bb_membranes ------------------------------------------------------
    ("Cloze", "The plasma membrane's core structure is the {{c1::phospholipid bilayer}}.",
     "", "bb_membranes", "q_dev_025"),
    ("Cloze", "In a phospholipid, the phosphate head is {{c1::hydrophilic}} and the fatty-acid tails are {{c1::hydrophobic}}.",
     "", "bb_membranes", "q_dev_026"),
    ("Cloze", "{{c1::Active}} transport moves solutes against their gradient (needs energy); {{c1::passive}} transport moves them down the gradient.",
     "", "bb_membranes", "q_ho_029|q_ho_030"),
    ("Cloze", "Osmosis is the diffusion of {{c1::water}} across a selectively permeable membrane.",
     "", "bb_membranes", "q_ho_032|q_syn_017"),
    ("Basic", "Why can O₂ cross the membrane by simple diffusion but glucose usually cannot?",
     "O₂ is small and nonpolar, so it dissolves through the lipid bilayer; glucose is larger and polar, so it needs a transport protein.",
     "bb_membranes", "q_ho_029"),
    ("Cloze", "Cholesterol in animal cell membranes modulates membrane {{c1::fluidity}}.",
     "", "bb_membranes", "q_ho_031"),

    # ---- bb_dna ------------------------------------------------------------
    ("Cloze", "DNA replication is {{c1::semiconservative}}: each daughter has one old and one new strand.",
     "", "bb_dna", "q_dev_027"),
    ("Cloze", "In DNA, A pairs with {{c1::T}} and G pairs with {{c1::C}}.",
     "", "bb_dna", "q_ho_033|q_syn_018"),
    ("Cloze", "The two strands of DNA run {{c1::antiparallel}} and are complementary.",
     "", "bb_dna", "q_ho_036|q_syn_018"),
    ("Cloze", "{{c1::Helicase}} unwinds the double helix; {{c1::ligase}} joins Okazaki fragments.",
     "", "bb_dna", "q_ho_034|q_dev_029"),
    ("Basic", "Why is the lagging strand synthesized in fragments?",
     "DNA polymerase only builds 5'→3'; on the lagging strand the template runs the opposite way, so it is copied in short Okazaki fragments.",
     "bb_dna", "q_ho_035"),
    ("Cloze", "DNA polymerase builds new strands only in the {{c1::5'→3'}} direction.",
     "", "bb_dna", "q_dev_028"),

    # ---- bb_genetics -------------------------------------------------------
    ("Cloze", "A monohybrid cross Aa × Aa gives a phenotypic ratio of {{c1::3:1}} and a genotypic ratio of {{c1::1:2:1}}.",
     "", "bb_genetics", "q_dev_030|q_ho_037|q_syn_013"),
    ("Cloze", "{{c1::Genotype}} is the genetic makeup; {{c1::phenotype}} is the observable trait.",
     "", "bb_genetics", "q_dev_031"),
    ("Cloze", "Mendel's law of {{c1::segregation}}: the two alleles of a gene separate during gamete formation.",
     "", "bb_genetics", "q_ho_038"),
    ("Cloze", "A testcross uses a {{c1::homozygous recessive}} partner to reveal an unknown genotype.",
     "", "bb_genetics", "q_ho_039|q_syn_015"),
    ("Basic", "In codominance, how is the heterozygote expressed?",
     "Both alleles are expressed fully and at the same time (e.g., type AB blood) — not blended.",
     "bb_genetics", "q_dev_044"),
    ("Cloze", "Genes far apart on the same chromosome assort nearly {{c1::independently}} because of crossing over.",
     "", "bb_genetics", "q_ho_040"),

    # ---- cp_acids_bases ----------------------------------------------------
    ("Cloze", "Brønsted–Lowry acids {{c1::donate}} H⁺; bases {{c1::accept}} H⁺.",
     "", "cp_acids_bases", "q_dev_006|q_dev_007"),
    ("Cloze", "CH₃COOH is a {{c1::weaker}} acid than HCl (conjugate base strength runs opposite to acid strength).",
     "", "cp_acids_bases", "q_dev_007"),
    ("Cloze", "When product is added to a reaction at equilibrium, the reaction shifts toward {{c1::reactants}}.",
     "", "cp_acids_bases", "q_dev_006|q_syn_012"),
    ("Cloze", "Increasing {{c1::[H⁺]}} shifts a base toward its {{c1::protonated}} (conjugate acid) form.",
     "", "cp_acids_bases", "q_dev_006"),
    ("Cloze", "HF and HCN in water: the ionization equilibrium lies to the {{c1::left}}, so both are {{c1::weak}} acids (only partial ionization).",
     "", "cp_acids_bases", "q_dev_007"),
    ("Cloze", "A buffer contains a {{c1::weak acid}} and its {{c1::conjugate base}}, so it resists pH change.",
     "", "cp_acids_bases", "q_dev_011|q_syn_010"),
    ("Cloze", "At 25 °C a neutral solution has [H⁺] = {{c1::1×10⁻⁷ M}} and pH = {{c1::7}}.",
     "", "cp_acids_bases", "q_ho_007"),
    ("Basic", "Why is the conjugate base of a strong acid a very weak base?",
     "A strong acid gives up its proton almost completely because the resulting conjugate base is stable and has little tendency to reaccept H⁺.",
     "cp_acids_bases", "q_dev_007"),
    ("Cloze", "For a strong acid, pH = −log[H⁺]; a 0.010 M HCl solution has pH {{c1::2}}.",
     "", "cp_acids_bases", "q_ho_005|q_syn_024"),
    ("Cloze", "A conjugate acid–base pair differs by one H⁺, e.g. {{c1::H₂CO₃}} / {{c1::HCO₃⁻}}.",
     "", "cp_acids_bases", "q_ho_006"),
    ("Cloze", "Each pH unit is a 10× change in [H⁺], so pH 4 is {{c1::100}}× more acidic than pH 6.",
     "", "cp_acids_bases", "q_ho_008"),

    # ---- cp_electrochem ----------------------------------------------------
    ("Cloze", "In a galvanic cell, oxidation occurs at the {{c1::anode}} and reduction at the {{c1::cathode}}.",
     "", "cp_electrochem", "q_dev_008|q_ho_004|q_syn_005"),
    ("Cloze", "A galvanic cell has a {{c1::positive}} E°cell, so its redox reaction is {{c1::spontaneous}} (ΔG° < 0).",
     "", "cp_electrochem", "q_dev_009|q_syn_006"),
    ("Cloze", "The {{c1::salt bridge}} keeps the half-cells electrically neutral by allowing ion flow.",
     "", "cp_electrochem", "q_dev_010"),
    ("Basic", "How does electrolysis differ from a galvanic cell in energy terms?",
     "Electrolysis uses external electrical energy to drive a nonspontaneous reaction; a galvanic cell releases energy from a spontaneous one.",
     "cp_electrochem", "q_ho_003"),
    ("Cloze", "The species that is oxidized is the {{c1::reducing agent}} (e.g., Zn in Zn + Cu²⁺).",
     "", "cp_electrochem", "q_ho_001"),
    ("Cloze", "By the Nernst equation, raising the concentration of product ions {{c1::lowers}} the cell potential.",
     "", "cp_electrochem", "q_ho_002|q_syn_007"),

    # ---- cp_thermo ---------------------------------------------------------
    ("Cloze", "Gibbs free energy: ΔG = ΔH − {{c1::T}}ΔS.",
     "", "cp_thermo", "q_dev_013|q_syn_019"),
    ("Cloze", "A reaction is spontaneous at all temperatures when ΔH is {{c1::negative}} and ΔS is {{c1::positive}}.",
     "", "cp_thermo", "q_dev_012"),
    ("Cloze", "At equilibrium, ΔG = {{c1::0}}.",
     "", "cp_thermo", "q_ho_011|q_syn_008"),
    ("Cloze", "Entropy (S) measures the {{c1::disorder}} (dispersal of energy and matter) of a system.",
     "", "cp_thermo", "q_ho_012"),
    ("Basic", "Does a negative ΔG mean the reaction is fast?",
     "No — ΔG < 0 means spontaneous (thermodynamically favorable). Speed is set separately by activation energy / kinetics.",
     "cp_thermo", "q_ho_010|q_syn_021"),
    ("Cloze", "When ΔH > 0 and ΔS > 0, a reaction is spontaneous only at {{c1::high}} temperature.",
     "", "cp_thermo", "q_ho_009|q_syn_019"),
    ("Cloze", "A spontaneous process proceeds without a continuous {{c1::external energy}} input.",
     "", "cp_thermo", "q_dev_014"),

    # ---- cp_kinetics -------------------------------------------------------
    ("Cloze", "A catalyst lowers the {{c1::activation energy}}; it does not change {{c1::ΔG}} or the equilibrium.",
     "", "cp_kinetics", "q_dev_016|q_syn_021"),
    ("Cloze", "Raising temperature speeds a reaction because more molecules exceed the {{c1::activation energy}}.",
     "", "cp_kinetics", "q_dev_015"),
    ("Cloze", "For rate = k[A][B]², the overall reaction order is {{c1::3}}.",
     "", "cp_kinetics", "q_ho_013|q_syn_020"),
    ("Basic", "Why doesn't a catalyst change the equilibrium position?",
     "It lowers activation energy for the forward and reverse steps equally, speeding both — so it changes rate, not the equilibrium constant.",
     "cp_kinetics", "q_dev_016"),
    ("Cloze", "The rate constant k depends on {{c1::temperature}} and a {{c1::catalyst}}, not on reactant concentration.",
     "", "cp_kinetics", "q_dev_017"),
    ("Cloze", "For a reaction first order in A, doubling [A] multiplies the rate by {{c1::2}}.",
     "", "cp_kinetics", "q_ho_014|q_syn_020"),
    ("Cloze", "A {{c1::zero-order}} reaction's rate is independent of reactant concentration.",
     "", "cp_kinetics", "q_ho_015"),
    ("Cloze", "Activation energy is the {{c1::minimum}} energy reactants need in order to react.",
     "", "cp_kinetics", "q_ho_016"),

    # ---- cp_fluids ---------------------------------------------------------
    ("Cloze", "Continuity for an incompressible fluid: A₁v₁ = {{c1::A₂v₂}} (volume flow rate is conserved).",
     "", "cp_fluids", "q_dev_018|q_dev_019|q_syn_022|q_syn_023"),
    ("Cloze", "By Bernoulli's principle, where fluid speed is higher, pressure is {{c1::lower}} (at constant height).",
     "", "cp_fluids", "q_ho_017|q_syn_022"),
    ("Cloze", "An object floats when the buoyant force equals its {{c1::weight}}.",
     "", "cp_fluids", "q_ho_018"),
    ("Basic", "In a pipe that narrows, what happens to the fluid's speed and why?",
     "Speed increases: the same volume per second must pass through a smaller cross-sectional area (continuity).",
     "cp_fluids", "q_dev_018"),
    ("Cloze", "{{c1::Pascal's}} principle: pressure applied to an enclosed fluid is transmitted undiminished throughout it.",
     "", "cp_fluids", "q_dev_042"),
    ("Cloze", "The SI unit of pressure, the pascal, equals {{c1::N/m²}}.",
     "", "cp_fluids", "q_ho_059"),

    # ---- ps_memory ---------------------------------------------------------
    ("Cloze", "Encoding gets information in; {{c1::storage}} holds it; {{c1::retrieval}} gets it back out.",
     "", "ps_memory", "q_dev_032"),
    ("Cloze", "Short-term (working) memory holds about {{c1::7 ± 2}} items.",
     "", "ps_memory", "q_dev_033"),
    ("Cloze", "{{c1::Long-term}} memory is the relatively permanent, large-capacity store.",
     "", "ps_memory", "q_ho_041"),
    ("Cloze", "The {{c1::serial position}} effect: the first and last list items are recalled best.",
     "", "ps_memory", "q_ho_043"),
    ("Basic", "What is the difference between explicit and implicit memory?",
     "Explicit (declarative): consciously recalled facts and events. Implicit: skills and conditioned responses expressed without conscious recall.",
     "ps_memory", "q_ho_044"),
    ("Cloze", "Maintaining information in short-term memory by repetition is {{c1::rehearsal}}.",
     "", "ps_memory", "q_dev_034"),
    ("Cloze", "{{c1::Context-dependent}} memory: recall improves when the retrieval context matches encoding.",
     "", "ps_memory", "q_ho_042|q_syn_029"),

    # ---- ps_learning -------------------------------------------------------
    ("Cloze", "In Pavlov's dogs, food is the {{c1::unconditioned stimulus}} and salivation to food is the {{c1::unconditioned response}}.",
     "", "ps_learning", "q_dev_035"),
    ("Cloze", "After conditioning, the bell becomes the {{c1::conditioned stimulus}}.",
     "", "ps_learning", "q_ho_045"),
    ("Cloze", "A reinforcer {{c1::increases}} a behavior; a punisher {{c1::decreases}} it.",
     "", "ps_learning", "q_dev_036"),
    ("Cloze", "Negative reinforcement {{c1::increases}} behavior by {{c1::removing}} an aversive stimulus.",
     "", "ps_learning", "q_ho_046|q_syn_026"),
    ("Basic", "How does extinction occur in classical conditioning?",
     "Presenting the conditioned stimulus repeatedly without the unconditioned stimulus weakens and eventually eliminates the conditioned response.",
     "ps_learning", "q_dev_037"),
    ("Cloze", "A {{c1::variable-ratio}} schedule reinforces behavior after an unpredictable number of responses.",
     "", "ps_learning", "q_ho_047|q_syn_025"),

    # ---- ps_social ---------------------------------------------------------
    ("Cloze", "The {{c1::fundamental attribution error}}: we over-credit others' behavior to personality and under-weight the situation.",
     "", "ps_social", "q_dev_038|q_syn_027"),
    ("Cloze", "{{c1::Conformity}} is matching a group standard; {{c1::obedience}} is following an authority's command.",
     "", "ps_social", "q_dev_039|q_ho_048"),
    ("Cloze", "The {{c1::bystander}} effect: the more people present, the less likely any one person helps.",
     "", "ps_social", "q_ho_049"),
    ("Cloze", "{{c1::Cognitive dissonance}} is the discomfort from holding conflicting attitudes or acting against one's attitude.",
     "", "ps_social", "q_dev_043|q_syn_028"),
    ("Basic", "What did Milgram's obedience studies demonstrate?",
     "Ordinary people will often follow an authority figure's instructions to harm another — the power of obedience to authority.",
     "ps_social", "q_ho_048"),
    ("Cloze", "An {{c1::attitude}} is an evaluation (favorable or unfavorable) of a person, object, or idea.",
     "", "ps_social", "q_ho_050"),

    # ---- ps_demographics ---------------------------------------------------
    ("Cloze", "Health {{c1::disparities}} are preventable differences in health outcomes across social groups.",
     "", "ps_demographics", "q_dev_040"),
    ("Cloze", "The social {{c1::gradient}} in health: outcomes tend to improve with higher socioeconomic status.",
     "", "ps_demographics", "q_ho_052|q_syn_030"),
    ("Cloze", "SES is commonly measured by income, education, and {{c1::occupation}}.",
     "", "ps_demographics", "q_ho_051"),
    ("Basic", "What is a social determinant of health? Give an example.",
     "A non-medical social factor that shapes health — e.g., access to education, income level, or safe housing.",
     "ps_demographics", "q_dev_041"),

    # ======================================================================
    # Synthesis backing cards (support q_syn_*). Each is a COMPONENT fact — no
    # card states an item's integrated answer (see SYNTHESIS-QUESTIONS-DRAFT.md,
    # "Fixes applied"). Existing cards above are also linked to q_syn_* ids so
    # each synthesis item's full prerequisite set is captured for the
    # memory⟂performance signal.
    # ======================================================================

    # ---- bb_enzymes (NEW-E1..E5) ------------------------------------------
    ("Cloze", "A competitive inhibitor binds the enzyme's {{c1::active site}}, directly competing with substrate for binding.",
     "", "bb_enzymes", "q_syn_001|q_syn_002"),
    ("Cloze", "Noncompetitive inhibition: Vmax {{c1::decreases}} while Km stays {{c1::unchanged}}.",
     "", "bb_enzymes", "q_syn_001"),
    ("Cloze", "Km is the substrate concentration at {{c1::half of Vmax}}; a higher Km means lower substrate affinity.",
     "", "bb_enzymes", "q_syn_001"),
    ("Basic", "In an enzyme assay comparing 'with inhibitor' vs 'without', which variable is held constant and which is deliberately varied?",
     "Hold the total enzyme amount (and temperature) constant. Substrate concentration is the independent variable you vary; reaction velocity is the dependent variable you measure.",
     "bb_enzymes", "q_syn_003"),
    ("Basic", "How does Km differ in kind from Keq?",
     "Km is a kinetic quantity — the [S] at half-Vmax, describing how the enzyme handles substrate. Keq is a thermodynamic quantity — the equilibrium ratio set by the free-energy difference between reactants and products.",
     "bb_enzymes", "q_syn_004"),
    ("Cloze", "A competitive inhibitor raises the enzyme's {{c1::apparent Km}} (more substrate is needed to reach a given velocity) because it competes for the active site.",
     "", "bb_enzymes", "q_syn_001"),
    ("Cloze", "Uncompetitive inhibition lowers {{c1::both}} Vmax and Km, because the inhibitor binds only the enzyme–substrate complex.",
     "", "bb_enzymes", "q_syn_001"),
    ("Cloze", "Competitive inhibition is {{c1::surmountable}}: the inhibitor binds reversibly at the active site, so adding excess substrate outcompetes it.",
     "", "bb_enzymes", "q_syn_002"),

    # ---- cp_electrochem (NEW-EC1..EC5) ------------------------------------
    ("Cloze", "E°cell = E°(cathode) − E°(anode); the half-cell with the {{c1::higher (more positive)}} reduction potential is the cathode.",
     "", "cp_electrochem", "q_syn_005"),
    ("Cloze", "ΔG° = {{c1::−nFE°cell}}, so a positive E°cell gives a {{c1::negative}} ΔG° (spontaneous).",
     "", "cp_electrochem", "q_syn_006"),
    ("Basic", "For ΔG° = −nFE°cell, what is n?",
     "n is the number of moles of electrons transferred in the balanced redox reaction (e.g., n = 2 for Zn(s) + Cu²⁺ → Zn²⁺ + Cu(s)).",
     "cp_electrochem", "q_syn_006"),
    ("Cloze", "Ecell (the actual potential) changes with ion concentrations via the Nernst equation, but E°cell (standard) is {{c1::fixed}}.",
     "", "cp_electrochem", "q_syn_007"),
    ("Cloze", "A galvanic cell keeps doing electrical work until it reaches {{c1::equilibrium}}, at which point Ecell = {{c1::0}} (a dead battery).",
     "", "cp_electrochem", "q_syn_008"),

    # ---- cp_acids_bases (NEW-AB1..AB4) ------------------------------------
    ("Cloze", "Henderson–Hasselbalch: pH = pKa + log([A⁻]/[HA]); when [A⁻] = [HA], pH = {{c1::pKa}}.",
     "", "cp_acids_bases", "q_syn_009|q_syn_011"),
    ("Basic", "In a buffer, which species neutralizes a small amount of added strong acid (H⁺), and what does it become?",
     "The conjugate base (A⁻) reacts with the added H⁺ and is converted into the weak acid (HA), consuming the added acid.",
     "cp_acids_bases", "q_syn_010"),
    ("Basic", "If something suppresses a weak acid's dissociation, what happens to [H⁺] and pH?",
     "Less dissociation releases fewer H⁺, so [H⁺] falls and the pH rises.",
     "cp_acids_bases", "q_syn_012"),
    ("Cloze", "A strong acid ionizes {{c1::completely}} (lower pH); a weak acid at equal concentration ionizes only {{c1::partially}} (higher pH).",
     "", "cp_acids_bases", "q_syn_024"),

    # ---- bb_genetics (NEW-G1..G3) -----------------------------------------
    ("Cloze", "For independent genes, the probability of a combined genotype/phenotype is the {{c1::product}} of the separate gene probabilities (e.g., 1/2 × 1/3 = 1/6).",
     "", "bb_genetics", "q_syn_013|q_syn_014"),
    ("Cloze", "A dihybrid cross of two double heterozygotes (YyRr × YyRr) gives a phenotypic ratio of {{c1::9:3:3:1}} under independent assortment.",
     "", "bb_genetics", "q_syn_014"),
    ("Basic", "In a testcross (× homozygous recessive), how do you read one gene's result?",
     "A ~1:1 dominant:recessive split means the tested parent is heterozygous for that gene; offspring that are all dominant mean it is homozygous dominant.",
     "bb_genetics", "q_syn_015"),

    # ---- bb_citric_acid / bb_glycolysis (NEW-BB1..BB2) --------------------
    ("Cloze", "One glucose → 2 pyruvate → 2 acetyl-CoA → {{c1::2}} turns of the citric acid cycle.",
     "", "bb_citric_acid", "q_syn_016"),
    ("Basic", "Which stages of glucose oxidation make ATP/GTP by substrate-level phosphorylation, and which supplies the much larger remainder?",
     "Glycolysis and the citric acid cycle make ATP/GTP directly by substrate-level phosphorylation; the electron transport chain (oxidative phosphorylation) supplies the much larger remainder.",
     "bb_glycolysis", "q_syn_016"),

    # ---- bb_membranes (NEW-M1) --------------------------------------------
    ("Cloze", "In osmosis, water moves toward the {{c1::hypertonic}} (higher-solute) side; a cell in a hypotonic solution {{c1::swells}} and may lyse.",
     "", "bb_membranes", "q_syn_017"),

    # ---- bb_dna (NEW-D1) --------------------------------------------------
    ("Basic", "To write the complement of a DNA strand in the 5'→3' direction, what two steps do you take?",
     "Pair each base (A-T, G-C), then reverse the order — because the two strands are antiparallel (e.g., 5'-AATGC-3' → 5'-GCATT-3').",
     "bb_dna", "q_syn_018"),

    # ---- cp_thermo (NEW-T1, decomposed to the unit component) -------------
    ("Cloze", "When combining ΔH (in kJ) with ΔS (in J) in ΔG = ΔH − TΔS, first convert both to the {{c1::same energy unit}} (e.g., kJ → J).",
     "", "cp_thermo", "q_syn_019"),

    # ---- cp_kinetics (NEW-K1, decomposed to the order definition) ---------
    ("Cloze", "In a rate law rate = k[A]^m[B]^n, the exponent on each reactant is its {{c1::order}}; the sum m+n is the overall order.",
     "", "cp_kinetics", "q_syn_020"),

    # ---- ps_learning (NEW-L1..L2) -----------------------------------------
    ("Cloze", "A {{c1::variable-ratio}} schedule (e.g., gambling) produces a high, steady response rate that is highly resistant to extinction.",
     "", "ps_learning", "q_syn_025"),
    ("Basic", "How is negative reinforcement different from punishment?",
     "Negative reinforcement removes an aversive stimulus and thereby increases a behavior; punishment (positive or negative) decreases a behavior.",
     "ps_learning", "q_syn_026"),

    # ---- ps_social (NEW-S1) -----------------------------------------------
    ("Cloze", "{{c1::Actor–observer}} bias: we attribute our own behavior to the situation but others' behavior to their disposition (the latter overlaps the fundamental attribution error).",
     "", "ps_social", "q_syn_027"),

    # ---- ps_demographics (NEW-DEM1) ---------------------------------------
    ("Basic", "How does a social gradient in health differ from a simple poverty threshold?",
     "A gradient means health improves at every step up the SES ladder — not only the poorest are worse off. A threshold would mean only those below a cutoff suffer.",
     "ps_demographics", "q_syn_030"),

    # ======================================================================
    # Component-card GRANULARITY pass — eval trio (cp_acids_bases, bb_enzymes,
    # cp_kinetics). Each card below is an ATOMIC prerequisite fact for a
    # specific question, so per-card M and the re-check probe can localize the
    # exact failed sub-concept. NONE encode an item's integrated MCQ answer —
    # they teach a foundational fact the question depends on (see
    # docs/COMPONENT-CARD-GRANULARITY.md). Sources: OpenStax Chemistry 2e
    # (acid–base, kinetics) and OpenStax Biology 2e (enzymes), consistent with
    # the questions these support.
    # ======================================================================

    # ---- bb_enzymes (GRAN) ------------------------------------------------
    # q_dev_003 depends on: ΔG signs, energy absorbed/released, the shared
    # activation barrier, and rate ≠ thermodynamics. The first two are new
    # atomic components (choices B and C).
    ("Cloze", "An {{c1::endergonic}} reaction absorbs (consumes) energy; an {{c1::exergonic}} reaction releases energy.",
     "", "bb_enzymes", "q_dev_003"),
    ("Cloze", "Both endergonic and exergonic reactions must first overcome an {{c1::activation-energy}} barrier before they proceed.",
     "", "bb_enzymes", "q_dev_003"),
    # q_dev_004: why rate (not ΔG) is the proxy — Ea is kinetic, not thermodynamic.
    ("Cloze", "Activation energy is a {{c1::kinetic}} property, so it cannot be inferred from ΔG or spontaneity (which are {{c1::thermodynamic}}).",
     "", "bb_enzymes", "q_dev_004"),
    # q_dev_005: general activator-vs-inhibitor direction (teaches the concept,
    # not just this item's "decreases affinity" answer).
    ("Cloze", "An allosteric {{c1::activator}} raises, while an allosteric {{c1::inhibitor}} lowers, the active site's affinity for substrate.",
     "", "bb_enzymes", "q_dev_005"),
    # q_ho_026: the allosteric site as the named contrast to the active site.
    ("Cloze", "The {{c1::allosteric}} site is a regulatory binding site separate from the active site.",
     "", "bb_enzymes", "q_ho_026"),
    # q_ho_027 distractors: enzyme not consumed; substrate is transformed.
    ("Cloze", "An enzyme is a catalyst, so it is {{c1::not consumed}} by the reaction it speeds up.",
     "", "bb_enzymes", "q_ho_027"),
    ("Cloze", "During catalysis the substrate is {{c1::chemically transformed}} into product (it is not left unchanged).",
     "", "bb_enzymes", "q_ho_027"),
    # q_ho_028: name the denaturation concept behind loss of activity.
    ("Cloze", "{{c1::Denaturation}} is the loss of a protein's 3-D shape, which distorts the enzyme's active site and lowers activity.",
     "", "bb_enzymes", "q_ho_028"),
    # q_syn_003: experimental-design prerequisites (control / IV / DV).
    ("Cloze", "A {{c1::controlled}} variable is held constant so any change in the outcome can be attributed to the treatment.",
     "", "bb_enzymes", "q_syn_003"),
    ("Cloze", "In an experiment the {{c1::independent}} variable is deliberately changed and the {{c1::dependent}} variable is measured.",
     "", "bb_enzymes", "q_syn_003"),
    # q_syn_004: the underlying reason ΔG/Keq are catalyst-invariant (teaches
    # the prerequisite, not the item's yes/no answer).
    ("Cloze", "ΔG and Keq depend only on the {{c1::free-energy difference}} between reactants and products, which a catalyst or inhibitor cannot change.",
     "", "bb_enzymes", "q_syn_004"),

    # ---- cp_acids_bases (GRAN) --------------------------------------------
    # q_dev_006: the NH3 weak-base equilibrium the item is built on.
    ("Cloze", "Ammonia is a weak base: NH₃ + H₂O ⇌ {{c1::NH₄⁺}} + {{c1::OH⁻}}.",
     "", "cp_acids_bases", "q_dev_006"),
    # q_dev_006 / q_syn_012: the common-ion effect (distractors + shift logic).
    ("Cloze", "Common-ion effect: adding an ion already in the equilibrium (e.g., NH₄⁺ to NH₃, or acetate to acetic acid) {{c1::suppresses}} the weak acid/base ionization.",
     "", "cp_acids_bases", "q_dev_006|q_syn_012"),
    # q_dev_007: the inverse acid/conjugate-base strength relationship, stated atomically.
    ("Cloze", "The {{c1::weaker}} the acid, the stronger its conjugate base (and the reverse).",
     "", "cp_acids_bases", "q_dev_007"),
    # q_dev_011 distractor: a strong-acid/strong-base pair cannot buffer.
    ("Cloze", "A strong acid and strong base cannot form a buffer — they simply {{c1::react to completion}}.",
     "", "cp_acids_bases", "q_dev_011"),
    # q_ho_007: Kw and the neutral-solution condition.
    ("Cloze", "At 25 °C the water autoionization constant Kw = [H⁺][OH⁻] = {{c1::1.0×10⁻¹⁴}}.",
     "", "cp_acids_bases", "q_ho_007"),
    ("Cloze", "A neutral aqueous solution is defined by {{c1::[H⁺] = [OH⁻]}}.",
     "", "cp_acids_bases", "q_ho_007"),
    # q_syn_011: the Henderson–Hasselbalch ratio proportionality (per pH unit).
    ("Cloze", "By Henderson–Hasselbalch, raising pH by 1 unit above the pKa multiplies the [A⁻]/[HA] ratio by {{c1::10}}.",
     "", "cp_acids_bases", "q_syn_011"),
    # q_syn_012: percent dissociation responds to suppression.
    ("Cloze", "Suppressing a weak acid's ionization lowers its {{c1::percent dissociation}}.",
     "", "cp_acids_bases", "q_syn_012"),

    # ---- cp_kinetics (GRAN) -----------------------------------------------
    # q_dev_015 distractors: temperature does NOT lower Ea or change ΔG.
    ("Cloze", "Raising temperature increases reaction rate but does {{c1::not}} lower the activation energy or change ΔG.",
     "", "cp_kinetics", "q_dev_015"),
    # (q_dev_016's "alternate pathway/lower Ea" mechanism is intentionally NOT
    # re-authored here: it is the item's own answer, and the existing
    # "catalyst lowers Ea, doesn't change ΔG/equilibrium" card already backs it.)
    # q_dev_017: the Arrhenius relationship names k's temperature dependence.
    ("Cloze", "The temperature dependence of the rate constant k is described by the {{c1::Arrhenius}} equation.",
     "", "cp_kinetics", "q_dev_017"),
    # q_ho_016 distractors: Ea is the transition-state barrier, not ΔH/ΔG.
    ("Cloze", "Activation energy is the barrier to reach the {{c1::transition state}}; it is not the reactant–product energy difference (ΔH/ΔG).",
     "", "cp_kinetics", "q_ho_016"),
    # q_syn_020: the method-of-initial-rates procedure (not the specific answer).
    ("Cloze", "Method of initial rates: find a reactant's order by comparing experiments in which only {{c1::that reactant's}} concentration changes.",
     "", "cp_kinetics", "q_syn_020"),
    # q_syn_021: thermodynamics vs kinetics are independent (prereq, not the answer).
    ("Cloze", "Thermodynamic favorability (ΔG) and reaction rate are {{c1::independent}} — a spontaneous reaction can still be very slow.",
     "", "cp_kinetics", "q_syn_021"),
]


def csv_field(value: str) -> str:
    """Always-quote text/back fields; empty -> empty (no quotes)."""
    if value == "":
        return ""
    return '"' + value.replace('"', '""') + '"'


def row(note_type: str, text: str, back: str, topic_id: str, supports: str) -> str:
    return ",".join([
        note_type,
        csv_field(text),
        csv_field(back),
        f"topic:{topic_id}",
        supports,
    ])


# Anki import directives (verified against the fork's parser,
# rslib/src/import_export/text/csv/metadata.rs::parse_meta_value).
#
# Every leading line beginning with '#' is treated as import config, NOT a note
# (parse_line strips '#'; the CSV reader is built with .comment(Some(b'#'))), so
# these blocks guarantee the old `note_type,text,back,...` header can never be
# imported as a junk note — no manual "first row is field names" toggle needed.
#
# Column order emitted by row(): 1=note_type 2=text 3=back 4=tags 5=supports_question
#   - #separator:Comma    -> delimiter is comma (must precede #columns:)
#   - #html:false         -> fields are escaped, so literal '<'/'>' (e.g. "ΔG < 0") render as text
#   - #notetype:...        -> pins the notetype for the split files
#   - #columns:...         -> labels; matching a label to a field name maps that column;
#                             unmatched labels (note_type, supports_question) stay unmapped/ignored
#   - #tags column:4       -> column 4 supplies tags (excluded from field mapping)
# Combined file mixes note types, so it uses #notetype column:1 (per-row notetype).
_COMMON = ["#separator:Comma", "#html:false"]

DIRECTIVES_CLOZE = _COMMON + [
    "#notetype:Cloze",
    "#columns:note_type,Text,back,tags,supports_question",
    "#tags column:4",
]
DIRECTIVES_BASIC = _COMMON + [
    "#notetype:Basic",
    "#columns:note_type,Front,Back,tags,supports_question",
    "#tags column:4",
]
DIRECTIVES_ALL = _COMMON + [
    "#notetype column:1",
    "#tags column:4",
]


def write_csv(path: Path, directives: list[str], rows: list[str]) -> None:
    path.write_text("\n".join([*directives, *rows]) + "\n", encoding="utf-8")


def coverage_check() -> None:
    """Warn if any non-CARS question in questions.json lacks a backing card."""
    qpath = DATA / "questions.json"
    if not qpath.exists():
        return
    questions = json.loads(qpath.read_text(encoding="utf-8"))
    science = {q["id"] for q in questions if q["section"] != "CARS"}
    covered: set[str] = set()
    for *_rest, supports in CARDS:
        for qid in (supports.split("|") if supports else []):
            covered.add(qid.strip())
    missing = sorted(science - covered)
    print(f"per-question coverage: {len(science & covered)}/{len(science)} "
          f"science questions have >=1 backing card")
    if missing:
        print(f"  WARNING: no backing card for: {missing}")
    dangling = sorted(covered - {q["id"] for q in questions})
    if dangling:
        print(f"  WARNING: supports point to missing question ids: {dangling}")


def main() -> None:
    all_rows, cloze_rows, basic_rows = [], [], []
    for note_type, text, back, topic_id, supports in CARDS:
        line = row(note_type, text, back, topic_id, supports)
        all_rows.append(line)
        if note_type == "Cloze":
            cloze_rows.append(line)
        else:
            basic_rows.append(line)

    write_csv(DATA / "flashcards-dev.csv", DIRECTIVES_ALL, all_rows)
    write_csv(DATA / "flashcards-dev-cloze.csv", DIRECTIVES_CLOZE, cloze_rows)
    write_csv(DATA / "flashcards-dev-basic.csv", DIRECTIVES_BASIC, basic_rows)

    topics = sorted({c[3] for c in CARDS})
    print(f"wrote {len(all_rows)} notes "
          f"(cloze={len(cloze_rows)}, basic={len(basic_rows)}) "
          f"across {len(topics)} topics")
    cloze_pct = round(100 * len(cloze_rows) / len(all_rows))
    print(f"cloze share: {cloze_pct}% (target ~70–80%)")
    coverage_check()


if __name__ == "__main__":
    main()

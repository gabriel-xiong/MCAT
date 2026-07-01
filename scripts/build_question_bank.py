#!/usr/bin/env python3
"""Build data/questions.json for the MCAT Speedrun performance bank.

Authoring source of record for the curated question bank. Science items are
grounded in the named OpenStax chapters listed in data/openstax-sources.json
(CC-BY); CARS items are ORIGINAL passages authored for this project (CC0) —
we do not copy AAMC/Khan/other proprietary QBanks (locked decision).

Runtime never calls this; it only reads the emitted questions.json. Rules:
  - deterministic 4-option MCQ, exactly one correct answer (A–D)
  - every item carries source_name / source_url / source_location / split
  - topic_id must exist in mcat-outline.v1.json; section derived from topic
  - prefer pathway / regulation / reasoning items over bare definitions
Run:  python scripts/build_question_bank.py   (writes data/questions.json)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

LETTERS = "ABCD"

# topic_id -> (source_name, source_url). Mirrors data/openstax-sources.json.
SRC: dict[str, tuple[str, str]] = {
    "cp_electrochem": (
        "OpenStax Chemistry 2e",
        "https://openstax.org/books/chemistry-2e/pages/17-2-galvanic-cells",
    ),
    "cp_acids_bases": (
        "OpenStax Chemistry 2e",
        "https://openstax.org/books/chemistry-2e/pages/14-2-bronsted-lowry-acids-and-bases",
    ),
    "cp_thermo": (
        "OpenStax Chemistry 2e",
        "https://openstax.org/books/chemistry-2e/pages/16-4-free-energy",
    ),
    "cp_kinetics": (
        "OpenStax Chemistry 2e",
        "https://openstax.org/books/chemistry-2e/pages/12-4-integrated-rate-laws",
    ),
    "cp_fluids": (
        "OpenStax College Physics",
        "https://openstax.org/books/college-physics/pages/12-2-bernoullis-equation",
    ),
    "bb_glycolysis": (
        "OpenStax Biology 2e",
        "https://openstax.org/books/biology-2e/pages/7-2-glycolysis",
    ),
    "bb_citric_acid": (
        "OpenStax Biology 2e",
        "https://openstax.org/books/biology-2e/pages/7-3-oxidation-of-pyruvate-and-the-citric-acid-cycle",
    ),
    "bb_enzymes": (
        "OpenStax Biology 2e",
        "https://openstax.org/books/biology-2e/pages/6-5-enzymes",
    ),
    "bb_membranes": (
        "OpenStax Biology 2e",
        "https://openstax.org/books/biology-2e/pages/5-1-components-and-structure",
    ),
    "bb_dna": (
        "OpenStax Biology 2e",
        "https://openstax.org/books/biology-2e/pages/14-3-basics-of-dna-replication",
    ),
    "bb_genetics": (
        "OpenStax Biology 2e",
        "https://openstax.org/books/biology-2e/pages/12-2-characteristics-and-traits",
    ),
    "ps_memory": (
        "OpenStax Psychology 2e",
        "https://openstax.org/books/psychology-2e/pages/8-1-how-memory-functions",
    ),
    "ps_learning": (
        "OpenStax Psychology 2e",
        "https://openstax.org/books/psychology-2e/pages/6-1-what-is-learning",
    ),
    "ps_social": (
        "OpenStax Psychology 2e",
        "https://openstax.org/books/psychology-2e/pages/12-2-self-presentation",
    ),
    "ps_demographics": (
        "OpenStax Psychology 2e",
        "https://openstax.org/books/psychology-2e/pages/14-3-stress-and-illness",
    ),
    "cars_comprehension": ("Original passage (CC0, MCAT Speedrun)", ""),
    "cars_reasoning_within": ("Original passage (CC0, MCAT Speedrun)", ""),
    "cars_reasoning_beyond": ("Original passage (CC0, MCAT Speedrun)", ""),
}


def section_of(topic_id: str) -> str:
    return {
        "cp": "CP",
        "bb": "BB",
        "ps": "PS",
        "ca": "CARS",
    }[topic_id[:2]]


# Question-level cognitive_demand (recall | application | synthesis) — required
# for the science cross-system reasoning signal (see docs/ERROR-DIAGNOSIS-SPEC.md).
#
# Honesty (retag 2026-07-01): an earlier skill-derived heuristic mapped every
# AAMC-skill-2 item to `application`, which over-inflated the count — this bank
# is deliberately recall-heavy (define X / name the enzyme / state a value).
# So the existing bank now DEFAULTS to `recall`, and the genuine reasoning items
# carry an explicit `demand=` at their call site (evaluation, computation, or a
# multi-step apply → application; integrating >=2 concepts → synthesis). The
# q_syn_* items carry their own cognitive_demand. CARS gets none.
#
# A new DEV/HELD_OUT item that is genuinely application/synthesis MUST set
# demand= explicitly; without it the honest baseline treats it as recall.


# --- CARS passages (original, CC0) -----------------------------------------
P_HIST = (
    "PASSAGE\n"
    "Historians often claim to reconstruct the past 'as it actually happened,' "
    "yet every history is written from a vantage point. The selection of which "
    "events matter, which documents to trust, and which voices to amplify "
    "reflects the historian's own moment. This does not make history mere "
    "fiction. Rather, it means objectivity in history is not the absence of "
    "perspective but the disciplined awareness of it. A historian who "
    "acknowledges her assumptions, and tests them against evidence that might "
    "overturn them, comes closer to truth than one who pretends to have none.\n\n"
)
P_CHOICE = (
    "PASSAGE\n"
    "We often assume that more options make us freer. But beyond a certain "
    "point, additional choices can paralyze rather than liberate. Faced with "
    "dozens of nearly identical products, a shopper may spend more effort "
    "deciding, enjoy the decision less, and second-guess it afterward. Freedom, "
    "on this view, is not simply the quantity of available options but the "
    "capacity to choose well among them. A society that multiplies choices "
    "without cultivating judgment may expand liberty in name while eroding it "
    "in practice.\n\n"
)

# --- Science data passages (original data items, CC0; grounded in OpenStax) --
# Each multi-question passage is kept wholly within ONE split (no cross-split
# leakage) and shares one identical stem prefix across its questions.
P_ENZYME = (
    "PASSAGE\n"
    "An enzyme converts substrate S to product P. A researcher measures the "
    "initial reaction velocity (v0) at several substrate concentrations, first "
    "with enzyme alone and then with the same amount of enzyme plus a fixed "
    "concentration of inhibitor X. Enzyme amount and temperature are identical "
    "in both runs.\n\n"
    "  [S] (mM) | v0, enzyme only (umol/min) | v0, enzyme + X (umol/min)\n"
    "  ---------+---------------------------+--------------------------\n"
    "     1     |            33             |            14\n"
    "     2     |            50             |            25\n"
    "     4     |            67             |            40\n"
    "     8     |            80             |            57\n"
    "    16     |            89             |            73\n\n"
    "At very high (saturating) [S], both curves approach the same maximum "
    "velocity (Vmax ~ 100 umol/min). The substrate concentration giving "
    "half-maximal velocity is about 2 mM without X and about 6 mM with X.\n\n"
)
P_GALVANIC = (
    "PASSAGE\n"
    "A galvanic cell is built from two standard half-cells at 25 C:\n\n"
    "  Cu2+(aq) + 2e- -> Cu(s)     E deg = +0.34 V\n"
    "  Zn2+(aq) + 2e- -> Zn(s)     E deg = -0.76 V\n\n"
    "The two metals are connected by an external wire and the half-cells by a "
    "salt bridge. (F ~ 96,500 C/mol.)\n\n"
)
P_BUFFER = (
    "PASSAGE\n"
    "A chemist prepares an acetate buffer from acetic acid (CH3COOH) and its "
    "conjugate base acetate (CH3COO-). For acetic acid, pKa = 4.74. The initial "
    "buffer contains [CH3COOH] = 0.10 M and [CH3COO-] = 0.10 M. The relevant "
    "equilibrium is:  CH3COOH <=> CH3COO- + H+.\n\n"
)
P_DIHYBRID = (
    "PASSAGE\n"
    "In pea plants, seed color and seed shape are controlled by two genes on "
    "different chromosomes (they assort independently). Yellow (Y) is dominant "
    "to green (y); round (R) is dominant to wrinkled (r). Two doubly "
    "heterozygous plants are crossed:  YyRr x YyRr.\n\n"
)


def q(topic, skill, stem, choices, correct, location, split, demand=None):
    """correct is the 0-based index of the right choice.

    ``demand`` sets ``cognitive_demand`` explicitly (application|synthesis) for a
    genuine reasoning item; omit it for recall items, which are the honest
    baseline for this bank (see docs/ERROR-DIAGNOSIS-SPEC.md).
    """
    assert len(choices) == 4, stem
    name, url = SRC[topic]
    item = {
        "topic_id": topic,
        "section": section_of(topic),
        "skill": skill,
        "stem": stem,
        "choices": choices,
        "correct": LETTERS[correct],
        "source_name": name,
        "source_url": url,
        "source_location": location,
        "split": split,
    }
    if demand is not None:
        item["_demand"] = demand
    return item


def cg(misconception, trap=None):
    """A ``content_gap`` choice_diagnosis entry for a distractor.

    Landing here requires a FALSE BELIEF about the science, named by
    ``misconception``. This is the content axis — the only axis we author on a
    choice; ``application``/``misread`` are inferred from behaviour, never tagged
    here. ``trap`` is retained only for backward compatibility; a genuine
    execution-error landing should use :func:`trap` instead (it must NOT carry a
    ``content_gap``). See docs/ERROR-DIAGNOSIS-SPEC.md "Choice tagging
    methodology".
    """
    entry = {"maps_to": "content_gap", "misconception": misconception}
    if trap is not None:
        entry["trap"] = trap
    return entry


def trap(kind):
    """A predictable EXECUTION-error landing (not a content belief).

    Feeds the behavioral/misread prior, never the content axis, so ``maps_to`` is
    null and there is no ``misconception``. Allowed kinds:
    ``negation`` | ``unit`` | ``inverse`` | ``scaling`` | ``transpose`` |
    ``partial`` (see docs/ERROR-DIAGNOSIS-SPEC.md "Choice tagging methodology").
    A non-diagnostic distractor (arbitrary wrong number / plausible-but-unrelated
    grab) uses ``None`` directly, not this helper.
    """
    return {"maps_to": None, "trap": kind}


def qsyn(qid, topic, skill, demand, stem, choices, correct, location, split, cd):
    """Synthesis/application item with a STABLE id (q_syn_*), explicit
    cognitive_demand, and an authored choice_diagnosis (1:1 with choices, the
    correct index is None). Unlike q(), the id is fixed here, never auto-indexed.
    """
    assert len(choices) == 4, qid
    assert len(cd) == 4, qid
    assert cd[correct] is None, f"{qid}: correct index choice_diagnosis must be None"
    name, url = SRC[topic]
    return {
        "id": qid,
        "topic_id": topic,
        "section": section_of(topic),
        "skill": skill,
        "stem": stem,
        "choices": choices,
        "correct": LETTERS[correct],
        "cognitive_demand": demand,
        "choice_diagnosis": cd,
        "source_name": name,
        "source_url": url,
        "source_location": location,
        "split": split,
    }


DEV: list[dict] = [
    # --- existing seven (kept verbatim: ids q_dev_001..007) ----------------
    q("bb_citric_acid", "2",
      "GTP or ATP is produced during the conversion of ________.",
      ["isocitrate into α-ketoglutarate",
       "succinyl CoA into succinate",
       "fumarate into malate",
       "malate into oxaloacetate"], 1, "Ch. 7 Review Q9", "dev"),
    q("bb_citric_acid", "2",
      "The effect of high levels of ADP is to ________ in cellular respiration.",
      ["increase the activity of specific enzymes",
       "decrease the activity of specific enzymes",
       "have no effect on the activity of specific enzymes",
       "slow down the pathway"], 0, "Ch. 7 Review Q16", "dev"),
    q("bb_enzymes", "2",
      "Which of the following comparisons or contrasts between endergonic and "
      "exergonic reactions is false?",
      ["Endergonic reactions have a positive ∆G and exergonic reactions have a "
       "negative ∆G.",
       "Endergonic reactions consume energy and exergonic reactions release "
       "energy.",
       "Both endergonic and exergonic reactions require a small amount of "
       "energy to overcome an activation barrier.",
       "Endergonic reactions take place slowly and exergonic reactions take "
       "place quickly."], 3, "Ch. 6 Review Q7", "dev", demand="application"),
    q("bb_enzymes", "2",
      "Which of the following is the best way to judge the relative activation "
      "energies between two given chemical reactions?",
      ["Compare the ∆G values between the two reactions.",
       "Compare their reaction rates.",
       "Compare their ideal environmental conditions.",
       "Compare the spontaneity between the two reactions."], 1,
      "Ch. 6 Review Q8", "dev", demand="application"),
    q("bb_enzymes", "2",
      "An allosteric inhibitor does which of the following?",
      ["Binds to an enzyme away from the active site and changes the "
       "conformation of the active site, increasing its affinity for substrate "
       "binding.",
       "Binds to the active site and blocks it from binding substrate.",
       "Binds to an enzyme away from the active site and changes the "
       "conformation of the active site, decreasing its affinity for the "
       "substrate.",
       "Binds directly to the active site and mimics the substrate."], 2,
      "Ch. 6 Review Q14", "dev"),
    q("cp_acids_bases", "2",
      "Which of the following will increase the percent of NH3 that is "
      "converted to the ammonium ion in water?",
      ["addition of NaOH", "addition of HCl", "addition of NH4Cl",
       "addition of NH3 gas only"], 1, "Ch. 14 Exercises Q48", "dev",
      demand="application"),
    q("cp_acids_bases", "2",
      "Both HF and HCN ionize in water to a limited extent. Which of the "
      "conjugate bases, F− or CN−, is the stronger base?",
      ["F−", "CN−", "They are equally strong bases.",
       "Neither acts as a base in water."], 1, "Ch. 14 Exercises Q44", "dev",
      demand="application"),

    # --- CP additions ------------------------------------------------------
    q("cp_electrochem", "1",
      "In a galvanic (voltaic) cell, oxidation occurs at the ______ and "
      "electrons travel through the external wire toward the ______.",
      ["anode; cathode", "cathode; anode", "anode; anode",
       "cathode; cathode"], 0, "Ch. 17.2 Galvanic Cells", "dev"),
    q("cp_electrochem", "2",
      "A standard cell has E°cell = +1.10 V. What does the positive standard "
      "cell potential indicate about the reaction as written?",
      ["It is nonspontaneous (ΔG° > 0).",
       "It is spontaneous (ΔG° < 0).",
       "It is at equilibrium (ΔG° = 0).",
       "It cannot occur without an external power source."], 1,
      "Ch. 17.4 Potential, Free Energy, and Equilibrium", "dev"),
    q("cp_electrochem", "2",
      "The salt bridge in a galvanic cell functions primarily to:",
      ["supply electrons directly to the cathode",
       "maintain electrical neutrality by allowing ion flow between half-cells",
       "increase the cell voltage without limit",
       "catalyze the electrode reactions"], 1,
      "Ch. 17.2 Galvanic Cells", "dev"),
    q("cp_acids_bases", "2",
      "A buffer resists changes in pH because it contains appreciable amounts "
      "of both a ______.",
      ["strong acid and strong base",
       "weak acid and its conjugate base",
       "weak acid and a strong base in equal moles",
       "neutral salt and pure water"], 1, "Ch. 14.6 Buffers", "dev"),
    q("cp_thermo", "2",
      "A reaction is spontaneous at all temperatures when:",
      ["ΔH < 0 and ΔS > 0", "ΔH > 0 and ΔS < 0",
       "ΔH < 0 and ΔS < 0", "ΔH > 0 and ΔS > 0"], 0,
      "Ch. 16.4 Free Energy", "dev"),
    q("cp_thermo", "1",
      "Which expression correctly relates Gibbs free energy to enthalpy and "
      "entropy at constant temperature?",
      ["ΔG = ΔH + TΔS", "ΔG = ΔH − TΔS", "ΔG = TΔS − ΔH",
       "ΔG = ΔH × TΔS"], 1, "Ch. 16.4 Free Energy", "dev"),
    q("cp_thermo", "2",
      "A spontaneous process is one that:",
      ["occurs without a continuous external input of energy",
       "always occurs rapidly",
       "always releases heat to the surroundings",
       "always requires a catalyst"], 0, "Ch. 16.3 Spontaneity", "dev"),
    q("cp_kinetics", "2",
      "Increasing temperature generally increases reaction rate primarily "
      "because:",
      ["it increases ΔG for the reaction",
       "a larger fraction of collisions have energy ≥ the activation energy",
       "it lowers the activation energy of the reaction",
       "it makes the reaction more exothermic"], 1,
      "Ch. 12.5 Collision Theory", "dev"),
    q("cp_kinetics", "2",
      "A catalyst increases the rate of a reaction by:",
      ["raising the temperature of the system",
       "providing an alternate pathway with a lower activation energy",
       "making the reaction more exothermic",
       "shifting the equilibrium toward products"], 1,
      "Ch. 12.7 Catalysis", "dev"),
    q("cp_kinetics", "2",
      "The rate constant k of a reaction depends on:",
      ["the concentrations of the reactants",
       "temperature and the presence of a catalyst",
       "the volume of the container only",
       "how much time has elapsed"], 1, "Ch. 12.5 Collision Theory", "dev"),
    q("cp_fluids", "2",
      "For an ideal fluid in streamline flow through a horizontal pipe that "
      "narrows, as the cross-sectional area decreases the fluid speed:",
      ["increases (equation of continuity)", "decreases",
       "stays constant", "drops to zero"], 0,
      "Ch. 12.1 Flow Rate and Continuity", "dev"),
    q("cp_fluids", "2",
      "The volume flow rate (Q = A·v) staying constant in a pipe of varying "
      "width is a direct consequence of:",
      ["Bernoulli's principle",
       "the equation of continuity (conservation of mass)",
       "Pascal's principle", "Archimedes' principle"], 1,
      "Ch. 12.1 Flow Rate and Continuity", "dev"),

    # --- BB additions ------------------------------------------------------
    q("bb_glycolysis", "1",
      "The net ATP yield from the glycolysis of one glucose molecule (by "
      "substrate-level phosphorylation) is:",
      ["2 ATP", "4 ATP", "36 ATP", "0 ATP"], 0, "Ch. 7.2 Glycolysis", "dev"),
    q("bb_glycolysis", "1",
      "Glycolysis takes place in the ______ of the cell.",
      ["mitochondrial matrix", "cytoplasm (cytosol)", "nucleus",
       "endoplasmic reticulum"], 1, "Ch. 7.2 Glycolysis", "dev"),
    q("bb_glycolysis", "2",
      "Besides ATP, glycolysis produces which reduced electron carrier?",
      ["FADH₂", "NADPH", "NADH", "GTP"], 2, "Ch. 7.2 Glycolysis", "dev"),
    q("bb_citric_acid", "2",
      "Which molecule is regenerated at the end of each citric acid cycle turn "
      "to accept another acetyl group?",
      ["citrate", "oxaloacetate", "pyruvate", "acetyl-CoA"], 1,
      "Ch. 7.3 Citric Acid Cycle", "dev"),
    q("bb_enzymes", "2",
      "The maximum reaction velocity (Vmax) of an enzyme-catalyzed reaction is "
      "reached when:",
      ["substrate concentration is very low",
       "all enzyme active sites are saturated with substrate",
       "the enzyme has been denatured",
       "a competitive inhibitor is present"], 1, "Ch. 6.5 Enzymes", "dev"),
    q("bb_membranes", "1",
      "The fundamental structural framework of the plasma membrane is the:",
      ["peptidoglycan wall", "phospholipid bilayer", "cellulose matrix",
       "glycogen network"], 1, "Ch. 5.1 Components and Structure", "dev"),
    q("bb_membranes", "2",
      "In a membrane phospholipid, the phosphate head is ______ and the "
      "fatty-acid tails are ______.",
      ["hydrophobic; hydrophilic", "hydrophilic; hydrophobic",
       "hydrophilic; hydrophilic", "hydrophobic; hydrophobic"], 1,
      "Ch. 5.1 Components and Structure", "dev"),
    q("bb_dna", "1",
      "DNA replication is described as semiconservative because each daughter "
      "molecule contains:",
      ["two newly synthesized strands",
       "one parental (template) strand and one new strand",
       "two parental strands", "only RNA"], 1,
      "Ch. 14.3 Basics of DNA Replication", "dev"),
    q("bb_dna", "2",
      "Which enzyme synthesizes new DNA strands by adding nucleotides in the "
      "5'→3' direction?",
      ["DNA helicase", "DNA polymerase", "primase", "DNA ligase"], 1,
      "Ch. 14.4 DNA Replication in Prokaryotes", "dev"),
    q("bb_dna", "2",
      "Which enzyme joins adjacent Okazaki fragments by forming phosphodiester "
      "bonds?",
      ["helicase", "primase", "DNA ligase", "polymerase"], 2,
      "Ch. 14.4 DNA Replication in Prokaryotes", "dev"),
    q("bb_genetics", "2",
      "A cross between two heterozygotes (Aa × Aa) for a simple dominant trait "
      "gives an expected phenotypic ratio of:",
      ["1:1", "3:1", "9:3:3:1", "1:2:1"], 1,
      "Ch. 12.2 Characteristics and Traits", "dev"),
    q("bb_genetics", "1",
      "An organism's ______ is its genetic makeup, while its ______ is its "
      "observable characteristics.",
      ["phenotype; genotype", "genotype; phenotype", "allele; gene",
       "gamete; zygote"], 1, "Ch. 12.2 Characteristics and Traits", "dev"),

    # --- PS additions ------------------------------------------------------
    q("ps_memory", "1",
      "The three basic processes of memory are:",
      ["sensation, perception, cognition",
       "encoding, storage, retrieval",
       "input, output, feedback",
       "acquisition, extinction, recovery"], 1,
      "Ch. 8.1 How Memory Functions", "dev"),
    q("ps_memory", "2",
      "Classic research suggests short-term (working) memory holds about how "
      "many items at once?",
      ["7 ± 2 items", "essentially unlimited", "1 item", "about 100 items"], 0,
      "Ch. 8.2 Parts of the Brain Involved in Memory", "dev"),
    q("ps_memory", "2",
      "Maintaining information in short-term memory through repetition is "
      "called:",
      ["chunking", "rehearsal", "retrieval", "encoding failure"], 1,
      "Ch. 8.1 How Memory Functions", "dev"),
    q("ps_learning", "1",
      "In Pavlov's experiments, the food that naturally elicits salivation is "
      "the:",
      ["conditioned stimulus (CS)", "unconditioned stimulus (US)",
       "conditioned response (CR)", "neutral stimulus"], 1,
      "Ch. 6.2 Classical Conditioning", "dev"),
    q("ps_learning", "2",
      "In operant conditioning, a reinforcer:",
      ["decreases the behavior it follows",
       "increases the likelihood of the behavior it follows",
       "has no effect on behavior",
       "always involves physical punishment"], 1,
      "Ch. 6.3 Operant Conditioning", "dev"),
    q("ps_learning", "2",
      "Extinction in classical conditioning occurs when:",
      ["the CS is repeatedly presented without the US, weakening the CR",
       "a new unconditioned stimulus is introduced",
       "the reinforcer is doubled",
       "the response becomes permanent"], 0,
      "Ch. 6.2 Classical Conditioning", "dev"),
    q("ps_social", "2",
      "The tendency to attribute others' behavior to internal traits while "
      "underestimating situational factors is the:",
      ["self-serving bias", "fundamental attribution error",
       "just-world hypothesis", "bystander effect"], 1,
      "Ch. 12.1 What Is Social Psychology?", "dev"),
    q("ps_social", "2",
      "Adjusting one's behavior or thinking to align with a group standard is:",
      ["obedience", "conformity", "aggression", "persuasion"], 1,
      "Ch. 12.3 Attitudes and Persuasion", "dev"),
    q("ps_demographics", "1",
      "Health disparities are best described as:",
      ["random differences in health with no pattern",
       "preventable differences in health outcomes across social groups",
       "differences caused solely by genetics",
       "differences that cannot be measured"], 1,
      "Ch. 14.3 Stress and Illness", "dev"),
    q("ps_demographics", "2",
      "Which is an example of a social determinant of health?",
      ["a person's blood type",
       "access to education, income, and safe housing",
       "a spontaneous genetic mutation",
       "eye color"], 1, "Ch. 14.3 Stress and Illness", "dev"),
    q("cp_fluids", "1",
      "Pascal's principle states that pressure applied to an enclosed fluid "
      "is:",
      ["transmitted undiminished to every part of the fluid",
       "quickly lost as heat",
       "proportional to the fluid's temperature",
       "zero at the bottom of the container"], 0,
      "Ch. 11.5 Pascal's Principle", "dev"),
    q("ps_social", "2",
      "Cognitive dissonance refers to the psychological discomfort felt when:",
      ["one holds two conflicting attitudes or a behavior clashes with an "
       "attitude",
       "one is rewarded for a behavior",
       "a neutral stimulus is repeated",
       "a group reaches unanimous consensus"], 0,
      "Ch. 12.3 Attitudes and Persuasion", "dev"),
    q("bb_genetics", "2",
      "In codominance, the heterozygote:",
      ["shows an intermediate blend of the two alleles",
       "expresses both alleles fully and simultaneously",
       "expresses only the dominant allele",
       "is always nonviable"], 1, "Ch. 12.3 Laws of Inheritance", "dev"),

    # --- CARS additions (original passages) --------------------------------
    q("cars_comprehension", "1",
      P_HIST + "QUESTION\nThe passage's central claim is that:",
      ["history is essentially a form of fiction",
       "objectivity in history comes from acknowledging and testing one's "
       "perspective, not from having none",
       "historians should avoid relying on documents",
       "only eyewitnesses can write accurate history"], 1,
      "Passage A (History & Objectivity), Q1", "dev"),
    q("cars_comprehension", "1",
      P_CHOICE + "QUESTION\nAccording to the passage, freedom is best "
      "understood as:",
      ["the sheer number of options available",
       "the capacity to choose well among options",
       "the complete absence of constraints",
       "the ability to avoid making decisions"], 1,
      "Passage B (Choice & Freedom), Q1", "dev"),
    q("cars_reasoning_within", "3",
      P_HIST + "QUESTION\nThe author would most likely agree that a historian "
      "who 'pretends to have none' (no assumptions):",
      ["is thereby more objective than her peers",
       "is less likely to reach truth than one who examines her assumptions",
       "produces the most reliable history",
       "should be trusted without question"], 1,
      "Passage A (History & Objectivity), Q2", "dev"),
    q("cars_reasoning_within", "3",
      P_CHOICE + "QUESTION\nThe phrase 'expand liberty in name while eroding "
      "it in practice' most nearly suggests the author believes:",
      ["nominal freedom can coincide with reduced real freedom",
       "liberty and number of choices are identical",
       "practical outcomes do not matter",
       "society should prohibit consumer choices"], 0,
      "Passage B (Choice & Freedom), Q2", "dev"),
    q("cars_reasoning_beyond", "4",
      P_CHOICE + "QUESTION\nWhich real-world scenario best illustrates the "
      "passage's argument?",
      ["A student with two electives quickly picks one and is satisfied.",
       "A diner handed a 12-page menu feels overwhelmed, takes a long time to "
       "order, and later regrets the choice.",
       "A shopper finds a store closed and goes home.",
       "A person with no available options feels content."], 1,
      "Passage B (Choice & Freedom), Q3", "dev"),
    q("cars_reasoning_beyond", "4",
      P_HIST + "QUESTION\nApplying the passage's logic, which practice would "
      "most improve a historian's objectivity?",
      ["ignoring sources that conflict with her interpretation",
       "actively seeking evidence that could disprove her assumptions",
       "writing without consulting primary documents",
       "adopting whichever interpretation is most popular"], 1,
      "Passage A (History & Objectivity), Q3", "dev"),
]

HELD_OUT: list[dict] = [
    # CP
    q("cp_electrochem", "2",
      "For the reaction Zn(s) + Cu²⁺ → Zn²⁺ + Cu(s), which species is the "
      "reducing agent?",
      ["Zn(s)", "Cu²⁺", "Zn²⁺", "Cu(s)"], 0,
      "Ch. 17.2 Galvanic Cells", "held_out", demand="application"),
    q("cp_electrochem", "2",
      "According to the Nernst equation, increasing the concentration of "
      "product ions (relative to reactants) will generally ______ Ecell.",
      ["increase", "decrease", "not change", "reverse the sign of E°"], 1,
      "Ch. 17.4 Potential, Free Energy, and Equilibrium", "held_out",
      demand="application"),
    q("cp_electrochem", "1",
      "Electrolysis differs from a galvanic cell in that electrolysis:",
      ["produces electrical energy from a spontaneous reaction",
       "uses electrical energy to drive a nonspontaneous reaction",
       "cannot involve oxidation–reduction",
       "always has a positive E°cell"], 1,
      "Ch. 17.7 Electrolysis", "held_out"),
    q("cp_electrochem", "1",
      "In any electrochemical cell, reduction always occurs at the:",
      ["anode", "cathode", "salt bridge", "electrolyte"], 1,
      "Ch. 17.2 Galvanic Cells", "held_out"),
    q("cp_acids_bases", "1",
      "What is the pH of a 0.010 M aqueous solution of HCl (a strong acid) at "
      "25 °C?",
      ["2.0", "1.0", "12.0", "0.010"], 0, "Ch. 14.3 pH and pOH", "held_out"),
    q("cp_acids_bases", "2",
      "Which pair is a conjugate acid–base pair?",
      ["HCl and NaOH", "H₂CO₃ and HCO₃⁻", "H₃O⁺ and O²⁻",
       "CH₃COOH and Cl⁻"], 1,
      "Ch. 14.2 Brønsted-Lowry Acids and Bases", "held_out",
      demand="application"),
    q("cp_acids_bases", "1",
      "At 25 °C, Kw = 1.0×10⁻¹⁴. In a neutral aqueous solution, [H⁺] equals:",
      ["1.0×10⁻⁷ M", "1.0×10⁻¹⁴ M", "1.0 M", "0 M"], 0,
      "Ch. 14.1 Ionization of Water", "held_out"),
    q("cp_acids_bases", "2",
      "A solution of pH 4 is how many times more acidic (in [H⁺]) than a "
      "solution of pH 6?",
      ["2", "10", "100", "1000"], 2, "Ch. 14.3 pH and pOH", "held_out",
      demand="application"),
    q("cp_thermo", "2",
      "For a process with ΔH > 0 and ΔS > 0, the reaction becomes spontaneous:",
      ["at high temperature", "at low temperature",
       "at all temperatures", "at no temperature"], 0,
      "Ch. 16.4 Free Energy", "held_out"),
    q("cp_thermo", "2",
      "A negative ΔG for a reaction indicates that the reaction is:",
      ["thermodynamically favorable (spontaneous)", "necessarily fast",
       "endothermic", "at equilibrium"], 0, "Ch. 16.4 Free Energy",
      "held_out"),
    q("cp_thermo", "2",
      "At equilibrium, the value of ΔG for the reaction is:",
      ["0", "large and negative", "large and positive",
       "equal to ΔG° always"], 0, "Ch. 16.4 Free Energy", "held_out"),
    q("cp_thermo", "1",
      "Entropy (S) is best described as a measure of:",
      ["the total energy of a system",
       "the dispersal (disorder) of energy and matter",
       "the reaction rate",
       "the activation energy"], 1, "Ch. 16.2 Entropy", "held_out"),
    q("cp_kinetics", "2",
      "For the rate law rate = k[A][B]², the overall reaction order is:",
      ["1", "2", "3", "0"], 2, "Ch. 12.3 Rate Laws", "held_out",
      demand="application"),
    q("cp_kinetics", "2",
      "If a reaction is first order in A, doubling [A] changes the rate by a "
      "factor of:",
      ["2", "4", "1 (no change)", "0.5"], 0, "Ch. 12.3 Rate Laws", "held_out",
      demand="application"),
    q("cp_kinetics", "1",
      "For a zero-order reaction, the rate is:",
      ["proportional to [A]", "independent of reactant concentration",
       "proportional to [A]²", "always zero"], 1,
      "Ch. 12.4 Integrated Rate Laws", "held_out"),
    q("cp_kinetics", "1",
      "The activation energy of a reaction is:",
      ["the energy difference between products and reactants",
       "the minimum energy reactants need to form products",
       "always equal to ΔG",
       "lowered simply by raising the temperature"], 1,
      "Ch. 12.5 Collision Theory", "held_out"),
    q("cp_fluids", "2",
      "By Bernoulli's principle, where an ideal fluid's speed is higher (at "
      "constant height), its pressure is:",
      ["higher", "lower", "unchanged", "zero"], 1,
      "Ch. 12.2 Bernoulli's Equation", "held_out"),
    q("cp_fluids", "1",
      "An object floats in a fluid when the buoyant force equals:",
      ["its own weight", "zero", "the entire weight of the fluid",
       "atmospheric pressure"], 0, "Ch. 11.7 Archimedes' Principle",
      "held_out"),
    # BB
    q("bb_glycolysis", "2",
      "Under aerobic conditions, the end product of glycolysis (per glucose) "
      "that enters the mitochondrion is:",
      ["two molecules of pyruvate", "two molecules of lactate",
       "one molecule of acetyl-CoA", "two molecules of ethanol"], 0,
      "Ch. 7.2 Glycolysis", "held_out"),
    q("bb_glycolysis", "2",
      "The committed, rate-limiting step of glycolysis is catalyzed by:",
      ["hexokinase", "phosphofructokinase-1 (PFK-1)", "pyruvate kinase",
       "aldolase"], 1, "Ch. 7.2 Glycolysis", "held_out"),
    q("bb_glycolysis", "1",
      "The initial 'energy investment' phase of glycolysis consumes how many "
      "ATP?",
      ["2", "4", "0", "6"], 0, "Ch. 7.2 Glycolysis", "held_out"),
    q("bb_glycolysis", "2",
      "Under anaerobic conditions in human muscle, pyruvate is converted to "
      "______ to regenerate NAD⁺.",
      ["ethanol", "lactate", "acetyl-CoA", "citrate"], 1,
      "Ch. 7.5 Fermentation", "held_out"),
    q("bb_citric_acid", "2",
      "Per turn of the citric acid cycle, how many CO₂ molecules are released?",
      ["1", "2", "3", "0"], 1, "Ch. 7.3 Citric Acid Cycle", "held_out"),
    q("bb_citric_acid", "2",
      "Most of the energy harvested by the citric acid cycle is captured as:",
      ["ATP directly", "reduced electron carriers NADH and FADH₂",
       "heat", "GTP only"], 1, "Ch. 7.3 Citric Acid Cycle", "held_out"),
    q("bb_citric_acid", "2",
      "For each acetyl-CoA oxidized, the citric acid cycle produces how many "
      "NADH?",
      ["1", "2", "3", "4"], 2, "Ch. 7.3 Citric Acid Cycle", "held_out"),
    q("bb_enzymes", "1",
      "The region of an enzyme where substrate binds and catalysis occurs is "
      "the:",
      ["allosteric site", "active site", "R group", "peptide backbone"], 1,
      "Ch. 6.5 Enzymes", "held_out"),
    q("bb_enzymes", "2",
      "According to the induced-fit model, when substrate binds an enzyme:",
      ["the enzyme is permanently consumed",
       "the active site changes shape to fit the substrate more snugly",
       "the substrate is left chemically unchanged",
       "the activation energy increases"], 1, "Ch. 6.5 Enzymes", "held_out"),
    q("bb_enzymes", "2",
      "Raising temperature well above an enzyme's optimum typically:",
      ["increases activity without limit",
       "denatures the enzyme and decreases activity",
       "has no effect on activity",
       "lowers only the Km"], 1, "Ch. 6.5 Enzymes", "held_out"),
    q("bb_membranes", "2",
      "Simple diffusion of a small nonpolar molecule (e.g., O₂) across a "
      "membrane:",
      ["requires ATP hydrolysis",
       "moves the molecule down its concentration gradient without energy "
       "input",
       "requires a specific transport protein",
       "moves the molecule against its gradient"], 1,
      "Ch. 5.2 Passive Transport", "held_out"),
    q("bb_membranes", "2",
      "Which process moves solutes against their concentration gradient and "
      "requires energy?",
      ["simple diffusion", "facilitated diffusion", "active transport",
       "osmosis"], 2, "Ch. 5.3 Active Transport", "held_out"),
    q("bb_membranes", "2",
      "Cholesterol in animal cell membranes primarily functions to:",
      ["store genetic information", "modulate membrane fluidity",
       "catalyze glycolysis", "form the hydrophilic head groups"], 1,
      "Ch. 5.1 Components and Structure", "held_out"),
    q("bb_membranes", "1",
      "Osmosis is the diffusion of ______ across a selectively permeable "
      "membrane.",
      ["solutes", "water", "proteins", "ions only"], 1,
      "Ch. 5.2 Passive Transport", "held_out"),
    q("bb_dna", "1",
      "In DNA, adenine pairs with ______ and guanine pairs with ______.",
      ["thymine; cytosine", "cytosine; thymine", "uracil; guanine",
       "thymine; adenine"], 0, "Ch. 14.2 DNA Structure", "held_out"),
    q("bb_dna", "2",
      "The enzyme that unwinds the DNA double helix at the replication fork "
      "is:",
      ["ligase", "helicase", "polymerase", "primase"], 1,
      "Ch. 14.4 DNA Replication in Prokaryotes", "held_out"),
    q("bb_dna", "2",
      "Okazaki fragments are synthesized on the ______ strand during "
      "replication.",
      ["leading", "lagging", "template-only", "RNA"], 1,
      "Ch. 14.4 DNA Replication in Prokaryotes", "held_out"),
    q("bb_dna", "1",
      "The two strands of a DNA double helix are:",
      ["identical and parallel",
       "antiparallel and complementary",
       "both composed of RNA",
       "held together by covalent bonds between bases"], 1,
      "Ch. 14.2 DNA Structure", "held_out"),
    q("bb_genetics", "2",
      "In a monohybrid cross Aa × Aa, the expected genotypic ratio is:",
      ["1:2:1 (AA:Aa:aa)", "3:1", "1:1", "all Aa"], 0,
      "Ch. 12.2 Characteristics and Traits", "held_out"),
    q("bb_genetics", "2",
      "Mendel's law of segregation states that:",
      ["alleles of different genes assort independently",
       "the two alleles for a gene separate during gamete formation",
       "dominant alleles are always more common",
       "traits blend evenly in offspring"], 1,
      "Ch. 12.2 Characteristics and Traits", "held_out"),
    q("bb_genetics", "2",
      "A testcross is performed by crossing an individual of unknown genotype "
      "with one that is:",
      ["homozygous dominant", "homozygous recessive", "heterozygous",
       "haploid"], 1, "Ch. 12.2 Characteristics and Traits", "held_out"),
    q("bb_genetics", "3",
      "Two genes located far apart on the same chromosome tend to:",
      ["always be inherited together",
       "assort nearly independently due to crossing over",
       "never undergo recombination",
       "be located on different chromosomes"], 1,
      "Ch. 12.3 Laws of Inheritance", "held_out", demand="synthesis"),
    # PS
    q("ps_memory", "1",
      "The relatively permanent, seemingly unlimited store of memory is:",
      ["sensory memory", "short-term memory", "long-term memory",
       "iconic memory"], 2, "Ch. 8.1 How Memory Functions", "held_out"),
    q("ps_memory", "2",
      "Retrieval is easier when the context at recall matches the context at "
      "encoding; this is:",
      ["the misinformation effect",
       "context-dependent memory (encoding specificity)",
       "proactive interference",
       "the self-reference effect"], 1,
      "Ch. 8.3 Ways to Enhance Memory", "held_out"),
    q("ps_memory", "1",
      "The tendency to recall the first and last items of a list better than "
      "the middle is the:",
      ["spacing effect", "serial position effect", "misinformation effect",
       "priming effect"], 1, "Ch. 8.1 How Memory Functions", "held_out"),
    q("ps_memory", "1",
      "Explicit (declarative) memory includes:",
      ["riding a bicycle", "facts and events you can consciously recall",
       "conditioned reflexes", "motor skills"], 1,
      "Ch. 8.1 How Memory Functions", "held_out"),
    q("ps_learning", "1",
      "In classical conditioning, the previously neutral stimulus that comes "
      "to elicit a response after pairing is the:",
      ["unconditioned stimulus", "conditioned stimulus",
       "unconditioned response", "reinforcer"], 1,
      "Ch. 6.2 Classical Conditioning", "held_out"),
    q("ps_learning", "2",
      "Negative reinforcement ______ a behavior by ______ an aversive "
      "stimulus.",
      ["decreases; adding", "increases; removing", "decreases; removing",
       "increases; adding"], 1, "Ch. 6.3 Operant Conditioning", "held_out"),
    q("ps_learning", "2",
      "A schedule that reinforces behavior after an unpredictable number of "
      "responses is a:",
      ["fixed-ratio schedule", "variable-ratio schedule",
       "fixed-interval schedule", "continuous schedule"], 1,
      "Ch. 6.3 Operant Conditioning", "held_out"),
    q("ps_social", "2",
      "In Milgram's experiments, participants' willingness to administer "
      "shocks demonstrated the power of:",
      ["conformity to peers", "obedience to authority",
       "the bystander effect", "groupthink"], 1,
      "Ch. 12.5 Obedience", "held_out"),
    q("ps_social", "2",
      "The bystander effect describes how the presence of others ______ the "
      "likelihood that any one person will help.",
      ["increases", "decreases", "does not change", "guarantees"], 1,
      "Ch. 12.6 Prosocial Behavior", "held_out"),
    q("ps_social", "1",
      "An attitude is best defined as:",
      ["a permanent genetic trait",
       "an evaluation (favorable or unfavorable) of a person, object, or idea",
       "an involuntary physical reflex",
       "a type of long-term memory"], 1,
      "Ch. 12.3 Attitudes and Persuasion", "held_out"),
    q("ps_demographics", "2",
      "Socioeconomic status (SES) is typically measured using income, "
      "education, and:",
      ["blood type", "occupation", "height", "personality type"], 1,
      "Ch. 14.3 Stress and Illness", "held_out"),
    q("ps_demographics", "3",
      "A social gradient in health means that:",
      ["health tends to improve as one moves up the socioeconomic ladder",
       "health is unrelated to social position",
       "only the very poorest experience worse health",
       "wealth directly causes disease"], 0,
      "Ch. 14.3 Stress and Illness", "held_out", demand="synthesis"),
    # CARS
    q("cars_comprehension", "1",
      P_HIST + "QUESTION\nAs used in the passage, 'vantage point' most nearly "
      "means:",
      ["a physical location", "a particular perspective or standpoint",
       "a factual error", "a specific historical period"], 1,
      "Passage A (History & Objectivity), Q4", "held_out"),
    q("cars_comprehension", "2",
      P_CHOICE + "QUESTION\nThe author's overall attitude toward simply "
      "increasing the number of options is best described as:",
      ["unqualified enthusiasm", "cautious skepticism",
       "total rejection of all choice", "complete indifference"], 1,
      "Passage B (Choice & Freedom), Q4", "held_out"),
    q("cars_reasoning_within", "3",
      P_HIST + "QUESTION\nThe sentence 'This does not make history mere "
      "fiction' functions primarily to:",
      ["concede that history is fiction",
       "anticipate and rebut a likely misreading of the argument",
       "introduce an unrelated topic",
       "contradict the passage's thesis"], 1,
      "Passage A (History & Objectivity), Q5", "held_out"),
    q("cars_reasoning_within", "3",
      P_CHOICE + "QUESTION\nThe passage is organized primarily to:",
      ["reject the possibility of meaningful choice",
       "qualify a common assumption by redefining freedom",
       "list the steps of good decision-making",
       "compare two brands of products"], 1,
      "Passage B (Choice & Freedom), Q5", "held_out"),
    q("cars_reasoning_beyond", "4",
      P_CHOICE + "QUESTION\nWhich finding, if true, would most WEAKEN the "
      "author's argument?",
      ["People given many options consistently report greater satisfaction and "
       "decide easily.",
       "Shoppers facing many options take longer to decide.",
       "Some people report disliking shopping.",
       "Good judgment can be taught over time."], 0,
      "Passage B (Choice & Freedom), Q6", "held_out"),
    q("cars_reasoning_beyond", "4",
      P_HIST + "QUESTION\nThe passage's reasoning about historians could best "
      "be extended to:",
      ["a journalist who acknowledges her biases and checks them against "
       "evidence",
       "a calculator that never makes arithmetic errors",
       "a witness who refuses to testify",
       "a novelist inventing fictional characters"], 0,
      "Passage A (History & Objectivity), Q6", "held_out"),
    q("cp_fluids", "1",
      "The SI unit of pressure, the pascal (Pa), is equivalent to:",
      ["N/m²", "kg·m/s²", "J·s", "N·m"], 0, "Ch. 11.2 Pressure", "held_out"),
    q("cars_comprehension", "2",
      P_CHOICE + "QUESTION\nThe 'shopper' example in the passage is used "
      "primarily to:",
      ["prove that all shopping is harmful",
       "illustrate how an excess of options can reduce satisfaction",
       "argue for banning nearly identical products",
       "describe the author's personal shopping habits"], 1,
      "Passage B (Choice & Freedom), Q7", "held_out"),
]


# --- Synthesis & application items (stable ids q_syn_001..030) --------------
# Each integrates >=2 concepts (synthesis) or applies one concept to novel
# data / a multi-step calculation (application); none are pure recall. Every
# distractor carries a content-axis choice_diagnosis. See
# docs/SYNTHESIS-QUESTIONS-DRAFT.md (reviewed + fixed 2026-07-01) for the spec.
SYNTHESIS: list[dict] = [
    # --- Passage 1 — Enzyme inhibition data (bb_enzymes, held_out) ----------
    qsyn("q_syn_001", "bb_enzymes", "4", "synthesis",
         P_ENZYME + "QUESTION\nWhich type of inhibition does X most likely exhibit?",
         ["Competitive", "Noncompetitive", "Uncompetitive",
          "Irreversible (covalent)"], 0,
         "Ch. 6.5 Enzymes (inhibition; Michaelis–Menten)", "held_out",
         [None,
          cg("expects Vmax to fall; confuses noncompetitive (Vmax↓, Km "
             "unchanged) with the observed Vmax-unchanged/Km-up pattern"),
          cg("uncompetitive lowers both Vmax and Km; misreads the table"),
          cg("assumes higher apparent Km implies irreversible/covalent "
             "inhibition")]),
    qsyn("q_syn_002", "bb_enzymes", "2", "application",
         P_ENZYME + "QUESTION\nIf [S] is raised to very high (saturating) "
         "levels in the presence of X, the reaction velocity will:",
         ["approach the same maximum as without X",
          "remain below the uninhibited velocity at every [S], including "
          "saturating",
          "exceed the uninhibited Vmax",
          "become independent of [S] at all concentrations"], 0,
         "Ch. 6.5 Enzymes", "held_out",
         [None,
          cg("does not know competitive inhibition is overcome by excess "
             "substrate"),
          cg("believes adding substrate can push velocity past Vmax"),
          cg("confuses saturation with zero-order independence at all [S]")]),
    qsyn("q_syn_003", "bb_enzymes", "3", "application",
         P_ENZYME + "QUESTION\nSubstrate concentration is the independent "
         "variable (deliberately ranged across rows) and the presence of "
         "inhibitor X is the treatment being compared. Which other quantity "
         "most needed to be identical in both runs so that any difference in "
         "velocity can be attributed to X?",
         ["the substrate concentration", "the total amount of enzyme",
          "the measured reaction velocity", "the presence of inhibitor X"], 1,
         "Ch. 6.5 Enzymes; experimental design (AAMC Skill 4)", "held_out",
         [cg("the stem names [S] as the independent variable; selecting it "
             "ignores that [S] is varied on purpose, not a control"),
          None,
          cg("names the dependent variable — the measured outcome, not a "
             "control"),
          cg("X presence is the treatment being compared, so it cannot be "
             "held constant")]),
    qsyn("q_syn_004", "bb_enzymes", "2", "synthesis",
         P_ENZYME + "QUESTION\nInhibitor X changes the apparent Km measured "
         "for this enzyme. Does X change the reaction's ΔG or its equilibrium "
         "constant (Keq)?",
         ["Yes — it makes S→P less thermodynamically favorable",
          "No — it changes the rate/kinetics but not ΔG or Keq",
          "Yes — raising Km lowers Keq",
          "It changes ΔG only at high [S]"], 1,
         "Ch. 6.5 Enzymes; Ch. 6.3 (ΔG / spontaneity)", "held_out",
         [cg("treats a kinetic inhibitor as changing thermodynamic "
             "favorability"),
          None,
          cg("confuses Km (kinetic, [S] at ½Vmax) with Keq (thermodynamic)"),
          cg("thinks ΔG depends on substrate concentration")]),

    # --- Passage 2 — Galvanic cell + thermo (cp_electrochem, dev) -----------
    qsyn("q_syn_005", "cp_electrochem", "2", "application",
         P_GALVANIC + "QUESTION\nWhich electrode is the cathode, and what is "
         "the standard cell potential E°cell?",
         ["Cu is the cathode; E°cell = +1.10 V",
          "Zn is the cathode; E°cell = +1.10 V",
          "Cu is the cathode; E°cell = +0.42 V",
          "Cu is the cathode; E°cell = −1.10 V"], 0,
         "Ch. 17.2 Galvanic Cells; Ch. 17.3 Standard Reduction Potentials",
         "dev",
         [None,
          cg("assigns cathode to the more negative electrode (reverses "
             "anode/cathode)"),
          trap("inverse"),
          trap("negation")]),
    qsyn("q_syn_006", "cp_electrochem", "2", "synthesis",
         P_GALVANIC + "QUESTION\nUsing ΔG° = −nFE°cell, what is ΔG° for this "
         "cell reaction, and is it spontaneous?",
         ["≈ −212 kJ; spontaneous", "≈ +212 kJ; nonspontaneous",
          "≈ −106 kJ; spontaneous",
          "ΔG° = 0; the cell is at equilibrium"], 0,
         "Ch. 17.4 Potential, Free Energy, and Equilibrium", "dev",
         [None,
          trap("negation"),
          cg("used n = 1 instead of n = 2 electrons"),
          cg("assumes a standard cell is at equilibrium (confuses E°cell with "
             "Ecell = 0)")]),
    qsyn("q_syn_007", "cp_electrochem", "2", "application",
         P_GALVANIC + "QUESTION\nIf the concentration of Zn²⁺ (a product ion) "
         "is increased while Cu²⁺ is held constant, what happens to the actual "
         "cell potential Ecell?",
         ["Ecell decreases", "Ecell increases", "E°cell decreases",
          "no change, because E° is fixed"], 0,
         "Ch. 17.4 (Nernst equation)", "dev",
         [None,
          cg("wrong direction of the Nernst shift"),
          cg("confuses Ecell with E°cell — standard potential is fixed, so "
             "this option is a category error"),
          cg("believes ion concentration cannot affect the actual "
             "potential")]),
    qsyn("q_syn_008", "cp_electrochem", "2", "synthesis",
         P_GALVANIC + "QUESTION\nAs the cell operates and the reaction "
         "proceeds toward equilibrium, Ecell trends toward ____ and ΔG trends "
         "toward ____.",
         ["Ecell → 0; ΔG → 0", "Ecell increases; ΔG becomes more negative",
          "Ecell → E°cell; ΔG → ΔG°",
          "Ecell → 0; ΔG → a large negative value"], 0,
         "Ch. 17.4; Ch. 16.4 Free Energy", "dev",
         [None,
          cg("thinks an operating cell gains potential over time"),
          cg("confuses approaching equilibrium with returning to standard "
             "conditions"),
          trap("partial")]),

    # --- Passage 3 — Buffer / Henderson–Hasselbalch (cp_acids_bases, ho) ----
    qsyn("q_syn_009", "cp_acids_bases", "2", "application",
         P_BUFFER + "QUESTION\nWhat is the pH of the initial buffer?",
         ["4.74", "7.00", "9.26", "2.37"], 0,
         "Ch. 14.6 Buffers (Henderson–Hasselbalch)", "held_out",
         [None,
          cg("assumes equal concentrations imply a neutral pH of 7"),
          cg("used 14 − pKa (pOH/pKb confusion) or inverted the ratio"),
          None]),
    qsyn("q_syn_010", "cp_acids_bases", "2", "synthesis",
         P_BUFFER + "QUESTION\nA small amount of strong acid (HCl) is added to "
         "the buffer. What happens to the pH, and why?",
         ["pH drops sharply, as it would in pure water",
          "pH decreases only slightly; acetate (A⁻) reacts with the added H⁺ "
          "to form acetic acid",
          "pH increases, because acetate is a base",
          "pH does not change at all, because buffers hold pH perfectly "
          "constant"], 1,
         "Ch. 14.6 Buffers", "held_out",
         [cg("does not understand buffering — treats buffer like unbuffered "
             "water"),
          None,
          cg("wrong direction: adding acid cannot raise pH here"),
          cg("over-generalizes buffers as infinite/perfect capacity")]),
    qsyn("q_syn_011", "cp_acids_bases", "2", "application",
         P_BUFFER + "QUESTION\nTo instead prepare a buffer at pH 5.74 (one "
         "unit above the pKa), what ratio of [CH₃COO⁻] to [CH₃COOH] is "
         "needed?",
         ["1 : 10", "10 : 1", "1 : 1", "100 : 1"], 1,
         "Ch. 14.6 Buffers", "held_out",
         [trap("inverse"),
          None,
          cg("assumes every buffer is 1:1 regardless of target pH"),
          trap("scaling")]),
    qsyn("q_syn_012", "cp_acids_bases", "2", "synthesis",
         P_BUFFER + "QUESTION\nSolid sodium acetate is dissolved into a "
         "solution of pure acetic acid (adding CH₃COO⁻). What happens to the "
         "acetic-acid dissociation equilibrium, to its percent dissociation, "
         "and to the pH?",
         ["shifts left; percent dissociation of acetic acid decreases; pH "
          "rises",
          "shifts right; more H⁺ is released; pH drops",
          "no shift; acetate is only a spectator ion",
          "shifts left; but pH drops"], 0,
         "Ch. 14.6 Buffers; Le Chatelier (common-ion effect)", "held_out",
         [None,
          cg("wrong Le Chatelier direction for adding a common ion"),
          cg("does not recognize the common-ion effect"),
          trap("partial")]),

    # --- Passage 4 — Dihybrid probability (bb_genetics, dev) ----------------
    qsyn("q_syn_013", "bb_genetics", "2", "application",
         P_DIHYBRID + "QUESTION\nWhat is the probability that a given "
         "offspring is homozygous recessive for both genes (yyrr)?",
         ["1/16", "9/16", "1/4", "3/16"], 0,
         "Ch. 12.3 Laws of Inheritance (independent assortment; product rule)",
         "dev",
         [None,
          cg("reports the both-dominant phenotype fraction (9/16)"),
          trap("partial"),
          cg("confuses with a one-dominant/one-recessive class (3/16)")]),
    qsyn("q_syn_014", "bb_genetics", "2", "synthesis",
         P_DIHYBRID + "QUESTION\nWhat fraction of offspring are expected to be "
         "yellow and wrinkled (Y_ rr)?",
         ["3/16", "9/16", "1/16", "3/4"], 0,
         "Ch. 12.3 Laws of Inheritance", "dev",
         [None,
          cg("gives the both-dominant 9/16 (ignores that shape is recessive)"),
          cg("computes both-recessive instead of one dominant/one recessive"),
          trap("partial")]),
    qsyn("q_syn_015", "bb_genetics", "3", "synthesis",
         P_DIHYBRID + "QUESTION\nSeparately, a yellow, round plant of unknown "
         "genotype is testcrossed with a green, wrinkled plant (yyrr). The "
         "offspring are ½ yellow : ½ green, and all are round. What is the "
         "unknown plant's genotype?",
         ["YyRR", "YYRr", "YyRr", "YYRR"], 0,
         "Ch. 12.2 Characteristics and Traits (testcross); Ch. 12.3", "dev",
         [None,
          cg("maps the ratios to the wrong genes (reads color data onto "
             "shape)"),
          cg("assumes both genes heterozygous, ignoring the 'all round' "
             "result"),
          cg("assumes fully homozygous dominant despite the ½ green "
             "offspring")]),

    # --- Standalone science items ------------------------------------------
    qsyn("q_syn_016", "bb_citric_acid", "2", "synthesis",
         "Under aerobic conditions, one glucose molecule is fully oxidized: "
         "glycolysis yields 2 pyruvate, each pyruvate is converted to "
         "acetyl-CoA, and each acetyl-CoA is oxidized in the citric acid "
         "cycle. Counting only substrate-level phosphorylation (not the "
         "electron transport chain), how many net ATP/GTP are produced from "
         "one glucose through the end of the citric acid cycle?",
         ["2", "4", "36", "30"], 1,
         "Ch. 7.2 Glycolysis; Ch. 7.3 Citric Acid Cycle", "dev",
         [cg("counts only glycolysis; forgets the 2 GTP from the two TCA "
             "turns"),
          None,
          cg("gives total aerobic yield (~36) — conflates substrate-level "
             "with oxidative phosphorylation"),
          None]),
    qsyn("q_syn_017", "bb_membranes", "2", "application",
         "A red blood cell with an internal solute concentration of about 300 "
         "mOsm is placed into a 100 mOsm solution. What is the net movement of "
         "water and the likely outcome?",
         ["water leaves the cell; it shrinks (crenates)",
          "water enters the cell; it swells and may lyse",
          "no net movement; the solutions are isotonic",
          "solutes diffuse out of the cell to equalize concentrations"], 1,
         "Ch. 5.2 Passive Transport (osmosis, tonicity)", "held_out",
         [cg("reverses osmosis direction (treats the cell as if it were in a "
             "hypertonic bath)"),
          None,
          cg("misjudges tonicity (300 vs 100 mOsm are not equal)"),
          cg("thinks solute crosses rather than water — misunderstands "
             "osmosis")]),
    qsyn("q_syn_018", "bb_dna", "2", "application",
         "One strand of DNA reads 5'-TACGGA-3'. Written in the conventional "
         "5'→3' direction, the newly synthesized complementary strand is:",
         ["5'-TCCGTA-3'", "5'-ATGCCT-3'", "5'-TACGGA-3'", "5'-UCCGUA-3'"], 0,
         "Ch. 14.2 DNA Structure (base pairing, antiparallel strands)", "dev",
         [None,
          cg("writes the base complement but ignores antiparallel orientation "
             "(reports it 3'→5')"),
          cg("copies the template instead of pairing complementary bases"),
          cg("uses uracil (RNA) instead of thymine for DNA")]),
    qsyn("q_syn_019", "cp_thermo", "2", "synthesis",
         "A reaction has ΔH = +50 kJ/mol and ΔS = +150 J/(mol·K). Above "
         "approximately what temperature does the reaction become "
         "spontaneous?",
         ["333 K", "0.33 K", "3.0 K", "It is never spontaneous"], 0,
         "Ch. 16.4 Free Energy (ΔG=ΔH−TΔS; temperature dependence)", "dev",
         [None,
          trap("unit"),
          None,
          cg("thinks ΔH>0 means never spontaneous, ignoring the TΔS term at "
             "high T")]),
    qsyn("q_syn_020", "cp_kinetics", "4", "synthesis",
         "Initial-rate data for A + B → products:\n\n"
         "```\nExp | [A] (M) | [B] (M) | rate (M/s)\n"
         " 1  |  0.10   |  0.10   |   2.0\n"
         " 2  |  0.20   |  0.10   |   4.0\n"
         " 3  |  0.10   |  0.20   |   8.0\n```\n"
         "What is the rate law?",
         ["rate = k[A][B]²", "rate = k[A]²[B]", "rate = k[A][B]",
          "rate = k[A]²[B]²"], 0,
         "Ch. 12.3 Rate Laws (method of initial rates)", "held_out",
         [None,
          trap("transpose"),
          cg("reads B as first order (misses the ×4 → square)"),
          cg("misreads A as second order")]),
    qsyn("q_syn_021", "cp_kinetics", "2", "synthesis",
         "A reaction has ΔG = −100 kJ/mol yet proceeds imperceptibly slowly at "
         "room temperature. Which statement best explains this?",
         ["ΔG must actually be positive",
          "The reaction is thermodynamically favorable but has a high "
          "activation energy, so it is kinetically slow",
          "The reaction is already at equilibrium",
          "A catalyst would speed it up by making ΔG more negative"], 1,
         "Ch. 16.4 Free Energy; Ch. 12.5 Collision Theory / 12.7 Catalysis",
         "dev",
         [cg("conflates slow with nonspontaneous (thinks rate reveals ΔG)"),
          None,
          cg("confuses 'slow' with 'at equilibrium'"),
          cg("believes catalysts change ΔG (they change Ea only)")]),
    qsyn("q_syn_022", "cp_fluids", "2", "synthesis",
         "Water in streamline flow moves through a horizontal pipe that "
         "narrows from cross-sectional area A₁ to A₂ = A₁/2. Compared with the "
         "wide section, in the narrow section the water's speed and pressure "
         "are:",
         ["speed doubles; pressure decreases", "speed halves; pressure "
          "increases", "speed doubles; pressure increases",
          "speed is unchanged; pressure decreases"], 0,
         "Ch. 12.1 Flow Rate and Continuity; Ch. 12.2 Bernoulli's Equation",
         "held_out",
         [None,
          cg("reverses continuity (smaller area → slower)"),
          cg("gets continuity right but violates Bernoulli (thinks faster → "
             "higher pressure)"),
          cg("ignores continuity entirely")]),
    qsyn("q_syn_023", "cp_fluids", "2", "application",
         "Water flows at 2.0 m/s through a pipe of cross-sectional area 6.0 "
         "cm². The pipe then narrows to 2.0 cm². What is the water's speed in "
         "the narrow section?",
         ["6.0 m/s", "0.67 m/s", "2.0 m/s", "18 m/s"], 0,
         "Ch. 12.1 Flow Rate and Continuity", "dev",
         [None,
          trap("inverse"),
          cg("assumes speed is unchanged"),
          None]),
    qsyn("q_syn_024", "cp_acids_bases", "2", "application",
         "Equal volumes of 0.10 M HCl and 0.10 M acetic acid (Ka = 1.8×10⁻⁵) "
         "are compared. Which statement about their pH is correct?",
         ["Both have the same pH because their concentrations are equal",
          "HCl has the lower pH because it ionizes completely",
          "Acetic acid has the lower pH because it is the stronger acid",
          "Both are neutral (pH 7)"], 1,
         "Ch. 14.3 pH and pOH; Ch. 14.2 (strong vs weak acids)", "held_out",
         [cg("assumes equal concentration ⇒ equal pH, ignoring ionization "
             "extent"),
          None,
          cg("reverses acid strength (calls acetic acid the stronger acid)"),
          cg("thinks acids can be pH-neutral")]),
    qsyn("q_syn_025", "ps_learning", "2", "application",
         "A slot machine pays out after an unpredictable number of plays. "
         "Gamblers keep pulling the lever at a high, steady rate, and the "
         "behavior is very resistant to extinction. This pattern best "
         "illustrates:",
         ["a fixed-interval schedule", "a variable-ratio schedule",
          "negative reinforcement", "a fixed-ratio schedule"], 1,
         "Ch. 6.3 Operant Conditioning (reinforcement schedules)", "dev",
         [cg("confuses interval (time-based) with ratio (response-based) "
             "schedules"),
          None,
          cg("mislabels a reinforcement schedule as negative reinforcement"),
          cg("confuses fixed with variable ratio (misses 'unpredictable')")]),
    qsyn("q_syn_026", "ps_learning", "2", "application",
         "A person takes aspirin whenever they have a headache; the relief "
         "that follows makes them more likely to take aspirin the next time. "
         "This is an example of:",
         ["positive reinforcement", "negative reinforcement",
          "positive punishment", "negative punishment"], 1,
         "Ch. 6.3 Operant Conditioning", "held_out",
         [cg("assumes any behavior increase is positive reinforcement (adding "
             "a stimulus)"),
          None,
          cg("confuses reinforcement (increases behavior) with punishment "
             "(decreases it)"),
          cg("confuses negative reinforcement with negative punishment")]),
    qsyn("q_syn_027", "ps_social", "2", "synthesis",
         "Jordan watches a classmate trip and thinks, 'How clumsy.' Later, "
         "when Jordan trips, they blame the uneven floor. The judgment of the "
         "classmate illustrates ____, and Jordan's judgment of their own "
         "stumble illustrates ____.",
         ["the fundamental attribution error; the actor–observer bias",
          "the self-serving bias; the fundamental attribution error",
          "the just-world hypothesis; conformity",
          "the bystander effect; obedience"], 0,
         "Ch. 12.1 What Is Social Psychology? (attribution)", "dev",
         [None,
          cg("reverses the two biases"),
          None,
          None]),
    qsyn("q_syn_028", "ps_social", "2", "application",
         "A person who values their health but smokes daily feels "
         "uncomfortable, then persuades themselves that 'the health risks are "
         "exaggerated.' Resolving the discomfort by changing a belief best "
         "illustrates:",
         ["reduction of cognitive dissonance", "classical conditioning",
          "the bystander effect", "negative reinforcement"], 0,
         "Ch. 12.3 Attitudes and Persuasion (cognitive dissonance)",
         "held_out",
         [None,
          cg("confuses attitude change with associative (classical) "
             "learning"),
          None,
          cg("confuses a cognitive process with operant reinforcement")]),
    qsyn("q_syn_029", "ps_memory", "2", "application",
         "Students who study in a quiet room recall more when tested in a "
         "quiet room than when tested in a noisy one; those who studied with "
         "background noise show the reverse. This is best explained by:",
         ["the serial position effect",
          "context-dependent memory (encoding specificity)",
          "proactive interference", "chunking"], 1,
         "Ch. 8.3 Ways to Enhance Memory (context-dependent memory)", "dev",
         [cg("confuses a list-position effect with context effects"),
          None,
          cg("confuses interference (competing memories) with context "
             "matching"),
          cg("confuses an encoding strategy with a retrieval-context "
             "effect")]),
    qsyn("q_syn_030", "ps_demographics", "4", "synthesis",
         "A study reports age-adjusted mortality by income quintile:\n\n"
         "```\nIncome quintile | deaths per 1,000/yr\n"
         " lowest         |        12\n"
         " second         |        10\n"
         " middle         |         8\n"
         " fourth         |         6\n"
         " highest        |         5\n```\n"
         "Which concept does this pattern best illustrate, and what does it "
         "imply?",
         ["a social gradient in health — outcomes improve stepwise with "
          "rising SES, not only for the poorest",
          "health disparities are essentially random",
          "only the very poorest have worse health (a threshold effect)",
          "the differences are fully explained by genetics"], 0,
         "Ch. 14.3 Stress and Illness (SES, social determinants)", "held_out",
         [None,
          cg("denies the clear monotonic pattern in the data"),
          cg("threshold misconception — misses that risk falls at every step, "
             "not just at the bottom"),
          cg("attributes a social-gradient pattern solely to genetics, "
             "ignoring social determinants")]),
]


def main() -> None:
    out = []
    for i, item in enumerate(DEV, 1):
        item["id"] = f"q_dev_{i:03d}"
        out.append(item)
    for i, item in enumerate(HELD_OUT, 1):
        item["id"] = f"q_ho_{i:03d}"
        out.append(item)
    # Synthesis items carry their own stable ids (q_syn_*) — never renumbered.
    out.extend(SYNTHESIS)

    # reorder keys for readability
    ordered = []
    for it in out:
        is_cars = it["section"] == "CARS"
        entry = {
            "id": it["id"],
            "stem": it["stem"],
            "choices": it["choices"],
            "correct": it["correct"],
            "topic_id": it["topic_id"],
            "section": it["section"],
            "skill": it["skill"],
        }
        # cognitive_demand is science-only; CARS is diagnosed by skill
        # archetype + pacing, not the error-typing engine (spec: Two tracks).
        # Precedence: explicit q_syn demand > per-call override (_demand) >
        # honest recall baseline for the existing bank.
        if not is_cars:
            entry["cognitive_demand"] = (
                it.get("cognitive_demand")
                or it.get("_demand")
                or "recall"
            )
        # choice_diagnosis is optional content-axis authoring (science-only).
        if it.get("choice_diagnosis") is not None:
            entry["choice_diagnosis"] = it["choice_diagnosis"]
        entry.update({
            "source_name": it["source_name"],
            "source_url": it["source_url"],
            "source_location": it["source_location"],
            "split": it["split"],
        })
        ordered.append(entry)

    (DATA / "questions.json").write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    dev = sum(1 for x in ordered if x["split"] == "dev")
    held = sum(1 for x in ordered if x["split"] == "held_out")
    topics = sorted({x["topic_id"] for x in ordered})
    print(f"wrote {len(ordered)} questions: dev={dev}, held_out={held}")
    print(f"topics covered: {len(topics)}")
    per: dict[str, dict[str, int]] = {}
    for x in ordered:
        d = per.setdefault(x["topic_id"], {"dev": 0, "held_out": 0})
        d[x["split"]] += 1
    for t in topics:
        print(f"  {t:26} dev={per[t]['dev']}  held_out={per[t]['held_out']}")

    # refresh curation-status.json counts (preserve targets + milestones)
    status_path = DATA / "curation-status.json"
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        for tid, counts in status.get("topics", {}).items():
            counts["dev"] = per.get(tid, {}).get("dev", 0)
            counts["held_out"] = per.get(tid, {}).get("held_out", 0)
        status["generated_totals"] = {
            "total": len(ordered),
            "dev": dev,
            "held_out": held,
            "topics_with_questions": len(topics),
        }
        status_path.write_text(
            json.dumps(status, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("updated curation-status.json counts")


if __name__ == "__main__":
    main()

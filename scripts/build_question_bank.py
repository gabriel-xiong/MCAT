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


# --- Bulk content-axis tags for the recall bank (q_dev_* / q_ho_*) ----------
# The 30 q_syn_* items author choice_diagnosis inline (above). This dict adds
# the same content-axis tagging to the existing recall-heavy DEV/HELD_OUT
# science items, keyed by their generated id (assigned in main() by position).
#
# Discipline (docs/ERROR-DIAGNOSIS-SPEC.md "Choice tagging methodology"):
#   - cg(<misconception>)  : distractor encodes a SPECIFIC false belief; each
#                            cg within a question is a DISTINCT misconception.
#   - trap(<kind>)         : predictable EXECUTION landing (kind in the enum
#                            negation|unit|inverse|scaling|transpose|partial);
#                            rides on maps_to null, no misconception.
#   - None                 : genuinely non-diagnostic (arbitrary number /
#                            unrelated grab) — carries no content or trap signal.
# The correct choice is ALWAYS None. CARS items are never listed here.
# Traps are rare in this recall-heavy bank (they need an execution/attractor
# landing, which mainly occurs on the numeric CP items) — conceptual "which/
# what/define" distractors are honest content confusions, not traps.
CHOICE_DIAGNOSIS: dict[str, list] = {
    # --- DEV science --------------------------------------------------------
    "q_dev_001": [  # GTP/ATP-producing TCA step (correct B: succinyl CoA→succinate)
        cg("thinks the isocitrate→α-ketoglutarate step (an oxidative "
           "decarboxylation yielding NADH+CO₂) performs substrate-level "
           "phosphorylation"),
        None,
        cg("thinks the fumarate→malate hydration step produces GTP/ATP"),
        cg("thinks the malate→oxaloacetate step (which yields NADH) produces "
           "GTP/ATP")],
    "q_dev_002": [  # high ADP effect (correct A: increases enzyme activity)
        None,
        cg("reverses the energy-charge signal — believes high ADP inhibits "
           "respiratory enzymes"),
        cg("thinks ADP is not an allosteric regulator of respiration"),
        None],  # 'slow the pathway' repeats B's reversal belief → non-diagnostic
    "q_dev_003": [  # false endergonic/exergonic statement (correct D)
        cg("believes it is false that endergonic reactions have +ΔG and "
           "exergonic −ΔG — misassigns the ΔG sign of spontaneity"),
        cg("believes it is false that endergonic reactions consume and "
           "exergonic release energy"),
        cg("believes exergonic reactions need no activation energy — thinks "
           "spontaneous means no energy barrier"),
        None],
    "q_dev_004": [  # judge relative activation energies (correct B: rates)
        cg("thinks a larger/more favorable ΔG means a faster reaction — "
           "confuses thermodynamic magnitude with rate"),
        None,
        cg("thinks the ideal environmental conditions reveal activation "
           "energy"),
        cg("thinks spontaneous reactions are necessarily fast — confuses "
           "spontaneity with kinetics")],
    "q_dev_005": [  # allosteric inhibitor (correct C)
        cg("describes an allosteric activator (increases affinity), not an "
           "inhibitor"),
        cg("describes competitive inhibition (binds the active site) rather "
           "than allosteric (binds elsewhere)"),
        None,
        cg("describes a substrate-mimic binding the active site, not an "
           "allosteric site")],
    "q_dev_006": [  # increase NH3→NH4+ conversion (correct B: add HCl)
        cg("thinks adding a base (NaOH) drives NH₃→NH₄⁺; NaOH consumes H⁺ and "
           "shifts the opposite way"),
        None,
        cg("adds NH₄Cl (the common-ion product), which shifts back toward "
           "NH₃ and lowers conversion"),
        cg("thinks adding more NH₃ raises the fraction converted to NH₄⁺")],
    "q_dev_007": [  # stronger conjugate base F- vs CN- (correct B: CN-)
        cg("picks F⁻ — reverses the inverse relation (HF is the stronger "
           "acid, so F⁻ is the weaker conjugate base)"),
        None,
        cg("thinks the two conjugate bases are equally strong, ignoring the "
           "difference in parent-acid strength"),
        cg("thinks conjugate bases of weak acids do not act as bases in "
           "water")],
    "q_dev_008": [  # oxidation site + e- flow (correct A: anode; cathode)
        None,
        cg("reverses electrode roles — puts oxidation at the cathode and "
           "electron flow toward the anode"),
        cg("thinks electrons flow toward the anode rather than to the "
           "cathode"),
        cg("thinks oxidation occurs at the cathode")],
    "q_dev_009": [  # +E°cell meaning (correct B: spontaneous, ΔG°<0)
        cg("reverses the sign relation — thinks +E°cell means nonspontaneous "
           "(ΔG°>0)"),
        None,
        cg("thinks a nonzero standard potential means the cell is at "
           "equilibrium (ΔG°=0)"),
        cg("thinks a spontaneous galvanic reaction needs an external power "
           "source (confuses it with electrolysis)")],
    "q_dev_010": [  # salt bridge function (correct B: maintain neutrality)
        cg("thinks the salt bridge carries electrons to the cathode "
           "(electrons travel through the external wire, not the bridge)"),
        None,
        None,  # 'increase voltage without limit' — implausible, non-diagnostic
        cg("thinks the salt bridge catalyzes the electrode reactions")],
    "q_dev_011": [  # buffer composition (correct B: weak acid + conj. base)
        cg("thinks a buffer is a strong acid plus a strong base"),
        None,
        cg("thinks a weak acid fully neutralized by strong base (equal moles) "
           "is a buffer, missing that excess weak acid is needed"),
        cg("thinks a neutral salt in pure water buffers pH")],
    "q_dev_012": [  # spontaneous at all T (correct A: ΔH<0, ΔS>0)
        None,
        cg("picks ΔH>0, ΔS<0 (never spontaneous) — the reversed sign "
           "combination"),
        cg("thinks ΔH<0, ΔS<0 is spontaneous at all T (it is only at low T)"),
        cg("thinks ΔH>0, ΔS>0 is spontaneous at all T (it is only at high T)")],
    "q_dev_013": [  # Gibbs relation (correct B: ΔG=ΔH−TΔS)
        cg("misremembers the Gibbs relation with +TΔS (wrong sign on the "
           "entropy term)"),
        None,
        cg("misremembers the Gibbs relation as TΔS−ΔH (terms rearranged, "
           "sign inverted)"),
        cg("thinks the entropy term is multiplied (ΔH×TΔS) rather than "
           "subtracted")],
    "q_dev_014": [  # spontaneous process (correct A: no continuous energy input)
        None,
        cg("thinks spontaneous means fast — conflates spontaneity with rate"),
        cg("thinks spontaneous means exothermic / always releases heat"),
        cg("thinks a spontaneous process always requires a catalyst")],
    "q_dev_015": [  # temperature raises rate (correct B: more collisions ≥ Ea)
        cg("thinks temperature raises ΔG and that this speeds the reaction"),
        None,
        cg("thinks raising temperature lowers the activation energy (only a "
           "catalyst lowers Ea)"),
        cg("thinks temperature makes the reaction more exothermic and that "
           "this raises the rate")],
    "q_dev_016": [  # catalyst mechanism (correct B: lower-Ea pathway)
        cg("thinks a catalyst works by raising the system temperature"),
        None,
        cg("thinks a catalyst makes the reaction more exothermic (changes "
           "ΔH)"),
        cg("thinks a catalyst shifts the equilibrium toward products (it "
           "speeds both directions, not the position)")],
    "q_dev_017": [  # what k depends on (correct B: temperature + catalyst)
        cg("thinks the rate constant k depends on reactant concentrations "
           "(those change rate, not k)"),
        None,
        None,  # 'container volume only' — implausible, non-diagnostic
        cg("thinks k changes as the reaction proceeds over time")],
    "q_dev_018": [  # continuity, narrowing pipe (correct A: speed increases)
        None,
        cg("reverses continuity — thinks narrowing the pipe slows the fluid"),
        cg("thinks speed is unchanged when the pipe narrows (ignores "
           "continuity)"),
        None],  # 'drops to zero' — implausible, non-diagnostic
    "q_dev_019": [  # Q=A·v constancy is from (correct B: continuity)
        cg("attributes constant flow rate to Bernoulli's principle rather "
           "than continuity/conservation of mass"),
        None,
        None,  # Pascal's principle — unrelated law grab
        None],  # Archimedes' principle — unrelated law grab
    "q_dev_020": [  # net glycolysis ATP (correct A: 2)
        None,
        trap("partial"),  # gross 4, forgot to subtract the 2 ATP invested
        cg("gives the total aerobic yield (~36) — conflates substrate-level "
           "glycolysis with full oxidative phosphorylation"),
        None],  # '0 ATP' — arbitrary
    "q_dev_021": [  # glycolysis location (correct B: cytoplasm)
        cg("thinks glycolysis occurs in the mitochondrial matrix (confuses it "
           "with the citric acid cycle)"),
        None,
        None,  # nucleus — unrelated organelle grab
        None],  # ER — unrelated organelle grab
    "q_dev_022": [  # glycolysis electron carrier (correct C: NADH)
        cg("thinks glycolysis produces FADH₂ (FADH₂ comes from the citric "
           "acid cycle)"),
        cg("confuses NADPH (anabolic / pentose-phosphate carrier) with the "
           "NADH glycolysis makes"),
        None,
        cg("thinks GTP is a reduced electron carrier (it is a nucleotide, not "
           "an electron carrier)")],
    "q_dev_023": [  # TCA acetyl acceptor regenerated (correct B: oxaloacetate)
        cg("names citrate (the first cycle product) rather than the "
           "regenerated acceptor oxaloacetate"),
        None,
        cg("names pyruvate (upstream of the cycle) as the acetyl acceptor"),
        cg("names acetyl-CoA — the group donated, not the acceptor that is "
           "regenerated")],
    "q_dev_024": [  # Vmax reached when (correct B: sites saturated)
        cg("thinks Vmax is reached at low substrate concentration (reverses "
           "the saturation relationship)"),
        None,
        cg("thinks a denatured enzyme reaches Vmax (denaturation abolishes "
           "activity)"),
        cg("thinks a competitive inhibitor's presence produces Vmax")],
    "q_dev_025": [  # membrane framework (correct B: phospholipid bilayer)
        cg("confuses the membrane's lipid framework with a cell-wall polymer "
           "(peptidoglycan is a bacterial cell wall)"),
        None,
        None,  # cellulose — repeats the cell-wall confusion (non-diagnostic)
        None],  # glycogen — unrelated storage-molecule grab
    "q_dev_026": [  # phospholipid head/tails (correct B: philic; phobic)
        cg("reverses amphipathic character — thinks the phosphate head is "
           "hydrophobic and the tails hydrophilic"),
        None,
        cg("thinks both head and tails are hydrophilic (misses the nonpolar "
           "tails)"),
        cg("thinks both head and tails are hydrophobic (misses the polar "
           "phosphate head)")],
    "q_dev_027": [  # semiconservative replication (correct B)
        cg("describes the conservative model (a daughter with two newly "
           "synthesized strands)"),
        None,
        cg("thinks both strands are parental — no new synthesis"),
        None],  # 'only RNA' — implausible grab
    "q_dev_028": [  # synthesizes DNA 5'→3' (correct B: DNA polymerase)
        cg("thinks helicase synthesizes DNA (helicase unwinds the helix)"),
        None,
        cg("thinks primase synthesizes the new strand (primase lays RNA "
           "primers)"),
        cg("thinks ligase synthesizes DNA (ligase joins fragments)")],
    "q_dev_029": [  # joins Okazaki fragments (correct C: ligase)
        cg("thinks helicase joins fragments (helicase unwinds DNA)"),
        cg("thinks primase joins fragments (primase makes RNA primers)"),
        None,
        cg("thinks polymerase seals the final nick (ligase forms that "
           "phosphodiester bond)")],
    "q_dev_030": [  # Aa×Aa phenotypic ratio (correct B: 3:1)
        cg("gives 1:1 (a testcross ratio) for a monohybrid heterozygote "
           "cross"),
        None,
        cg("gives the dihybrid 9:3:3:1 ratio for a single-gene cross"),
        cg("gives the genotypic ratio 1:2:1 instead of the phenotypic 3:1")],
    "q_dev_031": [  # genotype/phenotype definitions (correct B)
        cg("swaps the definitions of genotype and phenotype"),
        None,
        None,  # allele; gene — unrelated term-pair grab
        None],  # gamete; zygote — unrelated term-pair grab
    "q_dev_032": [  # three memory processes (correct B: encode/store/retrieve)
        None,  # sensation/perception/cognition — unrelated triad grab
        None,
        None,  # input/output/feedback — unrelated triad grab
        cg("gives conditioning terms (acquisition, extinction, recovery) as "
           "memory processes — confuses learning stages with memory stages")],
    "q_dev_033": [  # STM capacity (correct A: 7±2)
        None,
        cg("thinks short-term/working memory is essentially unlimited "
           "(confuses it with long-term capacity)"),
        None,  # '1 item' — arbitrary
        None],  # '~100 items' — arbitrary
    "q_dev_034": [  # maintenance by repetition (correct B: rehearsal)
        cg("confuses chunking (grouping items) with rehearsal (repetition)"),
        None,
        cg("confuses retrieval (getting info out) with rehearsal (maintaining "
           "it)"),
        None],  # 'encoding failure' — unrelated grab
    "q_dev_035": [  # food = which stimulus (correct B: US)
        cg("labels the natural (unlearned) stimulus as the conditioned "
           "stimulus — reverses learned vs innate"),
        None,
        cg("labels a stimulus as a response (confuses the US with the "
           "conditioned response)"),
        cg("calls the food a neutral stimulus (food innately elicits "
           "salivation)")],
    "q_dev_036": [  # reinforcer definition (correct B: increases behavior)
        cg("thinks a reinforcer decreases behavior (confuses reinforcement "
           "with punishment)"),
        None,
        None,  # 'no effect' — implausible grab
        cg("equates reinforcement with physical punishment")],
    "q_dev_037": [  # classical extinction (correct A: CS without US)
        None,
        cg("thinks introducing a new US causes extinction"),
        None,  # 'reinforcer doubled' — mixes an operant term in; non-diagnostic
        cg("thinks the conditioned response becomes permanent (opposite of "
           "extinction)")],
    "q_dev_038": [  # attribute others to traits (correct B: FAE)
        cg("confuses the self-serving bias (protecting one's own esteem) with "
           "the fundamental attribution error"),
        None,
        cg("confuses the just-world hypothesis with the fundamental "
           "attribution error"),
        None],  # bystander effect — unrelated social concept grab
    "q_dev_039": [  # align with group standard (correct B: conformity)
        cg("confuses obedience (following authority) with conformity "
           "(matching group norms)"),
        None,
        None,  # aggression — unrelated grab
        cg("confuses persuasion (attitude change via argument) with "
           "conformity")],
    "q_dev_040": [  # health disparities (correct B: preventable, social)
        cg("thinks health disparities are random with no social pattern"),
        None,
        cg("attributes health disparities solely to genetics, ignoring "
           "social determinants"),
        None],  # 'cannot be measured' — implausible grab
    "q_dev_041": [  # social determinant example (correct B: education/income)
        cg("mistakes an inherited biological trait (blood type) for a social "
           "determinant of health"),
        None,
        None,  # genetic mutation — repeats the biological-vs-social confusion
        None],  # eye color — repeats the biological-vs-social confusion
    "q_dev_042": [  # Pascal's principle (correct A: transmitted undiminished)
        None,
        None,  # 'lost as heat' — implausible grab
        cg("thinks applied pressure is proportional to fluid temperature "
           "(confuses Pascal's principle with thermal/gas behavior)"),
        None],  # 'zero at the bottom' — implausible grab
    "q_dev_043": [  # cognitive dissonance (correct A: conflicting attitudes)
        None,
        cg("thinks dissonance arises from being rewarded (confuses it with "
           "reinforcement)"),
        None,  # 'neutral stimulus repeated' — classical-conditioning grab
        cg("thinks dissonance comes from group consensus (confuses it with "
           "conformity/groupthink)")],
    "q_dev_044": [  # codominance (correct B: both alleles fully expressed)
        cg("confuses codominance with incomplete dominance (an intermediate "
           "blend)"),
        None,
        cg("describes complete dominance (only the dominant allele shows), "
           "not codominance"),
        None],  # 'always nonviable' — implausible grab

    # --- HELD_OUT science ---------------------------------------------------
    "q_ho_001": [  # reducing agent for Zn+Cu²⁺ (correct A: Zn)
        None,
        cg("names the oxidizing agent (Cu²⁺, which is reduced) as the "
           "reducing agent — reverses the roles"),
        cg("names the product Zn²⁺ (already oxidized) as the reducing agent"),
        cg("names Cu(s) (the product of reduction) as the reducing agent")],
    "q_ho_002": [  # Nernst: more product ions → Ecell (correct B: decrease)
        cg("wrong direction — thinks raising product-ion concentration "
           "increases Ecell"),
        None,
        cg("thinks ion concentrations don't affect Ecell (ignores the Nernst "
           "dependence)"),
        cg("thinks changing concentration reverses the sign of E° (confuses "
           "Ecell with the fixed standard E°)")],
    "q_ho_003": [  # electrolysis vs galvanic (correct B: drives nonspontaneous)
        cg("describes a galvanic cell (energy from a spontaneous reaction) — "
           "reverses electrolysis"),
        None,
        cg("thinks electrolysis does not involve oxidation–reduction"),
        cg("thinks electrolysis has a positive E°cell (it drives "
           "nonspontaneous, negative-E° reactions)")],
    "q_ho_004": [  # reduction occurs at (correct B: cathode)
        cg("thinks reduction occurs at the anode (reverses the electrode "
           "definitions)"),
        None,
        None,  # salt bridge — not an electrode; grab
        None],  # electrolyte — not an electrode; grab
    "q_ho_005": [  # pH of 0.010 M HCl (correct A: 2.0)
        None,
        trap("scaling"),  # used 0.10 M (off by one power of ten) → pH 1.0
        cg("reports pOH (14−pH=12.0) — treats the strong acid as if computing "
           "the basic scale"),
        cg("reports the concentration (0.010) as the pH — omits taking "
           "−log[H⁺]")],
    "q_ho_006": [  # conjugate acid–base pair (correct B: H₂CO₃/HCO₃⁻)
        cg("thinks a strong acid + strong base (HCl/NaOH) are a conjugate "
           "pair (they are not related by one H⁺)"),
        None,
        cg("thinks H₃O⁺ and O²⁻ are a conjugate pair (they differ by more "
           "than one proton)"),
        cg("pairs an acid with an unrelated anion (CH₃COOH/Cl⁻ are not "
           "conjugates)")],
    "q_ho_007": [  # neutral-water [H⁺] (correct A: 1e-7)
        None,
        cg("uses Kw (10⁻¹⁴) itself as [H⁺] rather than its square root"),
        None,  # '1.0 M' — arbitrary
        cg("thinks neutral water has zero H⁺ (no autoionization)")],
    "q_ho_008": [  # pH 4 vs pH 6 acidity ratio (correct C: 100)
        cg("treats the pH scale as linear — takes the difference (6−4=2) "
           "instead of 10^Δ"),
        trap("scaling"),  # used one pH unit (10¹) instead of two (10²)
        None,
        None],  # '1000' (10³) — arbitrary over-count
    "q_ho_009": [  # ΔH>0, ΔS>0 spontaneous when (correct A: high T)
        None,
        cg("reverses the temperature dependence — thinks ΔH>0,ΔS>0 is "
           "spontaneous at low T"),
        cg("thinks ΔH>0,ΔS>0 is spontaneous at all temperatures"),
        cg("thinks ΔH>0,ΔS>0 is never spontaneous (ignores that TΔS overtakes "
           "ΔH at high T)")],
    "q_ho_010": [  # negative ΔG indicates (correct A: spontaneous)
        None,
        cg("thinks negative ΔG means the reaction is fast (confuses "
           "spontaneity with rate)"),
        cg("thinks negative ΔG means endothermic (confuses the free-energy "
           "sign with enthalpy)"),
        cg("thinks negative ΔG means at equilibrium (equilibrium is ΔG=0)")],
    "q_ho_011": [  # ΔG at equilibrium (correct A: 0)
        None,
        cg("thinks ΔG is large and negative at equilibrium (confuses "
           "spontaneity with the equilibrium condition)"),
        cg("thinks ΔG is large and positive at equilibrium"),
        cg("thinks ΔG always equals ΔG° (they are equal only at standard "
           "conditions)")],
    "q_ho_012": [  # entropy is (correct B: dispersal/disorder)
        cg("confuses entropy with the total energy of the system"),
        None,
        None,  # 'reaction rate' — unrelated grab
        None],  # 'activation energy' — unrelated grab
    "q_ho_013": [  # overall order of k[A][B]² (correct C: 3)
        trap("partial"),  # took only [A]'s order (1); didn't sum the exponents
        cg("reports the largest single exponent (2, the order in B) as the "
           "overall order — doesn't know overall order is the sum"),
        None,
        None],  # '0' — arbitrary
    "q_ho_014": [  # first order in A, double [A] (correct A: ×2)
        None,
        trap("scaling"),  # applied 2² (squared) despite the stated first order
        cg("thinks changing concentration doesn't change the rate (zero-order "
           "reasoning despite the stated first order)"),
        trap("inverse")],  # took the reciprocal of the factor (0.5×)
    "q_ho_015": [  # zero-order rate (correct B: independent of conc.)
        cg("thinks a zero-order rate is proportional to [A] (that is first "
           "order)"),
        None,
        cg("thinks a zero-order rate is proportional to [A]² (that is second "
           "order)"),
        cg("thinks 'zero order' means the rate is literally zero (misreads "
           "the order as the rate value)")],
    "q_ho_016": [  # activation energy is (correct B: min energy to react)
        cg("confuses activation energy with the products−reactants energy "
           "difference (ΔH/ΔG)"),
        None,
        cg("thinks activation energy equals ΔG"),
        cg("thinks raising temperature lowers Ea (temperature raises the "
           "fraction of molecules with ≥Ea, not Ea itself)")],
    "q_ho_017": [  # Bernoulli: higher speed → pressure (correct B: lower)
        cg("reverses Bernoulli — thinks faster flow means higher pressure"),
        None,
        cg("thinks fluid speed does not affect pressure"),
        None],  # 'zero' — implausible grab
    "q_ho_018": [  # object floats when buoyant force = (correct A: its weight)
        None,
        None,  # 'zero' — implausible grab
        cg("thinks the buoyant force equals the entire weight of the fluid, "
           "not the weight of displaced fluid"),
        cg("confuses buoyant force with atmospheric pressure")],
    "q_ho_019": [  # aerobic end product of glycolysis (correct A: 2 pyruvate)
        None,
        cg("gives lactate — the anaerobic fermentation product — under "
           "aerobic conditions"),
        cg("thinks glycolysis directly yields acetyl-CoA (pyruvate becomes "
           "acetyl-CoA only after entering the mitochondrion)"),
        cg("gives ethanol — a yeast fermentation product — for human aerobic "
           "glycolysis")],
    "q_ho_020": [  # committed rate-limiting step (correct B: PFK-1)
        cg("names hexokinase (the first step) as the committed rate-limiting "
           "step"),
        None,
        cg("names pyruvate kinase (the last step) as the rate-limiting step"),
        None],  # aldolase — a glycolytic-enzyme grab, not a regulatory step
    "q_ho_021": [  # ATP consumed in investment phase (correct A: 2)
        None,
        cg("confuses the 4 ATP produced in the payoff phase with the 2 "
           "consumed in the investment phase"),
        None,  # '0' — arbitrary
        None],  # '6' — arbitrary
    "q_ho_022": [  # anaerobic muscle: pyruvate → (correct B: lactate)
        cg("gives ethanol (yeast fermentation) for human muscle anaerobic "
           "metabolism"),
        None,
        cg("thinks pyruvate → acetyl-CoA (the aerobic pathway) regenerates "
           "NAD⁺ anaerobically"),
        None],  # citrate — TCA-intermediate grab
    "q_ho_023": [  # CO₂ released per TCA turn (correct B: 2)
        cg("thinks only one CO₂ is released per turn"),
        None,
        cg("thinks three CO₂ are released per turn"),
        None],  # '0' — arbitrary
    "q_ho_024": [  # most cycle energy captured as (correct B: NADH/FADH₂)
        cg("thinks the cycle captures most energy as ATP directly (it makes "
           "mostly reduced carriers)"),
        None,
        None,  # 'heat' — grab
        cg("thinks GTP is the main energy product (only 1 GTP/turn; most "
           "energy is in NADH/FADH₂)")],
    "q_ho_025": [  # NADH per acetyl-CoA (correct C: 3) — count near-misses
        None,  # '1' — non-diagnostic count near-miss
        None,  # '2' — non-diagnostic count near-miss
        None,
        None],  # '4' — non-diagnostic count near-miss
    "q_ho_026": [  # active site (correct B)
        cg("confuses the allosteric (regulatory) site with the active "
           "(catalytic) site"),
        None,
        None,  # 'R group' — grab
        None],  # 'peptide backbone' — grab
    "q_ho_027": [  # induced-fit model (correct B: active site reshapes)
        cg("thinks the enzyme is consumed in the reaction (enzymes are "
           "catalysts, not consumed)"),
        None,
        cg("thinks the substrate is left chemically unchanged (it is "
           "converted to product)"),
        cg("thinks enzymes increase activation energy (they lower it)")],
    "q_ho_028": [  # heat above optimum (correct B: denatures)
        cg("thinks higher temperature always increases enzyme activity "
           "without limit (ignores denaturation)"),
        None,
        None,  # 'no effect' — implausible grab
        None],  # 'lowers only the Km' — grab
    "q_ho_029": [  # simple diffusion of nonpolar molecule (correct B)
        cg("thinks simple diffusion requires ATP (confuses it with active "
           "transport)"),
        None,
        cg("thinks simple diffusion needs a transport protein (that is "
           "facilitated diffusion)"),
        cg("thinks simple diffusion moves molecules against their gradient")],
    "q_ho_030": [  # against-gradient + energy (correct C: active transport)
        cg("thinks simple diffusion moves solutes against their gradient"),
        cg("thinks facilitated diffusion moves solutes against their gradient "
           "(it is passive, down-gradient)"),
        None,
        cg("thinks osmosis (water movement) is the energy-requiring solute "
           "transport")],
    "q_ho_031": [  # cholesterol function (correct B: modulate fluidity)
        None,  # 'store genetic information' — implausible grab
        None,
        None,  # 'catalyze glycolysis' — implausible grab
        cg("thinks cholesterol forms the hydrophilic head groups (it sits "
           "among the tails, modulating fluidity)")],
    "q_ho_032": [  # osmosis is diffusion of (correct B: water)
        cg("thinks osmosis is the diffusion of solutes rather than water"),
        None,
        None,  # 'proteins' — grab
        cg("thinks osmosis is the diffusion of ions specifically")],
    "q_ho_033": [  # base pairing (correct A: thymine; cytosine)
        None,
        cg("swaps the pairing partners (A–C, G–T)"),
        cg("uses uracil (RNA) for adenine's partner and mispairs guanine — "
           "RNA/DNA base confusion"),
        cg("pairs guanine with adenine (two purines) — violates purine–"
           "pyrimidine pairing")],
    "q_ho_034": [  # unwinds helix at fork (correct B: helicase)
        cg("thinks ligase unwinds the helix (ligase seals nicks)"),
        None,
        cg("thinks polymerase unwinds the helix (polymerase synthesizes "
           "DNA)"),
        cg("thinks primase unwinds the helix (primase makes RNA primers)")],
    "q_ho_035": [  # Okazaki fragments on which strand (correct B: lagging)
        cg("thinks Okazaki fragments form on the leading strand"),
        None,
        None,  # 'template-only' — grab
        None],  # 'RNA' — grab
    "q_ho_036": [  # DNA strands are (correct B: antiparallel/complementary)
        cg("thinks the two strands are identical and parallel (they are "
           "complementary and antiparallel)"),
        None,
        None,  # 'both RNA' — grab
        cg("thinks the bases are joined by covalent bonds (they pair via "
           "hydrogen bonds)")],
    "q_ho_037": [  # Aa×Aa genotypic ratio (correct A: 1:2:1)
        None,
        cg("gives the phenotypic ratio 3:1 instead of the genotypic 1:2:1"),
        cg("gives a 1:1 ratio (testcross) for a heterozygote × heterozygote "
           "cross"),
        cg("thinks all offspring are heterozygous Aa (ignores segregation "
           "into AA and aa)")],
    "q_ho_038": [  # law of segregation (correct B: alleles separate)
        cg("confuses the law of segregation with the law of independent "
           "assortment"),
        None,
        cg("thinks dominant alleles are always more common (dominance ≠ "
           "frequency)"),
        cg("endorses blending inheritance (Mendel's work refuted blending)")],
    "q_ho_039": [  # testcross partner (correct B: homozygous recessive)
        cg("thinks a testcross uses a homozygous dominant partner (which "
           "would mask recessive alleles)"),
        None,
        cg("thinks a testcross uses a heterozygous partner"),
        None],  # 'haploid' — grab
    "q_ho_040": [  # genes far apart on same chromosome (correct B)
        cg("thinks genes on the same chromosome are always inherited together "
           "(ignores crossing over)"),
        None,
        cg("thinks genes far apart never recombine (they recombine "
           "frequently)"),
        cg("misreads the premise — treats same-chromosome genes as being on "
           "different chromosomes")],
    "q_ho_041": [  # permanent unlimited store (correct C: long-term memory)
        cg("confuses sensory memory (brief, fleeting) with the permanent "
           "long-term store"),
        cg("confuses short-term memory (limited, seconds) with the permanent "
           "long-term store"),
        None,
        None],  # 'iconic memory' — a sensory-memory subtype; repeats A's error
    "q_ho_042": [  # context-dependent memory (correct B)
        cg("confuses the misinformation effect (memory distortion) with "
           "context-dependent retrieval"),
        None,
        cg("confuses proactive interference (old memories disrupting new) "
           "with context matching"),
        cg("confuses the self-reference effect (better memory for "
           "self-relevant info) with context-dependent memory")],
    "q_ho_043": [  # first/last items best (correct B: serial position)
        cg("confuses the spacing effect (distributed practice) with the "
           "serial position effect"),
        None,
        None,  # 'misinformation effect' — unrelated grab
        cg("confuses priming (implicit activation) with the serial position "
           "effect")],
    "q_ho_044": [  # explicit memory includes (correct B: facts/events)
        cg("classifies a motor skill (riding a bike) as explicit memory (it "
           "is implicit/procedural)"),
        None,
        cg("classifies conditioned reflexes as explicit memory (they are "
           "implicit)"),
        None],  # 'motor skills' — repeats the procedural-vs-explicit error
    "q_ho_045": [  # neutral→elicits response (correct B: conditioned stimulus)
        cg("calls the learned (conditioned) stimulus the unconditioned "
           "stimulus — reverses learned vs innate"),
        None,
        cg("labels a stimulus as a response (confuses the CS with the "
           "unconditioned response)"),
        cg("uses the operant term 'reinforcer' for a classical-conditioning "
           "stimulus")],
    "q_ho_046": [  # negative reinforcement (correct B: increases; removing)
        cg("thinks negative reinforcement decreases behavior by adding a "
           "stimulus (describes positive punishment)"),
        None,
        cg("thinks negative reinforcement decreases behavior (confuses "
           "reinforcement with punishment)"),
        cg("thinks negative reinforcement adds a stimulus (describes positive "
           "reinforcement)")],
    "q_ho_047": [  # unpredictable # responses (correct B: variable-ratio)
        cg("confuses fixed-ratio (predictable count) with variable-ratio "
           "(unpredictable count)"),
        None,
        cg("confuses fixed-interval (time-based) with variable-ratio "
           "(response-based)"),
        cg("confuses continuous reinforcement (every response) with a "
           "variable-ratio schedule")],
    "q_ho_048": [  # Milgram (correct B: obedience to authority)
        cg("confuses conformity (matching peers) with obedience (following an "
           "authority's orders)"),
        None,
        None,  # bystander effect — unrelated grab
        cg("confuses groupthink (consensus-seeking) with obedience to "
           "authority")],
    "q_ho_049": [  # bystander effect (correct B: decreases helping)
        cg("reverses the bystander effect — thinks more onlookers increase "
           "helping"),
        None,
        cg("thinks the number of bystanders has no effect on helping"),
        None],  # 'guarantees' — implausible grab
    "q_ho_050": [  # attitude defined as (correct B: an evaluation)
        cg("thinks an attitude is a fixed genetic trait (attitudes are "
           "learned evaluations)"),
        None,
        cg("confuses an attitude with an involuntary reflex"),
        None],  # 'type of long-term memory' — grab
    "q_ho_051": [  # SES measured by (correct B: occupation) — grabs
        None,  # blood type — arbitrary biological grab
        None,
        None,  # height — arbitrary grab
        None],  # personality type — grab
    "q_ho_052": [  # social gradient means (correct A)
        None,
        cg("denies any relationship between social position and health"),
        cg("threshold misconception — thinks only the very poorest have worse "
           "health, missing the stepwise gradient"),
        cg("thinks wealth directly causes disease (misreads the gradient's "
           "causality)")],
    "q_ho_059": [  # pascal (Pa) equals (correct A: N/m²)
        None,
        cg("gives units of force (kg·m/s² = N), not pressure (force per "
           "area)"),
        None,  # 'J·s' — unrelated (action) units grab
        cg("gives N·m (energy/torque) instead of N/m² for pressure")],
}


def _attach_choice_diagnosis(item: dict) -> None:
    """Attach a bulk-authored content-axis choice_diagnosis by id.

    q_syn_* items author it inline; this covers the DEV/HELD_OUT science bank.
    CARS is never tagged. Fails loudly on length or correct-index mismatch so a
    positional id miscount can't silently mis-tag a question.
    """
    cd = CHOICE_DIAGNOSIS.get(item["id"])
    if cd is None:
        return
    assert item["section"] != "CARS", f"{item['id']}: CARS must not carry choice_diagnosis"
    assert len(cd) == len(item["choices"]), f"{item['id']}: choice_diagnosis length mismatch"
    correct_idx = LETTERS.index(item["correct"])
    assert cd[correct_idx] is None, f"{item['id']}: correct index choice_diagnosis must be None"
    item["choice_diagnosis"] = cd


def main() -> None:
    out = []
    for i, item in enumerate(DEV, 1):
        item["id"] = f"q_dev_{i:03d}"
        _attach_choice_diagnosis(item)
        out.append(item)
    for i, item in enumerate(HELD_OUT, 1):
        item["id"] = f"q_ho_{i:03d}"
        _attach_choice_diagnosis(item)
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

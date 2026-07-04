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

    # ======================================================================
    # §7d PARAPHRASE-GAP INSTRUMENT — reworded held_out probes (q_ho_061+)
    # Each item is the fresh, held_out second stem of an anchor-concept pair
    # authored for data/paraphrase-test.json. It tests the SAME idea as an
    # existing dev/held_out question in genuinely different wording (never a
    # numeric clone) so we can compare flashcard recall against accuracy on
    # reworded questions. Kept held_out so a volunteer has not seen them in a
    # dev performance session. See docs/PARAPHRASE-TEST.md.
    # ======================================================================

    # ---- cp_acids_bases (q_ho_061..071) -----------------------------------
    q("cp_acids_bases", "2",
      "In the reaction NH₃ + H₂O ⇌ NH₄⁺ + OH⁻, which species acts as the "
      "Brønsted–Lowry acid (the proton donor)?",
      ["H₂O", "NH₃", "NH₄⁺", "OH⁻"], 0,
      "Ch. 14.1 Brønsted-Lowry Acids and Bases", "held_out"),
    q("cp_acids_bases", "2",
      "A Brønsted–Lowry base is best defined as a substance that:",
      ["donates a proton (H⁺) to another species",
       "accepts a proton (H⁺) from another species",
       "increases the H⁺ concentration of a solution",
       "produces OH⁻ only by dissociating in water"], 1,
      "Ch. 14.1 Brønsted-Lowry Acids and Bases", "held_out"),
    q("cp_acids_bases", "2",
      "Hydrochloric acid (HCl) is a very strong acid. Its conjugate base, "
      "Cl⁻, is therefore:",
      ["an extremely weak base that barely accepts protons",
       "a strong base that readily accepts protons",
       "a strong acid itself",
       "amphoteric, acting equally as an acid and a base"], 0,
      "Ch. 14.3 Relative Strengths of Acids and Bases", "held_out"),
    q("cp_acids_bases", "2",
      "Which of the following mixtures would function as an effective pH "
      "buffer?",
      ["HCl and NaCl (a strong acid and its salt)",
       "CH₃COOH and CH₃COONa (acetic acid and sodium acetate)",
       "NaOH and NaCl (a strong base and a neutral salt)",
       "NaCl dissolved in water alone"], 1,
      "Ch. 14.6 Buffers", "held_out", demand="application"),
    q("cp_acids_bases", "2",
      "At 25 °C, pure water self-ionizes so that [H⁺] and [OH⁻] are equal. "
      "What is the pH of this neutral water?",
      ["0", "7", "14", "It depends on how much water is present"], 1,
      "Ch. 14.2 pH and pOH", "held_out"),
    q("cp_acids_bases", "2",
      "A strong monoprotic acid is dissolved in water to a concentration of "
      "1.0×10⁻³ M and ionizes completely. What is the pH of the solution at "
      "25 °C?",
      ["1", "2", "3", "11"], 2,
      "Ch. 14.2 pH and pOH", "held_out", demand="application"),
    q("cp_acids_bases", "2",
      "What is the conjugate base of the bicarbonate ion, HCO₃⁻?",
      ["H₂CO₃", "CO₃²⁻", "CO₂", "OH⁻"], 1,
      "Ch. 14.1 Brønsted-Lowry Acids and Bases", "held_out", demand="application"),
    q("cp_acids_bases", "2",
      "If the hydrogen-ion concentration [H⁺] of a solution increases by a "
      "factor of 1000, how does its pH change?",
      ["it decreases by 3 units", "it increases by 3 units",
       "it decreases by 1000 units", "it does not change"], 0,
      "Ch. 14.2 pH and pOH", "held_out", demand="application"),
    q("cp_acids_bases", "2",
      "For a weak-acid buffer, when the concentration of the conjugate base "
      "equals the concentration of the weak acid, the pH of the buffer is:",
      ["equal to the acid's pKa", "equal to 7 regardless of the acid",
       "one unit above the pKa", "equal to 14 − pKa"], 0,
      "Ch. 14.6 Buffers (Henderson–Hasselbalch)", "held_out",
      demand="application"),
    q("cp_acids_bases", "2",
      "A student adds sodium formate (HCOONa) to a solution of formic acid "
      "(HCOOH). What happens to the percent ionization of the formic acid?",
      ["it decreases, because added formate shifts the ionization "
       "equilibrium toward the un-ionized acid",
       "it increases, because more ions are now present",
       "it is unchanged, because formate does not take part in the "
       "equilibrium",
       "it increases, because the solution becomes more acidic"], 0,
      "Ch. 14.6 Buffers; Le Chatelier (common-ion effect)", "held_out",
      demand="application"),
    q("cp_acids_bases", "2",
      "Two solutions are prepared at the same concentration: one of a strong "
      "acid and one of a weak acid. Compared with the strong-acid solution, "
      "the weak-acid solution will have:",
      ["a lower pH, because weak acids ionize completely",
       "a higher pH, because the weak acid ionizes only partially",
       "exactly the same pH, because the concentrations are equal",
       "a higher pH, because weak acids do not ionize at all"], 1,
      "Ch. 14.3 Relative Strengths of Acids and Bases", "held_out",
      demand="application"),

    # ---- bb_enzymes (q_ho_072..082) ---------------------------------------
    q("bb_enzymes", "2",
      "An enzyme increases the rate of a biochemical reaction primarily by:",
      ["lowering the activation energy of the reaction",
       "making the reaction more exergonic (more negative ΔG)",
       "raising the temperature of the cell",
       "shifting the reaction's equilibrium toward products"], 0,
      "Ch. 6.5 Enzymes", "held_out", demand="application"),
    q("bb_enzymes", "2",
      "A reaction that has a positive Gibbs free energy change (ΔG > 0) is "
      "best described as:",
      ["exergonic and energy-releasing",
       "endergonic and energy-requiring",
       "spontaneous under standard conditions",
       "impossible under any conditions"], 1,
      "Ch. 6.3 The Laws of Thermodynamics; Ch. 6.5 Enzymes", "held_out"),
    q("bb_enzymes", "2",
      "A competitive inhibitor decreases enzyme activity by:",
      ["binding directly in the active site and blocking substrate access",
       "binding at a site away from the active site and changing the "
       "enzyme's shape",
       "permanently destroying the enzyme by forming covalent bonds",
       "lowering the temperature of the reaction"], 0,
      "Ch. 6.5 Enzymes (inhibition)", "held_out"),
    q("bb_enzymes", "2",
      "As substrate concentration becomes very high, the rate of an "
      "enzyme-catalyzed reaction levels off at a maximum value (Vmax). This "
      "plateau occurs because:",
      ["the enzyme's active sites become saturated with substrate",
       "the substrate begins to inhibit the enzyme",
       "the enzyme is used up (consumed) by the reaction",
       "the activation energy increases at high substrate levels"], 0,
      "Ch. 6.5 Enzymes (Michaelis–Menten; saturation)", "held_out",
      demand="application"),
    q("bb_enzymes", "2",
      "A mutation alters an amino acid in the exact pocket where an enzyme's "
      "substrate normally binds and is converted to product. Which part of "
      "the enzyme has been changed?",
      ["the active site", "an allosteric (regulatory) site",
       "a disulfide bridge far from catalysis", "the signal peptide"], 0,
      "Ch. 6.5 Enzymes (active site)", "held_out", demand="application"),
    q("bb_enzymes", "2",
      "The induced-fit model of enzyme action differs from the older "
      "lock-and-key model in that it proposes:",
      ["the enzyme's active site changes shape as the substrate binds",
       "the substrate must match the active site perfectly and rigidly "
       "beforehand",
       "enzymes bind substrate without any physical contact",
       "the substrate permanently alters the enzyme's primary sequence"], 0,
      "Ch. 6.5 Enzymes (induced fit)", "held_out"),
    q("bb_enzymes", "2",
      "A solution of an enzyme is heated to a temperature far above the "
      "enzyme's optimum. The most likely result is that the enzyme's "
      "catalytic activity will:",
      ["drop sharply as the enzyme denatures and loses its "
       "three-dimensional shape",
       "keep rising indefinitely because higher temperature always speeds "
       "reactions",
       "stay exactly constant, since temperature does not affect enzymes",
       "increase because denaturation exposes more active sites"], 0,
      "Ch. 6.5 Enzymes (temperature, denaturation)", "held_out",
      demand="application"),
    q("bb_enzymes", "2",
      "The reduced activity caused by a competitive inhibitor can be "
      "reversed by:",
      ["adding a large excess of substrate",
       "removing all substrate from the solution",
       "lowering the enzyme concentration",
       "adding still more of the competitive inhibitor"], 0,
      "Ch. 6.5 Enzymes (competitive inhibition)", "held_out",
      demand="application"),
    q("bb_enzymes", "2",
      "Adding a reversible inhibitor slows an enzyme-catalyzed reaction. "
      "Does the inhibitor change the reaction's equilibrium constant (Keq)?",
      ["No — it changes the reaction's rate (kinetics) but not its "
       "equilibrium or ΔG",
       "Yes — slowing the reaction lowers its Keq",
       "Yes — it makes the products less thermodynamically stable",
       "Only at very high substrate concentrations"], 0,
      "Ch. 6.5 Enzymes; Ch. 6.3 (ΔG / equilibrium)", "held_out",
      demand="application"),
    q("bb_enzymes", "2",
      "The Michaelis constant (Km) of an enzyme is defined as the substrate "
      "concentration at which the reaction rate is:",
      ["equal to half of Vmax", "equal to Vmax", "zero",
       "at its absolute maximum"], 0,
      "Ch. 6.5 Enzymes (Km, Michaelis–Menten)", "held_out"),
    q("bb_enzymes", "2",
      "Enzyme X and enzyme Y act on the same substrate, but enzyme X has a "
      "much higher Km. Compared with enzyme Y, enzyme X:",
      ["binds the substrate less tightly (has lower affinity)",
       "binds the substrate more tightly (has higher affinity)",
       "must have a higher Vmax by definition",
       "is fully saturated at a lower substrate concentration"], 0,
      "Ch. 6.5 Enzymes (Km and affinity)", "held_out", demand="application"),

    # ---- cp_kinetics (q_ho_083..090) --------------------------------------
    q("cp_kinetics", "2",
      "A catalyst is added to a reaction mixture that has already reached "
      "equilibrium. What effect does it have?",
      ["it speeds the forward and reverse reactions equally, leaving the "
       "equilibrium position unchanged",
       "it shifts the equilibrium toward the products",
       "it shifts the equilibrium toward the reactants",
       "it increases the amount of product present at equilibrium"], 0,
      "Ch. 12.7 Catalysis", "held_out", demand="application"),
    q("cp_kinetics", "2",
      "Raising the temperature of a reaction usually increases its rate "
      "markedly. The main reason is that at higher temperature:",
      ["a larger fraction of molecular collisions have energy greater than "
       "the activation energy",
       "the activation energy of the reaction decreases",
       "the ΔG of the reaction becomes more negative",
       "the reactant molecules become larger"], 0,
      "Ch. 12.5 Collision Theory", "held_out", demand="application"),
    q("cp_kinetics", "2",
      "Which of the following changes would alter the numerical value of a "
      "reaction's rate constant, k?",
      ["increasing the temperature",
       "increasing the concentration of a reactant",
       "increasing the volume of the container",
       "increasing the total pressure at constant temperature"], 0,
      "Ch. 12.5 Collision Theory; Ch. 12.4 Rate Laws", "held_out",
      demand="application"),
    q("cp_kinetics", "2",
      "A reaction follows the rate law rate = k[X]²[Y]. What is its overall "
      "reaction order?",
      ["1", "2", "3", "0"], 2,
      "Ch. 12.3 Rate Laws", "held_out", demand="application"),
    q("cp_kinetics", "2",
      "A reaction is first order with respect to reactant A. If the "
      "concentration of A is tripled (with everything else held constant), "
      "the reaction rate will:",
      ["triple (increase by a factor of 3)",
       "double (increase by a factor of 2)",
       "increase by a factor of 9", "stay the same"], 0,
      "Ch. 12.3 Rate Laws (order and rate)", "held_out",
      demand="application"),
    q("cp_kinetics", "2",
      "For a reaction that is zero order in reactant A, doubling the "
      "concentration of A will:",
      ["have no effect on the reaction rate", "double the reaction rate",
       "quadruple the reaction rate", "halve the reaction rate"], 0,
      "Ch. 12.4 Integrated Rate Laws (zero order)", "held_out",
      demand="application"),
    q("cp_kinetics", "2",
      "In a chemical reaction, the minimum energy that colliding reactant "
      "molecules must possess in order to react is called the:",
      ["activation energy", "free energy (ΔG)",
       "bond dissociation enthalpy", "heat of reaction (ΔH)"], 0,
      "Ch. 12.5 Collision Theory (activation energy)", "held_out"),
    q("cp_kinetics", "2",
      "In the rate law rate = k[A]^m[B]^n, the exponent m represents:",
      ["the order of the reaction with respect to A",
       "the number of moles of A in the balanced equation",
       "the rate constant for A",
       "the concentration of A at equilibrium"], 0,
      "Ch. 12.3 Rate Laws", "held_out", demand="application"),
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

    # --- §7d paraphrase-gap probes (q_ho_061..090) -------------------------
    "q_ho_061": [  # BL acid in NH₃+H₂O (correct A: H₂O)
        None,
        cg("identifies NH₃ as the acid; NH₃ accepts the proton, so it is the "
           "Brønsted–Lowry base here"),
        cg("names the conjugate acid NH₄⁺ (a product), not the reactant that "
           "donated the proton"),
        cg("names OH⁻, the conjugate base of water, rather than the proton "
           "donor")],
    "q_ho_062": [  # define BL base (correct B: accepts H⁺)
        cg("gives the definition of a Brønsted–Lowry acid (proton donor), the "
           "exact opposite of a base"),
        None,
        cg("describes the effect of adding an acid, not the definition of a "
           "base"),
        cg("restricts bases to the narrower Arrhenius (OH⁻-producing) "
           "definition rather than the broader proton-acceptor definition")],
    "q_ho_063": [  # conjugate base of strong acid (correct A: very weak base)
        None,
        cg("reverses the inverse relationship — thinks a strong acid yields a "
           "strong conjugate base"),
        cg("confuses the conjugate base with an acid; Cl⁻ has no proton to "
           "donate"),
        cg("treats Cl⁻ as amphoteric, ignoring that a strong acid's conjugate "
           "base is essentially inert")],
    "q_ho_064": [  # effective buffer (correct B: acetic acid + acetate)
        cg("thinks a strong acid plus its salt buffers; a fully-ionized strong "
           "acid has no weak-acid/conjugate-base equilibrium to resist pH "
           "change"),
        None,
        cg("thinks a strong base and a neutral salt form a buffer; there is no "
           "conjugate weak-acid/base pair"),
        cg("thinks a neutral salt solution alone can buffer pH")],
    "q_ho_065": [  # pH of neutral water (correct B: 7)
        cg("thinks neutral means pH 0, confusing neutrality with strong "
           "acidity"),
        None,
        cg("assigns pH 14 (the strongly basic extreme) to neutral water"),
        cg("thinks pH depends on the quantity of water rather than on [H⁺]")],
    "q_ho_066": [  # pH of 1.0×10⁻³ M strong acid (correct C: 3)
        cg("uses the wrong exponent, treating the concentration as 0.1 M"),
        cg("uses 0.01 M instead of 0.001 M for the concentration"),
        None,
        trap("negation")],  # 11 = 14 − 3, computes pOH then forgets to convert
    "q_ho_067": [  # conjugate base of HCO₃⁻ (correct B: CO₃²⁻)
        cg("gives the conjugate ACID (adds a proton to HCO₃⁻) instead of the "
           "conjugate base"),
        None,
        cg("names a decomposition product (CO₂), not the species differing by "
           "one H⁺"),
        cg("grabs hydroxide, a generic base, rather than the species one "
           "proton removed from HCO₃⁻")],
    "q_ho_068": [  # [H⁺] ×1000 → pH (correct A: −3 units)
        None,
        trap("inverse"),  # right magnitude, wrong direction (more H⁺ = lower pH)
        cg("treats pH as a linear (not logarithmic) function of [H⁺]"),
        cg("thinks changing [H⁺] does not affect pH")],
    "q_ho_069": [  # buffer with [A⁻]=[HA] (correct A: pH = pKa)
        None,
        cg("assumes equal concentrations force a neutral pH of 7, ignoring the "
           "acid's pKa"),
        cg("mis-applies Henderson–Hasselbalch; a 1:1 ratio gives log 1 = 0, so "
           "pH = pKa, not pKa + 1"),
        cg("uses a pOH/pKb-style 14 − pKa relationship that does not apply "
           "here")],
    "q_ho_070": [  # common-ion effect on formic acid (correct A: decreases)
        None,
        cg("predicts the wrong Le Chatelier direction — thinks the added "
           "conjugate base drives more ionization"),
        cg("does not recognize formate as the common ion shared with the "
           "acid's ionization equilibrium"),
        cg("assumes the solution becomes more acidic and that this raises "
           "percent ionization")],
    "q_ho_071": [  # weak vs strong acid at equal conc (correct B: higher pH)
        cg("thinks weak acids ionize completely, reversing the strong/weak "
           "distinction"),
        None,
        cg("assumes equal concentration means equal pH, ignoring differences "
           "in ionization"),
        cg("believes a weak acid does not ionize at all, rather than only "
           "partially")],
    "q_ho_072": [  # enzyme increases rate by (correct A: lowers Ea)
        None,
        cg("thinks an enzyme changes the reaction's ΔG/thermodynamics rather "
           "than only its kinetics"),
        cg("attributes the rate increase to heating rather than to a lowered "
           "energy barrier"),
        cg("believes an enzyme shifts the equilibrium position instead of "
           "speeding both directions equally")],
    "q_ho_073": [  # positive ΔG (correct B: endergonic)
        cg("swaps the definitions — assigns the exergonic (ΔG < 0) label to a "
           "positive ΔG"),
        None,
        cg("calls a positive-ΔG reaction spontaneous, reversing the sign "
           "convention for spontaneity"),
        cg("thinks ΔG > 0 makes a reaction impossible, ignoring that energy "
           "input or coupling can drive it")],
    "q_ho_074": [  # competitive inhibitor mechanism (correct A: active site)
        None,
        cg("describes allosteric/noncompetitive inhibition (binds away from "
           "the active site), not competitive"),
        cg("describes irreversible covalent inhibition rather than reversible "
           "competitive binding"),
        cg("attributes inhibition to temperature rather than to occupying the "
           "active site")],
    "q_ho_075": [  # Vmax plateau (correct A: saturation)
        None,
        cg("invokes substrate inhibition rather than simple saturation of "
           "active sites"),
        cg("thinks the enzyme is consumed; a catalyst is regenerated, not used "
           "up"),
        cg("claims activation energy rises with substrate, which does not "
           "cause the Vmax plateau")],
    "q_ho_076": [  # mutation in substrate pocket (correct A: active site)
        None,
        cg("names the allosteric (regulatory) site rather than the "
           "substrate-binding catalytic pocket"),
        cg("picks a distant structural feature unrelated to substrate binding "
           "or catalysis"),
        cg("names a targeting sequence, not the catalytic region")],
    "q_ho_077": [  # induced fit vs lock-and-key (correct A: shape changes)
        None,
        cg("describes the rigid lock-and-key view, the model that induced fit "
           "revised"),
        cg("denies the physical binding interaction that both models require"),
        cg("confuses a conformational (shape) change with a permanent change "
           "to the amino-acid sequence")],
    "q_ho_078": [  # heating far above optimum (correct A: denatures)
        None,
        cg("assumes rate rises without limit with temperature, ignoring "
           "denaturation above the optimum"),
        cg("thinks enzyme activity is independent of temperature"),
        cg("believes denaturation creates more functional active sites rather "
           "than destroying them")],
    "q_ho_079": [  # reverse competitive inhibition (correct A: excess substrate)
        None,
        cg("thinks removing substrate relieves competitive inhibition; it "
           "would only slow the reaction further"),
        cg("thinks lowering enzyme amount outcompetes the inhibitor; it just "
           "reduces total activity"),
        cg("thinks adding more inhibitor reverses inhibition rather than "
           "deepening it")],
    "q_ho_080": [  # inhibitor and Keq (correct A: no, only kinetics)
        None,
        cg("thinks a kinetic slowdown lowers the equilibrium constant, "
           "conflating rate with equilibrium"),
        cg("believes the inhibitor alters product thermodynamic stability "
           "(ΔG)"),
        cg("makes the thermodynamic outcome depend on substrate "
           "concentration")],
    "q_ho_081": [  # Km definition (correct A: half of Vmax)
        None,
        cg("confuses Km with the substrate level that gives full Vmax rather "
           "than half"),
        cg("thinks Km is the substrate concentration where the rate is zero"),
        cg("equates Km with the point of maximum velocity")],
    "q_ho_082": [  # higher Km meaning (correct A: lower affinity)
        None,
        cg("reverses the relationship — treats a higher Km as tighter binding "
           "(higher affinity)"),
        cg("assumes Km fixes Vmax; the two parameters are independent"),
        cg("thinks a higher Km means saturation at lower [S]; it actually "
           "requires more substrate")],
    "q_ho_083": [  # catalyst at equilibrium (correct A: no shift)
        None,
        cg("thinks a catalyst favors the forward reaction and shifts "
           "equilibrium toward products"),
        cg("thinks a catalyst shifts equilibrium toward reactants"),
        cg("believes a catalyst increases equilibrium yield rather than only "
           "the rate")],
    "q_ho_084": [  # temperature raises rate (correct A: fraction exceed Ea)
        None,
        cg("thinks temperature lowers the activation energy; only a catalyst "
           "does that"),
        cg("attributes the rate increase to a thermodynamic (ΔG) change rather "
           "than collision energetics"),
        cg("invokes an irrelevant change in molecular size")],
    "q_ho_085": [  # what changes k (correct A: temperature)
        None,
        cg("thinks reactant concentration changes k; concentration affects "
           "rate but not the constant"),
        cg("confuses a volume change (a concentration effect) with a change in "
           "k"),
        cg("thinks pressure at constant T changes k rather than just "
           "concentrations")],
    "q_ho_086": [  # overall order of k[X]²[Y] (correct C: 3)
        cg("counts only one reactant instead of summing the exponents"),
        cg("reports the order in X alone (2) rather than the overall order"),
        None,
        cg("treats the reaction as zero order despite nonzero exponents")],
    "q_ho_087": [  # first order, triple [A] (correct A: triple)
        None,
        cg("applies a factor of 2 regardless of the actual change in "
           "concentration"),
        cg("treats the reaction as second order (3² = 9) rather than first "
           "order"),
        cg("thinks concentration does not affect the rate of a first-order "
           "reaction")],
    "q_ho_088": [  # zero order, double [A] (correct A: no effect)
        None,
        cg("treats the reaction as first order (rate doubles) rather than zero "
           "order"),
        cg("treats the reaction as second order (rate quadruples)"),
        trap("inverse")],
    "q_ho_089": [  # activation energy definition (correct A)
        None,
        cg("confuses the kinetic energy barrier with the thermodynamic "
           "free-energy change (ΔG)"),
        cg("names bond dissociation enthalpy, a specific bond quantity, not "
           "the reaction's energy barrier"),
        cg("names the enthalpy change of reaction (ΔH) rather than the barrier "
           "to reacting")],
    "q_ho_090": [  # exponent m in rate law (correct A: order wrt A)
        None,
        cg("assumes the exponent equals the stoichiometric coefficient, which "
           "holds only for elementary steps"),
        cg("confuses the order exponent with the rate constant"),
        cg("confuses the exponent with an equilibrium concentration")],
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


# ---------------------------------------------------------------------------
# Correct-answer explanations (static, NO-AI). Every question carries a concise
# rationale for WHY the correct answer is correct, grounded in that item's named
# source (OpenStax for science; the original CC0 passage for CARS). Shown to the
# student AFTER they answer, and reused as the app's AI-off fallback / baseline
# for the AI "explain your miss" feature (which only READs this field). Keep it
# source-grounded prose, authoritative (no hedging), 1–4 sentences, self-
# contained, and factually consistent with the stored correct answer. Keyed by
# stable question id; every id in the emitted bank MUST have a non-empty entry.
# ---------------------------------------------------------------------------
EXPLANATIONS: dict[str, str] = {
    # --- DEV: biochemistry / biology --------------------------------------
    "q_dev_001": (
        "In the citric acid cycle the conversion of succinyl-CoA to succinate "
        "is the cycle's only substrate-level phosphorylation: energy from "
        "cleaving the high-energy thioester bond drives direct synthesis of one "
        "GTP (or ATP). The other listed steps are redox or hydration reactions "
        "that reduce NAD⁺/FAD rather than making a nucleoside triphosphate."
    ),
    "q_dev_002": (
        "A high ADP level signals that the cell's energy charge is low, so ADP "
        "acts as an allosteric activator of key respiratory enzymes (such as "
        "isocitrate dehydrogenase), increasing their activity to accelerate ATP "
        "production. Abundant ATP would have the opposite, inhibitory effect."
    ),
    "q_dev_003": (
        "Whether a reaction is endergonic (+ΔG) or exergonic (−ΔG) describes its "
        "thermodynamics — energy absorbed or released — not its speed. Reaction "
        "rate is set by the activation-energy barrier, so an exergonic reaction "
        "can be slow and an endergonic one need not be; that makes the "
        "speed-based statement the false comparison. The other statements "
        "correctly describe ΔG signs, energy flow, and the shared activation "
        "barrier."
    ),
    "q_dev_004": (
        "Activation energy governs kinetics, not thermodynamics, so it cannot be "
        "read from ΔG or spontaneity. Because a lower activation energy lets more "
        "collisions succeed per unit time, comparing the two reactions' rates is "
        "the best available proxy for their relative activation energies."
    ),
    "q_dev_005": (
        "An allosteric inhibitor binds a site other than the active site and "
        "induces a conformational change that reshapes the active site, lowering "
        "its affinity for substrate. This distinguishes it from a competitive "
        "inhibitor, which binds the active site directly."
    ),
    "q_dev_006": (
        "Ammonia ionizes as NH₃ + H₂O ⇌ NH₄⁺ + OH⁻. Adding HCl supplies H⁺ that "
        "neutralizes OH⁻ (and protonates NH₃), pulling the equilibrium toward "
        "NH₄⁺ by Le Châtelier's principle and increasing the percent converted. "
        "Adding NaOH, NH₄Cl, or more NH₃ would instead suppress conversion."
    ),
    "q_dev_007": (
        "The weaker the acid, the stronger its conjugate base. HCN (Ka ≈ 6×10⁻¹⁰) "
        "is a much weaker acid than HF (Ka ≈ 7×10⁻⁴), so its conjugate base CN⁻ "
        "is the stronger base of the two."
    ),
    "q_dev_008": (
        "By definition, oxidation occurs at the anode, and the electrons it "
        "releases travel through the external wire to the cathode, where "
        "reduction occurs (mnemonic: 'an ox' oxidation at the anode, 'red cat' "
        "reduction at the cathode)."
    ),
    "q_dev_009": (
        "Because ΔG° = −nFE°cell, a positive E°cell makes ΔG° negative, so the "
        "reaction as written is spontaneous under standard conditions. This is "
        "why a galvanic cell delivers electrical work without an external power "
        "source."
    ),
    "q_dev_010": (
        "As the cell operates, one half-cell tends to build up positive charge "
        "and the other negative; the salt bridge lets ions migrate between them "
        "to keep each half-cell electrically neutral so current can continue. It "
        "does not carry electrons or catalyze the electrode reactions."
    ),
    "q_dev_011": (
        "A buffer resists pH change because it contains appreciable amounts of "
        "both a weak acid and its conjugate base: the conjugate base neutralizes "
        "added acid and the weak acid neutralizes added base. A strong acid/base "
        "pair would simply react to completion and provide no buffering."
    ),
    "q_dev_012": (
        "From ΔG = ΔH − TΔS, ΔG is negative at every temperature only when ΔH is "
        "negative and ΔS is positive, because then both terms drive ΔG negative "
        "regardless of T. Any other sign combination makes spontaneity "
        "temperature-dependent or impossible."
    ),
    "q_dev_013": (
        "The Gibbs free-energy change at constant temperature is defined as "
        "ΔG = ΔH − TΔS, combining the enthalpy change with the "
        "temperature-weighted entropy change."
    ),
    "q_dev_014": (
        "A spontaneous process proceeds on its own once initiated, without a "
        "continuous external supply of energy. Spontaneity says nothing about "
        "speed and does not require heat release or a catalyst."
    ),
    "q_dev_015": (
        "Raising the temperature broadens the molecular energy distribution so a "
        "larger fraction of collisions meet or exceed the activation energy, "
        "increasing the reaction rate. Temperature does not lower Ea or change ΔG."
    ),
    "q_dev_016": (
        "A catalyst speeds a reaction by providing an alternative pathway with a "
        "lower activation energy, so more collisions succeed. It does not shift "
        "the equilibrium position or change ΔG — it only helps the system reach "
        "equilibrium faster."
    ),
    "q_dev_017": (
        "The rate constant k is independent of reactant concentrations; it "
        "depends on temperature (via the Arrhenius equation) and on whether a "
        "catalyst is present. Concentrations affect the rate through the rate "
        "law, not through k itself."
    ),
    "q_dev_018": (
        "By the equation of continuity (A·v = constant) for an incompressible "
        "fluid, when the cross-sectional area decreases the speed must increase "
        "to keep the volume flow rate constant."
    ),
    "q_dev_019": (
        "A constant volume flow rate (Q = A·v) in a pipe of varying width follows "
        "directly from conservation of mass for an incompressible fluid — the "
        "equation of continuity. Bernoulli's principle instead relates speed to "
        "pressure."
    ),
    "q_dev_020": (
        "Glycolysis invests 2 ATP in its early phase and generates 4 ATP by "
        "substrate-level phosphorylation, for a net gain of 2 ATP per glucose."
    ),
    "q_dev_021": (
        "Glycolysis occurs in the cytosol (cytoplasm) and requires no membranes "
        "or organelles, unlike the citric acid cycle (mitochondrial matrix) and "
        "oxidative phosphorylation."
    ),
    "q_dev_022": (
        "Besides a net 2 ATP, glycolysis reduces NAD⁺ to NADH (2 per glucose) at "
        "the glyceraldehyde-3-phosphate dehydrogenase step. NADPH and FADH₂ are "
        "not products of glycolysis."
    ),
    "q_dev_023": (
        "Each turn of the citric acid cycle begins when acetyl-CoA combines with "
        "oxaloacetate to form citrate and ends by regenerating oxaloacetate, "
        "which is then free to accept another acetyl group."
    ),
    "q_dev_024": (
        "Vmax is the maximum rate reached when the substrate concentration is "
        "high enough to saturate all enzyme active sites, so adding still more "
        "substrate cannot increase the rate further."
    ),
    "q_dev_025": (
        "The plasma membrane's basic structural framework is the phospholipid "
        "bilayer, within which proteins, cholesterol, and carbohydrates are "
        "embedded (the fluid-mosaic model). Peptidoglycan and cellulose are "
        "cell-wall materials, not the animal-cell membrane framework."
    ),
    "q_dev_026": (
        "A membrane phospholipid is amphipathic: its phosphate-containing head is "
        "hydrophilic (polar) and its fatty-acid tails are hydrophobic (nonpolar). "
        "This dual character drives spontaneous bilayer formation in water."
    ),
    "q_dev_027": (
        "Replication is semiconservative because each daughter double helix keeps "
        "one original (parental) template strand paired with one newly "
        "synthesized strand, as shown by Meselson and Stahl."
    ),
    "q_dev_028": (
        "DNA polymerase adds nucleotides only to the 3′ end of a growing strand, "
        "synthesizing in the 5′→3′ direction. Helicase unwinds the helix, primase "
        "lays RNA primers, and ligase seals nicks."
    ),
    "q_dev_029": (
        "DNA ligase forms the phosphodiester bonds that join adjacent Okazaki "
        "fragments on the lagging strand into a continuous strand. Polymerase "
        "extends strands, primase makes primers, and helicase unwinds the helix."
    ),
    "q_dev_030": (
        "A monohybrid cross of two heterozygotes (Aa × Aa) gives a 3:1 phenotypic "
        "ratio (3 dominant : 1 recessive), because only the homozygous-recessive "
        "quarter shows the recessive phenotype. The 1:2:1 ratio is genotypic and "
        "9:3:3:1 is a dihybrid ratio."
    ),
    "q_dev_031": (
        "An organism's genotype is its genetic (allelic) makeup, whereas its "
        "phenotype is its observable characteristics arising from that genotype "
        "interacting with the environment."
    ),
    "q_dev_032": (
        "Memory involves three basic processes: encoding (getting information "
        "in), storage (retaining it over time), and retrieval (accessing it when "
        "needed)."
    ),
    "q_dev_033": (
        "Classic work by George Miller estimated the capacity of short-term "
        "(working) memory at about seven, plus or minus two, items — 'the "
        "magical number seven.'"
    ),
    "q_dev_034": (
        "Keeping information active in short-term memory by repeating it is "
        "(maintenance) rehearsal. Chunking instead groups items into larger "
        "units, and encoding is the initial entry of information."
    ),
    "q_dev_035": (
        "In Pavlov's paradigm the food automatically triggers salivation without "
        "prior learning, so it is the unconditioned stimulus; the salivation it "
        "elicits is the unconditioned response."
    ),
    "q_dev_036": (
        "By definition a reinforcer increases the likelihood of the behavior it "
        "follows — whether by adding a pleasant stimulus (positive) or removing "
        "an aversive one (negative). Punishment, by contrast, decreases behavior."
    ),
    "q_dev_037": (
        "Extinction occurs when the conditioned stimulus is presented repeatedly "
        "without the unconditioned stimulus, so the conditioned response "
        "gradually weakens and disappears."
    ),
    "q_dev_038": (
        "The fundamental attribution error is the tendency to over-attribute "
        "others' behavior to internal dispositions while underweighting "
        "situational causes. The self-serving bias instead concerns how we "
        "explain our own outcomes."
    ),
    "q_dev_039": (
        "Conformity is adjusting one's behavior or thinking to match a group "
        "standard. Obedience differs in that it involves following the orders of "
        "an authority."
    ),
    "q_dev_040": (
        "Health disparities are preventable differences in health outcomes linked "
        "to social, economic, or environmental disadvantage across groups — not "
        "random or purely genetic differences."
    ),
    "q_dev_041": (
        "Social determinants of health are the conditions in which people live "
        "and work — such as access to education, income, and safe housing — that "
        "shape health. Blood type, mutations, and eye color are biological, not "
        "social, factors."
    ),
    "q_dev_042": (
        "Pascal's principle states that a pressure change applied to an enclosed, "
        "incompressible fluid is transmitted undiminished to every portion of the "
        "fluid and the walls of its container — the basis of hydraulic systems."
    ),
    "q_dev_043": (
        "Cognitive dissonance is the psychological discomfort that arises when a "
        "person holds two conflicting cognitions or acts in a way that clashes "
        "with an attitude, motivating them to reduce the inconsistency."
    ),
    "q_dev_044": (
        "In codominance the heterozygote expresses both alleles fully and "
        "simultaneously (e.g., type AB blood), rather than showing a blended "
        "intermediate (incomplete dominance) or only the dominant allele."
    ),
    # --- DEV: CARS (original CC0 passages) ---------------------------------
    "q_dev_045": (
        "The passage explicitly redefines objectivity as 'not the absence of "
        "perspective but the disciplined awareness of it,' concluding that a "
        "historian who acknowledges and tests her assumptions comes closer to "
        "truth. That is the central claim; the author expressly denies that "
        "history is 'mere fiction.'"
    ),
    "q_dev_046": (
        "The passage states outright that freedom 'is not simply the quantity of "
        "available options but the capacity to choose well among them,' directly "
        "supporting the 'choose well' reading over the mere-number or "
        "no-constraints interpretations."
    ),
    "q_dev_047": (
        "The closing sentence says a historian who acknowledges and tests her "
        "assumptions 'comes closer to truth than one who pretends to have none,' "
        "so the author treats pretending to have no assumptions as an obstacle to "
        "truth, not a mark of objectivity."
    ),
    "q_dev_048": (
        "'Expand liberty in name while eroding it in practice' contrasts freedom "
        "as merely labeled with freedom as actually experienced, so the author "
        "means nominal freedom can increase even as real freedom declines."
    ),
    "q_dev_049": (
        "The passage's thesis is that too many options can paralyze, reduce "
        "enjoyment, and prompt second-guessing. The overwhelmed diner who takes "
        "long to order and later regrets the choice mirrors this 'paradox of "
        "choice' exactly; the other scenarios involve few or no options."
    ),
    "q_dev_050": (
        "The passage praises the historian who tests her assumptions 'against "
        "evidence that might overturn them,' so actively seeking disconfirming "
        "evidence best applies its logic. Ignoring conflicting sources or "
        "following popularity would do the opposite."
    ),
    # --- HELD_OUT: chemistry / physics / biology ---------------------------
    "q_ho_001": (
        "The reducing agent is the species that is oxidized (loses electrons) and "
        "thereby reduces the other. Zn(s) → Zn²⁺ loses electrons, reducing Cu²⁺ "
        "to Cu, so Zn is the reducing agent."
    ),
    "q_ho_002": (
        "By the Nernst equation, Ecell = E°cell − (RT/nF)·lnQ. Raising the "
        "concentration of product ions increases the reaction quotient Q, which "
        "lowers Ecell. E° itself is a constant and does not change."
    ),
    "q_ho_003": (
        "In electrolysis an external power source supplies electrical energy to "
        "drive a nonspontaneous (ΔG > 0, E°cell < 0) redox reaction — the reverse "
        "of a galvanic cell, which produces electricity from a spontaneous "
        "reaction."
    ),
    "q_ho_004": (
        "By definition, reduction (gain of electrons) always occurs at the "
        "cathode in any electrochemical cell, galvanic or electrolytic; oxidation "
        "occurs at the anode."
    ),
    "q_ho_005": (
        "HCl is a strong acid that ionizes completely, so [H⁺] = 0.010 M = 10⁻² M "
        "and pH = −log(10⁻²) = 2.0."
    ),
    "q_ho_006": (
        "A conjugate acid–base pair differs by exactly one H⁺. H₂CO₃ and HCO₃⁻ "
        "differ by a single proton, so they are a conjugate pair; the other "
        "options are not related by transfer of one proton."
    ),
    "q_ho_007": (
        "In neutral water [H⁺] = [OH⁻], and since Kw = [H⁺][OH⁻] = 1.0×10⁻¹⁴, "
        "each equals the square root, 1.0×10⁻⁷ M."
    ),
    "q_ho_008": (
        "Each pH unit is a tenfold change in [H⁺]. A difference of two pH units "
        "(6 − 4) corresponds to 10² = 100 times greater [H⁺], so pH 4 is 100× "
        "more acidic than pH 6."
    ),
    "q_ho_009": (
        "With ΔG = ΔH − TΔS, a positive ΔH and positive ΔS give a negative ΔG "
        "only when T is large enough that the TΔS term outweighs ΔH — so the "
        "reaction becomes spontaneous at high temperature."
    ),
    "q_ho_010": (
        "A negative ΔG indicates a thermodynamically favorable (spontaneous) "
        "reaction. It says nothing about rate, and the reaction can be "
        "spontaneous whether it is exothermic or endothermic."
    ),
    "q_ho_011": (
        "At equilibrium the forward and reverse processes are balanced and there "
        "is no net driving force, so ΔG = 0. (This is distinct from ΔG°, which is "
        "generally nonzero.)"
    ),
    "q_ho_012": (
        "Entropy (S) measures the dispersal of energy and matter — the number of "
        "accessible microstates, often described as disorder. It is not the "
        "system's total energy or its rate."
    ),
    "q_ho_013": (
        "The overall reaction order is the sum of the exponents in the rate law: "
        "1 (for A) + 2 (for B) = 3."
    ),
    "q_ho_014": (
        "For a reaction first order in A, rate ∝ [A]¹, so doubling [A] doubles the "
        "rate (a factor of 2)."
    ),
    "q_ho_015": (
        "A zero-order reaction has rate = k[A]⁰ = k, so the rate is constant and "
        "independent of reactant concentration."
    ),
    "q_ho_016": (
        "The activation energy is the minimum energy colliding reactants must "
        "have to reach the transition state and form products. It is not the "
        "reactant–product energy difference (that is ΔH/ΔG) and is not lowered "
        "simply by heating."
    ),
    "q_ho_017": (
        "Bernoulli's equation for an ideal fluid at constant height requires that "
        "where the fluid's speed is higher, its pressure is lower, since the "
        "kinetic and pressure terms trade off to keep the total constant."
    ),
    "q_ho_018": (
        "An object floats in equilibrium when the upward buoyant force equals its "
        "own weight; by Archimedes' principle that buoyant force equals the "
        "weight of the displaced fluid, not the entire fluid."
    ),
    "q_ho_019": (
        "Glycolysis converts one glucose to two molecules of pyruvate; under "
        "aerobic conditions the pyruvate enters the mitochondrion (where it is "
        "converted to acetyl-CoA). Lactate and ethanol form only under anaerobic "
        "fermentation."
    ),
    "q_ho_020": (
        "Phosphofructokinase-1 catalyzes the committed, rate-limiting step of "
        "glycolysis (fructose-6-phosphate → fructose-1,6-bisphosphate) and is the "
        "pathway's key regulatory control point."
    ),
    "q_ho_021": (
        "The early 'energy investment' phase of glycolysis uses 2 ATP (at the "
        "hexokinase and PFK-1 steps) to phosphorylate the sugar before the "
        "energy-payoff phase generates ATP."
    ),
    "q_ho_022": (
        "In human muscle under anaerobic conditions, lactate fermentation reduces "
        "pyruvate to lactate, regenerating the NAD⁺ needed to keep glycolysis "
        "running. Ethanol fermentation occurs in yeast, not humans."
    ),
    "q_ho_023": (
        "Each turn of the citric acid cycle releases 2 CO₂ molecules, at the "
        "isocitrate dehydrogenase and α-ketoglutarate dehydrogenase steps."
    ),
    "q_ho_024": (
        "Most of the energy harvested by the citric acid cycle is stored in the "
        "reduced electron carriers NADH and FADH₂ (which later drive the electron "
        "transport chain); only a small amount is captured directly as GTP/ATP."
    ),
    "q_ho_025": (
        "Per acetyl-CoA, one turn of the citric acid cycle produces 3 NADH (plus "
        "1 FADH₂ and 1 GTP/ATP)."
    ),
    "q_ho_026": (
        "The active site is the region of an enzyme where substrate binds and "
        "catalysis occurs; the allosteric site is a separate regulatory site "
        "elsewhere on the enzyme."
    ),
    "q_ho_027": (
        "In the induced-fit model, substrate binding causes the enzyme's active "
        "site to change shape to fit the substrate more snugly, enhancing "
        "catalysis. The enzyme is not consumed and the substrate is chemically "
        "transformed."
    ),
    "q_ho_028": (
        "Heating well above an enzyme's optimum disrupts the noncovalent "
        "interactions that maintain its three-dimensional shape (denaturation), "
        "distorting the active site and decreasing activity."
    ),
    "q_ho_029": (
        "Simple diffusion moves a small nonpolar molecule such as O₂ directly "
        "through the bilayer down its concentration gradient, requiring neither "
        "ATP nor a transport protein."
    ),
    "q_ho_030": (
        "Active transport moves solutes against their concentration gradient and "
        "therefore requires an energy input (e.g., ATP). Diffusion and osmosis "
        "are passive and move substances down their gradients."
    ),
    "q_ho_031": (
        "In animal cell membranes cholesterol acts as a fluidity buffer: it "
        "restrains movement at high temperatures and prevents tight packing at "
        "low temperatures, keeping the membrane appropriately fluid."
    ),
    "q_ho_032": (
        "Osmosis is specifically the diffusion of water across a selectively "
        "permeable membrane, moving from higher water (lower solute) toward lower "
        "water (higher solute) concentration."
    ),
    "q_ho_033": (
        "By complementary base pairing, adenine pairs with thymine (two hydrogen "
        "bonds) and guanine pairs with cytosine (three hydrogen bonds)."
    ),
    "q_ho_034": (
        "Helicase unwinds and separates the two strands of the double helix at "
        "the replication fork; ligase, polymerase, and primase act on the exposed "
        "strands afterward."
    ),
    "q_ho_035": (
        "Because DNA polymerase synthesizes only 5′→3′, the lagging strand is made "
        "discontinuously as short Okazaki fragments, whereas the leading strand is "
        "synthesized continuously."
    ),
    "q_ho_036": (
        "The two strands of a DNA double helix run antiparallel (opposite 5′→3′ "
        "orientations) and are complementary (A–T, G–C), held together by "
        "hydrogen bonds between the paired bases."
    ),
    "q_ho_037": (
        "A monohybrid cross Aa × Aa gives the genotypic ratio 1 AA : 2 Aa : 1 aa; "
        "the 3:1 ratio is the phenotypic (not genotypic) outcome."
    ),
    "q_ho_038": (
        "Mendel's law of segregation states that the two alleles of a gene "
        "separate during gamete formation so each gamete carries only one. "
        "Independent assortment is the separate law dealing with different genes."
    ),
    "q_ho_039": (
        "A testcross pairs an individual of unknown genotype with a "
        "homozygous-recessive individual, because the recessive parent contributes "
        "only recessive alleles and lets the unknown's alleles show up directly in "
        "the offspring phenotypes."
    ),
    "q_ho_040": (
        "Genes far apart on the same chromosome are frequently separated by "
        "crossing over during meiosis, so they recombine often and assort nearly "
        "independently, behaving almost as if on different chromosomes."
    ),
    "q_ho_041": (
        "Long-term memory is the relatively permanent store with essentially "
        "unlimited capacity, in contrast to the brief, limited sensory and "
        "short-term stores."
    ),
    "q_ho_042": (
        "Retrieval improves when the recall context matches the encoding context "
        "— context-dependent memory, an instance of the encoding-specificity "
        "principle."
    ),
    "q_ho_043": (
        "The serial position effect is the tendency to remember items at the "
        "beginning (primacy) and end (recency) of a list better than those in the "
        "middle."
    ),
    "q_ho_044": (
        "Explicit (declarative) memory covers facts and events that can be "
        "consciously and intentionally recalled. Skills like riding a bicycle are "
        "implicit (procedural) memory."
    ),
    "q_ho_045": (
        "A previously neutral stimulus that, after repeated pairing with the "
        "unconditioned stimulus, comes to elicit a response is the conditioned "
        "stimulus."
    ),
    "q_ho_046": (
        "Negative reinforcement increases a behavior by removing an aversive "
        "stimulus (e.g., a seatbelt alarm stops when you buckle up). 'Negative' "
        "refers to removal, not to decreasing behavior — that would be punishment."
    ),
    "q_ho_047": (
        "A variable-ratio schedule delivers reinforcement after an unpredictable "
        "(varying) number of responses and produces high, steady response rates "
        "that resist extinction — as seen in gambling."
    ),
    "q_ho_048": (
        "Milgram's shock experiments demonstrated obedience — willingness to "
        "follow the commands of an authority figure even against one's conscience. "
        "Conformity involves matching peers, not following an authority's orders."
    ),
    "q_ho_049": (
        "The bystander effect describes how the presence of other people "
        "decreases the likelihood that any single individual will help, largely "
        "through diffusion of responsibility."
    ),
    "q_ho_050": (
        "An attitude is an evaluation — favorable or unfavorable — of a person, "
        "object, or idea. It is a learned evaluative stance, not a genetic trait, "
        "a reflex, or a type of memory."
    ),
    "q_ho_051": (
        "Socioeconomic status is conventionally measured by a combination of "
        "income, education, and occupation — not by biological features such as "
        "blood type or height."
    ),
    "q_ho_052": (
        "A social gradient in health means health outcomes improve stepwise at "
        "each higher rung of the socioeconomic ladder — affecting the whole "
        "population, not only the very poorest, and not explained away as random "
        "or purely genetic."
    ),
    # --- HELD_OUT: CARS (original CC0 passages) ----------------------------
    "q_ho_053": (
        "In context the passage uses 'vantage point' figuratively to mean the "
        "historian's particular perspective or standpoint (her 'own moment'), not "
        "a literal physical location or a historical period."
    ),
    "q_ho_054": (
        "The author grants that we assume more options make us freer but argues "
        "they can paralyze and erode real freedom — an attitude of cautious "
        "skepticism, not enthusiasm, total rejection, or indifference."
    ),
    "q_ho_055": (
        "Having argued that all history reflects perspective, the author "
        "immediately heads off the obvious misreading — that history is therefore "
        "just fiction — by denying it, so the sentence anticipates and rebuts a "
        "likely objection."
    ),
    "q_ho_056": (
        "The passage opens with the common assumption that more options mean more "
        "freedom, then qualifies it by redefining freedom as the capacity to "
        "choose well — so its structure is to qualify an assumption through "
        "redefinition."
    ),
    "q_ho_057": (
        "The author's claim is that excessive options paralyze and reduce "
        "satisfaction. Evidence that people given many options consistently decide "
        "easily and report greater satisfaction directly contradicts that causal "
        "claim, weakening it most."
    ),
    "q_ho_058": (
        "The passage's logic is that disciplined awareness of one's perspective, "
        "tested against evidence, yields objectivity. A journalist who "
        "acknowledges her biases and checks them against evidence is the closest "
        "parallel; an error-free calculator has no perspective to examine."
    ),
    "q_ho_059": (
        "The pascal is defined as one newton per square meter (N/m²), i.e., force "
        "per unit area. kg·m/s² is the newton (a force) and N·m is the joule "
        "(energy)."
    ),
    "q_ho_060": (
        "The shopper facing dozens of nearly identical products concretely "
        "illustrates the passage's thesis that an excess of options can raise "
        "effort and reduce satisfaction — it is not a claim that all shopping is "
        "harmful or a description of the author's own habits."
    ),
    # --- SYNTHESIS / application (q_syn_*, stable ids) ---------------------
    "q_syn_001": (
        "Adding X leaves Vmax unchanged (both curves approach ~100 µmol/min) but "
        "raises the apparent Km (from ~2 mM to ~6 mM). A higher Km with an "
        "unchanged Vmax is the signature of competitive inhibition, which can be "
        "overcome by high substrate."
    ),
    "q_syn_002": (
        "Because X is competitive, high substrate concentrations outcompete the "
        "inhibitor for the active site, so at saturating [S] the velocity "
        "approaches the same Vmax as the uninhibited enzyme — consistent with the "
        "data, where both curves converge near 100 µmol/min."
    ),
    "q_syn_003": (
        "To attribute any velocity difference to inhibitor X, every quantity other "
        "than the independent variable ([S]) and the treatment (X) must be held "
        "constant. The total amount of enzyme is the critical control — differing "
        "enzyme amounts would change velocity independently of X."
    ),
    "q_syn_004": (
        "Enzymes and their inhibitors affect only the rate (kinetics) of a "
        "reaction, not its thermodynamics. X changes the apparent Km but leaves ΔG "
        "and Keq unchanged, since those depend only on the free-energy difference "
        "between reactants and products."
    ),
    "q_syn_005": (
        "The half-cell with the higher (more positive) reduction potential is "
        "reduced and serves as the cathode, so Cu²⁺/Cu (+0.34 V) is the cathode. "
        "E°cell = E°cathode − E°anode = 0.34 − (−0.76) = +1.10 V."
    ),
    "q_syn_006": (
        "Using ΔG° = −nFE°cell with n = 2, F ≈ 96,500 C/mol, and E°cell = +1.10 V: "
        "ΔG° = −(2)(96,500)(1.10) ≈ −2.12×10⁵ J ≈ −212 kJ. The negative value "
        "means the reaction is spontaneous."
    ),
    "q_syn_007": (
        "By the Nernst equation, raising the product-ion concentration (Zn²⁺) "
        "increases Q and therefore lowers the actual cell potential Ecell. E°cell "
        "is a standard constant and does not change."
    ),
    "q_syn_008": (
        "As a galvanic cell discharges toward equilibrium its driving force fades: "
        "Ecell decreases toward 0 (a 'dead battery') and ΔG rises toward 0. At "
        "equilibrium there is no further net reaction."
    ),
    "q_syn_009": (
        "By the Henderson–Hasselbalch equation, pH = pKa + log([A⁻]/[HA]). With "
        "equal concentrations of acetate and acetic acid the log term is 0, so "
        "pH = pKa = 4.74."
    ),
    "q_syn_010": (
        "A buffer resists but does not eliminate pH change. The added H⁺ is "
        "consumed by acetate (A⁻ + H⁺ → HA), so the pH drops only slightly rather "
        "than sharply as it would in unbuffered water."
    ),
    "q_syn_011": (
        "By Henderson–Hasselbalch, pH = pKa + log([A⁻]/[HA]); one unit above the "
        "pKa requires log([A⁻]/[HA]) = 1, i.e., a [CH₃COO⁻]:[CH₃COOH] ratio of "
        "10:1."
    ),
    "q_syn_012": (
        "Adding the common ion acetate shifts the equilibrium CH₃COOH ⇌ CH₃COO⁻ + "
        "H⁺ to the left (Le Châtelier / common-ion effect), decreasing acetic "
        "acid's percent dissociation and lowering [H⁺], so the pH rises."
    ),
    "q_syn_013": (
        "Because the genes assort independently, use the product rule: P(yy) = 1/4 "
        "and P(rr) = 1/4, so P(yyrr) = 1/4 × 1/4 = 1/16."
    ),
    "q_syn_014": (
        "Independent assortment gives P(yellow, Y_) = 3/4 and P(wrinkled, rr) = "
        "1/4, so P(yellow and wrinkled) = 3/4 × 1/4 = 3/16."
    ),
    "q_syn_015": (
        "Offspring were ½ yellow : ½ green, so the yellow parent is Yy (Yy × yy → "
        "1:1). All offspring were round despite the rr tester, so the parent "
        "contributes only R and must be homozygous RR. The genotype is therefore "
        "YyRR."
    ),
    "q_syn_016": (
        "Counting only substrate-level phosphorylation: glycolysis nets 2 ATP, "
        "pyruvate→acetyl-CoA yields none, and the citric acid cycle makes 1 "
        "GTP/ATP per acetyl-CoA × 2 = 2, for a total of 4. The 30–36 figures "
        "include oxidative phosphorylation, which is excluded here."
    ),
    "q_syn_017": (
        "The cell interior (300 mOsm) is hypertonic to the 100 mOsm surroundings, "
        "so water moves osmotically into the cell, causing it to swell and "
        "potentially lyse. The membrane is not freely permeable to the solutes, so "
        "they do not simply diffuse out."
    ),
    "q_syn_018": (
        "Pairing antiparallel and complementary (A–T, G–C), the complement of "
        "3′-ATGCCT-5′ read in the conventional 5′→3′ direction is 5′-TCCGTA-3′. "
        "DNA uses thymine, not uracil, ruling out the U-containing option."
    ),
    "q_syn_019": (
        "Spontaneity requires ΔG = ΔH − TΔS < 0, i.e., T > ΔH/ΔS. With ΔH = 50,000 "
        "J/mol and ΔS = 150 J/(mol·K), T > 50,000/150 ≈ 333 K."
    ),
    "q_syn_020": (
        "Comparing Exp 1→2, doubling [A] doubles the rate → first order in A. "
        "Comparing Exp 1→3, doubling [B] quadruples the rate → second order in B. "
        "So rate = k[A][B]²."
    ),
    "q_syn_021": (
        "ΔG governs thermodynamic favorability, not speed. A very negative ΔG with "
        "a high activation energy means the reaction is spontaneous yet "
        "kinetically slow; a catalyst would speed it by lowering Ea, not by "
        "changing ΔG."
    ),
    "q_syn_022": (
        "By continuity, halving the area doubles the speed (A₁v₁ = A₂v₂). By "
        "Bernoulli's equation at constant height, the faster-moving fluid in the "
        "narrow section has lower pressure."
    ),
    "q_syn_023": (
        "By continuity A₁v₁ = A₂v₂: v₂ = (6.0 cm² × 2.0 m/s)/2.0 cm² = 6.0 m/s."
    ),
    "q_syn_024": (
        "At equal concentration the strong acid HCl ionizes completely to give the "
        "full [H⁺], whereas weak acetic acid only partially ionizes. HCl therefore "
        "has the higher [H⁺] and the lower pH."
    ),
    "q_syn_025": (
        "Reinforcement after an unpredictable number of responses is a "
        "variable-ratio schedule, which produces high, steady response rates that "
        "resist extinction — exactly the gambling pattern described."
    ),
    "q_syn_026": (
        "The behavior (taking aspirin) increases because it removes an aversive "
        "stimulus (the headache). Removing something unpleasant to strengthen a "
        "behavior is negative reinforcement, not positive reinforcement or "
        "punishment."
    ),
    "q_syn_027": (
        "Judging the classmate's stumble as 'clumsy' (a dispositional cause) is "
        "the fundamental attribution error. Blaming the floor for one's own "
        "stumble while attributing others' to disposition is the actor–observer "
        "bias."
    ),
    "q_syn_028": (
        "The smoker holds conflicting cognitions (valuing health yet smoking) and "
        "eases the discomfort by changing a belief ('the risks are exaggerated'). "
        "Resolving that tension by altering a cognition is reduction of cognitive "
        "dissonance."
    ),
    "q_syn_029": (
        "Recall is best when the test environment matches the study environment "
        "and reverses when it does not — the encoding-specificity / "
        "context-dependent memory effect, not interference or chunking."
    ),
    "q_syn_030": (
        "Mortality falls at each step up the income quintiles, not just for the "
        "poorest — the hallmark of a social gradient in health. It implies SES is "
        "systematically related to health across the whole distribution, not "
        "randomly or only at a threshold."
    ),

    # --- §7d paraphrase-gap probes (q_ho_061..090) -------------------------
    "q_ho_061": (
        "A Brønsted–Lowry acid donates a proton (H⁺). In NH₃ + H₂O ⇌ NH₄⁺ + "
        "OH⁻, water gives up an H⁺ to ammonia, so H₂O is the acid (and NH₃, "
        "which accepts the proton, is the base)."
    ),
    "q_ho_062": (
        "In the Brønsted–Lowry framework a base is a proton (H⁺) acceptor, "
        "while an acid is a proton donor. This is broader than the Arrhenius "
        "definition, so a base need not release OH⁻ directly."
    ),
    "q_ho_063": (
        "Acid strength and conjugate-base strength are inversely related: the "
        "more completely an acid donates its proton, the more stable and less "
        "basic its conjugate base. HCl ionizes essentially completely, so Cl⁻ "
        "is an extremely weak, effectively non-basic species."
    ),
    "q_ho_064": (
        "A buffer needs a weak acid together with its conjugate base (or a weak "
        "base with its conjugate acid). Acetic acid (CH₃COOH) and acetate (from "
        "CH₃COONa) form exactly such a conjugate pair, so the mixture resists "
        "pH change when small amounts of acid or base are added."
    ),
    "q_ho_065": (
        "At 25 °C, Kw = 1.0×10⁻¹⁴ and neutrality means [H⁺] = [OH⁻] = "
        "1.0×10⁻⁷ M. Thus pH = −log(1.0×10⁻⁷) = 7, independent of how much "
        "water is present."
    ),
    "q_ho_066": (
        "A strong monoprotic acid ionizes completely, so [H⁺] equals its "
        "concentration, 1.0×10⁻³ M. pH = −log(1.0×10⁻³) = 3."
    ),
    "q_ho_067": (
        "A conjugate base is formed by removing one H⁺. Taking a proton from "
        "HCO₃⁻ gives CO₃²⁻ (adding a proton would instead give the conjugate "
        "acid H₂CO₃)."
    ),
    "q_ho_068": (
        "pH = −log[H⁺], so each 10-fold rise in [H⁺] lowers pH by 1 unit. A "
        "1000-fold (10³) increase lowers the pH by 3 units."
    ),
    "q_ho_069": (
        "By the Henderson–Hasselbalch equation, pH = pKa + log([A⁻]/[HA]). When "
        "[A⁻] = [HA] the ratio is 1 and log 1 = 0, so pH = pKa."
    ),
    "q_ho_070": (
        "Formate (HCOO⁻) is the conjugate base produced when formic acid "
        "ionizes (HCOOH ⇌ HCOO⁻ + H⁺). Adding formate — a common ion — shifts "
        "the equilibrium back toward the un-ionized acid (Le Chatelier), so the "
        "acid's percent ionization decreases."
    ),
    "q_ho_071": (
        "At equal concentration, a strong acid ionizes essentially completely "
        "(higher [H⁺], lower pH) while a weak acid ionizes only partially "
        "(lower [H⁺], higher pH). So the weak-acid solution has the higher pH."
    ),
    "q_ho_072": (
        "Enzymes are catalysts: they provide a pathway with a lower activation "
        "energy, speeding the reaction without changing ΔG, the equilibrium "
        "position, or the temperature."
    ),
    "q_ho_073": (
        "By convention, ΔG > 0 marks an endergonic reaction that requires "
        "(absorbs) energy and is nonspontaneous as written; ΔG < 0 marks an "
        "exergonic, energy-releasing, spontaneous reaction."
    ),
    "q_ho_074": (
        "A competitive inhibitor resembles the substrate and binds reversibly "
        "in the active site, directly competing with substrate; allosteric "
        "inhibitors instead bind elsewhere and change the enzyme's "
        "conformation."
    ),
    "q_ho_075": (
        "At saturating substrate, essentially every enzyme active site is "
        "occupied and turning over as fast as it can, so adding more substrate "
        "cannot increase the rate — the reaction reaches its maximum velocity, "
        "Vmax."
    ),
    "q_ho_076": (
        "The pocket where substrate binds and is chemically transformed is the "
        "active site; a mutation there directly affects catalysis. Allosteric "
        "sites and other structural features lie elsewhere."
    ),
    "q_ho_077": (
        "In the induced-fit model, substrate binding induces a conformational "
        "change in the enzyme's active site so it wraps more snugly around the "
        "substrate — unlike the static, pre-formed complementarity of "
        "lock-and-key."
    ),
    "q_ho_078": (
        "Well above the optimum temperature, the noncovalent interactions "
        "holding an enzyme's tertiary structure break down; the enzyme "
        "denatures, its active site is disrupted, and activity falls sharply."
    ),
    "q_ho_079": (
        "Competitive inhibitors bind reversibly in the active site, so they "
        "compete with substrate. Flooding the system with excess substrate "
        "outcompetes the inhibitor and restores the reaction rate toward Vmax."
    ),
    "q_ho_080": (
        "An enzyme (and any inhibitor of it) affects only kinetics — how fast "
        "equilibrium is reached — not the position of equilibrium. Keq and ΔG "
        "are thermodynamic properties set by the reactants and products, "
        "unchanged by a catalyst or its inhibitor."
    ),
    "q_ho_081": (
        "Km, the Michaelis constant, is defined as the substrate concentration "
        "at which the reaction velocity equals one-half of Vmax; it is an "
        "inverse index of the enzyme's affinity for substrate."
    ),
    "q_ho_082": (
        "Km is the substrate concentration giving half-maximal velocity. A "
        "higher Km means more substrate is needed to half-saturate the enzyme, "
        "i.e., the enzyme binds substrate less tightly — lower affinity."
    ),
    "q_ho_083": (
        "A catalyst lowers the activation energy for both the forward and "
        "reverse steps by the same amount, so it speeds attainment of "
        "equilibrium without changing the equilibrium position, Keq, or the "
        "final amounts of product."
    ),
    "q_ho_084": (
        "Temperature raises the average kinetic energy, so a greater fraction "
        "of colliding molecules meet or exceed the activation-energy threshold. "
        "The activation energy itself is not lowered by heating (that is a "
        "catalyst's role)."
    ),
    "q_ho_085": (
        "The rate constant k depends on temperature (and on whether a catalyst "
        "is present), not on reactant concentrations. Changing concentration, "
        "volume, or pressure changes the rate but leaves k itself unchanged at "
        "constant temperature."
    ),
    "q_ho_086": (
        "The overall order is the sum of the exponents in the rate law: 2 (for "
        "X) + 1 (for Y) = 3."
    ),
    "q_ho_087": (
        "For a reaction first order in A, rate ∝ [A]¹. Tripling [A] multiplies "
        "the rate by 3¹ = 3."
    ),
    "q_ho_088": (
        "A zero-order reaction has rate = k[A]⁰ = k, independent of [A]. "
        "Changing the concentration of A therefore has no effect on the rate."
    ),
    "q_ho_089": (
        "Activation energy (Ea) is the minimum energy that colliding molecules "
        "must have for a reaction to occur; it sets the height of the kinetic "
        "barrier and is distinct from thermodynamic quantities like ΔG or ΔH."
    ),
    "q_ho_090": (
        "In a rate law, the exponent on each reactant is that reactant's "
        "reaction order (determined experimentally); m is the order with "
        "respect to A. It is not necessarily the stoichiometric coefficient."
    ),
}


# ---------------------------------------------------------------------------
# Per-choice feedback (static, NO-AI). In ADDITION to the single correct-answer
# ``explanation`` above, every question carries a ``choice_feedback`` array
# aligned 1:1 with ``choices`` (same length and order). Each entry is a short,
# source-grounded rationale: for the CORRECT choice, a terse "why this is
# correct"; for each distractor, the SPECIFIC reason that choice fails (name the
# misconception, the execution error for a trap, or briefly why a near-miss is
# tempting but wrong). The stored ``choice_diagnosis`` tags are only HINTS —
# these strings are authored to state the actual reason, never to restate the
# choice. Shown to the student after answering (the chosen distractor's line is
# the AI-off fallback and the baseline the AI explainer must beat). Keyed by
# stable question id; every id in the emitted bank MUST have a full-length,
# all-non-empty entry (enforced by scripts/validate_data.py).
# ---------------------------------------------------------------------------
CHOICE_FEEDBACK: dict[str, list[str]] = {
    # --- DEV -----------------------------------------------------------------
    "q_dev_001": [
        "Incorrect — the isocitrate→α-ketoglutarate step is an oxidative decarboxylation that makes NADH and CO₂, not a nucleoside triphosphate.",
        "Correct — succinyl-CoA→succinate is the cycle's only substrate-level phosphorylation; cleaving the high-energy thioester bond directly makes one GTP/ATP.",
        "Incorrect — fumarate→malate is a hydration step; it adds water and produces no GTP/ATP.",
        "Incorrect — malate→oxaloacetate is a redox step that reduces NAD⁺ to NADH; it makes no GTP/ATP.",
    ],
    "q_dev_002": [
        "Correct — high ADP signals low energy charge, so ADP allosterically activates key respiratory enzymes to speed ATP production.",
        "Incorrect — this reverses the energy-charge signal; ATP (not ADP) is the inhibitor, while high ADP activates.",
        "Incorrect — ADP is an allosteric regulator of respiration, so it does affect enzyme activity.",
        "Incorrect — high ADP accelerates, not slows, the pathway to replenish ATP.",
    ],
    "q_dev_003": [
        "Incorrect — this statement is true (endergonic +ΔG, exergonic −ΔG), so it is not the false comparison asked for.",
        "Incorrect — this is a true statement (endergonic consume, exergonic release energy), so it isn't the false one.",
        "Incorrect — this is true: both reaction types must overcome an activation barrier.",
        "Correct — this is the false statement; ΔG describes thermodynamics, not speed, so an exergonic reaction can be slow and an endergonic one fast.",
    ],
    "q_dev_004": [
        "Incorrect — ΔG is a thermodynamic quantity and doesn't reveal the activation-energy barrier.",
        "Correct — a lower activation energy lets more collisions succeed per unit time, so relative reaction rates are the best proxy for relative Ea.",
        "Incorrect — ideal environmental conditions don't indicate the activation energy.",
        "Incorrect — spontaneity is thermodynamic; a spontaneous reaction can still be slow, so it doesn't reveal Ea.",
    ],
    "q_dev_005": [
        "Incorrect — increasing affinity describes an allosteric activator, not an inhibitor.",
        "Incorrect — binding the active site directly describes competitive inhibition, not allosteric.",
        "Correct — an allosteric inhibitor binds away from the active site and reshapes it, lowering substrate affinity.",
        "Incorrect — a substrate mimic that binds the active site is a competitive inhibitor, not an allosteric one.",
    ],
    "q_dev_006": [
        "Incorrect — NaOH consumes H⁺ and shifts NH₃ + H₂O ⇌ NH₄⁺ + OH⁻ backward, lowering conversion.",
        "Correct — added HCl neutralizes OH⁻ and protonates NH₃, pulling the equilibrium toward NH₄⁺ and raising percent conversion.",
        "Incorrect — NH₄Cl adds the common ion NH₄⁺, shifting back toward NH₃ and lowering conversion.",
        "Incorrect — adding more NH₃ raises the amount but not the fraction converted to NH₄⁺.",
    ],
    "q_dev_007": [
        "Incorrect — this reverses the inverse relation; HF is the stronger acid, so F⁻ is the weaker conjugate base.",
        "Correct — HCN is far weaker than HF, so its conjugate base CN⁻ is the stronger base.",
        "Incorrect — the parent acids differ greatly in strength, so their conjugate bases are not equally strong.",
        "Incorrect — conjugate bases of weak acids do act as bases in water.",
    ],
    "q_dev_008": [
        "Correct — oxidation occurs at the anode and electrons travel through the wire to the cathode ('an ox, red cat').",
        "Incorrect — this reverses both roles; oxidation is at the anode, not the cathode.",
        "Incorrect — electrons flow to the cathode, not back to the anode.",
        "Incorrect — oxidation occurs at the anode, not the cathode.",
    ],
    "q_dev_009": [
        "Incorrect — this reverses the relation; ΔG° = −nFE°cell, so a positive E° gives a negative ΔG°.",
        "Correct — a positive E°cell makes ΔG° negative, so the reaction is spontaneous as written.",
        "Incorrect — a nonzero E° means the cell is not at equilibrium (equilibrium is E = 0).",
        "Incorrect — a spontaneous galvanic cell delivers work without an external power source; that describes electrolysis.",
    ],
    "q_dev_010": [
        "Incorrect — electrons travel through the external wire, not the salt bridge.",
        "Correct — the salt bridge lets ions migrate to keep each half-cell electrically neutral so current continues.",
        "Incorrect — the salt bridge maintains neutrality; it doesn't raise voltage without limit.",
        "Incorrect — the salt bridge doesn't catalyze the electrode reactions.",
    ],
    "q_dev_011": [
        "Incorrect — a strong acid/base pair reacts to completion and provides no buffering.",
        "Correct — a weak acid with its conjugate base neutralizes added base and acid respectively, resisting pH change.",
        "Incorrect — fully neutralizing a weak acid with equal moles of strong base leaves no reserve of weak acid to buffer.",
        "Incorrect — a neutral salt in pure water has no conjugate acid/base pair and cannot buffer.",
    ],
    "q_dev_012": [
        "Correct — with ΔH negative and ΔS positive, ΔG = ΔH − TΔS is negative at every temperature.",
        "Incorrect — this combination gives a positive ΔG at all T (never spontaneous).",
        "Incorrect — ΔH<0, ΔS<0 is spontaneous only at low temperature, not all T.",
        "Incorrect — ΔH>0, ΔS>0 is spontaneous only at high temperature, not all T.",
    ],
    "q_dev_013": [
        "Incorrect — the entropy term is subtracted, not added.",
        "Correct — at constant temperature, ΔG = ΔH − TΔS.",
        "Incorrect — the terms are rearranged and the sign inverted; the correct form is ΔH − TΔS.",
        "Incorrect — the entropy term is subtracted, not multiplied.",
    ],
    "q_dev_014": [
        "Correct — a spontaneous process proceeds on its own once started, without continuous external energy input.",
        "Incorrect — spontaneity says nothing about speed; spontaneous reactions can be slow.",
        "Incorrect — spontaneity doesn't require heat release; endothermic processes can be spontaneous.",
        "Incorrect — a catalyst is not required for spontaneity.",
    ],
    "q_dev_015": [
        "Incorrect — temperature doesn't raise ΔG, and ΔG isn't what sets the rate.",
        "Correct — higher temperature broadens the energy distribution so more collisions meet or exceed Ea.",
        "Incorrect — temperature doesn't lower Ea; only a catalyst does that.",
        "Incorrect — temperature doesn't make the reaction more exothermic (ΔH is fixed).",
    ],
    "q_dev_016": [
        "Incorrect — a catalyst doesn't work by heating the system.",
        "Correct — a catalyst provides an alternate pathway with lower activation energy, so more collisions succeed.",
        "Incorrect — a catalyst doesn't change ΔH or make the reaction more exothermic.",
        "Incorrect — a catalyst speeds both directions equally and doesn't shift the equilibrium position.",
    ],
    "q_dev_017": [
        "Incorrect — concentrations change the rate through the rate law, not the value of k.",
        "Correct — k depends on temperature (Arrhenius) and on whether a catalyst is present.",
        "Incorrect — container volume alone doesn't set k.",
        "Incorrect — k doesn't change as the reaction proceeds over time.",
    ],
    "q_dev_018": [
        "Correct — by the equation of continuity (A·v constant), narrowing the pipe increases the fluid speed.",
        "Incorrect — this reverses continuity; a smaller area means faster, not slower, flow.",
        "Incorrect — speed must change to keep the volume flow rate constant when area changes.",
        "Incorrect — the fluid keeps flowing; its speed increases rather than dropping to zero.",
    ],
    "q_dev_019": [
        "Incorrect — Bernoulli relates speed to pressure, not the constancy of volume flow rate.",
        "Correct — constant Q = A·v follows from conservation of mass, the equation of continuity.",
        "Incorrect — Pascal's principle concerns transmitted pressure, not flow rate.",
        "Incorrect — Archimedes' principle concerns buoyancy, not flow continuity.",
    ],
    "q_dev_020": [
        "Correct — glycolysis makes 4 ATP but invests 2, for a net gain of 2 ATP per glucose.",
        "Incorrect — 4 is the gross ATP produced; the net (after the 2-ATP investment) is 2.",
        "Incorrect — ~36 is the total aerobic yield including oxidative phosphorylation, not glycolysis alone.",
        "Incorrect — glycolysis does net a positive 2 ATP, not zero.",
    ],
    "q_dev_021": [
        "Incorrect — the mitochondrial matrix hosts the citric acid cycle, not glycolysis.",
        "Correct — glycolysis occurs in the cytosol and needs no membranes or organelles.",
        "Incorrect — glycolysis is cytosolic, not nuclear.",
        "Incorrect — glycolysis does not occur in the endoplasmic reticulum.",
    ],
    "q_dev_022": [
        "Incorrect — FADH₂ is produced by the citric acid cycle, not glycolysis.",
        "Incorrect — NADPH is an anabolic / pentose-phosphate carrier, not a glycolytic product.",
        "Correct — glycolysis reduces NAD⁺ to NADH at the glyceraldehyde-3-phosphate dehydrogenase step.",
        "Incorrect — GTP is a nucleotide, not a reduced electron carrier.",
    ],
    "q_dev_023": [
        "Incorrect — citrate is the first product formed, not the regenerated acceptor.",
        "Correct — oxaloacetate is regenerated each turn to accept another acetyl group.",
        "Incorrect — pyruvate is upstream of the cycle, not the acetyl acceptor.",
        "Incorrect — acetyl-CoA is the group donated, not the acceptor that is regenerated.",
    ],
    "q_dev_024": [
        "Incorrect — at low substrate the rate is far below Vmax; saturation requires high [S].",
        "Correct — Vmax is reached when all enzyme active sites are saturated with substrate.",
        "Incorrect — a denatured enzyme loses activity and never reaches Vmax.",
        "Incorrect — a competitive inhibitor lowers the apparent rate, not producing Vmax.",
    ],
    "q_dev_025": [
        "Incorrect — peptidoglycan is a bacterial cell wall, not the membrane framework.",
        "Correct — the phospholipid bilayer is the membrane's structural framework (fluid-mosaic model).",
        "Incorrect — cellulose is a plant cell-wall material, not the membrane.",
        "Incorrect — glycogen is a storage polysaccharide, not a membrane framework.",
    ],
    "q_dev_026": [
        "Incorrect — this reverses it; the phosphate head is hydrophilic and the tails hydrophobic.",
        "Correct — the phosphate head is hydrophilic (polar) and the fatty-acid tails are hydrophobic (nonpolar).",
        "Incorrect — the nonpolar fatty-acid tails are hydrophobic, not hydrophilic.",
        "Incorrect — the polar phosphate head is hydrophilic, not hydrophobic.",
    ],
    "q_dev_027": [
        "Incorrect — two new strands describes the conservative model, which was disproven.",
        "Correct — each daughter helix keeps one parental template strand paired with one new strand.",
        "Incorrect — both strands parental would mean no synthesis occurred.",
        "Incorrect — DNA replication produces DNA, not RNA.",
    ],
    "q_dev_028": [
        "Incorrect — helicase unwinds the helix; it doesn't synthesize DNA.",
        "Correct — DNA polymerase adds nucleotides to the 3′ end, synthesizing 5′→3′.",
        "Incorrect — primase lays down RNA primers, not the DNA strand.",
        "Incorrect — ligase joins fragments; it doesn't synthesize new strands.",
    ],
    "q_dev_029": [
        "Incorrect — helicase unwinds DNA; it doesn't join fragments.",
        "Incorrect — primase makes RNA primers, not phosphodiester joins.",
        "Correct — DNA ligase forms the phosphodiester bonds joining Okazaki fragments.",
        "Incorrect — polymerase extends strands, but ligase seals the final nick.",
    ],
    "q_dev_030": [
        "Incorrect — 1:1 is a testcross ratio, not a heterozygote × heterozygote cross.",
        "Correct — Aa × Aa gives a 3:1 phenotypic ratio (only the aa quarter shows the recessive trait).",
        "Incorrect — 9:3:3:1 is a dihybrid (two-gene) ratio.",
        "Incorrect — 1:2:1 is the genotypic, not phenotypic, ratio.",
    ],
    "q_dev_031": [
        "Incorrect — this swaps the terms; genotype is the genetic makeup, phenotype the observable traits.",
        "Correct — genotype is the genetic makeup and phenotype is the observable characteristics.",
        "Incorrect — allele/gene don't mean 'genetic makeup' versus 'observable traits.'",
        "Incorrect — gamete/zygote are cell types, not the makeup-versus-traits distinction.",
    ],
    "q_dev_032": [
        "Incorrect — sensation/perception/cognition are broad cognitive processes, not the memory stages.",
        "Correct — memory's three basic processes are encoding, storage, and retrieval.",
        "Incorrect — input/output/feedback is a systems metaphor, not the memory model.",
        "Incorrect — acquisition/extinction/recovery are conditioning (learning) terms, not memory stages.",
    ],
    "q_dev_033": [
        "Correct — Miller's classic estimate is about seven, plus or minus two, items.",
        "Incorrect — unlimited capacity describes long-term, not short-term, memory.",
        "Incorrect — one item drastically underestimates short-term capacity.",
        "Incorrect — about 100 items far exceeds short-term memory's limited span.",
    ],
    "q_dev_034": [
        "Incorrect — chunking groups items into larger units; it isn't simple repetition.",
        "Correct — maintaining information by repetition is (maintenance) rehearsal.",
        "Incorrect — retrieval is getting information out, not maintaining it.",
        "Incorrect — encoding failure is a failure to store, not a maintenance strategy.",
    ],
    "q_dev_035": [
        "Incorrect — the food is unlearned, so it's the unconditioned (not conditioned) stimulus.",
        "Correct — food naturally elicits salivation without learning, making it the unconditioned stimulus.",
        "Incorrect — the food is a stimulus, not a response.",
        "Incorrect — food innately triggers salivation, so it isn't neutral.",
    ],
    "q_dev_036": [
        "Incorrect — decreasing behavior describes punishment, not reinforcement.",
        "Correct — a reinforcer increases the likelihood of the behavior it follows.",
        "Incorrect — by definition a reinforcer changes behavior frequency.",
        "Incorrect — reinforcement is not the same as physical punishment.",
    ],
    "q_dev_037": [
        "Correct — presenting the CS repeatedly without the US weakens and eliminates the CR (extinction).",
        "Incorrect — introducing a new unconditioned stimulus doesn't define extinction.",
        "Incorrect — reinforcers belong to operant conditioning, not classical extinction.",
        "Incorrect — a permanent response is the opposite of extinction.",
    ],
    "q_dev_038": [
        "Incorrect — the self-serving bias concerns explaining one's own outcomes, not others' behavior.",
        "Correct — over-attributing others' behavior to internal traits is the fundamental attribution error.",
        "Incorrect — the just-world hypothesis is the belief that people get what they deserve.",
        "Incorrect — the bystander effect concerns helping in groups, not attribution.",
    ],
    "q_dev_039": [
        "Incorrect — obedience is following an authority's orders, not matching group norms.",
        "Correct — adjusting to match a group standard is conformity.",
        "Incorrect — aggression is behavior intended to harm, unrelated to matching a group.",
        "Incorrect — persuasion is attitude change via argument, not aligning to a group standard.",
    ],
    "q_dev_040": [
        "Incorrect — health disparities follow social patterns; they aren't random.",
        "Correct — health disparities are preventable differences in outcomes across social groups.",
        "Incorrect — disparities reflect social determinants, not genetics alone.",
        "Incorrect — disparities are measurable, e.g., by comparing group outcomes.",
    ],
    "q_dev_041": [
        "Incorrect — blood type is an inherited biological trait, not a social determinant.",
        "Correct — education, income, and safe housing are social determinants of health.",
        "Incorrect — a genetic mutation is a biological, not social, factor.",
        "Incorrect — eye color is a biological trait, not a social determinant.",
    ],
    "q_dev_042": [
        "Correct — Pascal's principle: pressure applied to an enclosed fluid is transmitted undiminished throughout.",
        "Incorrect — the applied pressure is transmitted, not lost as heat.",
        "Incorrect — this confuses Pascal's principle with thermal/gas behavior.",
        "Incorrect — pressure is not zero at the bottom; it's transmitted everywhere.",
    ],
    "q_dev_043": [
        "Correct — cognitive dissonance is the discomfort from holding conflicting cognitions or acting against an attitude.",
        "Incorrect — being rewarded relates to reinforcement, not dissonance.",
        "Incorrect — a repeated neutral stimulus relates to habituation/conditioning, not dissonance.",
        "Incorrect — group consensus relates to conformity/groupthink, not dissonance.",
    ],
    "q_dev_044": [
        "Incorrect — an intermediate blend describes incomplete dominance, not codominance.",
        "Correct — in codominance the heterozygote expresses both alleles fully and simultaneously (e.g., AB blood).",
        "Incorrect — expressing only the dominant allele is complete dominance.",
        "Incorrect — codominant heterozygotes are viable and express both alleles.",
    ],
    "q_dev_045": [
        "Incorrect — the author expressly denies that history is 'mere fiction.'",
        "Correct — the passage redefines objectivity as disciplined awareness of perspective, tested against evidence.",
        "Incorrect — the passage doesn't advise avoiding documents; it discusses which to trust.",
        "Incorrect — the passage never claims only eyewitnesses can write accurate history.",
    ],
    "q_dev_046": [
        "Incorrect — the passage explicitly says freedom is 'not simply the quantity of available options.'",
        "Correct — the passage defines freedom as the capacity to choose well among options.",
        "Incorrect — absence of constraints is not the passage's definition of freedom.",
        "Incorrect — avoiding decisions is not what the passage means by freedom.",
    ],
    "q_dev_047": [
        "Incorrect — the author treats pretending to have no assumptions as an obstacle, not a virtue.",
        "Correct — the closing line says such a historian is less likely to reach truth than one who examines her assumptions.",
        "Incorrect — the passage says the opposite: pretending to have none yields less reliable history.",
        "Incorrect — the passage doesn't endorse trusting such a historian without question.",
    ],
    "q_dev_048": [
        "Correct — the phrase contrasts nominal freedom with real freedom, so the two can diverge.",
        "Incorrect — the passage denies that liberty equals the number of choices.",
        "Incorrect — the author clearly cares about practical outcomes ('in practice').",
        "Incorrect — the passage doesn't call for prohibiting choices.",
    ],
    "q_dev_049": [
        "Incorrect — two easy options and satisfaction is the opposite of the paralysis the passage describes.",
        "Correct — the overwhelmed diner who takes long and later regrets mirrors the paradox of choice.",
        "Incorrect — a closed store gives no options, not an excess of them.",
        "Incorrect — having no options isn't the passage's point about having too many.",
    ],
    "q_dev_050": [
        "Incorrect — ignoring conflicting sources is the opposite of testing one's assumptions.",
        "Correct — actively seeking disconfirming evidence applies the passage's logic for objectivity.",
        "Incorrect — writing without primary documents wouldn't test one's assumptions against evidence.",
        "Incorrect — adopting the popular interpretation isn't the disciplined self-testing the passage praises.",
    ],
    # --- HELD_OUT ------------------------------------------------------------
    "q_ho_001": [
        "Correct — Zn is oxidized (loses electrons), reducing Cu²⁺, so it is the reducing agent.",
        "Incorrect — Cu²⁺ is reduced, making it the oxidizing agent, not the reducing agent.",
        "Incorrect — Zn²⁺ is the already-oxidized product, not the reducing agent.",
        "Incorrect — Cu(s) is the product of reduction, not the reducing agent.",
    ],
    "q_ho_002": [
        "Incorrect — raising product-ion concentration raises Q, which lowers (not raises) Ecell.",
        "Correct — higher product-ion concentration increases Q, so by the Nernst equation Ecell decreases.",
        "Incorrect — the Nernst equation makes Ecell depend on ion concentrations.",
        "Incorrect — E° is a fixed constant; concentration changes affect Ecell, not E°'s sign.",
    ],
    "q_ho_003": [
        "Incorrect — producing energy from a spontaneous reaction describes a galvanic cell.",
        "Correct — electrolysis uses external electrical energy to drive a nonspontaneous redox reaction.",
        "Incorrect — electrolysis still involves oxidation–reduction.",
        "Incorrect — electrolysis drives reactions with negative E°cell, not positive.",
    ],
    "q_ho_004": [
        "Incorrect — oxidation, not reduction, occurs at the anode.",
        "Correct — reduction always occurs at the cathode in any electrochemical cell.",
        "Incorrect — the salt bridge maintains neutrality; it isn't an electrode.",
        "Incorrect — the electrolyte is the ion medium, not the site of reduction.",
    ],
    "q_ho_005": [
        "Correct — HCl ionizes fully, so [H⁺] = 10⁻² M and pH = −log(10⁻²) = 2.0.",
        "Incorrect — pH 1.0 would require [H⁺] = 0.10 M; here it is 0.010 M.",
        "Incorrect — 12.0 is the pOH, not the pH of this acidic solution.",
        "Incorrect — 0.010 is the concentration; you must take −log[H⁺].",
    ],
    "q_ho_006": [
        "Incorrect — HCl and NaOH aren't related by one proton, so they aren't a conjugate pair.",
        "Correct — H₂CO₃ and HCO₃⁻ differ by exactly one H⁺, a conjugate acid–base pair.",
        "Incorrect — H₃O⁺ and O²⁻ differ by more than one proton.",
        "Incorrect — CH₃COOH and Cl⁻ are unrelated, not a conjugate pair.",
    ],
    "q_ho_007": [
        "Correct — with [H⁺]=[OH⁻] and Kw=10⁻¹⁴, each is the square root, 1.0×10⁻⁷ M.",
        "Incorrect — 10⁻¹⁴ is Kw itself, not [H⁺]; take its square root.",
        "Incorrect — 1.0 M would be extremely acidic, not neutral.",
        "Incorrect — water autoionizes, so [H⁺] isn't zero.",
    ],
    "q_ho_008": [
        "Incorrect — the pH scale is logarithmic; you can't just subtract (6−4=2).",
        "Incorrect — 10 would be a one-unit difference; here the difference is two units.",
        "Correct — two pH units means 10² = 100 times greater [H⁺].",
        "Incorrect — 1000 corresponds to a three-unit difference, not two.",
    ],
    "q_ho_009": [
        "Correct — with ΔH>0 and ΔS>0, ΔG turns negative only when TΔS outweighs ΔH, i.e., at high T.",
        "Incorrect — at low T the positive ΔH dominates, so it is nonspontaneous.",
        "Incorrect — it isn't spontaneous at all temperatures, only above a threshold.",
        "Incorrect — it does become spontaneous once T is high enough.",
    ],
    "q_ho_010": [
        "Correct — a negative ΔG marks a thermodynamically favorable (spontaneous) reaction.",
        "Incorrect — ΔG says nothing about rate; spontaneous reactions can be slow.",
        "Incorrect — the ΔG sign is about free energy, not enthalpy; the reaction can be exo- or endothermic.",
        "Incorrect — equilibrium corresponds to ΔG = 0, not negative.",
    ],
    "q_ho_011": [
        "Correct — at equilibrium there is no net driving force, so ΔG = 0.",
        "Incorrect — a large negative ΔG indicates a spontaneous drive, not equilibrium.",
        "Incorrect — a large positive ΔG indicates a nonspontaneous direction, not equilibrium.",
        "Incorrect — ΔG equals ΔG° only at standard conditions, not generally at equilibrium.",
    ],
    "q_ho_012": [
        "Incorrect — entropy measures dispersal of energy/matter, not total energy.",
        "Correct — entropy measures the dispersal (disorder) of energy and matter.",
        "Incorrect — reaction rate is a kinetic quantity, unrelated to entropy's definition.",
        "Incorrect — activation energy is a kinetic barrier, not entropy.",
    ],
    "q_ho_013": [
        "Incorrect — 1 counts only A's order; overall order sums all exponents.",
        "Incorrect — 2 is the order in B alone, not the overall order.",
        "Correct — overall order is 1 (A) + 2 (B) = 3.",
        "Incorrect — the reaction isn't zero order; the exponents are nonzero.",
    ],
    "q_ho_014": [
        "Correct — first order means rate ∝ [A], so doubling [A] doubles the rate.",
        "Incorrect — a factor of 4 would be second order, not first.",
        "Incorrect — a first-order rate does change with [A]; it isn't unchanged.",
        "Incorrect — doubling [A] increases the rate; it doesn't halve it.",
    ],
    "q_ho_015": [
        "Incorrect — proportional to [A] is first order, not zero order.",
        "Correct — zero order means rate = k[A]⁰ = k, independent of concentration.",
        "Incorrect — proportional to [A]² is second order.",
        "Incorrect — 'zero order' refers to the exponent, not a literally zero rate.",
    ],
    "q_ho_016": [
        "Incorrect — the products−reactants energy difference is ΔH/ΔG, not Ea.",
        "Correct — Ea is the minimum energy colliding reactants need to reach the transition state.",
        "Incorrect — Ea is a kinetic barrier, distinct from ΔG.",
        "Incorrect — heating raises the fraction of molecules with ≥Ea but doesn't lower Ea itself.",
    ],
    "q_ho_017": [
        "Incorrect — this reverses Bernoulli; faster flow means lower, not higher, pressure.",
        "Correct — by Bernoulli, where speed is higher the pressure is lower (at constant height).",
        "Incorrect — pressure does change with speed per Bernoulli.",
        "Incorrect — pressure decreases but doesn't drop to zero.",
    ],
    "q_ho_018": [
        "Correct — an object floats when the buoyant force equals its own weight.",
        "Incorrect — a zero buoyant force would let the object sink, not float.",
        "Incorrect — buoyant force equals the weight of displaced fluid, not the entire fluid.",
        "Incorrect — atmospheric pressure isn't what balances weight for floating.",
    ],
    "q_ho_019": [
        "Correct — glycolysis yields two pyruvate per glucose, which enter the mitochondrion aerobically.",
        "Incorrect — lactate forms in anaerobic fermentation, not under aerobic conditions.",
        "Incorrect — pyruvate becomes acetyl-CoA only after entering the mitochondrion, and it is 2 per glucose.",
        "Incorrect — ethanol is a yeast fermentation product, not human aerobic glycolysis.",
    ],
    "q_ho_020": [
        "Incorrect — hexokinase catalyzes the first step, not the committed rate-limiting one.",
        "Correct — PFK-1 catalyzes the committed, rate-limiting step of glycolysis.",
        "Incorrect — pyruvate kinase acts at the last step, not the rate-limiting control point.",
        "Incorrect — aldolase cleaves the six-carbon sugar; it isn't the regulatory step.",
    ],
    "q_ho_021": [
        "Correct — the energy-investment phase uses 2 ATP (hexokinase and PFK-1 steps).",
        "Incorrect — 4 ATP is the payoff-phase output, not the investment.",
        "Incorrect — the investment phase does consume ATP, not zero.",
        "Incorrect — 6 overstates the investment; only 2 ATP are used.",
    ],
    "q_ho_022": [
        "Incorrect — ethanol is produced by yeast, not human muscle.",
        "Correct — human muscle reduces pyruvate to lactate anaerobically, regenerating NAD⁺.",
        "Incorrect — pyruvate→acetyl-CoA is the aerobic route and doesn't regenerate NAD⁺ anaerobically.",
        "Incorrect — citrate is a citric-acid-cycle intermediate, not the fermentation product.",
    ],
    "q_ho_023": [
        "Incorrect — one turn releases two CO₂, not one.",
        "Correct — each turn releases 2 CO₂ (isocitrate DH and α-ketoglutarate DH steps).",
        "Incorrect — three CO₂ overcounts; only two are released per turn.",
        "Incorrect — the cycle does release CO₂, not zero.",
    ],
    "q_ho_024": [
        "Incorrect — the cycle captures little energy as ATP directly.",
        "Correct — most energy is stored in the reduced electron carriers NADH and FADH₂.",
        "Incorrect — heat is a byproduct, not the captured energy form.",
        "Incorrect — only 1 GTP per turn is made; most energy is in NADH/FADH₂.",
    ],
    "q_ho_025": [
        "Incorrect — one turn makes 3 NADH, not 1.",
        "Incorrect — 2 undercounts; the cycle makes 3 NADH per acetyl-CoA.",
        "Correct — one turn produces 3 NADH (plus 1 FADH₂ and 1 GTP/ATP).",
        "Incorrect — 4 overcounts NADH; it is 3 (the FADH₂ is a separate carrier).",
    ],
    "q_ho_026": [
        "Incorrect — the allosteric site is regulatory, not where catalysis occurs.",
        "Correct — the active site is where substrate binds and catalysis occurs.",
        "Incorrect — an R group is an amino-acid side chain, not the catalytic region.",
        "Incorrect — the peptide backbone is structural, not the substrate-binding site.",
    ],
    "q_ho_027": [
        "Incorrect — enzymes are catalysts and are regenerated, not consumed.",
        "Correct — in induced fit the active site changes shape to fit the substrate more snugly.",
        "Incorrect — the substrate is chemically converted to product, not left unchanged.",
        "Incorrect — enzymes lower activation energy, not raise it.",
    ],
    "q_ho_028": [
        "Incorrect — above the optimum, heat denatures the enzyme rather than boosting activity endlessly.",
        "Correct — excessive heat denatures the enzyme, distorting the active site and lowering activity.",
        "Incorrect — temperature strongly affects enzyme activity.",
        "Incorrect — extreme heat denatures the enzyme, not merely lowering Km.",
    ],
    "q_ho_029": [
        "Incorrect — simple diffusion needs no ATP; that's active transport.",
        "Correct — a small nonpolar molecule diffuses through the bilayer down its gradient without energy.",
        "Incorrect — needing a transport protein describes facilitated diffusion.",
        "Incorrect — diffusion moves down, not against, the gradient.",
    ],
    "q_ho_030": [
        "Incorrect — simple diffusion is passive and moves down the gradient.",
        "Incorrect — facilitated diffusion is also passive, down-gradient, and needs no energy.",
        "Correct — active transport moves solutes against their gradient and requires energy.",
        "Incorrect — osmosis is passive water movement, not energy-requiring solute transport.",
    ],
    "q_ho_031": [
        "Incorrect — cholesterol doesn't store genetic information.",
        "Correct — cholesterol buffers membrane fluidity across a range of temperatures.",
        "Incorrect — glycolysis is catalyzed by cytosolic enzymes, not cholesterol.",
        "Incorrect — cholesterol sits among the tails; it doesn't form the hydrophilic heads.",
    ],
    "q_ho_032": [
        "Incorrect — osmosis is water movement, not solute diffusion.",
        "Correct — osmosis is the diffusion of water across a selectively permeable membrane.",
        "Incorrect — proteins don't diffuse osmotically across the membrane.",
        "Incorrect — osmosis specifically refers to water, not ions.",
    ],
    "q_ho_033": [
        "Correct — adenine pairs with thymine and guanine with cytosine.",
        "Incorrect — this swaps the partners; A–T and G–C are correct.",
        "Incorrect — uracil is an RNA base, and G pairs with C, not with uracil.",
        "Incorrect — G pairs with C, not with adenine (two purines can't pair).",
    ],
    "q_ho_034": [
        "Incorrect — ligase seals nicks; it doesn't unwind the helix.",
        "Correct — helicase unwinds and separates the two strands at the replication fork.",
        "Incorrect — polymerase synthesizes DNA; it doesn't unwind it.",
        "Incorrect — primase lays RNA primers; it doesn't unwind the helix.",
    ],
    "q_ho_035": [
        "Incorrect — the leading strand is synthesized continuously, not as fragments.",
        "Correct — Okazaki fragments form on the lagging strand, made discontinuously.",
        "Incorrect — 'template-only' isn't a strand where fragments are made.",
        "Incorrect — Okazaki fragments are DNA, not RNA.",
    ],
    "q_ho_036": [
        "Incorrect — the strands are complementary and antiparallel, not identical and parallel.",
        "Correct — DNA strands run antiparallel and are complementary (A–T, G–C).",
        "Incorrect — DNA strands are DNA, not RNA.",
        "Incorrect — paired bases are held by hydrogen bonds, not covalent bonds.",
    ],
    "q_ho_037": [
        "Correct — Aa × Aa gives the genotypic ratio 1 AA : 2 Aa : 1 aa.",
        "Incorrect — 3:1 is the phenotypic, not genotypic, ratio.",
        "Incorrect — 1:1 is a testcross ratio.",
        "Incorrect — segregation produces AA and aa too, not all Aa.",
    ],
    "q_ho_038": [
        "Incorrect — that describes independent assortment, a separate law.",
        "Correct — segregation: the two alleles of a gene separate during gamete formation.",
        "Incorrect — dominance doesn't imply an allele is more common.",
        "Incorrect — blending inheritance was refuted by Mendel's work.",
    ],
    "q_ho_039": [
        "Incorrect — a homozygous dominant partner would mask recessive alleles.",
        "Correct — a testcross uses a homozygous-recessive partner so the unknown's alleles show up.",
        "Incorrect — a heterozygous partner wouldn't cleanly reveal the unknown genotype.",
        "Incorrect — a haploid partner isn't the standard testcross setup.",
    ],
    "q_ho_040": [
        "Incorrect — genes far apart are frequently separated by crossing over.",
        "Correct — distant genes recombine often, assorting nearly independently.",
        "Incorrect — far-apart genes recombine frequently, not never.",
        "Incorrect — the premise states they are on the same chromosome.",
    ],
    "q_ho_041": [
        "Incorrect — sensory memory is brief and fleeting, not permanent.",
        "Incorrect — short-term memory is limited and lasts seconds.",
        "Correct — long-term memory is the relatively permanent, essentially unlimited store.",
        "Incorrect — iconic memory is a brief visual sensory store.",
    ],
    "q_ho_042": [
        "Incorrect — the misinformation effect is a memory distortion, not context matching.",
        "Correct — matching recall and encoding contexts is context-dependent memory (encoding specificity).",
        "Incorrect — proactive interference is old memories disrupting new ones.",
        "Incorrect — the self-reference effect is better memory for self-relevant information.",
    ],
    "q_ho_043": [
        "Incorrect — the spacing effect concerns distributed practice, not list position.",
        "Correct — better recall of the first and last items is the serial position effect.",
        "Incorrect — the misinformation effect is memory distortion.",
        "Incorrect — priming is implicit activation, not list-position recall.",
    ],
    "q_ho_044": [
        "Incorrect — riding a bike is implicit (procedural) memory.",
        "Correct — explicit memory covers consciously recalled facts and events.",
        "Incorrect — conditioned reflexes are implicit memory.",
        "Incorrect — motor skills are procedural (implicit), not explicit.",
    ],
    "q_ho_045": [
        "Incorrect — the newly learned trigger is the conditioned, not unconditioned, stimulus.",
        "Correct — a previously neutral stimulus that elicits a response after pairing is the conditioned stimulus.",
        "Incorrect — this is a stimulus, not a response.",
        "Incorrect — 'reinforcer' is an operant-conditioning term, not classical.",
    ],
    "q_ho_046": [
        "Incorrect — that describes positive punishment (adding a stimulus to decrease behavior).",
        "Correct — negative reinforcement increases behavior by removing an aversive stimulus.",
        "Incorrect — reinforcement increases behavior; decreasing it would be punishment.",
        "Incorrect — adding a stimulus describes positive reinforcement, not negative.",
    ],
    "q_ho_047": [
        "Incorrect — fixed-ratio reinforces after a predictable count, not an unpredictable one.",
        "Correct — reinforcement after an unpredictable number of responses is a variable-ratio schedule.",
        "Incorrect — fixed-interval is time-based, not response-count based.",
        "Incorrect — continuous reinforces every response, not after a varying number.",
    ],
    "q_ho_048": [
        "Incorrect — conformity is matching peers, not following an authority.",
        "Correct — Milgram's shock studies demonstrated obedience to authority.",
        "Incorrect — the bystander effect concerns helping, not following orders.",
        "Incorrect — groupthink is consensus-seeking, not obedience to an authority.",
    ],
    "q_ho_049": [
        "Incorrect — this reverses the effect; more onlookers decrease individual helping.",
        "Correct — the bystander effect: more people present decreases any one person's likelihood of helping.",
        "Incorrect — the number of bystanders does affect helping.",
        "Incorrect — the presence of others reduces, and certainly doesn't guarantee, helping.",
    ],
    "q_ho_050": [
        "Incorrect — attitudes are learned evaluations, not fixed genetic traits.",
        "Correct — an attitude is a favorable or unfavorable evaluation of a person, object, or idea.",
        "Incorrect — an attitude is an evaluative stance, not an involuntary reflex.",
        "Incorrect — an attitude is not a type of memory.",
    ],
    "q_ho_051": [
        "Incorrect — blood type is biological, not a component of SES.",
        "Correct — SES is measured by income, education, and occupation.",
        "Incorrect — height is a biological trait, not an SES measure.",
        "Incorrect — personality type isn't a standard SES component.",
    ],
    "q_ho_052": [
        "Correct — a social gradient means health improves stepwise up the socioeconomic ladder.",
        "Incorrect — the gradient shows health is clearly related to social position.",
        "Incorrect — the gradient affects the whole population, not only the poorest.",
        "Incorrect — the gradient is an association across SES, not wealth directly causing disease.",
    ],
    "q_ho_053": [
        "Incorrect — the passage uses 'vantage point' figuratively, not as a physical location.",
        "Correct — in context it means the historian's particular perspective or standpoint.",
        "Incorrect — 'vantage point' isn't used to mean a factual error.",
        "Incorrect — it refers to perspective, not a historical period.",
    ],
    "q_ho_054": [
        "Incorrect — the author is wary of more options, not unqualifiedly enthusiastic.",
        "Correct — the author shows cautious skepticism about simply adding options.",
        "Incorrect — the author doesn't reject all choice, only excess without judgment.",
        "Incorrect — the author is engaged and argumentative, not indifferent.",
    ],
    "q_ho_055": [
        "Incorrect — the sentence denies, rather than concedes, that history is fiction.",
        "Correct — it anticipates and rebuts the likely misreading that history is just fiction.",
        "Incorrect — it stays on topic, addressing a natural objection.",
        "Incorrect — it supports, not contradicts, the passage's thesis.",
    ],
    "q_ho_056": [
        "Incorrect — the passage doesn't reject meaningful choice; it redefines freedom.",
        "Correct — it qualifies the common assumption by redefining freedom as choosing well.",
        "Incorrect — it doesn't lay out steps of decision-making.",
        "Incorrect — it isn't comparing two product brands.",
    ],
    "q_ho_057": [
        "Correct — evidence that many options bring easy decisions and greater satisfaction directly contradicts the thesis.",
        "Incorrect — longer decision time actually supports, not weakens, the argument.",
        "Incorrect — some people disliking shopping is irrelevant to the options-paralysis claim.",
        "Incorrect — that judgment can be taught is consistent with, not damaging to, the argument.",
    ],
    "q_ho_058": [
        "Correct — a journalist checking her biases against evidence parallels the passage's disciplined self-awareness.",
        "Incorrect — an error-free calculator has no perspective to examine.",
        "Incorrect — a witness refusing to testify doesn't illustrate testing one's assumptions.",
        "Incorrect — a novelist inventing fiction is the opposite of evidence-tested objectivity.",
    ],
    "q_ho_059": [
        "Correct — the pascal is one newton per square meter (force per area).",
        "Incorrect — kg·m/s² is the newton, a unit of force, not pressure.",
        "Incorrect — J·s is not a pressure unit.",
        "Incorrect — N·m is the joule (energy/torque), not pressure.",
    ],
    "q_ho_060": [
        "Incorrect — the example illustrates a point, not that all shopping is harmful.",
        "Correct — the shopper concretely illustrates how an excess of options can reduce satisfaction.",
        "Incorrect — the passage doesn't argue for banning products.",
        "Incorrect — it's an illustrative example, not the author's personal habits.",
    ],
    "q_ho_061": [
        "Correct — water donates a proton to ammonia, so H₂O is the Brønsted–Lowry acid.",
        "Incorrect — NH₃ accepts the proton, making it the base, not the acid.",
        "Incorrect — NH₄⁺ is a product (the conjugate acid), not the reactant donor.",
        "Incorrect — OH⁻ is water's conjugate base, not the proton donor.",
    ],
    "q_ho_062": [
        "Incorrect — donating a proton defines an acid, the opposite of a base.",
        "Correct — a Brønsted–Lowry base accepts a proton.",
        "Incorrect — increasing [H⁺] is the effect of adding an acid.",
        "Incorrect — that is the narrower Arrhenius definition; Brønsted–Lowry bases needn't release OH⁻.",
    ],
    "q_ho_063": [
        "Correct — HCl ionizes completely, so its conjugate base Cl⁻ is extremely weak.",
        "Incorrect — this reverses the inverse relationship; a strong acid gives a weak conjugate base.",
        "Incorrect — Cl⁻ has no proton to donate, so it isn't an acid.",
        "Incorrect — Cl⁻ is essentially inert, not amphoteric.",
    ],
    "q_ho_064": [
        "Incorrect — a strong acid and its salt have no weak-acid/conjugate-base equilibrium to buffer.",
        "Correct — acetic acid and acetate form a conjugate pair, so the mixture buffers pH.",
        "Incorrect — a strong base plus a neutral salt lacks a conjugate weak pair.",
        "Incorrect — a neutral salt alone can't buffer pH.",
    ],
    "q_ho_065": [
        "Incorrect — pH 0 is strongly acidic, not neutral.",
        "Correct — neutral water has [H⁺]=10⁻⁷ M, so pH = 7.",
        "Incorrect — pH 14 is strongly basic, not neutral.",
        "Incorrect — pH depends on [H⁺], not on the quantity of water.",
    ],
    "q_ho_066": [
        "Incorrect — pH 1 would need 0.1 M; the concentration is 10⁻³ M.",
        "Incorrect — pH 2 would need 10⁻² M, not 10⁻³ M.",
        "Correct — a strong acid gives [H⁺]=10⁻³ M, so pH = 3.",
        "Incorrect — 11 has the wrong sign; a strong acid is acidic (pH 3), not basic.",
    ],
    "q_ho_067": [
        "Incorrect — H₂CO₃ is the conjugate acid (adds a proton), not the conjugate base.",
        "Correct — removing one H⁺ from HCO₃⁻ gives the conjugate base CO₃²⁻.",
        "Incorrect — CO₂ is a decomposition product, not the species one proton removed.",
        "Incorrect — OH⁻ is a generic base, not the conjugate of HCO₃⁻.",
    ],
    "q_ho_068": [
        "Correct — pH = −log[H⁺], so a 10³-fold rise in [H⁺] lowers pH by 3 units.",
        "Incorrect — more [H⁺] lowers pH, not raises it.",
        "Incorrect — pH is logarithmic, so it changes by 3 units, not 1000.",
        "Incorrect — changing [H⁺] does change pH.",
    ],
    "q_ho_069": [
        "Correct — when [A⁻]=[HA], the log term is 0, so pH = pKa.",
        "Incorrect — pH 7 ignores the acid's pKa; equal concentrations give pH = pKa.",
        "Incorrect — a 1:1 ratio gives log 1 = 0, so pH = pKa, not pKa + 1.",
        "Incorrect — 14 − pKa is a pOH/pKb-style relation that doesn't apply here.",
    ],
    "q_ho_070": [
        "Correct — added formate (a common ion) shifts ionization back toward the un-ionized acid, lowering percent ionization.",
        "Incorrect — added ions shift the equilibrium backward; percent ionization decreases.",
        "Incorrect — formate is the common ion and does affect the equilibrium.",
        "Incorrect — the solution becomes less ionized, so percent ionization drops rather than rises.",
    ],
    "q_ho_071": [
        "Incorrect — weak acids ionize partially, so this reverses the strong/weak distinction.",
        "Correct — the weak acid ionizes only partially, giving lower [H⁺] and higher pH.",
        "Incorrect — equal concentration doesn't mean equal pH when ionization differs.",
        "Incorrect — a weak acid ionizes partially, not 'not at all.'",
    ],
    "q_ho_072": [
        "Correct — an enzyme lowers the activation energy, speeding the reaction.",
        "Incorrect — enzymes don't change ΔG or make a reaction more exergonic.",
        "Incorrect — enzymes don't work by heating the cell.",
        "Incorrect — enzymes speed both directions and don't shift the equilibrium position.",
    ],
    "q_ho_073": [
        "Incorrect — exergonic means ΔG<0; this reaction has ΔG>0.",
        "Correct — ΔG>0 marks an endergonic, energy-requiring reaction.",
        "Incorrect — ΔG>0 is nonspontaneous as written.",
        "Incorrect — a positive-ΔG reaction isn't impossible; energy input or coupling can drive it.",
    ],
    "q_ho_074": [
        "Correct — a competitive inhibitor binds the active site, blocking substrate access.",
        "Incorrect — binding away from the active site describes noncompetitive/allosteric inhibition.",
        "Incorrect — covalent, permanent binding is irreversible inhibition, not competitive.",
        "Incorrect — competitive inhibition works by occupying the active site, not by lowering temperature.",
    ],
    "q_ho_075": [
        "Correct — the Vmax plateau occurs because all active sites are saturated with substrate.",
        "Incorrect — the plateau is simple saturation, not substrate inhibition.",
        "Incorrect — the enzyme is a catalyst and isn't consumed.",
        "Incorrect — activation energy doesn't rise with substrate to cause the plateau.",
    ],
    "q_ho_076": [
        "Correct — the substrate-binding, catalytic pocket is the active site.",
        "Incorrect — the allosteric site is regulatory, not the substrate-binding pocket.",
        "Incorrect — a distant disulfide bridge isn't the catalytic binding pocket.",
        "Incorrect — a signal peptide is a targeting sequence, not the active site.",
    ],
    "q_ho_077": [
        "Correct — induced fit proposes the active site changes shape as substrate binds.",
        "Incorrect — a rigid, pre-formed match is the older lock-and-key view.",
        "Incorrect — both models require physical binding contact.",
        "Incorrect — induced fit is a conformational change, not a change to the amino-acid sequence.",
    ],
    "q_ho_078": [
        "Correct — far above the optimum the enzyme denatures and activity drops sharply.",
        "Incorrect — activity doesn't rise indefinitely; denaturation halts it.",
        "Incorrect — temperature strongly affects activity.",
        "Incorrect — denaturation destroys the active site rather than exposing more.",
    ],
    "q_ho_079": [
        "Correct — excess substrate outcompetes a competitive inhibitor, restoring the rate toward Vmax.",
        "Incorrect — removing substrate would only slow the reaction further.",
        "Incorrect — lowering enzyme just reduces total activity, not relieving inhibition.",
        "Incorrect — adding more inhibitor deepens, not reverses, the inhibition.",
    ],
    "q_ho_080": [
        "Correct — an inhibitor changes rate (kinetics) but not Keq or ΔG.",
        "Incorrect — slowing a reaction doesn't lower its equilibrium constant.",
        "Incorrect — the inhibitor doesn't alter product thermodynamic stability.",
        "Incorrect — Keq is independent of substrate concentration.",
    ],
    "q_ho_081": [
        "Correct — Km is the substrate concentration giving half of Vmax.",
        "Incorrect — Km corresponds to half-maximal, not full, velocity.",
        "Incorrect — Km isn't where the rate is zero.",
        "Incorrect — Km isn't the point of maximum velocity.",
    ],
    "q_ho_082": [
        "Correct — a higher Km means more substrate is needed to half-saturate, i.e., lower affinity.",
        "Incorrect — this reverses it; a higher Km means weaker, not tighter, binding.",
        "Incorrect — Km and Vmax are independent; a higher Km doesn't imply higher Vmax.",
        "Incorrect — a higher Km requires more substrate to saturate, not less.",
    ],
    "q_ho_083": [
        "Correct — a catalyst speeds forward and reverse equally, leaving the equilibrium position unchanged.",
        "Incorrect — a catalyst doesn't shift equilibrium toward products.",
        "Incorrect — a catalyst doesn't shift equilibrium toward reactants.",
        "Incorrect — a catalyst doesn't change the equilibrium amount of product.",
    ],
    "q_ho_084": [
        "Correct — higher temperature gives more collisions with energy ≥ Ea, speeding the reaction.",
        "Incorrect — temperature doesn't lower Ea; only a catalyst does.",
        "Incorrect — the rate increase is kinetic, not from a ΔG change.",
        "Incorrect — molecular size doesn't change with temperature to affect rate.",
    ],
    "q_ho_085": [
        "Correct — temperature (and a catalyst) changes the value of k.",
        "Incorrect — concentration changes the rate but not k.",
        "Incorrect — volume changes concentrations, not k.",
        "Incorrect — pressure at constant T changes concentrations, not k.",
    ],
    "q_ho_086": [
        "Incorrect — 1 counts one reactant; overall order sums the exponents.",
        "Incorrect — 2 is the order in X alone, not the overall order.",
        "Correct — overall order is 2 (X) + 1 (Y) = 3.",
        "Incorrect — the exponents are nonzero, so it isn't zero order.",
    ],
    "q_ho_087": [
        "Correct — first order means rate ∝ [A], so tripling [A] triples the rate.",
        "Incorrect — doubling would apply only if [A] doubled; here it triples.",
        "Incorrect — a factor of 9 would be second order (3²), not first.",
        "Incorrect — a first-order rate does change with [A].",
    ],
    "q_ho_088": [
        "Correct — zero order means rate = k, independent of [A].",
        "Incorrect — doubling the rate would be first-order behavior.",
        "Incorrect — quadrupling would be second order.",
        "Incorrect — zero-order rate doesn't change, let alone halve.",
    ],
    "q_ho_089": [
        "Correct — the minimum energy colliding molecules need to react is the activation energy.",
        "Incorrect — ΔG is a thermodynamic quantity, not the kinetic barrier.",
        "Incorrect — bond dissociation enthalpy is a specific bond quantity, not the reaction's barrier.",
        "Incorrect — ΔH is the enthalpy change, not the barrier to reacting.",
    ],
    "q_ho_090": [
        "Correct — the exponent m is the reaction order with respect to A (determined experimentally).",
        "Incorrect — the exponent isn't necessarily the stoichiometric coefficient.",
        "Incorrect — m is an order, not the rate constant.",
        "Incorrect — m isn't an equilibrium concentration.",
    ],
    # --- SYNTHESIS -----------------------------------------------------------
    "q_syn_001": [
        "Correct — an unchanged Vmax with a raised apparent Km (2→6 mM) is the signature of competitive inhibition.",
        "Incorrect — noncompetitive inhibition would lower Vmax and leave Km unchanged, but Vmax here is unchanged.",
        "Incorrect — uncompetitive inhibition lowers both Vmax and Km, contrary to the data.",
        "Incorrect — a raised apparent Km with recoverable Vmax indicates reversible competitive, not irreversible covalent, inhibition.",
    ],
    "q_syn_002": [
        "Correct — competitive inhibition is overcome by saturating substrate, so velocity approaches the same Vmax (~100).",
        "Incorrect — at saturating [S] the inhibited curve converges to Vmax, not staying below everywhere.",
        "Incorrect — substrate can't push velocity past Vmax.",
        "Incorrect — velocity becomes [S]-independent only near saturation, not at all concentrations.",
    ],
    "q_syn_003": [
        "Incorrect — [S] is the independent variable, deliberately varied, not a control.",
        "Correct — the total amount of enzyme must be held constant so any velocity difference is attributable to X.",
        "Incorrect — velocity is the measured outcome (dependent variable), not a control.",
        "Incorrect — X's presence is the treatment being compared, so it can't be held constant.",
    ],
    "q_syn_004": [
        "Incorrect — a kinetic inhibitor doesn't change thermodynamic favorability.",
        "Correct — X changes rate/kinetics (apparent Km) but not ΔG or Keq.",
        "Incorrect — Km is kinetic and Keq thermodynamic; changing Km doesn't change Keq.",
        "Incorrect — ΔG doesn't depend on substrate concentration.",
    ],
    "q_syn_005": [
        "Correct — the more positive half-cell (Cu²⁺/Cu, +0.34 V) is reduced (cathode); E°cell = 0.34 − (−0.76) = +1.10 V.",
        "Incorrect — Zn has the more negative potential, so it's the anode, not the cathode.",
        "Incorrect — +0.42 V comes from adding rather than subtracting the potentials.",
        "Incorrect — the sign is wrong; E°cell is +1.10 V, giving a spontaneous cell.",
    ],
    "q_syn_006": [
        "Correct — ΔG° = −(2)(96,500)(1.10) ≈ −212 kJ, so the reaction is spontaneous.",
        "Incorrect — the sign is wrong; with +E°cell, ΔG° is negative (spontaneous).",
        "Incorrect — this uses n = 1; the balanced reaction transfers n = 2 electrons.",
        "Incorrect — a standard cell with nonzero E° is not at equilibrium.",
    ],
    "q_syn_007": [
        "Correct — raising the product ion Zn²⁺ increases Q, lowering Ecell per the Nernst equation.",
        "Incorrect — this is the wrong direction; more product lowers Ecell.",
        "Incorrect — E°cell is a fixed standard constant, not the quantity that changes.",
        "Incorrect — ion concentrations do affect the actual potential Ecell.",
    ],
    "q_syn_008": [
        "Correct — as the cell discharges toward equilibrium, Ecell → 0 and ΔG → 0.",
        "Incorrect — an operating cell loses driving force; Ecell doesn't increase.",
        "Incorrect — approaching equilibrium isn't returning to standard conditions.",
        "Incorrect — Ecell → 0 is right, but ΔG rises toward 0, not toward a large negative value.",
    ],
    "q_syn_009": [
        "Correct — with equal [A⁻] and [HA], Henderson–Hasselbalch gives pH = pKa = 4.74.",
        "Incorrect — equal concentrations don't force pH 7; pH equals the pKa.",
        "Incorrect — 9.26 comes from a 14 − pKa or inverted-ratio error.",
        "Incorrect — 2.37 isn't produced by the correct Henderson–Hasselbalch calculation.",
    ],
    "q_syn_010": [
        "Incorrect — a buffer resists change; pH doesn't drop as sharply as in pure water.",
        "Correct — acetate consumes the added H⁺ (A⁻ + H⁺ → HA), so pH decreases only slightly.",
        "Incorrect — adding acid can't raise the pH.",
        "Incorrect — buffers resist but don't perfectly hold pH constant.",
    ],
    "q_syn_011": [
        "Incorrect — 1:10 is inverted; one unit above the pKa needs more base than acid.",
        "Correct — one pH unit above pKa requires log([A⁻]/[HA]) = 1, a 10:1 ratio.",
        "Incorrect — a 1:1 ratio gives pH = pKa, not one unit above.",
        "Incorrect — 100:1 gives two units above the pKa, not one.",
    ],
    "q_syn_012": [
        "Correct — added acetate (common ion) shifts the equilibrium left, lowering percent dissociation and raising pH.",
        "Incorrect — a common ion shifts left, not right; it doesn't release more H⁺.",
        "Incorrect — acetate is the common ion here, not a mere spectator.",
        "Incorrect — the leftward shift lowers [H⁺], so pH rises rather than drops.",
    ],
    "q_syn_013": [
        "Correct — P(yyrr) = P(yy)×P(rr) = 1/4 × 1/4 = 1/16.",
        "Incorrect — 9/16 is the both-dominant phenotype fraction, not both-recessive.",
        "Incorrect — 1/4 is the probability for one gene; both genes together give 1/16.",
        "Incorrect — 3/16 is a one-dominant/one-recessive class, not yyrr.",
    ],
    "q_syn_014": [
        "Correct — P(Y_)×P(rr) = 3/4 × 1/4 = 3/16.",
        "Incorrect — 9/16 is both-dominant, ignoring that shape is recessive here.",
        "Incorrect — 1/16 is both-recessive, not one dominant and one recessive.",
        "Incorrect — 3/4 is only the color probability, not the combined fraction.",
    ],
    "q_syn_015": [
        "Correct — ½ yellow : ½ green shows Yy; all round despite the rr tester shows RR — so YyRR.",
        "Incorrect — this maps the ratios to the wrong genes.",
        "Incorrect — YyRr would give some wrinkled offspring, but all were round.",
        "Incorrect — YYRR would give all yellow, but offspring were ½ green.",
    ],
    "q_syn_016": [
        "Incorrect — 2 counts only glycolysis; the two TCA turns add 2 more GTP.",
        "Correct — substrate-level only: 2 (glycolysis) + 0 (pyruvate→acetyl-CoA) + 2 (TCA) = 4.",
        "Incorrect — ~36 includes oxidative phosphorylation, which is excluded here.",
        "Incorrect — 30 also includes oxidative phosphorylation, not counted here.",
    ],
    "q_syn_017": [
        "Incorrect — this reverses osmosis; the cell interior is hypertonic, so water enters.",
        "Correct — the 300 mOsm interior is hypertonic to the 100 mOsm bath, so water enters and the cell may lyse.",
        "Incorrect — 300 vs 100 mOsm are not equal, so the solutions aren't isotonic.",
        "Incorrect — water (not solute) crosses; the membrane isn't freely permeable to the solutes.",
    ],
    "q_syn_018": [
        "Correct — the antiparallel complement of 5′-TACGGA-3′, written 5′→3′, is 5′-TCCGTA-3′.",
        "Incorrect — this is the base complement but written in the wrong (3′→5′) orientation.",
        "Incorrect — this just copies the template rather than pairing complementary bases.",
        "Incorrect — DNA uses thymine, not uracil.",
    ],
    "q_syn_019": [
        "Correct — T > ΔH/ΔS = 50,000/150 ≈ 333 K.",
        "Incorrect — this fails to convert ΔH to joules (a unit error).",
        "Incorrect — 3.0 K comes from mishandling the exponents/units.",
        "Incorrect — with ΔS>0 the TΔS term wins at high T, so it does become spontaneous.",
    ],
    "q_syn_020": [
        "Correct — doubling [A] doubles rate (1st order in A); doubling [B] quadruples it (2nd order in B), so rate = k[A][B]².",
        "Incorrect — this transposes the orders; A is first order and B is second.",
        "Incorrect — B is second order (rate ×4 when [B] doubles), not first.",
        "Incorrect — A is first order (rate ×2 when [A] doubles), not second.",
    ],
    "q_syn_021": [
        "Incorrect — slow doesn't mean nonspontaneous; ΔG is truly −100 kJ/mol.",
        "Correct — a very negative ΔG with a high activation energy is spontaneous yet kinetically slow.",
        "Incorrect — slow isn't the same as being at equilibrium.",
        "Incorrect — a catalyst lowers Ea, not ΔG.",
    ],
    "q_syn_022": [
        "Correct — halving the area doubles the speed (continuity); faster flow means lower pressure (Bernoulli).",
        "Incorrect — narrowing speeds the flow, not slows it.",
        "Incorrect — speed doubling is right, but faster flow lowers pressure, not raises it.",
        "Incorrect — speed does change; halving the area doubles it.",
    ],
    "q_syn_023": [
        "Correct — v₂ = A₁v₁/A₂ = (6.0 × 2.0)/2.0 = 6.0 m/s.",
        "Incorrect — this inverts the area ratio.",
        "Incorrect — speed changes when the area changes; it isn't unchanged.",
        "Incorrect — 18 m/s misapplies the area ratio.",
    ],
    "q_syn_024": [
        "Incorrect — equal concentration doesn't give equal pH when ionization differs.",
        "Correct — HCl ionizes completely, giving higher [H⁺] and the lower pH.",
        "Incorrect — acetic acid is the weaker acid, so it has the higher pH.",
        "Incorrect — acids aren't pH-neutral.",
    ],
    "q_syn_025": [
        "Incorrect — a slot machine is response-based (ratio), not time-based (interval).",
        "Correct — payout after an unpredictable number of plays is a variable-ratio schedule.",
        "Incorrect — this is a reinforcement schedule, not negative reinforcement.",
        "Incorrect — the payout count is unpredictable (variable), not fixed.",
    ],
    "q_syn_026": [
        "Incorrect — no pleasant stimulus is added; an aversive one (the headache) is removed.",
        "Correct — removing the aversive headache strengthens the behavior — negative reinforcement.",
        "Incorrect — the behavior increases, so it's reinforcement, not punishment.",
        "Incorrect — nothing pleasant is taken away; this is negative reinforcement.",
    ],
    "q_syn_027": [
        "Correct — judging another as clumsy is the fundamental attribution error; blaming the floor for one's own trip is the actor–observer bias.",
        "Incorrect — this reverses the two biases.",
        "Incorrect — neither the just-world hypothesis nor conformity fits these attribution judgments.",
        "Incorrect — the bystander effect and obedience don't describe these attributions.",
    ],
    "q_syn_028": [
        "Correct — resolving conflicting cognitions by changing a belief is reduction of cognitive dissonance.",
        "Incorrect — this is attitude change, not associative (classical) learning.",
        "Incorrect — the bystander effect is unrelated to belief change.",
        "Incorrect — this is a cognitive process, not operant reinforcement.",
    ],
    "q_syn_029": [
        "Incorrect — this is about matching context, not list position.",
        "Correct — recall best when the test context matches the study context is context-dependent (encoding-specificity) memory.",
        "Incorrect — proactive interference is competing memories, not context matching.",
        "Incorrect — chunking is an encoding strategy, not a retrieval-context effect.",
    ],
    "q_syn_030": [
        "Correct — mortality falls at each income step, the hallmark of a social gradient in health.",
        "Incorrect — the data show a clear monotonic pattern, not randomness.",
        "Incorrect — risk falls at every step, not only at the very bottom.",
        "Incorrect — a social-gradient pattern reflects social determinants, not genetics alone.",
    ],
}


def _attach_explanation(item: dict) -> None:
    """Attach the static correct-answer explanation by id.

    Every emitted question must carry a non-empty ``explanation`` (enforced by
    scripts/validate_data.py). Fails loudly if an id is missing or blank so a
    new question can never ship without its rationale.
    """
    text = EXPLANATIONS.get(item["id"])
    assert text and text.strip(), f"{item['id']}: missing/blank explanation"
    item["explanation"] = text.strip()


def _attach_choice_feedback(item: dict) -> None:
    """Attach the static per-choice feedback array by id.

    ``choice_feedback`` must align 1:1 with ``choices`` (same length/order) and
    every entry must be non-empty (enforced by scripts/validate_data.py). Fails
    loudly on a missing id or a length/blank mismatch so a positional miscount
    or a new question can never ship without complete per-choice rationale.
    """
    fb = CHOICE_FEEDBACK.get(item["id"])
    assert fb is not None, f"{item['id']}: missing choice_feedback"
    assert len(fb) == len(item["choices"]), (
        f"{item['id']}: choice_feedback length {len(fb)} "
        f"!= choices {len(item['choices'])}"
    )
    for j, entry in enumerate(fb):
        assert entry and entry.strip(), f"{item['id']}: choice_feedback[{j}] blank"
    item["choice_feedback"] = [s.strip() for s in fb]


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

    # Every question (DEV, HELD_OUT, SYNTHESIS) gets its static correct-answer
    # explanation plus its per-choice feedback array. Ids are now final, so
    # attach after id assignment.
    for item in out:
        _attach_explanation(item)
        _attach_choice_feedback(item)

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
        # Static, NO-AI correct-answer explanation (required on every item).
        entry["explanation"] = it["explanation"]
        # Static, NO-AI per-choice feedback aligned 1:1 with choices.
        entry["choice_feedback"] = it["choice_feedback"]
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

#!/usr/bin/env python3
"""Build data/application-practice.json — the application-remediation pool.

WHY THIS FILE EXISTS
--------------------
The science error-diagnosis engine routes a miss to one of two remediation
channels (see docs/ERROR-DIAGNOSIS-SPEC.md):
  * ``content_gap``  -> review the specific backing memory concept
  * ``application``  -> the student HAD the content but failed to DEPLOY it on an
                       integration question, so the fix is *targeted practice on
                       similar integration items*.

That practice pool did not exist, so the ``application`` next-action degraded to
a generic "practice more applied items in [topic]." This builder authors the
real pool so the routing has a concrete destination.

DESIGN / CONSTRAINTS
--------------------
  * SEPARATE FILE. The pool is emitted to data/application-practice.json — it is
    deliberately kept OUT of data/questions.json (the eval/performance bank) so
    there is no leakage confusion. Runtime never calls this script; it only reads
    the emitted JSON.
  * NO LEAKAGE. Every item is an ORIGINAL integration scenario, distinct from the
    dev + held_out stems in questions.json (verified by scripts/eval_leakage.py).
  * NAMED SOURCES, AI OFF. Each item is grounded in the same named OpenStax
    chapters the main bank uses; source_name/source_url/source_location stored.
    No AI generation at runtime.
  * APPLICATION/SYNTHESIS ONLY. cognitive_demand is application or synthesis
    (multi-step, deploy-the-concept) — never recall.
  * SCIENCE ONLY. The ``application`` diagnosis is a science-engine signal; CARS
    is performance-only with no cognitive_demand, so it is excluded here.

STORAGE MARKERS (so the wiring pass can query the pool by topic)
----------------------------------------------------------------
  * ``pool``    == "application_practice"   (identifies membership in this pool)
  * ``split``   == "remediation"            (keeps it out of dev/held_out logic)
  * ``concept`` == short slug               (the sub-concept the item drills;
    lets the next-action EXCLUDE the just-missed concept and pick diverse items)

Run:  python scripts/build_application_practice.py   (writes the JSON)
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

LETTERS = "ABCD"

# topic_id -> (source_name, source_url). Mirrors data/openstax-sources.json and
# scripts/build_question_bank.py so the pool cites the same named chapters.
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
}


def section_of(topic_id: str) -> str:
    return {"cp": "CP", "bb": "BB", "ps": "PS"}[topic_id[:2]]


def cg(misconception: str) -> dict:
    """A ``content_gap`` distractor: landing here requires a FALSE BELIEF about
    the science, named by ``misconception`` (the content axis)."""
    return {"maps_to": "content_gap", "misconception": misconception}


def trap(kind: str) -> dict:
    """A predictable EXECUTION-error landing (behavioral prior, not content).
    ``maps_to`` is null; ``kind`` in negation|unit|inverse|scaling|transpose|partial."""
    return {"maps_to": None, "trap": kind}


_counters: dict[str, int] = {}


def item(topic, skill, demand, concept, stem, choices, correct, cd, expl, location):
    """One application/synthesis remediation item.

    ``correct`` is the 0-based index of the right choice. ``cd`` is the
    choice_diagnosis list (1:1 with choices; the correct index MUST be None).
    ``concept`` is the sub-concept slug used by the wiring pass to exclude the
    just-missed concept when selecting a remediation set.
    """
    assert len(choices) == 4, stem
    assert len(cd) == 4, stem
    assert cd[correct] is None, f"{concept}: correct index choice_diagnosis must be None"
    assert demand in {"application", "synthesis"}, demand
    _counters[topic] = _counters.get(topic, 0) + 1
    qid = f"ap_{topic}_{_counters[topic]:02d}"
    name, url = SRC[topic]
    return {
        "id": qid,
        "stem": stem,
        "choices": choices,
        "correct": LETTERS[correct],
        "topic_id": topic,
        "section": section_of(topic),
        "skill": skill,
        "cognitive_demand": demand,
        "concept": concept,
        "choice_diagnosis": cd,
        "explanation": expl,
        "source_name": name,
        "source_url": url,
        "source_location": location,
        "split": "remediation",
        "pool": "application_practice",
    }


POOL: list[dict] = [
    # ================= CP: Electrochemistry =================
    item(
        "cp_electrochem", "2", "application", "standard_cell_potential",
        "A galvanic cell is assembled from Ag+(aq) + e- -> Ag(s) (E deg = +0.80 V) "
        "and Ni2+(aq) + 2e- -> Ni(s) (E deg = -0.25 V). Which metal is oxidized, "
        "and what is the standard cell potential E deg_cell?",
        ["Ni is oxidized; E deg_cell = +1.05 V",
         "Ag is oxidized; E deg_cell = +1.05 V",
         "Ni is oxidized; E deg_cell = +0.55 V",
         "Ni is oxidized; E deg_cell = -1.05 V"],
        0,
        [None,
         cg("assigns oxidation to the half-cell with the higher reduction "
            "potential; reverses which electrode is the anode"),
         trap("inverse"),
         trap("negation")],
        "The half-cell with the higher (more positive) reduction potential is "
        "reduced at the cathode, so Ag+/Ag (+0.80 V) is the cathode and Ni is "
        "oxidized at the anode. E deg_cell = E deg_cathode - E deg_anode = "
        "0.80 - (-0.25) = +1.05 V.",
        "Ch. 17.2 Galvanic Cells; Ch. 17.3 Standard Reduction Potentials",
    ),
    item(
        "cp_electrochem", "2", "synthesis", "gibbs_cell_relationship",
        "A spontaneous galvanic cell has a measured standard cell potential "
        "E deg_cell = +0.46 V for a reaction transferring n = 2 electrons. Which "
        "statement about the standard free-energy change and the equilibrium "
        "constant is correct?",
        ["Delta-G deg < 0 and K > 1",
         "Delta-G deg > 0 and K < 1",
         "Delta-G deg < 0 and K < 1",
         "Delta-G deg = 0 and K = 1"],
        0,
        [None,
         cg("thinks a positive E deg_cell gives a positive Delta-G deg; inverts "
            "the sign in Delta-G deg = -nFE deg_cell"),
         cg("gets the Delta-G deg sign right but does not connect Delta-G deg < 0 "
            "to K > 1"),
         cg("assumes standard conditions mean the cell is at equilibrium")],
        "A positive E deg_cell makes Delta-G deg = -nFE deg_cell negative, so the "
        "reaction is spontaneous. Because Delta-G deg = -RT ln K, a negative "
        "Delta-G deg requires K > 1.",
        "Ch. 17.4 The Nernst Equation (Delta-G deg = -nFE deg_cell)",
    ),
    item(
        "cp_electrochem", "2", "application", "nernst_qualitative",
        "A galvanic cell initially operates at standard conditions. The "
        "concentration of the ion being reduced at the cathode is then increased "
        "well above 1 M, with everything else held standard. How does the "
        "measured cell potential Ecell compare to E deg_cell?",
        ["Ecell > E deg_cell",
         "Ecell < E deg_cell",
         "Ecell = E deg_cell",
         "Ecell = 0 V"],
        0,
        [None,
         cg("reverses the Nernst dependence; thinks more cathode reactant lowers "
            "the potential"),
         cg("believes concentration cannot affect cell potential"),
         cg("assumes any concentration change drives the cell to equilibrium")],
        "By the Nernst equation Ecell = E deg_cell - (RT/nF) ln Q. Increasing the "
        "concentration of a reactant (the cathode ion being reduced) lowers the "
        "reaction quotient Q, and a smaller Q raises Ecell above E deg_cell.",
        "Ch. 17.4 The Nernst Equation",
    ),

    # ================= CP: Acids, Bases, Buffers =================
    item(
        "cp_acids_bases", "2", "application", "henderson_hasselbalch",
        "An ammonia buffer is prepared with [NH3] = 0.20 M and [NH4+] = 0.020 M. "
        "For the ammonium ion, pKa = 9.25. What is the pH of the buffer?",
        ["10.25", "8.25", "9.25", "11.25"],
        0,
        [None,
         trap("inverse"),
         cg("assumes pH always equals pKa, ignoring the base/acid ratio"),
         trap("scaling")],
        "Using Henderson-Hasselbalch, pH = pKa + log([base]/[acid]) = "
        "9.25 + log(0.20/0.020) = 9.25 + log(10) = 9.25 + 1 = 10.25.",
        "Ch. 14.6 Buffers (Henderson-Hasselbalch)",
    ),
    item(
        "cp_acids_bases", "2", "application", "buffer_response",
        "A small amount of strong acid (HCl) is added to a carbonate buffer "
        "containing comparable amounts of HCO3- and H2CO3. Which best describes "
        "the result?",
        ["Most of the added H+ is consumed by the conjugate base (HCO3-), so the "
         "pH decreases only slightly",
         "The added H+ has no effect, because a buffer holds pH perfectly constant",
         "The pH rises, because adding acid to a buffer increases pH",
         "The pH drops as much as it would if the acid were added to pure water"],
        0,
        [None,
         cg("believes a buffer fixes pH absolutely rather than resisting change"),
         cg("reverses the direction of pH change when acid is added"),
         cg("thinks the buffer does not neutralize added acid at all")],
        "A buffer resists, but does not prevent, pH change. Added H+ is largely "
        "neutralized by the conjugate base HCO3- (converting it to H2CO3), so the "
        "pH falls only slightly rather than dropping sharply as it would in "
        "unbuffered water.",
        "Ch. 14.6 Buffers (buffer action)",
    ),
    item(
        "cp_acids_bases", "3", "synthesis", "conjugate_strength",
        "Acid HA has Ka = 1x10^-3 and acid HB has Ka = 1x10^-7. Which statement "
        "is correct?",
        ["HB is the weaker acid, so its conjugate base B- is the stronger base",
         "HA is the weaker acid, so its conjugate base A- is the stronger base",
         "HB is the stronger acid because the exponent 7 is larger than 3",
         "The two conjugate bases are equally strong because both acids are weak"],
        0,
        [None,
         cg("reverses the Ka-to-strength relationship (larger Ka = stronger acid)"),
         cg("misreads 1x10^-7 as larger than 1x10^-3"),
         cg("thinks all weak acids yield equally strong conjugate bases")],
        "A larger Ka means a stronger acid, so HA (Ka = 1x10^-3) is stronger and "
        "HB (Ka = 1x10^-7) is weaker. The weaker the acid, the stronger its "
        "conjugate base, so B- is the stronger conjugate base.",
        "Ch. 14.3 Relative Strengths of Acids and Bases",
    ),

    # ================= CP: Thermodynamics =================
    item(
        "cp_thermo", "2", "application", "gibbs_temperature",
        "Dissolving ammonium nitrate in water is endothermic (heat is absorbed) "
        "yet increases the disorder of the system. Treating the enthalpy and "
        "entropy changes as roughly temperature-independent, when is this "
        "dissolution thermodynamically favorable?",
        ["Only when the temperature is high enough for the entropy term to "
         "outweigh the endothermic enthalpy",
         "Only when the temperature is very low",
         "At every temperature, because disorder increases",
         "At no temperature, because heat is absorbed"],
        0,
        [None,
         cg("swaps the temperature dependence; treats the endothermic, "
            "entropy-increasing case as favored only when cold"),
         cg("assumes an entropy increase alone guarantees favorability at any "
            "temperature"),
         cg("assumes an endothermic process can never be favorable")],
        "Free-energy change is enthalpy minus temperature times entropy change. "
        "With a positive enthalpy change and a positive entropy change, the "
        "process becomes favorable only once the temperature is high enough for "
        "the entropy term to exceed the enthalpy cost.",
        "Ch. 16.4 Free Energy (temperature dependence of spontaneity)",
    ),
    item(
        "cp_thermo", "2", "synthesis", "reaction_coupling",
        "An endergonic reaction (Delta-G = +15 kJ/mol) is coupled to ATP "
        "hydrolysis (Delta-G = -30 kJ/mol). What is the overall Delta-G, and is "
        "the coupled process spontaneous?",
        ["-15 kJ/mol; spontaneous",
         "+45 kJ/mol; nonspontaneous",
         "+15 kJ/mol; nonspontaneous",
         "-45 kJ/mol; spontaneous"],
        0,
        [None,
         cg("subtracts magnitudes instead of adding signed values"),
         cg("believes coupling cannot change the overall Delta-G"),
         trap("scaling")],
        "Free-energy changes of coupled reactions add: +15 + (-30) = -15 kJ/mol. "
        "A negative overall Delta-G makes the coupled process spontaneous, which "
        "is how cells drive otherwise unfavorable reactions with ATP hydrolysis.",
        "Ch. 16.4 Free Energy (coupled reactions)",
    ),
    item(
        "cp_thermo", "2", "application", "reverse_reaction_sign",
        "Under a particular set of conditions, the forward direction of a "
        "reaction has a free-energy change of -40 kJ/mol. Under those same "
        "conditions, what is the free-energy change of the reverse direction, and "
        "is the reverse direction favorable?",
        ["+40 kJ/mol; not favorable",
         "-40 kJ/mol; favorable",
         "+40 kJ/mol; favorable",
         "0 kJ/mol; the reverse direction is at equilibrium"],
        0,
        [None,
         cg("thinks the reverse reaction has the same free-energy change as the "
            "forward reaction"),
         cg("flips the sign correctly but still calls a positive free-energy "
            "change favorable"),
         cg("assumes reversing a reaction means it sits at equilibrium")],
        "Reversing a reaction negates its free-energy change, so the reverse "
        "direction is +40 kJ/mol. A positive free-energy change is not favorable, "
        "so under these conditions the reverse direction does not proceed "
        "spontaneously.",
        "Ch. 16.4 Free Energy (sign of Delta-G for reverse reactions)",
    ),

    # ================= CP: Chemical Kinetics =================
    item(
        "cp_kinetics", "2", "application", "first_order_halflife",
        "A reaction is first order in reactant A with a half-life of 20 s. If the "
        "initial concentration of A is doubled, the half-life becomes:",
        ["20 s (unchanged)", "40 s", "10 s", "80 s"],
        0,
        [None,
         trap("scaling"),
         trap("inverse"),
         trap("scaling")],
        "For a first-order reaction, t(1/2) = 0.693/k is independent of the "
        "initial concentration, so doubling [A]0 leaves the half-life at 20 s. "
        "Only zero- and second-order half-lives depend on concentration.",
        "Ch. 12.4 Integrated Rate Laws (half-life)",
    ),
    item(
        "cp_kinetics", "2", "application", "rate_order_determination",
        "When the concentration of reactant A is doubled (all else constant), the "
        "initial rate quadruples. What is the reaction order with respect to A?",
        ["Second order", "First order", "Zero order", "Fourth order"],
        0,
        [None,
         cg("assumes rate is proportional to concentration (first order)"),
         cg("thinks rate independent of concentration despite the change"),
         trap("scaling")],
        "Rate is proportional to [A]^n, so doubling [A] multiplies the rate by "
        "2^n. Since the rate increased 4x = 2^2, n = 2 and the reaction is second "
        "order in A.",
        "Ch. 12.3 Rate Laws (method of initial rates)",
    ),
    item(
        "cp_kinetics", "2", "synthesis", "catalyst_effect",
        "Adding a catalyst speeds up a reversible reaction. Which statement "
        "correctly describes the effect on the rate constants and the equilibrium "
        "position?",
        ["It lowers the activation energy, raising the forward and reverse rate "
         "constants equally, leaving the equilibrium position unchanged",
         "It raises the forward rate constant only, shifting equilibrium toward "
         "products",
         "It increases the equilibrium constant K",
         "It speeds the reaction by raising the activation energy"],
        0,
        [None,
         cg("thinks a catalyst shifts equilibrium toward products"),
         cg("believes a catalyst changes the value of K"),
         cg("reverses the catalyst's effect on activation energy")],
        "A catalyst provides a lower-activation-energy pathway, increasing both "
        "the forward and reverse rate constants by the same factor. It speeds the "
        "approach to equilibrium but does not change K or the equilibrium "
        "position.",
        "Ch. 12.7 Catalysis (effect on rate vs equilibrium)",
    ),

    # ================= CP: Fluids (physics) =================
    item(
        "cp_fluids", "2", "application", "continuity",
        "An incompressible fluid flows steadily through a horizontal pipe whose "
        "cross-sectional area narrows to one-third of its original value. Compared "
        "with the wide section, the fluid speed in the narrow section is:",
        ["3 times greater", "1/3 as great", "unchanged", "9 times greater"],
        0,
        [None,
         trap("inverse"),
         cg("thinks flow speed is unaffected by cross-sectional area"),
         trap("scaling")],
        "The continuity equation A1*v1 = A2*v2 requires that reducing the area to "
        "one-third triples the speed, because the same volume flow rate must pass "
        "through the smaller opening.",
        "Ch. 12.1 Flow Rate and the Equation of Continuity",
    ),
    item(
        "cp_fluids", "2", "synthesis", "bernoulli_pressure",
        "In the same horizontal pipe, the fluid moves faster in the narrow "
        "section than in the wide section. How does the fluid pressure in the "
        "narrow (fast) section compare to that in the wide (slow) section?",
        ["Lower, because faster-moving fluid has lower pressure",
         "Higher, because narrowing the pipe squeezes and compresses the fluid",
         "Unchanged, because the pipe is horizontal",
         "Zero, because all the pressure energy becomes kinetic energy"],
        0,
        [None,
         cg("intuits that pressure rises where a pipe narrows"),
         cg("thinks horizontal flow means pressure cannot vary along the pipe"),
         cg("believes speeding up drops pressure all the way to zero")],
        "For horizontal flow, Bernoulli's equation reduces to P + (1/2)*rho*v^2 = "
        "constant, so where the speed v is higher the pressure P is lower. The "
        "narrow, faster section therefore has lower pressure than the wide "
        "section.",
        "Ch. 12.2 Bernoulli's Equation",
    ),
    item(
        "cp_fluids", "2", "application", "area_radius_scaling",
        "Water flows steadily through a pipe whose radius decreases by half. By "
        "what factor does the flow speed change in the narrower part?",
        ["Increases 4x", "Increases 2x", "Decreases to 1/2", "Unchanged"],
        0,
        [None,
         cg("scales area with radius linearly instead of with radius squared"),
         trap("inverse"),
         cg("thinks flow speed is independent of pipe radius")],
        "Cross-sectional area scales with the square of the radius, so halving "
        "the radius reduces the area to one-fourth. By continuity (A*v = "
        "constant), the speed must increase fourfold.",
        "Ch. 12.1 Flow Rate and the Equation of Continuity",
    ),

    # ================= BB: Glycolysis =================
    item(
        "bb_glycolysis", "2", "application", "net_atp_glycolysis",
        "Glycolysis generates 4 ATP by substrate-level phosphorylation but "
        "consumes 2 ATP in its early (energy-investment) steps. What is the net "
        "ATP yield per glucose from glycolysis alone?",
        ["2 ATP", "4 ATP", "6 ATP", "0 ATP"],
        0,
        [None,
         trap("partial"),
         trap("scaling"),
         cg("thinks the ATP investment cancels the entire ATP payoff")],
        "Glycolysis invests 2 ATP in the energy-investment phase and produces 4 "
        "ATP in the payoff phase, for a net gain of 4 - 2 = 2 ATP per glucose "
        "(along with 2 NADH).",
        "Ch. 7.2 Glycolysis (energy investment vs payoff)",
    ),
    item(
        "bb_glycolysis", "2", "synthesis", "fermentation_nad_regeneration",
        "In the absence of oxygen, cells reduce pyruvate to lactate (or ethanol). "
        "Why is this step necessary to keep glycolysis running?",
        ["It regenerates NAD+ so the oxidation step of glycolysis can continue",
         "It directly produces most of the cell's ATP from pyruvate",
         "It generates the oxygen needed for the electron transport chain",
         "It converts lactate back into glucose to fuel glycolysis"],
        0,
        [None,
         cg("thinks fermentation itself is a major ATP-producing step"),
         cg("believes fermentation makes oxygen for the ETC"),
         cg("confuses fermentation with gluconeogenesis")],
        "Glycolysis needs NAD+ for its glyceraldehyde-3-phosphate dehydrogenase "
        "step. Without oxygen, NADH cannot be reoxidized by the electron "
        "transport chain, so cells reduce pyruvate to regenerate NAD+ and keep "
        "glycolytic ATP production going.",
        "Ch. 7.2 Glycolysis; Ch. 7.5 Fermentation (NAD+ regeneration)",
    ),
    item(
        "bb_glycolysis", "2", "application", "pfk_feedback",
        "Phosphofructokinase (PFK) catalyzes a committed step of glycolysis and "
        "is inhibited by high levels of ATP. What is the physiological "
        "consequence when cellular ATP is abundant?",
        ["Glycolysis slows, conserving glucose when energy is already plentiful",
         "Glycolysis speeds up to produce even more ATP",
         "PFK is unaffected because ATP is a substrate, not a regulator",
         "Glucose is converted directly into ATP, bypassing glycolysis"],
        0,
        [None,
         cg("reverses feedback logic; expects abundant ATP to accelerate its own "
            "production"),
         cg("does not recognize ATP as an allosteric regulator of PFK"),
         cg("thinks ATP can be made from glucose without the glycolytic pathway")],
        "PFK controls the rate-limiting, committed step of glycolysis. Abundant "
        "ATP allosterically inhibits PFK (feedback inhibition), slowing glycolysis "
        "when the cell's energy charge is already high.",
        "Ch. 7.2 Glycolysis (regulation of PFK)",
    ),

    # ================= BB: Citric Acid Cycle / OXPHOS =================
    item(
        "bb_citric_acid", "2", "synthesis", "electron_carrier_yield",
        "One turn of the citric acid cycle produces 3 NADH and 1 FADH2. If each "
        "NADH yields about 2.5 ATP and each FADH2 about 1.5 ATP through oxidative "
        "phosphorylation, how much ATP comes from these carriers per turn?",
        ["About 9 ATP", "About 4 ATP", "About 10 ATP", "About 1 ATP"],
        0,
        [None,
         cg("counts the number of electron carriers rather than the ATP they "
            "yield"),
         trap("scaling"),
         cg("counts only the substrate-level GTP and ignores the carriers")],
        "3 NADH x 2.5 + 1 FADH2 x 1.5 = 7.5 + 1.5 = 9 ATP from oxidative "
        "phosphorylation per turn (plus 1 GTP from substrate-level "
        "phosphorylation).",
        "Ch. 7.3 Oxidation of Pyruvate and the Citric Acid Cycle; Ch. 7.4 OXPHOS",
    ),
    item(
        "bb_citric_acid", "2", "application", "oxygen_dependence",
        "The citric acid cycle uses no O2 in any of its own reactions, yet it "
        "halts quickly when O2 is absent. Why?",
        ["Without the O2-dependent electron transport chain, NAD+ and FAD are not "
         "regenerated, so the cycle runs out of oxidized carriers",
         "The cycle enzymes require O2 directly as a substrate",
         "Pyruvate cannot be produced in the absence of O2",
         "CO2 cannot be released from the cycle without O2"],
        0,
        [None,
         cg("thinks citric acid cycle enzymes consume O2 directly"),
         cg("believes glycolysis (pyruvate production) requires O2"),
         cg("thinks CO2 release from the cycle depends on O2")],
        "The cycle depends on a supply of NAD+ and FAD. These are regenerated "
        "only when NADH/FADH2 hand electrons to the electron transport chain, "
        "whose terminal acceptor is O2. Without O2 the oxidized carriers run out "
        "and the cycle stalls, even though no cycle enzyme uses O2 directly.",
        "Ch. 7.3 Citric Acid Cycle; Ch. 7.4 Oxidative Phosphorylation",
    ),
    item(
        "bb_citric_acid", "3", "application", "carbon_balance",
        "Per turn of the citric acid cycle, two carbons enter as the acetyl group "
        "of acetyl-CoA. How many carbons leave as CO2, and what does this imply?",
        ["Two carbons leave as CO2, matching the two that entered, so oxaloacetate "
         "is regenerated and the cycle can repeat",
         "No carbons leave; they are all stored in cycle intermediates",
         "Four carbons leave as CO2, depleting the cycle intermediates",
         "Two enter but only one leaves, so oxaloacetate steadily accumulates"],
        0,
        [None,
         cg("does not track that carbons exit the cycle as CO2"),
         cg("miscounts CO2 released per turn"),
         cg("thinks carbon input and output are unbalanced, so an intermediate "
            "accumulates")],
        "Each turn releases two CO2 (at the isocitrate -> alpha-ketoglutarate and "
        "alpha-ketoglutarate -> succinyl-CoA steps), balancing the two carbons of "
        "the acetyl group that entered. This regenerates oxaloacetate so the cycle "
        "can continue.",
        "Ch. 7.3 Oxidation of Pyruvate and the Citric Acid Cycle (carbon accounting)",
    ),

    # ================= BB: Enzymes =================
    item(
        "bb_enzymes", "2", "application", "inhibition_type_identification",
        "A reversible inhibitor binds an enzyme at a site other than the active "
        "site, and its effect cannot be overcome by adding more substrate. How "
        "does it affect Vmax and Km?",
        ["Lowers Vmax; Km is unchanged",
         "Vmax is unchanged; Km increases",
         "Both Vmax and Km increase",
         "Both Vmax and Km decrease"],
        0,
        [None,
         cg("describes competitive inhibition (Vmax unchanged, Km up) instead of "
            "noncompetitive"),
         cg("does not know noncompetitive inhibition lowers Vmax"),
         cg("describes uncompetitive inhibition (both lowered) instead")],
        "An inhibitor that binds away from the active site and is not relieved by "
        "excess substrate is noncompetitive. It effectively removes functional "
        "enzyme, lowering Vmax, while substrate affinity (Km) is unchanged.",
        "Ch. 6.5 Enzymes (competitive vs noncompetitive inhibition)",
    ),
    item(
        "bb_enzymes", "2", "application", "feedback_inhibition",
        "An enzyme early in a biosynthetic pathway is inhibited when the pathway's "
        "final product accumulates. This regulation is best described as:",
        ["Allosteric feedback inhibition that prevents overproduction of the end "
         "product",
         "Competitive inhibition by the pathway substrate",
         "Irreversible covalent inactivation of the enzyme",
         "Denaturation of the enzyme by its own product"],
        0,
        [None,
         cg("confuses the end product acting at a regulatory site with a substrate "
            "competing at the active site"),
         cg("mistakes reversible allosteric regulation for irreversible covalent "
            "modification"),
         cg("thinks product binding denatures rather than allosterically "
            "regulates the enzyme")],
        "The end product binds an allosteric (regulatory) site, changing the "
        "enzyme's conformation and reducing its activity. This feedback inhibition "
        "lets the cell switch off a pathway once enough product has been made.",
        "Ch. 6.5 Enzymes (allosteric regulation and feedback inhibition)",
    ),
    item(
        "bb_enzymes", "2", "application", "denaturation",
        "A human enzyme is maximally active at 37 C and pH 7. At 60 C its activity "
        "falls to nearly zero and does not return when the sample is cooled back "
        "to 37 C. The best explanation is:",
        ["High temperature denatured the enzyme, disrupting its active-site "
         "structure in a way that does not spontaneously reverse",
         "Higher temperature always increases enzyme rate, so the data must be "
         "erroneous",
         "The enzyme simply ran out of substrate at 60 C",
         "Cooling should have fully restored activity, so the enzyme was only "
         "temporarily slowed"],
        0,
        [None,
         cg("believes enzyme rate rises with temperature without limit, ignoring "
            "denaturation"),
         cg("attributes lost activity to substrate depletion rather than protein "
            "structure"),
         cg("assumes denaturation is readily reversible on cooling")],
        "Enzyme rate rises with temperature only until the protein denatures. At "
        "60 C the tertiary structure and active site are disrupted; because such "
        "denaturation is generally not reversible, activity does not return on "
        "cooling.",
        "Ch. 6.5 Enzymes (temperature, pH, and denaturation)",
    ),

    # ================= BB: Membranes & Transport =================
    item(
        "bb_membranes", "2", "application", "osmosis_direction",
        "A red blood cell is placed in a hypertonic solution. What happens to the "
        "cell, and why?",
        ["It shrinks (crenates) as water moves out toward the higher external "
         "solute concentration",
         "It swells and bursts as water moves into the cell",
         "Nothing happens, because the membrane is impermeable to water",
         "It shrinks because solutes are pumped out of the cell"],
        0,
        [None,
         cg("reverses the direction of osmosis (treats the solution as hypotonic)"),
         cg("thinks the membrane blocks water movement"),
         cg("attributes volume change to solute movement rather than osmotic water "
            "movement")],
        "Water moves by osmosis from lower to higher solute concentration. In a "
        "hypertonic solution the outside is more concentrated, so water leaves the "
        "cell and it shrinks (crenates).",
        "Ch. 5.2 Passive Transport (osmosis and tonicity)",
    ),
    item(
        "bb_membranes", "2", "synthesis", "active_transport",
        "A solute is moved across a membrane from a region of low concentration "
        "to a region of high concentration. Which statement must be true?",
        ["The process requires an energy input, such as ATP or a coupled ion "
         "gradient",
         "It occurs by simple diffusion down the solute's gradient",
         "It requires no energy because membranes are freely permeable",
         "It occurs only directly through the lipid bilayer, without proteins"],
        0,
        [None,
         cg("thinks movement against a gradient can occur by passive diffusion"),
         cg("believes transport never requires energy"),
         cg("ignores that against-gradient transport needs membrane proteins")],
        "Moving a solute against its concentration gradient (low to high) is "
        "active transport and requires energy, supplied directly by ATP (primary "
        "active transport) or by a previously established ion gradient (secondary "
        "active transport).",
        "Ch. 5.3 Active Transport",
    ),
    item(
        "bb_membranes", "2", "application", "facilitated_diffusion_saturation",
        "Glucose entry into a cell via a carrier protein rises with external "
        "glucose but levels off at high concentrations, whereas simple diffusion "
        "of a small nonpolar gas does not level off. What accounts for the "
        "difference?",
        ["Carrier proteins are limited in number and become saturated; simple "
         "diffusion has no carriers to saturate",
         "Glucose diffuses faster than gases at high concentration",
         "Simple diffusion also saturates, so the observation must be wrong",
         "Glucose is nonpolar and needs no transporter"],
        0,
        [None,
         cg("does not connect the plateau to a finite number of carrier proteins"),
         cg("thinks simple diffusion also shows saturation kinetics"),
         cg("misclassifies glucose as able to cross the bilayer without a "
            "transporter")],
        "Facilitated diffusion depends on a finite number of carrier proteins; "
        "once all carriers are occupied, adding more solute cannot increase the "
        "rate (saturation). Simple diffusion has no carriers, so its rate keeps "
        "rising with concentration.",
        "Ch. 5.2 Passive Transport (facilitated diffusion)",
    ),

    # ================= BB: DNA Structure & Replication =================
    item(
        "bb_dna", "2", "application", "leading_lagging_strand",
        "DNA polymerase can add nucleotides only in the 5' -> 3' direction. At a "
        "replication fork, this constraint means that:",
        ["One new strand is made continuously (leading) while the other is made "
         "in short Okazaki fragments (lagging)",
         "Both new strands are synthesized continuously in the same direction",
         "Both new strands are made entirely as Okazaki fragments",
         "The lagging strand is synthesized in the 3' -> 5' direction"],
        0,
        [None,
         cg("ignores the antiparallel templates that force discontinuous "
            "synthesis on one strand"),
         cg("over-applies discontinuous synthesis to both strands"),
         cg("thinks polymerase can reverse and synthesize 3' -> 5'")],
        "Because the two template strands are antiparallel and polymerase works "
        "only 5' -> 3', the strand templated toward the advancing fork is made "
        "continuously (leading), while the other is made discontinuously as "
        "Okazaki fragments (lagging).",
        "Ch. 14.4 DNA Replication in Prokaryotes (leading vs lagging strand)",
    ),
    item(
        "bb_dna", "2", "synthesis", "semiconservative_replication",
        "DNA labeled entirely with heavy nitrogen (15N) is allowed to replicate "
        "once in a light-nitrogen (14N) medium. What does each daughter duplex "
        "contain, and what does this demonstrate?",
        ["Each duplex has one heavy (old) and one light (new) strand, "
         "demonstrating semiconservative replication",
         "One duplex is fully heavy and one fully light, demonstrating "
         "conservative replication",
         "Both strands of each duplex are new, demonstrating dispersive "
         "replication",
         "All strands stay heavy, because parental DNA strands are not reused"],
        0,
        [None,
         cg("predicts the conservative model's fully-heavy/fully-light result"),
         cg("predicts the dispersive model's all-new result"),
         cg("does not recognize that parental strands serve as templates")],
        "Replication is semiconservative: each parental strand templates a new "
        "one, so after a single round in 14N every duplex has one original (15N) "
        "and one new (14N) strand -- the classic Meselson-Stahl result.",
        "Ch. 14.3 Basics of DNA Replication (semiconservative model)",
    ),
    item(
        "bb_dna", "2", "application", "proofreading",
        "DNA polymerase has 3' -> 5' exonuclease (proofreading) activity. A "
        "mutation that abolishes this proofreading activity would most likely:",
        ["Increase the mutation rate, because misincorporated bases are no longer "
         "removed",
         "Halt DNA replication entirely",
         "Have no effect, because base pairing is always perfectly accurate",
         "Decrease the mutation rate"],
        0,
        [None,
         cg("thinks proofreading is required for the polymerization reaction "
            "itself"),
         cg("assumes replication is error-free even without proofreading"),
         cg("reverses the effect: expects fewer mutations without proofreading")],
        "Proofreading exonuclease removes mismatched nucleotides immediately after "
        "they are added. Losing this activity leaves errors uncorrected, raising "
        "the mutation rate, although polymerization (replication) can still "
        "proceed.",
        "Ch. 14.4 DNA Replication (proofreading by DNA polymerase)",
    ),

    # ================= BB: Mendelian Genetics =================
    item(
        "bb_genetics", "2", "application", "monohybrid_ratio",
        "Two organisms heterozygous for a single gene (Aa x Aa) are crossed. What "
        "fraction of the offspring is expected to show the recessive phenotype?",
        ["1/4", "1/2", "3/4", "0"],
        0,
        [None,
         cg("reports the heterozygote genotype fraction instead of the recessive "
            "phenotype fraction"),
         cg("reports the dominant phenotype fraction (3/4) by mistake"),
         cg("thinks the recessive phenotype cannot appear from two hybrids")],
        "An Aa x Aa cross gives genotypes in a 1 AA : 2 Aa : 1 aa ratio. Only aa "
        "(1/4) shows the recessive phenotype; the other 3/4 show the dominant "
        "phenotype.",
        "Ch. 12.2 Characteristics and Traits (monohybrid cross)",
    ),
    item(
        "bb_genetics", "3", "application", "test_cross",
        "An organism displays the dominant phenotype, but whether it is AA or Aa "
        "is unknown. Crossing it with which partner best reveals its genotype?",
        ["A homozygous recessive (aa) individual",
         "A homozygous dominant (AA) individual",
         "Another individual with the same dominant phenotype",
         "Only a heterozygote can be used"],
        0,
        [None,
         cg("chooses a partner whose dominant alleles would mask the unknown "
            "recessive allele"),
         cg("does not realize matching dominant phenotypes hide the genotype"),
         cg("wrongly believes only a heterozygote partner works")],
        "A test cross with a homozygous recessive (aa) partner reveals hidden "
        "alleles: any recessive offspring means the unknown parent is Aa, whereas "
        "all-dominant offspring indicate AA. Crossing with AA would mask the "
        "difference.",
        "Ch. 12.2 Characteristics and Traits (test cross)",
    ),
    item(
        "bb_genetics", "3", "synthesis", "incomplete_dominance_ratio",
        "In snapdragons, red (CR CR) crossed with white (CW CW) yields all pink "
        "(CR CW) F1 plants. If two pink F1 plants are crossed, what phenotype "
        "ratio is expected in the F2 generation?",
        ["1 red : 2 pink : 1 white",
         "3 red : 1 white",
         "All pink",
         "1 red : 1 white"],
        0,
        [None,
         cg("applies complete-dominance 3:1 ratios to an incomplete-dominance "
            "cross"),
         cg("treats blending as permanent, expecting only the intermediate "
            "phenotype"),
         cg("omits the heterozygous (pink) class from the ratio")],
        "With incomplete dominance the heterozygote (pink) is a distinct "
        "phenotype, so the phenotype ratio matches the genotype ratio: CR CR (red) "
        ": CR CW (pink) : CW CW (white) = 1 : 2 : 1.",
        "Ch. 12.3 Laws of Inheritance (incomplete dominance)",
    ),

    # ================= PS: Memory and Cognition =================
    item(
        "ps_memory", "2", "application", "context_dependent_memory",
        "A student studies in a silent library but takes the exam in a noisy hall "
        "and struggles to recall material she clearly learned. This is best "
        "explained by:",
        ["Context-dependent memory -- retrieval is aided when the recall "
         "environment matches the encoding environment",
         "Encoding failure -- the material was never stored in the first place",
         "Proactive interference from earlier learning",
         "Decay of the memory trace over a few minutes"],
        0,
        [None,
         cg("attributes the failure to encoding even though the material was "
            "learned"),
         cg("misapplies proactive interference to an environment-mismatch case"),
         cg("invokes rapid decay rather than a retrieval-cue mismatch")],
        "Context-dependent memory holds that retrieval improves when the recall "
        "context matches the encoding context. The mismatch between the quiet "
        "study setting and the noisy exam hall weakens retrieval cues, hindering "
        "recall of well-learned material.",
        "Ch. 8.2 Parts of the Brain Involved with Memory; Ch. 8.3 Recall/Retrieval",
    ),
    item(
        "ps_memory", "2", "synthesis", "elaborative_rehearsal",
        "One student prepares by repeating definitions verbatim; another links "
        "each concept to personal examples. Why does the second student typically "
        "remember more?",
        ["Elaborative (deep, semantic) rehearsal creates more retrieval routes "
         "than rote maintenance rehearsal",
         "Maintenance rehearsal transfers information to long-term memory more "
         "reliably than elaboration",
         "Repetition is the only route to long-term storage",
         "Personal examples overload working memory and should reduce recall"],
        0,
        [None,
         cg("reverses the depth-of-processing effect, favoring rote repetition"),
         cg("believes rote repetition is the sole path to long-term memory"),
         cg("thinks elaboration harms memory by overloading working memory")],
        "Deep, elaborative processing that ties new material to existing knowledge "
        "creates stronger, more richly cued long-term memories than shallow "
        "maintenance rehearsal (simple repetition), consistent with the "
        "levels-of-processing framework.",
        "Ch. 8.1 How Memory Functions (encoding; levels of processing)",
    ),
    item(
        "ps_memory", "2", "application", "chunking",
        "A person recalls the letter string 'FBICIAIRS' far more easily after "
        "being told to read it as FBI-CIA-IRS. This improvement is due to:",
        ["Chunking -- grouping items into meaningful units expands effective "
         "short-term memory capacity",
         "An increase in the raw capacity of sensory memory",
         "The elimination of rehearsal and decay",
         "Transfer of the letters into procedural memory"],
        0,
        [None,
         cg("attributes the gain to sensory memory rather than chunking of STM"),
         cg("thinks chunking removes decay rather than reorganizing units"),
         cg("misclassifies the recall as procedural (skill) memory")],
        "Short-term memory holds a limited number of units (about 7 +/- 2). "
        "Chunking reorganizes individual letters into a few meaningful groups, so "
        "more information fits within the same capacity, improving recall.",
        "Ch. 8.1 How Memory Functions (short-term memory capacity; chunking)",
    ),

    # ================= PS: Learning and Conditioning =================
    item(
        "ps_learning", "2", "application", "classical_vs_operant",
        "A dog begins to salivate at the sound of a can opener because that sound "
        "has repeatedly preceded feeding. This is an example of:",
        ["Classical conditioning -- a previously neutral stimulus comes to elicit "
         "a reflexive response",
         "Operant conditioning through positive reinforcement",
         "Negative punishment",
         "Observational learning"],
        0,
        [None,
         cg("classifies a reflexive (involuntary) response as operant "
            "conditioning of a voluntary behavior"),
         cg("misapplies punishment to a stimulus-elicited reflex"),
         cg("mistakes stimulus pairing for learning by watching others")],
        "Salivation is an involuntary reflex, and the originally neutral "
        "can-opener sound comes to elicit it after being paired with food. That "
        "neutral-stimulus-to-reflex pairing defines classical conditioning, not "
        "operant conditioning (which involves voluntary behavior and its "
        "consequences).",
        "Ch. 6.2 Classical Conditioning",
    ),
    item(
        "ps_learning", "2", "synthesis", "reinforcement_vs_punishment",
        "A teacher cancels the class's weekend homework whenever students behave "
        "well, and good behavior then increases. This consequence is best "
        "classified as:",
        ["Negative reinforcement -- removing an aversive stimulus to increase a "
         "behavior",
         "Positive reinforcement",
         "Negative punishment",
         "Positive punishment"],
        0,
        [None,
         cg("labels any desirable outcome 'positive reinforcement,' ignoring that "
            "something was removed"),
         cg("confuses reinforcement (behavior increases) with punishment"),
         cg("confuses reinforcement with punishment and misreads the direction")],
        "Because the target behavior increases, this is reinforcement, not "
        "punishment. Since an aversive stimulus (homework) is removed, it is "
        "negative reinforcement -- 'negative' means removal, not 'bad.'",
        "Ch. 6.3 Operant Conditioning (reinforcement vs punishment)",
    ),
    item(
        "ps_learning", "2", "application", "reinforcement_schedule",
        "A gambler keeps playing a slot machine that pays out after an "
        "unpredictable number of plays. Which reinforcement schedule best explains "
        "this persistent, hard-to-extinguish behavior?",
        ["Variable-ratio schedule",
         "Fixed-interval schedule",
         "Continuous reinforcement",
         "Negative punishment"],
        0,
        [None,
         cg("confuses an unpredictable response-based payout with a time-based "
            "schedule"),
         cg("thinks every play is rewarded (continuous reinforcement)"),
         cg("misclassifies a reinforcing outcome as punishment")],
        "Slot machines reward after an unpredictable number of responses -- a "
        "variable-ratio schedule. Such schedules produce high, steady response "
        "rates that are especially resistant to extinction, which is why gambling "
        "can be so persistent.",
        "Ch. 6.3 Operant Conditioning (schedules of reinforcement)",
    ),

    # ================= PS: Social Processes and Behavior =================
    item(
        "ps_social", "2", "application", "attribution_error",
        "Watching a stranger trip, an observer thinks 'how clumsy,' but when she "
        "trips herself she blames the uneven pavement. This pattern reflects:",
        ["The fundamental attribution error (actor-observer bias) -- overweighting "
         "disposition for others and situation for oneself",
         "The self-serving bias applied to another person",
         "Groupthink",
         "The just-world hypothesis"],
        0,
        [None,
         cg("misapplies the self-serving bias to explanations of others' "
            "behavior"),
         cg("invokes a group decision-making bias for an individual attribution"),
         cg("substitutes the just-world hypothesis for an attribution bias")],
        "Attributing others' behavior to their character while attributing one's "
        "own behavior to circumstances is the actor-observer form of the "
        "fundamental attribution error -- a systematic bias toward dispositional "
        "explanations for other people.",
        "Ch. 12.1 What Is Social Psychology? (attribution; fundamental "
        "attribution error)",
    ),
    item(
        "ps_social", "2", "synthesis", "social_influence_types",
        "An employee reluctantly works late after a direct order from a "
        "supervisor. This behavior change is best classified as:",
        ["Obedience -- change in response to a direct command from an authority "
         "figure",
         "Conformity to peer-group norms",
         "Compliance with a persuasive request from an equal",
         "Internalization of a personal value"],
        0,
        [None,
         cg("confuses authority-driven obedience with matching peer norms "
            "(conformity)"),
         cg("labels an authority's command as a peer request (compliance)"),
         cg("mistakes externally ordered behavior for internalized personal "
            "values")],
        "Obedience is behavior change produced by a direct order from a perceived "
        "authority. Conformity is matching group norms without an explicit order, "
        "and compliance follows a request from a non-authority -- neither fits a "
        "supervisor's direct command.",
        "Ch. 12.3 Conformity, Compliance, and Obedience",
    ),
    item(
        "ps_social", "2", "application", "cognitive_dissonance",
        "After volunteering to do a boring task for very little pay, participants "
        "later rate the task as more enjoyable than those who were paid a large "
        "sum. The best explanation is:",
        ["Cognitive dissonance -- with little external justification, people "
         "change their attitude to fit their behavior",
         "Positive reinforcement from receiving the small payment",
         "The mere-exposure effect",
         "Observational learning from other participants"],
        0,
        [None,
         cg("expects a larger reward to produce greater liking, reversing the "
            "dissonance finding"),
         cg("attributes attitude change to mere repeated exposure"),
         cg("attributes the effect to learning by watching others")],
        "Low pay offers little external justification for doing a dull task, "
        "creating dissonance that people resolve by deciding they actually enjoyed "
        "it. High pay supplies enough justification, so no attitude change is "
        "needed -- the classic Festinger-Carlsmith result.",
        "Ch. 12.2 Self-presentation (attitudes and cognitive dissonance)",
    ),

    # ================= PS: Demographics and Health Disparities =================
    item(
        "ps_demographics", "3", "application", "social_determinants",
        "A study finds that a neighborhood's ZIP code predicts residents' life "
        "expectancy better than their genetic profiles do. Which interpretation "
        "is best supported?",
        ["Social determinants of health -- income, environment, and access to "
         "care -- strongly shape health outcomes",
         "Genetics plays no role in any health outcome",
         "ZIP code itself directly causes disease at the molecular level",
         "Life expectancy is essentially fixed at birth"],
        0,
        [None,
         cg("overgeneralizes to claim genetics is irrelevant to all health"),
         cg("treats a geographic proxy as a direct molecular cause"),
         cg("assumes life expectancy is immutable, ignoring social conditions")],
        "When place predicts health more strongly than genes, it points to social "
        "determinants -- income, environment, food and health-care access -- as "
        "major drivers of health disparities, without claiming that genetics is "
        "irrelevant.",
        "Ch. 14.3 Stress and Illness (social determinants of health)",
    ),
    item(
        "ps_demographics", "2", "synthesis", "chronic_stress_illness",
        "Chronic stress is associated with higher rates of cardiovascular "
        "disease. Which mechanism best connects the two?",
        ["Prolonged activation of the stress response (e.g., sustained cortisol "
         "and elevated blood pressure) damages the cardiovascular system over "
         "time",
         "Stress hormones are biologically inert and cannot affect the heart",
         "Stress affects only mood and never physical health",
         "Acute short-term stress and chronic stress harm the body in exactly the "
         "same way"],
        0,
        [None,
         cg("believes stress hormones have no physiological effect on the "
            "cardiovascular system"),
         cg("treats stress as purely psychological with no physical consequences"),
         cg("ignores that duration distinguishes adaptive acute stress from "
            "harmful chronic stress")],
        "The short-term stress response is adaptive, but chronic activation keeps "
        "cortisol and blood pressure elevated, contributing over time to "
        "hypertension and cardiovascular disease -- a key physiological link "
        "between chronic stress and physical illness.",
        "Ch. 14.3 Stress and Illness (stress physiology and disease)",
    ),
    item(
        "ps_demographics", "3", "application", "disparity_interpretation",
        "Group A shows worse diabetes outcomes than Group B. Before concluding "
        "the cause is biological, a researcher should first:",
        ["Check whether differences in access to care and socioeconomic status "
         "account for the outcome gap",
         "Assume the two groups differ genetically",
         "Conclude that the disparity is fixed and cannot be changed",
         "Treat socioeconomic variables as irrelevant to health outcomes"],
        0,
        [None,
         cg("jumps to a genetic explanation without ruling out social factors"),
         cg("assumes disparities are immutable rather than socially driven"),
         cg("dismisses socioeconomic status as a determinant of health")],
        "Health disparities frequently reflect unequal social conditions rather "
        "than inherent biology. Responsible interpretation first tests whether "
        "access to care, income, and other social determinants explain the "
        "outcome gap before invoking genetic causes.",
        "Ch. 14.3 Stress and Illness (interpreting health disparities)",
    ),
]


def main() -> int:
    out = DATA / "application-practice.json"
    out.write_text(
        json.dumps(POOL, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    by_topic: dict[str, int] = {}
    for it in POOL:
        by_topic[it["topic_id"]] = by_topic.get(it["topic_id"], 0) + 1
    print(f"Wrote {len(POOL)} application-practice items -> {out.name}")
    for tid in sorted(by_topic):
        print(f"  {tid}: {by_topic[tid]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

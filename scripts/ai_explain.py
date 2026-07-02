#!/usr/bin/env py -3.12
"""AI post-answer explainer for MCAT Speedrun performance mode.

When a user MISSES a performance question, this produces a short, source-grounded
explanation of *why the specific distractor they chose is wrong* and what the
correct solution is. The whole point of the feature is DIFFERENTIATION: the
feedback is tailored to the EXACT choice the user picked (choice B produces
materially different feedback than choice C on the same question), which a static
correct-answer blurb or a keyword/vector baseline structurally cannot do.

Design (maps to the Friday AI rubric):
  * Attribution — every explanation traces back to the question's named source
    (`source_name` + `source_url`/`source_location`). No untraceable claims.
  * Per-choice differentiation — driven by each question's `choice_diagnosis`
    ground-truth tags:
        content_gap  -> name + correct the SPECIFIC misconception that distractor
                        encodes; remediate via the backing memory concept.
        trap:<enum>  -> name the SPECIFIC execution error (negation/unit/inverse/
                        scaling/transpose/partial) and how to avoid it; remediate
                        via targeted interleaved practice.
        null         -> honest "plausible near-miss, no single misconception";
                        do NOT over-diagnose.
        CARS         -> passage-mapping feedback (no science choice_diagnosis).
  * Provider interface — a real LLM plugs in at `LLMProvider` (see the seam note
    there). Because live LLM calls are NOT assumed available here, the default
    provider is a DETERMINISTIC OFFLINE generator so the eval/baseline/AI-off
    paths are fully reproducible with AI OFF and no network. All reported numbers
    use the offline provider and are labelled as such.

The offline generator is genuinely per-choice-differentiated: it is built from
the `choice_diagnosis` tag + the answer key, NOT by rephrasing the static
`explanation` field. (The static `explanation`, owned by a sibling worker, is the
AI-OFF fallback and the baseline — see `ai_eval_explanations.py`.)

CLI:
    py -3.12 scripts/ai_explain.py --qid q_ho_053 --chose C
    py -3.12 scripts/ai_explain.py --demo
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Chemistry/physics text uses unicode (−, ΔG, ⁻); force UTF-8 stdout on Windows.
try:  # pragma: no cover
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCRIPTS = ROOT / "scripts"

LETTERS = "ABCD"

# --- remediation channels (mirror data/scoring-config.json error_types) --------
CHANNEL_CONTENT_GAP = "content_gap"
CHANNEL_REASONING = "reasoning"
CHANNEL_MISREAD = "misread"
CHANNEL_PASSAGE = "passage_mapping"

# Human phrasing for each execution-error trap (data/questions.json enum).
TRAP_PHRASES = {
    "negation": "you likely flipped a sign or negated a condition "
    "(e.g. spontaneous vs nonspontaneous, +ΔG vs −ΔG)",
    "unit": "you likely dropped or mismatched a unit conversion "
    "(e.g. kJ vs J, or a per-mole factor)",
    "inverse": "you likely inverted a ratio or relationship "
    "(used x where 1/x was needed, or swapped which quantity is on top)",
    "scaling": "you likely mis-scaled by a multiplicative factor "
    "(off by an n, a 2×, or a power of ten)",
    "transpose": "you likely transposed two quantities or values "
    "(swapped which term goes where)",
    "partial": "you likely stopped at a partial/intermediate result "
    "instead of carrying the calculation to completion",
}
TRAP_AVOID = {
    "negation": "Write the sign convention explicitly before you commit.",
    "unit": "Convert everything to one unit system first, then compute.",
    "inverse": "State the relationship in words before plugging in numbers.",
    "scaling": "Re-check the coefficient / n / power-of-ten in the final step.",
    "transpose": "Label each quantity and re-read the final substitution.",
    "partial": "Underline what the question actually asks for and finish the step.",
}


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_questions() -> list[dict]:
    return load_json(DATA / "questions.json")


def load_topic_names() -> dict[str, str]:
    path = DATA / "mcat-outline.v1.json"
    if not path.exists():
        path = DATA / "mcat-outline.example.json"
    names: dict[str, str] = {}
    for section in load_json(path).get("sections", []):
        for topic in section.get("topics", []):
            names[topic["id"]] = topic["name"]
    return names


def load_backing_concepts() -> dict[str, list[str]]:
    """Map question_id -> list of backing memory-concept strings.

    Sourced from scripts/build_flashcards.py CARDS (`supports_question` links).
    This lets a content_gap remediation name the SPECIFIC backing concept, not a
    vague "review this topic". Import is side-effect free (build_flashcards guards
    main under __main__).
    """
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    try:
        from build_flashcards import CARDS  # type: ignore
    except Exception:
        return {}

    def plain(text: str) -> str:
        # Strip cloze markup {{c1::x}} -> x for a readable concept phrase.
        import re

        return re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text)

    mapping: dict[str, list[str]] = {}
    for note_type, text, back, _topic, supports in CARDS:
        concept = plain(text) if note_type == "Cloze" else text
        for qid in (supports.split("|") if supports else []):
            mapping.setdefault(qid.strip(), []).append(concept)
    return mapping


# --------------------------------------------------------------------------- #
# Explanation model
# --------------------------------------------------------------------------- #
@dataclass
class Explanation:
    """A source-grounded, per-choice explanation for a missed question."""

    qid: str
    chosen_index: int
    chosen_letter: str
    correct_letter: str
    error_mode: str  # content_gap | trap:<enum> | near_miss | passage_mapping | correct
    why_wrong: str
    correct_path: str
    next_action: str
    remediation_channel: str
    source_name: str
    source_url: str
    source_location: str
    provider: str
    # A short machine-checkable claim of which choice is correct (safety gate).
    asserted_correct_letter: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def attribution(self) -> str:
        loc = f", {self.source_location}" if self.source_location else ""
        url = f" <{self.source_url}>" if self.source_url else ""
        return f"Source: {self.source_name}{loc}{url}"

    @property
    def is_grounded(self) -> bool:
        """Every AI output must trace to a NAMED source or it scores zero."""
        return bool(self.source_name and self.source_name.strip())

    def render(self) -> str:
        return (
            f"[{self.error_mode}] You picked {self.chosen_letter}; "
            f"correct is {self.correct_letter}.\n"
            f"Why your choice is wrong: {self.why_wrong}\n"
            f"Correct solution: {self.correct_path}\n"
            f"Next action: {self.next_action}\n"
            f"{self.attribution}"
        )

    def to_dict(self) -> dict:
        return {
            "qid": self.qid,
            "chosen_letter": self.chosen_letter,
            "correct_letter": self.correct_letter,
            "asserted_correct_letter": self.asserted_correct_letter,
            "error_mode": self.error_mode,
            "why_wrong": self.why_wrong,
            "correct_path": self.correct_path,
            "next_action": self.next_action,
            "remediation_channel": self.remediation_channel,
            "attribution": self.attribution,
            "is_grounded": self.is_grounded,
            "provider": self.provider,
        }


def diagnose_choice(q: dict, chosen_index: int) -> tuple[str, dict | None]:
    """Return (error_mode, diagnosis_entry) for the chosen index.

    error_mode in {correct, content_gap, trap:<enum>, near_miss, passage_mapping}.
    """
    correct_index = LETTERS.index(q["correct"])
    if chosen_index == correct_index:
        return "correct", None
    if q.get("section") == "CARS":
        return "passage_mapping", None
    cd = q.get("choice_diagnosis")
    if not cd or chosen_index >= len(cd):
        return "near_miss", None
    entry = cd[chosen_index]
    if entry is None:
        return "near_miss", None
    if entry.get("trap"):
        return f"trap:{entry['trap']}", entry
    if entry.get("maps_to") == "content_gap":
        return "content_gap", entry
    return "near_miss", entry


# --------------------------------------------------------------------------- #
# Provider interface
# --------------------------------------------------------------------------- #
class ExplainerProvider:
    """Interface every explainer backend implements."""

    name = "abstract"

    def explain(self, q: dict, chosen_index: int) -> Explanation:  # pragma: no cover
        raise NotImplementedError


class ProviderUnavailable(RuntimeError):
    """Raised when a live provider cannot be reached (no network / no key)."""


class OfflineDeterministicProvider(ExplainerProvider):
    """Deterministic, network-free, per-choice-differentiated generator.

    This is the reproducible stand-in for a live LLM. It composes feedback from
    the `choice_diagnosis` tag + answer key + named source. It is fully
    deterministic (same input -> byte-identical output), so eval numbers are
    reproducible. It does NOT read or rephrase the static `explanation` field.
    """

    name = "offline_deterministic"

    def __init__(
        self,
        topic_names: dict[str, str] | None = None,
        backing: dict[str, list[str]] | None = None,
    ) -> None:
        self.topic_names = topic_names if topic_names is not None else load_topic_names()
        self.backing = backing if backing is not None else load_backing_concepts()

    def _topic(self, q: dict) -> str:
        return self.topic_names.get(q["topic_id"], q["topic_id"])

    def _correct_statement(self, q: dict) -> str:
        ci = LETTERS.index(q["correct"])
        return f"{q['correct']} ({q['choices'][ci]})"

    def _backing_concept(self, qid: str) -> str | None:
        concepts = self.backing.get(qid)
        # Deterministic pick: shortest concept string (stable, readable).
        return min(concepts, key=lambda s: (len(s), s)) if concepts else None

    def explain(self, q: dict, chosen_index: int) -> Explanation:
        error_mode, entry = diagnose_choice(q, chosen_index)
        chosen_letter = LETTERS[chosen_index]
        chosen_text = q["choices"][chosen_index]
        correct_letter = q["correct"]
        correct_stmt = self._correct_statement(q)
        topic = self._topic(q)

        if error_mode == "correct":
            why = "You actually selected the correct choice."
            path = f"The correct answer is {correct_stmt}."
            action = "No remediation needed — keep this concept warm."
            channel = CHANNEL_MISREAD
        elif error_mode == "content_gap":
            misconception = entry.get("misconception", "a topic misconception")
            why = (
                f"Choice {chosen_letter} (\"{chosen_text}\") encodes a specific "
                f"misconception: {misconception}."
            )
            path = (
                f"The correct answer is {correct_stmt}. Correcting the "
                f"misconception resolves the item."
            )
            concept = self._backing_concept(q["id"])
            if concept:
                action = (
                    f"Content gap — review the backing concept for this item: "
                    f"\u201c{concept}\u201d (topic: {topic})."
                )
            else:
                action = f"Content gap — review the memory cards for {topic}."
            channel = CHANNEL_CONTENT_GAP
        elif error_mode.startswith("trap:"):
            trap = error_mode.split(":", 1)[1]
            phrase = TRAP_PHRASES.get(trap, "you made an execution slip")
            avoid = TRAP_AVOID.get(trap, "Slow down on the final step.")
            why = (
                f"Choice {chosen_letter} (\"{chosen_text}\") is an execution trap "
                f"({trap}): {phrase}. Your concept was likely fine; the final "
                f"value is what went wrong."
            )
            path = f"The correct answer is {correct_stmt}. {avoid}"
            action = (
                f"Execution error — do 3 interleaved Skill 2–4 items in {topic}, "
                f"checking the final step each time."
            )
            channel = CHANNEL_REASONING
        elif error_mode == "passage_mapping":
            why = (
                f"Choice {chosen_letter} (\"{chosen_text}\") maps to the wrong part "
                f"of the passage's argument for what this question asks."
            )
            path = (
                f"The correct answer is {correct_stmt}. Trace it to the specific "
                f"sentence(s) in the passage that support it."
            )
            action = (
                f"Passage mapping — do 3 more passage questions in {topic}; "
                f"for each choice, point to the line that proves or kills it."
            )
            channel = CHANNEL_PASSAGE
        else:  # near_miss
            why = (
                f"Choice {chosen_letter} (\"{chosen_text}\") is a plausible "
                f"near-miss; the data tags no single diagnostic misconception, so "
                f"I won't over-diagnose it."
            )
            path = (
                f"The correct answer is {correct_stmt}. Re-read the stem and "
                f"compare the two closest choices directly."
            )
            action = (
                f"Likely careless/near-miss — retry this item timed later "
                f"(no new content) and compare each choice to the stem."
            )
            channel = CHANNEL_MISREAD

        return Explanation(
            qid=q["id"],
            chosen_index=chosen_index,
            chosen_letter=chosen_letter,
            correct_letter=correct_letter,
            error_mode=error_mode,
            why_wrong=why,
            correct_path=path,
            next_action=action,
            remediation_channel=channel,
            source_name=q.get("source_name", ""),
            source_url=q.get("source_url", ""),
            source_location=q.get("source_location", ""),
            provider=self.name,
            asserted_correct_letter=correct_letter,
            tags=[error_mode],
        )


class LLMProvider(ExplainerProvider):
    """SEAM: where a real LLM plugs in.

    This is intentionally NOT wired to a network call. To enable a live model:
      1. Implement `_call_model(prompt)` with your provider SDK (OpenAI, Anthropic,
         a local server, etc.).
      2. Keep the prompt contract below: the model MUST (a) name the correct
         choice letter, (b) explain why the *chosen* distractor is wrong, and
         (c) cite the question's source_name. Pass `choice_diagnosis` in the
         prompt so the model stays per-choice specific.
      3. Return the text; `parse` maps it into an Explanation.
    The eval harness safety gate + pre-registered cutoff still apply to whatever
    this returns, and any output that fails is blocked and replaced by the static
    explanation (AI-off fallback). So a live model can never lower the floor.

    Runtime is offline here, so `explain` raises ProviderUnavailable, and callers
    fall back to OfflineDeterministicProvider (reproducible) or the static text.
    """

    name = "llm"

    def __init__(self, call_model=None) -> None:
        self._call_model = call_model  # inject a real callable to go live

    def build_prompt(self, q: dict, chosen_index: int) -> str:
        cd = q.get("choice_diagnosis")
        diag = cd[chosen_index] if cd and chosen_index < len(cd) else None
        return (
            "You are an MCAT tutor. A student missed this question.\n"
            f"STEM: {q['stem']}\n"
            f"CHOICES: {q['choices']}\n"
            f"CORRECT: {q['correct']}\n"
            f"STUDENT_CHOSE: {LETTERS[chosen_index]}\n"
            f"CHOICE_DIAGNOSIS_FOR_CHOICE: {diag}\n"
            f"SOURCE: {q.get('source_name')} — {q.get('source_location')}\n"
            "Explain, in 3 short parts: (1) why the STUDENT'S chosen answer is "
            "wrong, specific to that choice; (2) the correct solution; (3) one "
            "concrete next action. Name the correct choice letter and cite SOURCE."
        )

    def explain(self, q: dict, chosen_index: int) -> Explanation:
        if self._call_model is None:
            raise ProviderUnavailable(
                "No live model wired. Inject call_model=... to enable the LLM seam."
            )
        # Live path (only runs when a real callable is injected):
        _ = self._call_model(self.build_prompt(q, chosen_index))  # pragma: no cover
        raise ProviderUnavailable(  # pragma: no cover
            "LLMProvider.parse() not implemented — see seam docstring."
        )


def get_provider(prefer_llm: bool = False, call_model=None) -> ExplainerProvider:
    """Return the active AI provider.

    Tries the live LLM only if explicitly requested AND a call_model is injected;
    otherwise returns the deterministic offline provider (default), so the AI
    feature is always runnable offline. AI-OFF (static explanation) is handled by
    the caller, not here.
    """
    if prefer_llm and call_model is not None:
        try:
            provider = LLMProvider(call_model=call_model)
            return provider
        except ProviderUnavailable:
            pass
    return OfflineDeterministicProvider()


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _find(questions: list[dict], qid: str) -> dict:
    for q in questions:
        if q["id"] == qid:
            return q
    raise SystemExit(f"question id not found: {qid}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AI post-answer explainer (offline).")
    ap.add_argument("--qid", help="question id, e.g. q_ho_053")
    ap.add_argument("--chose", help="chosen letter A-D")
    ap.add_argument("--demo", action="store_true", help="show a few examples")
    args = ap.parse_args(argv)

    questions = load_questions()
    provider = OfflineDeterministicProvider()

    if args.demo:
        # Show that the SAME question yields DIFFERENT feedback per distractor.
        q = _find(questions, "q_syn_005")
        print(f"DEMO — one question, different chosen distractors:\n")
        print(f"Q {q['id']}: {q['stem'].splitlines()[-1]}")
        for i in range(4):
            if LETTERS[i] == q["correct"]:
                continue
            print(f"\n--- student chose {LETTERS[i]} ---")
            print(provider.explain(q, i).render())
        return 0

    if not args.qid or not args.chose:
        ap.print_help()
        return 2

    q = _find(questions, args.qid)
    idx = LETTERS.index(args.chose.strip().upper())
    print(provider.explain(q, idx).render())
    return 0


if __name__ == "__main__":
    sys.exit(main())

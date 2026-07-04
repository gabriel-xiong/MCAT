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
import os
import re
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
# Safety gate (canonical — imported by the eval harness too)
# --------------------------------------------------------------------------- #
def safety_block(expl: "Explanation", q: dict) -> bool:
    """Return True if this explanation must be BLOCKED (then replaced by static).

    Blocks the two failures that would let AI misinform a student:
      * ungrounded output (no named source), or
      * an output that asserts the WRONG correct choice.
    This gate runs in front of EVERY live-model output before it can reach a
    student or be scored, so a live model can never lower the floor.
    """
    if not expl.is_grounded:
        return True
    if expl.asserted_correct_letter and expl.asserted_correct_letter != q["correct"]:
        return True
    return False


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


# System instruction shared by every live provider (kept provider-agnostic).
LLM_SYSTEM_PROMPT = (
    "You are an MCAT tutor giving post-answer feedback to a student who MISSED a "
    "question. You are given the item's ground-truth answer key and, for the "
    "student's chosen distractor, a CHOICE_DIAGNOSIS with the specific "
    "misconception or execution-trap it encodes. Stay faithful to that diagnosis "
    "and to the named SOURCE — do not invent facts or a different answer.\n"
    "Return ONLY a compact JSON object with EXACTLY these string keys:\n"
    '  "correct_letter"  : the single correct choice letter (A-D).\n'
    '  "why_wrong"       : why the STUDENT\'S chosen distractor specifically is '
    "wrong. If a misconception is supplied, restate it faithfully (reuse its key "
    "terms). If a trap enum is supplied, name that trap word. If the diagnosis is "
    "null, call it a plausible near-miss and do NOT over-diagnose.\n"
    '  "correct_solution": the correct reasoning path, naming the correct choice.\n'
    '  "next_action"     : one concrete next step for the student.\n'
    "No markdown, no commentary outside the JSON."
)


class LLMProvider(ExplainerProvider):
    """SEAM: where a real LLM plugs in (provider-agnostic).

    A live model is enabled by injecting a `call_model(prompt) -> str` callable
    (see `build_live_call_model_from_env`, which builds one for OpenAI/Anthropic
    from environment config). The prompt contract (LLM_SYSTEM_PROMPT +
    `build_prompt`) requires the model to (a) name the correct choice letter,
    (b) explain why the *chosen* distractor is wrong — informed by the passed
    `choice_diagnosis` — (c) give the correct solution, and (d) stay tied to the
    question's named SOURCE. `parse` maps the model's JSON back into an
    Explanation; the question's own `source_name`/`source_url`/`source_location`
    are attached for attribution (grounding), and the model's asserted correct
    letter is preserved so the safety gate can catch a wrong-answer output.

    The safety gate (`safety_block`) + pre-registered cutoff still apply to
    whatever this returns; failures are blocked and replaced by the static
    explanation (AI-off fallback). So a live model can never lower the floor.

    With no callable injected (AI OFF), `explain` raises ProviderUnavailable and
    callers fall back to OfflineDeterministicProvider or the static text.
    """

    name = "llm"

    def __init__(self, call_model=None, model_label: str = "") -> None:
        self._call_model = call_model  # inject a real callable to go live
        self.model_label = model_label

    def build_prompt(self, q: dict, chosen_index: int) -> str:
        cd = q.get("choice_diagnosis")
        diag = cd[chosen_index] if cd and chosen_index < len(cd) else None
        return (
            f"STEM: {q['stem']}\n"
            f"CHOICES: {q['choices']}\n"
            f"CORRECT: {q['correct']}\n"
            f"STUDENT_CHOSE: {LETTERS[chosen_index]} "
            f"(\"{q['choices'][chosen_index]}\")\n"
            f"CHOICE_DIAGNOSIS_FOR_CHOSEN: {json.dumps(diag)}\n"
            f"SECTION: {q.get('section')}\n"
            f"SOURCE: {q.get('source_name')} — {q.get('source_location')}\n"
            "Produce the JSON described in the system message for THIS chosen "
            "distractor."
        )

    @staticmethod
    def _extract_json(raw: str) -> dict:
        """Tolerantly pull the JSON object out of a model response."""
        text = (raw or "").strip()
        if text.startswith("```"):
            # strip ```json ... ``` fences
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
            raise

    def parse(self, raw: str, q: dict, chosen_index: int) -> Explanation:
        """Map the model's JSON into an Explanation. Grounding (source_*) is
        attached from the question so attribution is guaranteed; the model's
        asserted correct letter is preserved for the safety gate to check."""
        try:
            data = self._extract_json(raw)
        except Exception as exc:  # malformed -> let caller fall back
            raise ProviderUnavailable(f"LLM returned unparseable output: {exc}")

        asserted = str(data.get("correct_letter", "")).strip().upper()[:1]
        why = str(data.get("why_wrong", "")).strip()
        path = str(data.get("correct_solution", "")).strip()
        action = str(data.get("next_action", "")).strip()
        if not (why and path):
            raise ProviderUnavailable("LLM output missing required fields.")

        error_mode, _entry = diagnose_choice(q, chosen_index)
        return Explanation(
            qid=q["id"],
            chosen_index=chosen_index,
            chosen_letter=LETTERS[chosen_index],
            correct_letter=q["correct"],
            error_mode=error_mode,
            why_wrong=why,
            correct_path=path,
            next_action=action or "Review the cited source and retry this item.",
            remediation_channel=_channel_for_mode(error_mode),
            source_name=q.get("source_name", ""),
            source_url=q.get("source_url", ""),
            source_location=q.get("source_location", ""),
            provider=f"llm:{self.model_label}" if self.model_label else "llm",
            asserted_correct_letter=asserted,
            tags=[error_mode, "llm"],
        )

    def explain(self, q: dict, chosen_index: int) -> Explanation:
        if self._call_model is None:
            raise ProviderUnavailable(
                "No live model wired. Inject call_model=... to enable the LLM seam."
            )
        raw = self._call_model(self.build_prompt(q, chosen_index))
        return self.parse(raw, q, chosen_index)


def _channel_for_mode(error_mode: str) -> str:
    if error_mode == "content_gap":
        return CHANNEL_CONTENT_GAP
    if error_mode.startswith("trap:"):
        return CHANNEL_REASONING
    if error_mode == "passage_mapping":
        return CHANNEL_PASSAGE
    return CHANNEL_MISREAD


# --------------------------------------------------------------------------- #
# Live provider config (env-driven, provider-agnostic, lazy SDK imports)
# --------------------------------------------------------------------------- #
def _resolve_api_key(env: dict, provider: str) -> str:
    """Read the key ONLY from the environment. Never logged or defaulted."""
    generic = env.get("MCAT_LLM_API_KEY")
    if generic:
        return generic
    var = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    return env.get(var, "")


DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-3-5-sonnet-latest"}

# Client-side ceiling (seconds) for a single live-LLM call. The SDK defaults
# (minutes, plus automatic retries) mean a slow/hung network call can block for
# a very long time. The UI runs this OFF the GUI thread, but this bound + no
# retries guarantee the worker returns promptly so the "Thinking…" state clears
# instead of spinning forever. Overridable via MCAT_LLM_TIMEOUT.
LLM_TIMEOUT_SECONDS = 15.0


def _timeout_from_env(env: dict, default: float = LLM_TIMEOUT_SECONDS) -> float:
    """Read MCAT_LLM_TIMEOUT (seconds) from env; fall back to the default."""
    raw = (env.get("MCAT_LLM_TIMEOUT") or "").strip()
    if not raw:
        return default
    try:
        val = float(raw)
    except ValueError:
        return default
    return val if val > 0 else default


def _http_post_json(
    url: str, headers: dict[str, str], payload: dict, timeout: float
) -> dict:
    """POST JSON and return the parsed JSON body, using ONLY the stdlib.

    This is the transport used when the provider SDK isn't installed: a live LLM
    call needs only the API key + network, not the ``openai``/``anthropic``
    package. Any HTTP or transport failure is surfaced as ``ProviderUnavailable``
    (the API key is never included in the message).
    """
    import urllib.error
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # 4xx/5xx (auth, model, rate limit…)
        body = ""
        try:
            body = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            pass
        raise ProviderUnavailable(f"HTTP {exc.code} from provider: {body}") from exc
    except urllib.error.URLError as exc:  # DNS / connect / read timeout
        raise ProviderUnavailable(f"transport error: {exc.reason}") from exc


def _make_openai_caller(
    model: str,
    api_key: str,
    *,
    system_prompt: str = LLM_SYSTEM_PROMPT,
    timeout: float = LLM_TIMEOUT_SECONDS,
):
    def _messages(prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

    def call(prompt: str) -> str:
        try:
            import openai  # lazy: only imported when a live call actually happens
        except ImportError:
            # SDK not installed — go direct over HTTPS with just the key. This is
            # the fix for "AI never succeeds" when a valid key is present but the
            # openai package isn't in the environment (no new dependency added).
            data = _http_post_json(
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {api_key}"},
                {
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": _messages(prompt),
                },
                timeout,
            )
            return (data.get("choices") or [{}])[0].get("message", {}).get(
                "content"
            ) or ""

        # timeout bounds connect+read; max_retries=0 keeps the total bounded to
        # a single attempt (the SDK otherwise retries, multiplying the wait).
        client = openai.OpenAI(api_key=api_key, timeout=timeout, max_retries=0)
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=_messages(prompt),
        )
        return resp.choices[0].message.content or ""

    return call


def _make_anthropic_caller(
    model: str,
    api_key: str,
    *,
    system_prompt: str = LLM_SYSTEM_PROMPT,
    timeout: float = LLM_TIMEOUT_SECONDS,
):
    full_system = system_prompt + "\nRespond with the raw JSON object only."

    def call(prompt: str) -> str:
        try:
            import anthropic  # lazy
        except ImportError:
            # SDK not installed — direct HTTPS call with just the key.
            data = _http_post_json(
                "https://api.anthropic.com/v1/messages",
                {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                {
                    "model": model,
                    "max_tokens": 1024,
                    "temperature": 0,
                    "system": full_system,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout,
            )
            return "".join(
                b.get("text", "")
                for b in (data.get("content") or [])
                if b.get("type") == "text"
            )

        client = anthropic.Anthropic(
            api_key=api_key, timeout=timeout, max_retries=0
        )
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=0,
            system=full_system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            b.text for b in msg.content if getattr(b, "type", None) == "text"
        )

    return call


def build_live_call_model_from_env(
    env: dict | None = None,
    *,
    system_prompt: str = LLM_SYSTEM_PROMPT,
    timeout: float | None = None,
):
    """Build a `call_model(prompt) -> str` callable from environment config, or
    return (None, "") when AI is OFF (no provider configured).

    Env contract:
      MCAT_LLM_PROVIDER : "openai" | "anthropic"  (unset -> AI OFF)
      MCAT_LLM_MODEL    : model id (optional; a sensible default is used)
      key               : MCAT_LLM_API_KEY, else OPENAI_API_KEY /
                          ANTHROPIC_API_KEY (read from env ONLY; never logged).

    Returns (callable_or_None, model_label). SDKs are imported lazily inside the
    callable, so this is safe to call with AI OFF or the SDKs not installed.
    """
    if env is None:
        try:
            from mcat_env import ensure_mcat_env_loaded

            ensure_mcat_env_loaded()
        except Exception:
            pass
        env = os.environ
    provider = (env.get("MCAT_LLM_PROVIDER") or "").strip().lower()
    if not provider:
        return None, ""  # AI OFF — caller uses offline/static
    if provider not in ("openai", "anthropic"):
        raise ValueError(
            f"Unknown MCAT_LLM_PROVIDER={provider!r} (expected openai|anthropic)."
        )
    model = (env.get("MCAT_LLM_MODEL") or "").strip() or DEFAULT_MODELS[provider]
    api_key = _resolve_api_key(env, provider)
    if not api_key:
        raise ProviderUnavailable(
            f"No API key for provider={provider}. Set MCAT_LLM_API_KEY or "
            f"{'OPENAI_API_KEY' if provider == 'openai' else 'ANTHROPIC_API_KEY'} "
            "in the environment (never commit it)."
        )
    call_timeout = timeout if timeout is not None else _timeout_from_env(env)
    if provider == "openai":
        caller = _make_openai_caller(
            model, api_key, system_prompt=system_prompt, timeout=call_timeout
        )
    else:
        caller = _make_anthropic_caller(
            model, api_key, system_prompt=system_prompt, timeout=call_timeout
        )
    return caller, f"{provider}:{model}"


def live_provider_from_env(
    env: dict | None = None, *, timeout: float | None = None
) -> "LLMProvider | None":
    """Return a configured live LLMProvider, or None if AI is OFF."""
    caller, label = build_live_call_model_from_env(env, timeout=timeout)
    if caller is None:
        return None
    return LLMProvider(call_model=caller, model_label=label)


def get_provider(prefer_llm: bool = False, call_model=None) -> ExplainerProvider:
    """Return the active AI provider.

    Tries the live LLM only if explicitly requested AND a call_model is injected;
    otherwise returns the deterministic offline provider (default), so the AI
    feature is always runnable offline. AI-OFF (static explanation) is handled by
    the caller / `serve_explanation`, not here.
    """
    if prefer_llm and call_model is not None:
        return LLMProvider(call_model=call_model)
    return OfflineDeterministicProvider()


def static_fallback_explanation(q: dict, chosen_index: int) -> Explanation:
    """The AI-OFF / gate-blocked fallback: a grounded, correct-answer
    Explanation built from the question's static `explanation` text. Always
    grounded and always names the correct choice, so it clears the gate."""
    correct_letter = q["correct"]
    ci = LETTERS.index(correct_letter)
    correct_stmt = f"{correct_letter} ({q['choices'][ci]})"
    expl_text = q.get("explanation") or (
        f"The correct answer is {correct_stmt}. See the cited source."
    )
    error_mode, _ = diagnose_choice(q, chosen_index)
    return Explanation(
        qid=q["id"],
        chosen_index=chosen_index,
        chosen_letter=LETTERS[chosen_index],
        correct_letter=correct_letter,
        error_mode=error_mode,
        why_wrong=str(expl_text),
        correct_path=f"The correct answer is {correct_stmt}.",
        next_action="Review the cited source for this item.",
        remediation_channel=_channel_for_mode(error_mode),
        source_name=q.get("source_name", ""),
        source_url=q.get("source_url", ""),
        source_location=q.get("source_location", ""),
        provider="static_fallback",
        asserted_correct_letter=correct_letter,
        tags=["static_fallback"],
    )


def serve_explanation(
    q: dict,
    chosen_index: int,
    provider: ExplainerProvider | None = None,
) -> Explanation:
    """Serving path with the SAFETY GATE in front of the (optionally live) model.

    Order of preference:
      1. If a live/offline `provider` is given, try it; on any error, fall back.
      2. Run the safety gate; if the output is blocked (ungrounded / wrong
         choice), replace it with the static fallback.
      3. If no provider (AI OFF), serve the static fallback directly.
    Guarantees the student always gets a grounded, correct-answer explanation.
    """
    if provider is not None:
        try:
            expl = provider.explain(q, chosen_index)
            if not safety_block(expl, q):
                return expl
        except ProviderUnavailable:
            pass
        except Exception:
            # Any live-model/network error must not break the app.
            pass
    return static_fallback_explanation(q, chosen_index)


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
    ap.add_argument(
        "--live",
        action="store_true",
        help="use the env-configured live LLM (MCAT_LLM_PROVIDER=...), gated + "
        "falling back to static on any failure",
    )
    args = ap.parse_args(argv)

    questions = load_questions()
    provider: ExplainerProvider | None = OfflineDeterministicProvider()
    if args.live:
        provider = live_provider_from_env()  # None if AI OFF
        if provider is None:
            print("AI OFF (MCAT_LLM_PROVIDER not set) — serving static fallback.")

    if args.demo:
        # Show that the SAME question yields DIFFERENT feedback per distractor.
        # Always deterministic + offline so the illustration is stable.
        demo_provider = OfflineDeterministicProvider()
        q = _find(questions, "q_syn_005")
        print(f"DEMO — one question, different chosen distractors:\n")
        print(f"Q {q['id']}: {q['stem'].splitlines()[-1]}")
        for i in range(4):
            if LETTERS[i] == q["correct"]:
                continue
            print(f"\n--- student chose {LETTERS[i]} ---")
            print(demo_provider.explain(q, i).render())
        return 0

    if not args.qid or not args.chose:
        ap.print_help()
        return 2

    q = _find(questions, args.qid)
    idx = LETTERS.index(args.chose.strip().upper())
    if args.live:
        # Gated serving path: live model, safety gate, static fallback.
        expl = serve_explanation(q, idx, provider)
    else:
        expl = provider.explain(q, idx)
    print(expl.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())

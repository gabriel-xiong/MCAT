#!/usr/bin/env py -3.12
"""Validate MCAT data files (outline, questions, config). No Anki dependency."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# --- §7d paraphrase-gap instrument (data/paraphrase-test.json) --------------
# One row per anchor flashcard concept -> exactly two reworded exam-style
# question ids that test the SAME idea (see docs/PARAPHRASE-TEST.md). Locked to
# the confirmed eval trio; within-topic anchors only; the second stem must be
# held_out so a volunteer has not seen it in a dev performance session.
PARAPHRASE_TRIO = {"cp_acids_bases", "bb_enzymes", "cp_kinetics"}
PARAPHRASE_ROW_FIELDS = {
    "topic_id", "concept", "card_ref", "card_front",
    "question_ids", "session_order",
}
VALID_SESSION_ORDER = {"memory_first", "performance_first"}
# Column order emitted by build_flashcards.py (no header row; leads with '#').
_CARD_COLUMNS = ["note_type", "text", "back", "tags", "supports_question"]

REQUIRED_QUESTION_FIELDS = {
    "id",
    "stem",
    "choices",
    "correct",
    "topic_id",
    "section",
    "skill",
    "source_name",
    "source_url",
    "source_location",
    "split",
    # Static, NO-AI correct-answer rationale shown after answering; also the
    # AI-off fallback / baseline for the AI explainer. Must be non-empty on
    # every question (checked below).
    "explanation",
    # Static, NO-AI per-choice rationale aligned 1:1 with choices (same length
    # and order). Every entry must be a non-empty string (checked below); the
    # chosen distractor's line is the AI-off fallback / AI-explainer baseline.
    "choice_feedback",
}
VALID_SPLITS = {"dev", "held_out"}
VALID_SECTIONS = {"CP", "CARS", "BB", "PS"}
CARS_SECTION = "CARS"
# Question-level difficulty axis for the science error-diagnosis engine.
VALID_COGNITIVE_DEMAND = {"recall", "application", "synthesis"}

# --- application-practice remediation pool (data/application-practice.json) ---
# The curated integration items the `application` diagnosis next-action routes a
# student to (see docs/APPLICATION-PRACTICE-POOL.md). Held to the SAME rigor as
# the main bank, plus: it is a separate pool (marker fields), science-only, and
# strictly application/synthesis (never recall) with an authored choice_diagnosis.
POOL_REQUIRED_FIELDS = {
    "id",
    "stem",
    "choices",
    "correct",
    "topic_id",
    "section",
    "skill",
    "cognitive_demand",
    "concept",
    "choice_diagnosis",
    "explanation",
    "source_name",
    "source_url",
    "source_location",
    "split",
    "pool",
}
POOL_MARKER = "application_practice"
POOL_SPLIT = "remediation"
# The pool is a science-engine destination; CARS is performance-only.
POOL_VALID_SECTIONS = {"CP", "BB", "PS"}
# Remediation items must be genuine integration items, never recall.
POOL_VALID_DEMAND = {"application", "synthesis"}
# choice_diagnosis content-axis mapping (science-only; bulk authoring deferred).
VALID_CHOICE_MAPS_TO = {"content_gap", None}
# Optional predictable-miss trap nudge (EXECUTION-error landing). A trap feeds
# the behavioral/misread prior, never the content axis, so a trap distractor
# carries maps_to null and NO misconception — a mere content confusion must be
# content_gap, not a trap (see docs/ERROR-DIAGNOSIS-SPEC.md "Choice tagging
# methodology").
VALID_TRAP = {"negation", "unit", "inverse", "scaling", "transpose", "partial"}


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def topic_ids(outline: dict) -> set[str]:
    ids: set[str] = set()
    for section in outline.get("sections", []):
        for topic in section.get("topics", []):
            ids.add(topic["id"])
    return ids


def validate_outline(path: Path) -> list[str]:
    errors: list[str] = []
    data = load_json(path)
    if not data.get("sections"):
        errors.append(f"{path.name}: missing sections")
    return errors


def validate_questions(path: Path, valid_topics: set[str]) -> list[str]:
    errors: list[str] = []
    questions = load_json(path)
    if not isinstance(questions, list):
        return [f"{path.name}: root must be a JSON array"]

    seen_ids: set[str] = set()
    for i, q in enumerate(questions):
        missing = REQUIRED_QUESTION_FIELDS - q.keys()
        if missing:
            errors.append(f"{path.name}[{i}]: missing fields {sorted(missing)}")
            continue
        if q["id"] in seen_ids:
            errors.append(f"{path.name}[{i}]: duplicate id {q['id']}")
        seen_ids.add(q["id"])
        if q["split"] not in VALID_SPLITS:
            errors.append(f"{path.name}[{i}]: invalid split {q['split']}")
        if q["section"] not in VALID_SECTIONS:
            errors.append(f"{path.name}[{i}]: invalid section {q['section']}")
        if q["topic_id"] not in valid_topics:
            errors.append(f"{path.name}[{i}]: unknown topic_id {q['topic_id']}")
        if q["correct"] not in {"A", "B", "C", "D"}:
            errors.append(f"{path.name}[{i}]: correct must be A–D")
        if len(q["choices"]) != 4:
            errors.append(f"{path.name}[{i}]: expected 4 choices")
        expl = q.get("explanation")
        if not isinstance(expl, str) or not expl.strip():
            errors.append(
                f"{path.name}[{i}]: explanation must be a non-empty string"
            )
        errors.extend(_validate_choice_feedback(path.name, i, q))

        is_cars = q["section"] == CARS_SECTION
        errors.extend(_validate_cognitive_demand(path.name, i, q, is_cars))
        errors.extend(_validate_choice_diagnosis(path.name, i, q, is_cars))
    return errors


def _validate_cognitive_demand(
    name: str, i: int, q: dict, is_cars: bool
) -> list[str]:
    """Required + valid on science; absent/ignored on CARS."""
    demand = q.get("cognitive_demand")
    if is_cars:
        return []  # CARS uses skill-archetype + pacing, not cognitive_demand
    if demand is None:
        return [f"{name}[{i}]: science question missing cognitive_demand"]
    if demand not in VALID_COGNITIVE_DEMAND:
        return [
            f"{name}[{i}]: invalid cognitive_demand {demand!r} "
            f"(allowed: {sorted(VALID_COGNITIVE_DEMAND)})"
        ]
    return []


def _validate_choice_feedback(name: str, i: int, q: dict) -> list[str]:
    """Static, NO-AI per-choice feedback. Required on every question: a list
    aligned 1:1 with choices (same length/order) whose every entry is a
    non-empty string. Unlike choice_diagnosis this applies to all sections
    (including CARS) and has no correct-index exception — the correct choice
    carries a 'why this is correct' line."""
    errors: list[str] = []
    fb = q.get("choice_feedback")
    if not isinstance(fb, list):
        errors.append(f"{name}[{i}]: choice_feedback must be a list")
        return errors
    if len(fb) != len(q["choices"]):
        errors.append(
            f"{name}[{i}]: choice_feedback length {len(fb)} "
            f"!= choices {len(q['choices'])}"
        )
        return errors
    for j, entry in enumerate(fb):
        if not isinstance(entry, str) or not entry.strip():
            errors.append(
                f"{name}[{i}]: choice_feedback[{j}] must be a non-empty string"
            )
    return errors


def _validate_choice_diagnosis(
    name: str, i: int, q: dict, is_cars: bool
) -> list[str]:
    """Optional content-axis tags. Science-only; aligned 1:1 with choices;
    correct index must be null; maps_to in {content_gap, null} (or a list of
    such). Bulk authoring is deferred, so most questions won't have this yet.
    """
    cd = q.get("choice_diagnosis")
    if cd is None:
        return []
    errors: list[str] = []
    if is_cars:
        errors.append(f"{name}[{i}]: choice_diagnosis not allowed on CARS")
        return errors
    if not isinstance(cd, list) or len(cd) != len(q["choices"]):
        errors.append(
            f"{name}[{i}]: choice_diagnosis must be a list aligned with choices"
        )
        return errors
    correct_idx = "ABCD".index(q["correct"]) if q["correct"] in "ABCD" else -1
    for j, entry in enumerate(cd):
        if j == correct_idx:
            if entry is not None:
                errors.append(
                    f"{name}[{i}]: choice_diagnosis[{j}] (correct) must be null"
                )
            continue
        if entry is None:
            continue
        maps = entry.get("maps_to")
        maps_list = maps if isinstance(maps, list) else [maps]
        for m in maps_list:
            if m not in VALID_CHOICE_MAPS_TO:
                errors.append(
                    f"{name}[{i}]: choice_diagnosis[{j}] maps_to {m!r} "
                    "must be content_gap or null"
                )
        trap = entry.get("trap")
        if trap is not None and trap not in VALID_TRAP:
            errors.append(
                f"{name}[{i}]: choice_diagnosis[{j}] trap {trap!r} "
                f"must be one of {sorted(VALID_TRAP)}"
            )
    return errors


def validate_application_practice(path: Path, valid_topics: set[str]) -> list[str]:
    """Validate the application-practice remediation pool with the same rigor as
    the main bank, plus the pool-specific invariants: pool/split markers,
    science-only sections, application|synthesis demand (never recall), and a
    REQUIRED, well-formed choice_diagnosis + non-empty concept slug."""
    errors: list[str] = []
    items = load_json(path)
    if not isinstance(items, list):
        return [f"{path.name}: root must be a JSON array"]

    seen_ids: set[str] = set()
    for i, q in enumerate(items):
        missing = POOL_REQUIRED_FIELDS - q.keys()
        if missing:
            errors.append(f"{path.name}[{i}]: missing fields {sorted(missing)}")
            continue
        if q["id"] in seen_ids:
            errors.append(f"{path.name}[{i}]: duplicate id {q['id']}")
        seen_ids.add(q["id"])
        if q["pool"] != POOL_MARKER:
            errors.append(
                f"{path.name}[{i}]: pool must be {POOL_MARKER!r} (got {q['pool']!r})"
            )
        if q["split"] != POOL_SPLIT:
            errors.append(
                f"{path.name}[{i}]: split must be {POOL_SPLIT!r} (got {q['split']!r})"
            )
        if q["section"] not in POOL_VALID_SECTIONS:
            errors.append(
                f"{path.name}[{i}]: section {q['section']!r} not science "
                f"(allowed: {sorted(POOL_VALID_SECTIONS)})"
            )
        if q["topic_id"] not in valid_topics:
            errors.append(f"{path.name}[{i}]: unknown topic_id {q['topic_id']}")
        if q["correct"] not in {"A", "B", "C", "D"}:
            errors.append(f"{path.name}[{i}]: correct must be A–D")
        if len(q["choices"]) != 4:
            errors.append(f"{path.name}[{i}]: expected 4 choices")
        expl = q.get("explanation")
        if not isinstance(expl, str) or not expl.strip():
            errors.append(
                f"{path.name}[{i}]: explanation must be a non-empty string"
            )
        concept = q.get("concept")
        if not isinstance(concept, str) or not concept.strip():
            errors.append(f"{path.name}[{i}]: concept must be a non-empty string")

        demand = q.get("cognitive_demand")
        if demand not in POOL_VALID_DEMAND:
            errors.append(
                f"{path.name}[{i}]: cognitive_demand {demand!r} must be "
                f"one of {sorted(POOL_VALID_DEMAND)} (never recall in this pool)"
            )
        # choice_diagnosis is REQUIRED for the pool (main bank treats it optional).
        if q.get("choice_diagnosis") is None:
            errors.append(f"{path.name}[{i}]: choice_diagnosis is required")
        else:
            errors.extend(_validate_choice_diagnosis(path.name, i, q, is_cars=False))
    return errors


def _decloze(text: str) -> str:
    """Strip Anki cloze markup so a card front matches the manifest card_front."""
    return " ".join(re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text).split())


def load_card_fronts() -> dict[str, set[str]] | None:
    """De-clozed flashcard fronts grouped by topic. None if the deck CSV is
    absent (the manifest card_front realness check is then skipped)."""
    path = DATA / "flashcards-dev.csv"
    if not path.exists():
        return None
    lines = [
        ln for ln in path.read_text(encoding="utf-8").splitlines()
        if ln and not ln.startswith("#")
    ]
    fronts: dict[str, set[str]] = {}
    for r in csv.DictReader(lines, fieldnames=_CARD_COLUMNS):
        tag = r.get("tags", "")
        topic = tag.split("topic:", 1)[1].split()[0] if "topic:" in tag else ""
        fronts.setdefault(topic, set()).add(_decloze(r.get("text", "")))
    return fronts


def validate_paraphrase(path: Path, questions: list[dict]) -> list[str]:
    """Validate the paraphrase-gap manifest: well-formed rows, within-trio
    topics, exactly two distinct within-topic question ids per concept, the
    second stem held_out (leakage discipline), unique concepts, no question
    reused across pairs, and a card_front that maps to a real within-topic
    flashcard."""
    errors: list[str] = []
    doc = load_json(path)
    concepts = doc.get("concepts") if isinstance(doc, dict) else doc
    if not isinstance(concepts, list):
        return [f"{path.name}: expected a 'concepts' list"]

    by_id = {q["id"]: q for q in questions}
    card_fronts = load_card_fronts()
    seen_concepts: set[str] = set()
    used_qids: dict[str, str] = {}

    for i, row in enumerate(concepts):
        tag = f"{path.name}[{i}]"
        missing = PARAPHRASE_ROW_FIELDS - row.keys()
        if missing:
            errors.append(f"{tag}: missing fields {sorted(missing)}")
            continue
        topic = row["topic_id"]
        concept = row["concept"]
        if topic not in PARAPHRASE_TRIO:
            errors.append(
                f"{tag}: topic_id {topic!r} not in the locked trio "
                f"{sorted(PARAPHRASE_TRIO)}"
            )
        if concept in seen_concepts:
            errors.append(f"{tag}: duplicate concept {concept!r}")
        seen_concepts.add(concept)
        if row["session_order"] not in VALID_SESSION_ORDER:
            errors.append(
                f"{tag}: invalid session_order {row['session_order']!r}"
            )

        qids = row["question_ids"]
        if not isinstance(qids, list) or len(qids) != 2:
            errors.append(f"{tag}: question_ids must be a list of exactly 2")
            continue
        if qids[0] == qids[1]:
            errors.append(f"{tag}: the two question_ids must be distinct")
        for qid in qids:
            if qid not in by_id:
                errors.append(f"{tag}: unknown question id {qid!r}")
                continue
            if by_id[qid]["topic_id"] != topic:
                errors.append(
                    f"{tag}: question {qid} topic {by_id[qid]['topic_id']!r} "
                    f"!= concept topic {topic!r} (within-topic anchors only)"
                )
            if qid in used_qids:
                errors.append(
                    f"{tag}: question {qid} already paired in "
                    f"{used_qids[qid]!r}"
                )
            used_qids[qid] = concept
        # Leakage discipline: the SECOND stem must be a fresh held_out probe.
        if qids[1] in by_id and by_id[qids[1]].get("split") != "held_out":
            errors.append(
                f"{tag}: second stem {qids[1]} must be held_out "
                f"(got {by_id[qids[1]].get('split')!r})"
            )
        # new_question_ids, if present, must be a subset of the pair.
        new_ids = row.get("new_question_ids", [])
        if not set(new_ids) <= set(qids):
            errors.append(f"{tag}: new_question_ids must be within question_ids")
        # card_front should resolve to a real flashcard in the SAME topic. This
        # is a cross-file link into the concurrently-edited deck CSV, so a
        # mismatch is a WARNING (re-point during reconciliation), not a hard
        # failure — the structural pair checks above are the hard invariants.
        if card_fronts is not None:
            front = " ".join(str(row["card_front"]).split())
            if front not in card_fronts.get(topic, set()):
                print(
                    f"  WARNING: {tag}: card_front for {concept!r} does not "
                    f"match any current {topic} flashcard (deck may have been "
                    "refactored — re-point card_ref/card_front)"
                )
    return errors


def main() -> int:
    outline_path = DATA / "mcat-outline.v1.json"
    if not outline_path.exists():
        outline_path = DATA / "mcat-outline.example.json"

    errors = validate_outline(outline_path)
    outline = load_json(outline_path)
    topics = topic_ids(outline)

    for name in ("questions.json", "questions.example.json"):
        qpath = DATA / name
        if qpath.exists():
            errors.extend(validate_questions(qpath, topics))

    pool_path = DATA / "application-practice.json"
    if pool_path.exists():
        errors.extend(validate_application_practice(pool_path, topics))

    paraphrase_path = DATA / "paraphrase-test.json"
    main_qpath = DATA / "questions.json"
    if paraphrase_path.exists() and main_qpath.exists():
        main_questions = load_json(main_qpath)
        if isinstance(main_questions, list):
            errors.extend(validate_paraphrase(paraphrase_path, main_questions))

    config_path = DATA / "scoring-config.json"
    if config_path.exists():
        load_json(config_path)
    else:
        errors.append("missing scoring-config.json")

    if errors:
        print("Validation FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    qpath = DATA / "questions.json"
    qcount = 0
    if qpath.exists():
        qs = load_json(qpath)
        if isinstance(qs, list):
            qcount = len(qs)
            dev = sum(1 for q in qs if q.get("split") == "dev")
            held = sum(1 for q in qs if q.get("split") == "held_out")
            print(f"Questions: {qcount} total (dev={dev}, held_out={held})")
            if qcount < 30:
                print("  WARNING: need ~30 dev questions for Wednesday (see openstax-sources.json)")

    pool_path = DATA / "application-practice.json"
    if pool_path.exists():
        pool = load_json(pool_path)
        if isinstance(pool, list):
            by_topic: dict[str, int] = {}
            for it in pool:
                by_topic[it.get("topic_id")] = by_topic.get(it.get("topic_id"), 0) + 1
            print(
                f"Application-practice pool: {len(pool)} items across "
                f"{len(by_topic)} topics"
            )

    paraphrase_path = DATA / "paraphrase-test.json"
    if paraphrase_path.exists():
        doc = load_json(paraphrase_path)
        rows = doc.get("concepts") if isinstance(doc, dict) else doc
        if isinstance(rows, list):
            per_topic: dict[str, int] = {}
            for r in rows:
                per_topic[r.get("topic_id")] = per_topic.get(r.get("topic_id"), 0) + 1
            authored = sum(len(r.get("new_question_ids", [])) for r in rows)
            summary = ", ".join(f"{t}={n}" for t, n in sorted(per_topic.items()))
            print(
                f"Paraphrase instrument: {len(rows)} anchor concepts "
                f"({summary}); {authored} newly authored questions"
            )

    print(f"Validation OK — {len(topics)} topics in {outline_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

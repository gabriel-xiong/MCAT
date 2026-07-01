#!/usr/bin/env py -3.12
"""Validate MCAT data files (outline, questions, config). No Anki dependency."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

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
}
VALID_SPLITS = {"dev", "held_out"}
VALID_SECTIONS = {"CP", "CARS", "BB", "PS"}
CARS_SECTION = "CARS"
# Question-level difficulty axis for the science error-diagnosis engine.
VALID_COGNITIVE_DEMAND = {"recall", "application", "synthesis"}
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

    print(f"Validation OK — {len(topics)} topics in {outline_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

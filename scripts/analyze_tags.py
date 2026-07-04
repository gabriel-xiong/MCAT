#!/usr/bin/env py -3.12
"""Analysis helper for the tag-validity assessment (NEW, non-destructive).

Reads data/questions.json and reports:
  1. Distribution of choice_diagnosis maps: content_gap / trap:<enum> / null,
     over all distractors, overall and per-topic (esp. the eval trio).
  2. Dumps every content_gap distractor (id, topic, chosen text, misconception)
     so the misconceptions can be judged distinctive vs generic.

Does NOT modify any data. Pure read + print.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TRIO = {"cp_acids_bases", "bb_enzymes", "cp_kinetics"}
LETTERS = "ABCD"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load():
    return json.loads((DATA / "questions.json").read_text(encoding="utf-8"))


def classify(entry):
    """Return one of: 'null', 'content_gap', 'trap:<enum>'."""
    if entry is None:
        return "null"
    if entry.get("trap"):
        return f"trap:{entry['trap']}"
    if entry.get("maps_to") == "content_gap":
        return "content_gap"
    return "null"  # maps_to null w/o trap == non-diagnostic near-miss


STOP = {
    "the", "a", "an", "of", "to", "in", "is", "are", "and", "or", "for", "on",
    "at", "by", "it", "its", "as", "be", "this", "that", "with", "from", "into",
    "than", "then", "which", "what", "when", "not", "no", "so", "if", "will",
    "can", "does", "do", "has", "have", "one", "two", "you", "your", "they",
    "would", "only", "more", "less", "at", "very", "because", "thinks",
    "believes", "assumes", "treats",
}


def toks(text):
    out = []
    cur = ""
    for ch in text.lower():
        if ch.isalnum():
            cur += ch
        else:
            if cur:
                out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return [t for t in out if t not in STOP]


# Markers that signal a SPECIFIC, contrastive misconception (recoverable):
# the tag names an alternative concept, a reversed relationship, or a specific
# category confusion — not just "the choice is wrong".
DISTINCTIVE_MARKERS = (
    "rather than", "instead of", "not the", "not a ", "confus", "revers",
    "swap", "opposite", "mistak", "describes ", "conflat", "misassign",
    "misapplie", "mis-app", "mis-app", "wrong direction", "wrong le chatelier",
    "wrong exponent", "equates", " vs ", "reports p", "linear", "common ion",
    "common-ion", "le chatelier", "confusing", "gives the definition",
    "definition of", "reads ", "misreads", "counts only", "square root",
    "as if", "over-generaliz", "narrower", "amphoteric",
)
# Markers that signal a GENERIC "just wrong / negation of the choice" tag.
GENERIC_PREFIXES = (
    "believes it is false", "believes it is true", "believes exergonic reactions need",
)


def distinctiveness(misc, choice_text):
    """Heuristic label: 'distinctive' | 'borderline' | 'generic'.

    Distinctive  = names an alternative concept / reversed relationship / specific
                   category confusion (a knowledgeable human could recover it).
    Generic      = pure negation or restatement of the choice ("just wrong").
    Borderline   = some concept present but weakly identifying / restates choice.
    """
    m = misc.lower().strip()
    if not m:
        return "generic"
    for p in GENERIC_PREFIXES:
        if m.startswith(p):
            return "generic"
    has_marker = any(mk in m for mk in DISTINCTIVE_MARKERS)
    # Overlap: fraction of misconception content-tokens that come from the choice.
    ct = set(toks(choice_text))
    mt = toks(misc)
    if mt:
        ov = sum(1 for t in mt if t in ct) / len(mt)
    else:
        ov = 0.0
    if has_marker:
        return "distinctive"
    # No contrast marker. If it largely restates the choice -> generic.
    if ov >= 0.5:
        return "generic"
    # Some independent content but no explicit contrast -> borderline.
    return "borderline"


def main():
    qs = load()
    # Distribution over DISTRACTORS only (exclude the correct slot).
    overall = Counter()
    per_topic = defaultdict(Counter)
    trap_kinds = Counter()
    content_gaps = []  # (qid, topic, choice_letter, choice_text, misconception)
    n_q_total = 0
    n_q_by_topic = Counter()

    for q in qs:
        n_q_total += 1
        topic = q.get("topic_id", "?")
        n_q_by_topic[topic] += 1
        cd = q.get("choice_diagnosis") or []
        correct_i = LETTERS.index(q["correct"]) if q.get("correct") in LETTERS else -1
        for i, choice in enumerate(q.get("choices", [])):
            if i == correct_i:
                continue
            entry = cd[i] if i < len(cd) else None
            cls = classify(entry)
            base = "trap" if cls.startswith("trap:") else cls
            overall[base] += 1
            per_topic[topic][base] += 1
            if cls.startswith("trap:"):
                trap_kinds[cls] += 1
            if cls == "content_gap":
                content_gaps.append(
                    (
                        q["id"],
                        topic,
                        LETTERS[i],
                        q["choices"][i],
                        entry.get("misconception", ""),
                    )
                )

    def total(c):
        return sum(c.values())

    print("=" * 78)
    print("DISTRIBUTION AUDIT — choice_diagnosis over DISTRACTORS (correct slot excluded)")
    print("=" * 78)
    print(f"Questions: {n_q_total}  |  Distractors: {total(overall)}")
    print("\nOVERALL:")
    t = total(overall)
    for k in ("content_gap", "trap", "null"):
        v = overall[k]
        print(f"  {k:<12} {v:4d}  ({v / t * 100:5.1f}%)")
    print("\n  trap breakdown:")
    for k, v in trap_kinds.most_common():
        print(f"    {k:<16} {v}")

    print("\nPER-TOPIC (distractor counts):")
    header = f"  {'topic':<18} {'nQ':>3} {'cg':>4} {'trap':>4} {'null':>4} {'cg%':>6}"
    print(header)
    for topic in sorted(per_topic, key=lambda x: (x not in TRIO, x)):
        c = per_topic[topic]
        tt = total(c)
        star = "*" if topic in TRIO else " "
        cgpct = c["content_gap"] / tt * 100 if tt else 0
        print(
            f" {star}{topic:<18} {n_q_by_topic[topic]:>3} "
            f"{c['content_gap']:>4} {c['trap']:>4} {c['null']:>4} {cgpct:>5.1f}%"
        )

    print("\nTRIO SUBTOTAL:")
    trio_c = Counter()
    for topic in TRIO:
        trio_c.update(per_topic[topic])
    tt = total(trio_c)
    for k in ("content_gap", "trap", "null"):
        v = trio_c[k]
        print(f"  {k:<12} {v:4d}  ({v / tt * 100:5.1f}%)" if tt else f"  {k}: 0")

    # Distinctiveness heuristic over content_gap distractors.
    dist_overall = Counter()
    dist_topic = defaultdict(Counter)
    labeled = []  # (qid, topic, letter, ctext, misc, label)
    for qid, topic, letter, ctext, misc in content_gaps:
        lab = distinctiveness(misc, ctext)
        dist_overall[lab] += 1
        dist_topic[topic][lab] += 1
        labeled.append((qid, topic, letter, ctext, misc, lab))

    print("\n" + "=" * 78)
    print("DISTINCTIVENESS AUDIT of content_gap tags (heuristic; hand-verified)")
    print("=" * 78)
    tcg = sum(dist_overall.values())
    print(f"content_gap distractors judged: {tcg}")
    for k in ("distinctive", "borderline", "generic"):
        v = dist_overall[k]
        print(f"  {k:<12} {v:4d}  ({v / tcg * 100:5.1f}%)")
    print("\nPER-TOPIC distinctiveness (content_gap only):")
    print(f"  {'topic':<20} {'dist':>4} {'bord':>4} {'gen':>4} {'dist%':>6}")
    for topic in sorted(dist_topic, key=lambda x: (x not in TRIO, x)):
        c = dist_topic[topic]
        tt = sum(c.values())
        star = "*" if topic in TRIO else " "
        dpct = c["distinctive"] / tt * 100 if tt else 0
        print(
            f" {star}{topic:<20} {c['distinctive']:>4} {c['borderline']:>4} "
            f"{c['generic']:>4} {dpct:>5.1f}%"
        )
    trio_d = Counter()
    for topic in TRIO:
        trio_d.update(dist_topic[topic])
    tt = sum(trio_d.values())
    print("\nTRIO distinctiveness subtotal:")
    for k in ("distinctive", "borderline", "generic"):
        v = trio_d[k]
        print(f"  {k:<12} {v:4d}  ({v / tt * 100:5.1f}%)" if tt else f"  {k}: 0")

    # Examples per label (trio-first).
    print("\nEXAMPLES BY LABEL:")
    for lab in ("distinctive", "borderline", "generic"):
        print(f"\n  --- {lab.upper()} examples ---")
        picks = [r for r in labeled if r[5] == lab and r[1] in TRIO][:6]
        for qid, topic, letter, ctext, misc, _ in picks:
            print(f"   [{qid} {letter}] ({topic}) choice: {ctext[:70]}")
            print(f"        misc: {misc[:110]}")

    # Dump content_gap misconceptions for distinctiveness judging.
    print("\n" + "=" * 78)
    print("CONTENT_GAP MISCONCEPTIONS (full dump, with heuristic label)")
    print("=" * 78)
    for topic in sorted({c[1] for c in labeled}, key=lambda x: (x not in TRIO, x)):
        rows = [c for c in labeled if c[1] == topic]
        star = "*" if topic in TRIO else " "
        print(f"\n{star}--- {topic} ({len(rows)} content_gap distractors) ---")
        for qid, _t, letter, ctext, misc, lab in rows:
            print(f"  [{qid} {letter}] <{lab}> choice: {ctext}")
            print(f"       misc: {misc}")


if __name__ == "__main__":
    main()

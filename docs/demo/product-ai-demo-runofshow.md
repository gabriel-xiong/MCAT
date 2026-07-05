# Demo run-of-show — combined product + AI (~6–8 min)

_Grader feedback baked in: **combine the product + AI demos** (they build on each
other), keep the **product basics short**, spend most time on **features that
changed since the MVP**, and **do not dwell on sync.**_

**One arc, not two demos.** Everything flows from a single performance-mode miss:
the miss reveals the three scores, the error-typing, the AI tutor + its offline
fallback, and the observability — sync is one short beat near the end.

**Setup before recording**
- Graded (strict) build installed; deck preloaded; dashboard visible.
- AI proxy deployed so the pill reads **"AI: On"** (have the offline-fallback
  path ready to show too).
- A known science question the demo account will **miss** (rehearse the choice).
- Screen at legible zoom; hide secrets; `mcat-ai-proxy.json` has **no key**.

---

## 0. Cold open — the one-sentence thesis (0:00–0:25)

> "Anki tells you what you *remember*. It can't tell you if you're *exam-ready* —
> and it never tells you *why* you missed. MCAT Speedrun adds three honest scores
> and a why-you-missed loop on top of the engine you already use."

Say the exam up front: **MCAT (472–528)**, prototype on ~15–25 topics — not a
full prep course.

## 1. Product basics — KEEP SHORT (0:25–1:30, ~1 min)

Fast, don't linger (this is the MVP-era surface):
- Two **separate** modes: **Memory** (normal Anki reviews) and **Performance**
  (curated, topic-gated exam questions). One line each.
- Topic gate in one breath: performance unlocks only after real reviews
  (≥3 cards seen, ≥5 Good/Easy); **CARS** is performance-only.
- Show a single memory review, then switch to performance mode. Move on.

> Time budget guard: if you're past ~1:30 here, cut to §2 — the basics are not
> the story.

## 2. Three honest scores + abstention as a feature (1:30–3:00, ~1.5 min) — POST-MVP

- Open the **three-score dashboard**: **Memory / Performance / Readiness**,
  shown **separately, never blended**.
- Point at the **coverage bar** and the **"not enough data yet"** states — frame
  abstention as **the honesty feature**: "It would rather withhold than show you
  a flattering guess." Readiness shows a **472–528 range** with coverage % and
  confidence, or it **abstains** — never a bare number.
- Show the **single next-action** card (what to do next, not three vague scores).
- One honest line: in the graded strict build, Memory abstains until a card
  matures (~3 weeks) and Readiness abstains until its inputs justify a range —
  **that's intended.**

## 3. Performance miss → why-you-missed (the marquee change) (3:00–5:00, ~2 min) — POST-MVP

This is the heart of the demo. Miss the rehearsed science question, then:
- The app runs an **objective re-check probe** (did you still recall the backing
  content?) and presents a **specific, evidence-backed hypothesis** about the
  error type — **"Looks like: *application* · NN%"** — to **confirm or override**
  in one tap. Emphasize **"infer, don't ask"** and *hypothesis, not verdict.*
- Show the error-type buckets driving different next actions (content_gap →
  review specific cards; application → drill applied items; misread → timed set).
- Show the **"Not sure" (IDK)** opt-out: it's **not scored** right/wrong and earns
  **no coverage credit** — the item-level mirror of readiness abstention.
- Show **application-practice remediation** launching a real, **unscored**
  practice set (visibly distinct from graded questions).

## 4. AI Assistant — folds into the SAME miss (5:00–6:15, ~1.25 min) — POST-MVP

- On that same wrong choice, open the **✨ Assistant** → a **live, per-choice**
  explanation of why **that specific distractor** is wrong + the correct
  solution, **cited to the named source** (OpenStax).
- Call out the **keyless hosted proxy**: "no API key on the grader's machine —
  the key stays server-side." Point at the honest **"AI: On"** pill.
- **Show the AI-off fallback:** toggle off (or note an unreachable proxy) → the
  **same source-grounded** static explanation appears; the app never breaks.
- One evidence line: on the hard differentiation set the AI **beats** the static
  and keyword baselines under a cross-model judge
  (`docs/QA-BASELINE-COMPARISON.md`) — choice-specificity 1.000 vs 0.000/~0.01.

## 5. Observability / honesty instrumentation (6:15–6:45, ~0.5 min) — POST-MVP

- Briefly: every attempt logs a full feature vector to a local sidecar; the
  read-only **export** + **calibration export** (probe-labeled rows) power the
  eval — **no telemetry, no network, no AI at runtime for scoring.**
- Mention the **green CI check + PR list** as the engineering-workflow evidence
  (hand off to the results demo, §6 of the results outline).

## 6. Sync — a SHORT beat, not the show (6:45–7:15, ~0.5 min)

- ~30–45s only: phone review → desktop reflects it (memory via stock Anki sync),
  and performance data via the portable **export/import bundle**
  (append-only union merge, uuid-deduped). Don't dwell; don't demo edge cases.

## 7. Close on honesty (7:15–8:00, ~0.75 min)

> "Three scores, never blended. Performance is real and leakage-free. Memory
> *calibration* is real but the *score* abstains — no mature cards yet. Readiness
> abstains, and says exactly what's missing. That restraint is the product."

Point to the proof packet (held-out results + leakage OK + AI-vs-baseline +
green CI + PRs) and hand to the **results demo**.

---

## Cut list (if running long, drop in this order)
1. Sync beat (§6) → mention in one sentence.
2. Observability (§5) → fold into the close.
3. Product basics (§1) → compress to 30s.

## Do-not-do (honesty guardrails)
- Never blend the three scores or show a bare readiness number.
- Never claim a learning outcome from synthetic data.
- Never show a flashcard reveal immediately followed by a performance question.
- Never surface a key; the pill must reflect the true backend state.

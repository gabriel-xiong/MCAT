# MCAT Speedrun — GRADED build quickstart (for graders)

_Last updated: 2026-07-04._

This is the **graded** build. It is deliberately different from the friend-tester
build in exactly **one** way that matters for grading: it runs the **strict
(full-course) scoring profile**, so the three scores **abstain honestly** until
real full-course study data exists. Nothing here is a bug — abstention is the
product's honesty rule in action.

> **One-line summary.** Flashcards, practice questions, and all three scores run
> **100% locally / offline**. The optional ✨ AI Assistant is the **only** thing
> that uses the network (a hosted proxy). With the shipped placeholder config the
> AI pill honestly reads **"AI: Not set up"** and the app behaves exactly like the
> offline build.

---

## 1. Install (Windows) — ~2 minutes

You get **two things**:

- an installer named **`MCAT-Speedrun-graded.msi`** (the graded app), and
- a ZIP named **`MCAT-Speedrun.zip`** (the preloaded deck + launcher + AI-proxy
  config).

**Steps:**

1. **Install the app.** Double-click **`MCAT-Speedrun-graded.msi`** and click
   through (**Next → Next → Finish**). _(If Windows shows a blue "unknown
   publisher" box: **More info → Run anyway** — it's an unsigned research
   prototype, not a virus.)_
2. **Unzip the folder** (`MCAT-Speedrun.zip`) somewhere easy, e.g. the Desktop.
3. **Open the folder** and **double-click `Start MCAT Speedrun.cmd`**.

You'll land on the **MCAT Speedrun** home screen with the deck preloaded and the
three-score dashboard. Everything is already set up — no import, no login, no
account.

---

## 2. What is different in the GRADED build (read this)

| Aspect | Graded (this build) | Friend-tester build |
|--------|---------------------|---------------------|
| Score profile | **`strict`** (full-course gates) | `tester` (low engagement gates) |
| Memory shows a number after | ≥ **200** graded reviews **and** ≥ 1 card matured to a ≥ **21-day** interval | ≥ 10 reviews, no maturity needed |
| Performance shows a number after | ≥ **30** attempts on unlocked topics | ≥ 8 attempts |
| Readiness range shows after | ≥ 200 reviews **and** ≥ 30 attempts **and** ≥ 50% outline coverage **and** ≥ 5 attempts per shipped science section **and** ≥ 5 CARS attempts | reduced gates (≥ 3/section, etc.) |
| Score labels | plain **measured** (no `provisional` badge) | `provisional` badge |

**Consequence for a short grading session:** the scores will very likely say
**"not enough data yet"** and **stay** that way through a brief sit-down. **This
is intended and correct** — the strict profile refuses to emit Memory,
Performance, or Readiness until it has full-course evidence to justify a number.
It would rather abstain than show you a flattering guess. (Card maturity alone
takes weeks of real spaced reviews, so Memory cannot populate in an afternoon —
by design.)

If you want to *see* populated strict scores, that requires real full-course
data (hundreds of reviews over weeks + dozens of exam attempts across sections).
The `MCAT/docs/EVAL-SUMMARY-GRADED.md` writeup reports the honest state of that
data today (Memory / Performance / Readiness, each with real-or-abstained,
sample size, coverage, confidence, and a missing-data note).

---

## 3. The three scores (never blended)

- **Memory** — FSRS recall-strength signal (retrievability × deck maturity).
  Abstains below 200 graded reviews / until a card is mature.
- **Performance** — accuracy on the curated exam-style questions, with a Wilson
  95% confidence band. Abstains below 30 attempts. **Not** derived from Memory.
- **Readiness** — a mapped **472–528 range** (never a bare point), with coverage
  % and a confidence indicator. Abstains unless every full-course gate is met.

The three scores are **never combined** into a single "% ready." Readiness is
always shown as a **range** with **coverage %**, a **confidence** indicator, and a
**single next action** — or it abstains.

---

## 4. The ✨ AI Assistant (the only online feature)

Everything except the AI Assistant is fully offline. The Assistant (per-choice
"why is my answer wrong" + follow-up Q&A) is **optional** and routes through a
**hosted proxy**, so:

- **You never enter an API key.** The upstream key lives only on the proxy host.
- **It needs internet.** The header pill reads:
  - **"AI: On"** — a proxy is configured and reachable → live per-choice answers.
  - **"AI: Not set up"** — the shipped config is still the **placeholder** (this
    is the default state until the builder deploys the proxy). The app is fully
    usable; the Assistant serves the same **offline, source-grounded** explanation.
  - **"AI: Off"** — you turned the Assistant off in the UI.
- **It never breaks the app.** Offline / unreachable / error → automatic fallback
  to the offline source-based explanation. Scores/questions/flashcards are
  unaffected.

**Turning live AI on (builder step, optional):** deploy the proxy and paste the
URL + token into `mcat-ai-proxy.json` next to the launcher — **no rebuild
needed.** Full steps: `MCAT/docs/AI-PROXY-SETUP.md`. **No secret is shipped in
this bundle** — `mcat-ai-proxy.json` contains only `REPLACE_WITH_…` placeholders.

---

## 5. Verifying this really is the graded (strict) build

- The dashboard score cards show **no `provisional` badge** (the friend build
  tags every score `provisional`).
- With a fresh profile, all three scores abstain with strict-gate wording
  (e.g. Memory: *"Needs ≥200 graded reviews"*; Readiness lists the failing
  full-course gates).
- Source of truth: `SCORE_PROFILE = "strict"` was compiled into this MSI
  (`anki-MCAT/pylib/anki/mcat_scores.py`); the friend MSI compiles `"tester"`.

---

## 6. FAQ

**Why are all my scores blank / "not enough data"?**
Because this is the strict graded profile and a short session doesn't meet the
full-course thresholds. That's the honest, intended behavior — not a bug.

**Do I need internet or an API key?**
No — for everything except the optional AI Assistant. No key is ever entered by
you. The AI feature needs internet; with the placeholder config it simply reads
"AI: Not set up" and uses the offline explanation.

**Is my data private / does anything upload?**
All study data stays local. The only network traffic is an AI Assistant request
**if** a proxy is configured and you use the Assistant.

# Demo run-of-show — combined product + AI (~6–8 min, timed narration script)

_Grader feedback baked in: **combine the product + AI demos** (they build on each
other), keep the **product basics short**, spend most time on **features that
changed since the MVP**, and **do not dwell on sync.**_

**How to use this doc.** It is a **near-word-for-word script**. `[SAY]` blocks are
the narration (read them almost verbatim; they're timed to fit). `[DO]` lines are
the on-screen action for that beat. Total target **7:00**, hard cap **8:00**. If
you fall behind, use the **Cut list** at the bottom.

**One arc, not two demos.** Everything flows from a single performance-mode miss:
the miss reveals the three scores, the error-typing, the AI tutor + its offline
fallback, and the observability — sync is one short beat near the end.

**Setup before recording**
- **Graded MSI installed** (`MCAT-Speedrun-graded.msi`) — not a from-source `./run` build.
- Open the seeded folder and double-click **`Start MCAT Speedrun.cmd`** (preloaded deck,
  strict profile, auto-sync off). See `docs/GRADED-QUICKSTART.md`.
- Dashboard visible on MCAT home screen.
- AI proxy deployed so the pill reads **"AI: On"** (have the offline-fallback path
  ready to show too — know how to toggle it).
- A known science question the demo account will **miss** (rehearse the exact wrong
  choice so the miss is one confident click).
- Screen at legible zoom; hide secrets; `mcat-ai-proxy.json` has **no key** visible.

---

## 0. Cold open — the one-sentence thesis (0:00–0:25)

[DO] Dashboard already on screen, static.

[SAY]
> "Anki tells you what you *remember*. It can't tell you whether you're *exam-ready*
> — and it never tells you *why* you missed. MCAT Speedrun adds three honest scores
> and a why-you-missed loop on top of the Anki engine you already use. The exam is
> the **MCAT, scored 472 to 528**; this is a prototype on about **20 topics**, not a
> full prep course."

## 1. Product basics — KEEP SHORT (0:25–1:30, ~1 min)

[DO] Point at the two mode entry points; do one flashcard review; switch to
performance mode. Move quickly.

[SAY]
> "Two separate modes. **Memory** is just normal Anki spaced-repetition review —
> here's one card. **Performance** is a separate session of curated, exam-style
> multiple-choice questions from named sources. They're kept apart on purpose: I
> never flip a flashcard and immediately quiz you on it. Performance mode only
> unlocks for a topic after you've actually studied it — at least three cards seen
> and five rated Good or Easy — except **CARS**, which is reasoning-only, so it has
> no flashcard gate. That's the surface from the MVP; the interesting part is what
> happens when you *miss* — and everything below is **post-MVP**."

> Time-budget guard: if you're past ~1:30 here, stop talking and go to §2.

## 2. Three honest scores + abstention as a feature (1:30–3:00, ~1.5 min) — POST-MVP

**MVP vs final callout:** MVP showed three score *slots*; final adds **coverage map**,
**strict abstention** (graded profile), and **next-action card**. See `docs/MVP-TO-FINAL.md`.

[DO] Open the three-score dashboard. Point to each score, the coverage bar, the
"not enough data yet" states, and the single next-action card.

[SAY]
> "Here are the three scores, and this is the biggest change since the MVP. **Memory,
> Performance, and Readiness — shown separately and never blended into one vanity
> number.** Memory is FSRS recall from your reviews. Performance is accuracy on the
> exam questions. Readiness is a mapped **472–528 range** with a coverage percentage
> and a confidence band — *or it abstains.*
>
> Look at what it's doing right now: it's **withholding**. Memory says 'calibration
> looks good but no card is mature yet.' Readiness says 'I don't have enough to give
> you a range.' In the graded build that abstention is **intended** — Memory needs a
> card to survive to a three-week interval, and Readiness won't invent precision from
> immature memory and a self-graded split. **It would rather tell you what's missing
> than show you a flattering guess.** And instead of three vague numbers, it gives you
> one **next action** — this card — right here."

## 3. Performance miss → why-you-missed (the marquee change) (3:00–5:00, ~2 min) — POST-MVP

[DO] Enter performance mode, answer the rehearsed question **wrong**. Let the
re-check probe fire; show the error-type hypothesis chip; confirm/override in one
tap; show the buckets → next actions; show the IDK opt-out; launch an
application-practice set.

[SAY]
> "This is the heart of it. I'll answer this chemistry question — and I'll miss it
> on purpose. Watch what happens instead of just 'wrong, here's the answer.'
>
> First it runs an **objective re-check probe**: it asks a quick backing-content
> question to test whether I actually still *know* the underlying fact. Then it
> shows a **hypothesis**, not a verdict — 'Looks like: **application**, 72%' — and I
> can **confirm or override it in one tap**. The design rule is *infer, don't
> interrogate*: it guesses from evidence and lets me correct it, rather than making
> me fill out a form.
>
> Why it matters: the error type drives **different next actions**. A **content gap**
> sends me back to specific flashcards. An **application** error drills applied
> problems. A **misread** pushes a timed set. Same wrong answer, different fix.
>
> Two honesty touches. This **'Not sure'** button — if I genuinely don't know, I
> tap it; that attempt is **not scored right or wrong and earns no coverage credit.**
> It's the item-level version of the dashboard's abstention. And **remediation** here
> launches a **separate, unscored practice set** — visibly different from the graded
> questions, so practice never contaminates the score."

## 4. AI Assistant — folds into the SAME miss (5:00–6:15, ~1.25 min) — POST-MVP

**MVP vs final callout:** AI was not in Wednesday MVP; final adds proxy + baselines +
offline fallback. Memory *score* fix (maturity basis) is dashboard-only — mention in §2.

[DO] On the same wrong choice, open the ✨ Assistant. Show the per-choice
explanation + source citation. Point at the "AI: On" pill. Then toggle AI off (or
note an unreachable proxy) and show the identical source-grounded static answer.

[SAY]
> "Now the AI tutor — and notice it's on the **same miss**, not a separate demo. I
> open the Assistant and it explains why **this specific distractor** I chose is
> wrong, gives the correct reasoning, and **cites the named OpenStax source**.
>
> Two things I want to call out. One: see this **'AI: On'** pill? The key is **not on
> this machine** — it lives server-side behind a hosted proxy, so a grader runs live
> AI with **no key to enter**. Two — and this is the honest part — watch what happens
> when I **turn AI off**." [DO: toggle off] "The **same source-grounded explanation**
> appears from the static fallback. The app never breaks and never goes blank; AI is
> an enhancement, not a crutch.
>
> And it's measured, not asserted: on the hard follow-up set, under a **cross-model
> judge**, the AI beats the static and keyword baselines — **90.7% versus 59.6% and
> 45%** atom coverage — and its per-choice specificity is **1.0 versus basically zero**
> for the baselines. That's in `QA-BASELINE-COMPARISON.md`, with the small-n caveats
> stated."

## 5. Observability / export (6:15–6:45, ~0.5 min) — POST-MVP

[DO] **Tools → MCAT: Export performance data** (or bundle export). Show JSON sidecar
briefly; mention `make ci-local` + `docs/HOW-TO-VERIFY.md` for graders.

[SAY]
> "Underneath, every attempt logs to a **local** sidecar — no telemetry, no AI in the
> scoring path. This export is what feeds the eval artifacts — held-out scorer,
> leakage check, memory calibration. Proof packet is one page: **`HOW-TO-VERIFY.md`**."

## 6. Sync — OPTIONAL addendum (skip in main demo)

**Do not dwell on sync in the 6–8 min cut.** If you recorded sync separately, use
`docs/SYNC-DEMO-SCRIPT.md` (~4 min). Otherwise one sentence:

[SAY]
> "Memory sync is stock Anki; performance data uses a uuid-deduped bundle. The merge
> rule is written in `SYNC-CONFLICT-RULE.md` — we did not capture a two-device
> recording for this submission."

[DO] Skip unless you have a clip ready.

## 7. Close on honesty (6:45–8:00, ~0.75 min)

[DO] Back to the dashboard.

[SAY]
> "So: **three scores, never blended.** Performance is real and **leakage-free**.
> Memory *calibration* is real, but the *score* abstains — no mature cards yet.
> Readiness abstains and tells you exactly what's missing. That restraint — being
> real where it can be, and honest about where it can't — **is the product.** Here's
> the proof packet: held-out results, the leakage check, AI-versus-baseline, and the
> green CI with the PRs — over to the results demo."

---

## Cut list (if running long, drop in this order)
1. Sync mention (§6) — already skipped by default.
2. Observability (§5) — fold its one line into the close.
3. Product basics (§1) — compress to ~30s (one review, one mode-switch, no gate detail).

## Do-not-do (honesty guardrails)
- Never blend the three scores or show a bare readiness number.
- Never claim a learning outcome from synthetic data.
- Never show a flashcard reveal immediately followed by a performance question.
- Never surface a key; the pill must reflect the true backend state.

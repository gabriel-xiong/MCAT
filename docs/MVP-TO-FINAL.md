# MVP → Final — demo narration changelog

_Bullet list for the 6–8 min product demo. Call these out when walking the graded
build (see [`demo/product-ai-demo-runofshow.md`](demo/product-ai-demo-runofshow.md))._

---

## What the MVP already had (keep brief in demo §1)

- Anki fork with **Memory mode** (normal FSRS reviews) and separate **Performance mode**
- Topic gate: ≥3 cards seen + ≥5 Good/Easy before science perf unlocks; **CARS** ungated
- Curated OpenStax question bank (170 Q, dev/held_out split)
- Basic three-score dashboard concept (Memory / Performance / Readiness)
- Desktop builds from source (`./run`)

---

## What changed for final submission (spend demo time here)

### Dashboard & honesty

- **Strict graded profile** — scores abstain until full-course gates met (≥200 reviews,
  mature cards, ≥30 perf attempts, ≥50% outline coverage). Friend build uses relaxed
  `tester` profile instead.
- **Coverage map** on official MCAT outline — Readiness **withholds** below ~50%
  coverage instead of guessing a 472–528 range.
- **Single next-action card** — one concrete step, not three vague numbers.
- **No score blending** — three scores always separate; no combined “% ready.”

### Performance & diagnosis (marquee)

- **Why-you-missed loop** on perf miss — re-check probe, inferred error type
  (`content_gap` / `application` / `misread`), confirm/override in one tap.
- **Error type → different remediation** — cards vs applied drill vs timed set.
- **IDK / “Not sure”** — honest abstention at item level (not scored, no coverage credit).
- **Unscored remediation sets** — practice visibly separate from graded attempts.

### AI (Friday add-on)

- **Per-choice Assistant** with OpenStax citation; **hosted proxy** (no key on grader machine).
- **AI on/off pill** — honest state; **offline static fallback** when proxy unset or unreachable.
- **Baseline comparisons** — choice-specificity vs static/keyword; cross-model QA judge
  (`docs/QA-BASELINE-COMPARISON.md`).

### Memory fix & data

- **Memory score basis fixed** — strict profile uses retrievability × **deck maturity**
  (not raw accuracy); abstains until ≥1 card reaches ≥21-day interval.
- **REAL memory calibration** — builder (Brier 0.0082, n=39) + participant alt
  (Brier 0.0028, n=38); artifacts in `docs/artifacts/memory-calibration-*`.

### Eval & verification (show in results demo, not product demo)

- Leakage check, paraphrase-gap instrument, held-out scoring pipeline (synthetic demo),
  Step 2 prediction harness, study-feature 3-build ablation (synthetic, inconclusive).
- **`make ci-local`** — 56 offline tests mirroring GitHub Actions.
- **Grader page:** [`HOW-TO-VERIFY.md`](HOW-TO-VERIFY.md).

### Distribution & ops

- **Graded MSI installer** + **`Start MCAT Speedrun.cmd`** launcher (preloaded deck,
  strict profile, **auto-sync off** on open/close).
- **`mcat-ai-proxy.json`** next to launcher — placeholder until proxy deployed.
- Perf data **export/import bundle** (uuid-deduped sidecar); memory still on stock Anki sync.

---

## Still open (say honestly if asked)

- **No sync recording** (§7b) — rule written, not on video.
- **No scorable held_out performance** — real alt bundle is dev-only (`scorable: false`).
- **Study feature** — synthetic ablation inconclusive (p=0.057); no real 3-arm data.
- **50k dashboard latency** — mastery fast; full-scale dashboard refresh slow.

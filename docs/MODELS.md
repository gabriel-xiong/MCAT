# Score models (v1 drafts)

One-page summaries for Sunday deliverable. Tune coefficients on **dev** data only; report on **held_out**.

---

## 1. Memory model

**Question:** What is the probability the student recalls a fact on a due flashcard?

**Input:** Anki revlog, FSRS card states, `topic:*` tags.

**Method:**

- Per card: FSRS **retrievability** at review time.
- Aggregate by section/topic → point estimate + range (e.g. Wilson interval or FSRS dispersion).
- Optional calibration layer on held-out reviews (reliability diagram; Brier score or log loss).

**Output example:**

> Memory (BB): 78% recall (range 72–84%). Last updated: [time].

**Give-up:** Withhold if total graded reviews &lt; 200 (`scoring-config.json`).

**What we do not claim:** Memory score = exam readiness.

---

## 2. Performance model

**Question:** On **new, exam-style** questions in unlocked topics, what accuracy should we expect?

**Input:** `PerformanceAttempt` rows; question `section`, `skill`, `topic_id`; eligibility filter.

**Method:**

- Accuracy = correct / attempts on eligible topics only.
- Segment by section (and optionally SIRS skill).
- **Not** derived as `memory × k`.
- Range widens when attempt count is low.

**Output example:**

> Performance (BB): 62% on 24 attempts (range 48–74%). Last updated: [time].

**Give-up:** Withhold if attempts &lt; 30 or no unlocked topics.

**Eval:** Held-out question set; paraphrase gap vs card recall (Speedrun 7d).

---

## 3. Readiness model

**Question:** If the exam were today, what **score range** is plausible given current data?

**Input:** Section-level performance accuracy, outline **coverage %**, attempt counts, memory–performance gap.

**Method (v1 — simple):

1. Map each section’s performance accuracy → section score band (118–132) via documented monotonic function.
2. Sum → total 472–528.
3. **Widen range** when: coverage &lt; 80%, attempts per section low, large memory–performance gap.
4. **Abstain** if coverage &lt; 50% OR any threshold in `scoring-config.json` fails.

**Output example:**

> Projected MCAT: 505 (range 498–512). Confidence: **low** — 38% of v1 outline covered; 24 performance attempts.  
> Gap: Memory BB 81% vs Performance BB 58%.  
> Next: 5 passage-mapping drills in glycolysis.

**Honesty:** AAMC full-lengths remain the best external validator. This is an **early proxy**, not a substitute for FL exams.

**Give-up rule:** Documented in `data/scoring-config.json` and PRD §7.

---

## Error typing → next action

On performance miss, user selects one of four types (`scoring-config.json`). Dashboard renders templated next action — not “more topic X” by default.

---

## Eval commands (when implemented)

```bash
make eval-memory
make eval-performance
make eval-leakage
```

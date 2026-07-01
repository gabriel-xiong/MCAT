# Product Requirements Document — MCAT Speedrun Study App

| Field | Value |
|-------|--------|
| **Product** | MCAT measurement layer on Anki |
| **Exam** | MCAT (472–528; sections 118–132) |
| **Owner** | Gabriel Xiong |
| **License** | AGPL-3.0-or-later (Anki fork) |
| **Status** | Pre-implementation — design locked |
| **Builder** | Solo developer |
| **Eval participant** | Premed friend (held-out performance questions) |

---

## 1. Executive summary

Students preparing for the MCAT use Anki for recall but lack a **live, honest signal** of exam-ready **performance** and **readiness**. This product forks Anki and AnkiDroid, adds a **performance mode** on top of memory-mode reviews, and displays **three separate scores** with ranges and abstention — bridging declarative recall and procedural exam performance without faking a single “% ready.”

**This is not a full MCAT prep course.** v1 covers a **representative subset** of outline topics (~15–25), a modest flashcard deck, and ~30–100 **curated** performance questions from named open sources (primarily OpenStax).

**BrainLift anchor:** Readiness is a continuous signal; recall and application are distinct cognitive outcomes; tools must capture **why** a student missed — not just the topic.

---

## 2. Problem statement

### 2.1 User pain

- Standard prep: content review → QBank → full-lengths in final weeks; **no early readiness signal** (BrainLift SPOV 1).  
- Students pair Anki with UWorld assuming that closes the gap; **declarative knowledge does not transfer to passage application** (SPOV 2, Bransford / AMEE).  
- Wrong answers collapse to “missed topic X” without **error type** — poor personalization (SPOV 3).  
- Students overestimate readiness (Artino: 95–98% overestimate in medical training contexts).  
- Anki optimizes **recall**; MCAT science sections are ~**65% Skills 2–4** (application, research design, data).

### 2.2 Product opportunity

Build **two modes, three scores, one feedback loop** on the engine students already use — measuring the **gap** between memory and performance instead of hiding it.

---

## 3. Goals and non-goals

### 3.1 Goals

1. Fork Anki; real **Rust mastery query**; ≥3 Rust tests + 1 Python test  
2. **Desktop + Android (AnkiDroid)** sharing one engine and **Anki sync**  
3. **Memory mode** (FSRS) + **Performance mode** (curated MCQs), topic-gated  
4. **Three scores** with ranges, give-up rules, next action  
5. **Error typing** on performance misses (4 categories) — ship by Wednesday  
6. **Coverage map** vs AAMC outline; readiness abstain below ~50% coverage  
7. **Study feature:** interleaved vs blocked performance sessions (3-build test)  
8. **Held-out eval** scripts (`make eval-*`, `make bench`)  
9. Optional **Friday AI** with gold-set eval; **AI off** must still run full app  

### 3.2 Non-goals

- Complete MCAT curriculum or premade mega-deck  
- iOS in v1  
- Custom FSRS / deep ML readiness model  
- Live LLM during performance review  
- Authoring MCQs from scratch without sourced answer keys  
- Validating projected scores against real MCAT outcomes (bonus only)

---

## 4. Personas, user stories, and journeys

### 4.1 Persona overview

| Persona | Role | Depth in this PRD |
|---------|------|-------------------|
| **Jordan** (primary) | MCAT student — product UX | Full persona below |
| **Gabriel** | Solo builder + primary study user | Stakeholder / eval data source |
| **Premed friend** | Held-out performance participant | Secondary |
| **Speedrun grader** | Reviews proof and honesty | Secondary |

---

### 4.2 Primary persona — Jordan (MCAT student)

| Attribute | Detail |
|-----------|--------|
| **Who** | Junior/senior undergrad or gap-year student, ~8–12 weeks from test date |
| **Prep style** | Self-directed; uses Anki daily (50–80 reviews/day); supplements with OpenStax or Khan; has not started AAMC full-lengths yet |
| **Tools today** | Anki (MileDown or similar subset), maybe a QBank trial — **disconnected** from Anki progress |
| **Goals** | Know if prep is working **before** burning FL exams; fix weak areas efficiently; study at desk + on phone between classes |
| **Frustrations** | Anki retention feels strong but practice passages still miss; no idea if “78% mature” means exam-ready; UWorld misses only show **topic**, not **why**; readiness feels like a surprise at first FL |
| **Behaviors** | Grinds cards in blocked topics; over-trusts card stats; avoids CARS because Anki doesn’t help; postpones FLs until “content is done” |
| **BrainLift fit** | Embodies SPOV 1 (no early readiness signal), SPOV 2 (recall ≠ application), SPOV 3 (what vs why), Insights 4, 6, and 8 |

Jordan is the **design target** for memory mode, performance mode, dashboard, and Android companion. Gabriel may be the only real Jordan during v1 — that is acceptable if limitations are documented in eval.

---

### 4.3 Secondary personas

**Gabriel (builder / de facto study user)**  
Builds the Anki fork; generates memory review data; may also use performance mode for plumbing. Needs clear separation between **dev/tune** data and **held-out** eval data.

**Premed friend (eval participant)**  
Takes one **frozen held-out** performance set (~45 min); does not build the app. Supplies independent performance accuracy for eval — not required to use the app daily.

**Speedrun grader**  
Needs re-runnable eval, Rust diff, sync recording, and honest abstention — not a polished fake readiness number.

---

### 4.4 User stories

Format: **As a [persona], I want [action], so that [outcome].**

#### Memory mode

| ID | Story |
|----|--------|
| US-M1 | As **Jordan**, I want to review flashcards with normal Anki grading, so that I build retention without changing my daily habit. |
| US-M2 | As **Jordan**, I want my reviews to count toward **topic eligibility** for performance mode, so that I only practice exam questions on content I have actually studied. |
| US-M3 | As **Jordan**, I want a **memory score with a range**, so that I know how reliable my recall is — not just how many cards I clicked through. |

#### Performance mode

| ID | Story |
|----|--------|
| US-P1 | As **Jordan**, I want **exam-style questions** on topics I have unlocked, so that I train application — not just card wording. |
| US-P2 | As **Jordan**, I want performance sessions **separate from** flashcard reviews, so that my performance score reflects real exam skills, not short-term recall of the answer I just saw. |
| US-P3 | As **Jordan**, I want to tag **why** I missed a question (content / mapping / reasoning / misread), so that the app tells me **what to do next** instead of “do more of topic X.” |
| US-P4 | As **Jordan**, I want a **CARS performance lane** without flashcard prerequisites, so that the app acknowledges ~23% of the exam that Anki cannot train. |

#### Dashboard and readiness

| ID | Story |
|----|--------|
| US-D1 | As **Jordan**, I want to see **memory, performance, and readiness separately**, so that I do not confuse knowing facts with being exam-ready. |
| US-D2 | As **Jordan**, I want readiness shown as a **range with confidence and coverage %**, so that I understand uncertainty before I take an AAMC full-length. |
| US-D3 | As **Jordan**, I want the app to **refuse a readiness score** when I have not covered enough of the syllabus, so that I am not misled by a strong deck on a tiny fraction of the MCAT. |
| US-D4 | As **Jordan**, I want a **single best next action** on the dashboard, so that I know whether to do cards, passage drills, or CARS — not three generic scores with no guidance. |

#### Mobile and sync

| ID | Story |
|----|--------|
| US-S1 | As **Jordan**, I want to **review cards on my phone** between classes, so that memory progress syncs with my desktop study. |
| US-S2 | As **Jordan**, I want **the same three scores on my phone** as on desktop (with give-up rules), so that readiness is one signal — not two conflicting apps. |
| US-S3 | As **Jordan**, I want offline reviews to **sync when I reconnect**, so that I do not lose progress or double-count reviews. |

#### Abstention and honesty

| ID | Story |
|----|--------|
| US-A1 | As **Jordan**, I want clear messaging when scores are withheld, so that I know **what data is missing** — not that the app is broken. |
| US-A2 | As **Jordan**, I want to see the **gap between memory and performance**, so that I can catch false confidence before my first FL. |

---

### 4.5 User journeys

#### Journey 1 — First week: building memory, no false readiness  
**BrainLift:** SPOV 1, Insight 4, Insight 8

1. Jordan imports a **subset deck** (~15–25 topics) and reviews daily in **memory mode**.  
2. Dashboard shows **memory score** with range; **readiness is withheld** (“Need 200 reviews and 50% outline coverage”).  
3. Jordan sees **coverage %** climb as topics get first reviews — not fooled by card completion alone.  
4. Topics hit eligibility (≥3 cards seen, ≥5 Good/Easy); **performance mode unlocks** for those topics only.  

**Outcome:** Early prep with honest “we don’t know yet” instead of a fake % ready.

---

#### Journey 2 — The gap: memory strong, performance weaker  
**BrainLift:** SPOV 2, Insight 1, Insight 6

1. Jordan’s **memory score** is high on glycolysis after a week of cards.  
2. Jordan starts a **separate performance session** (interleaved or blocked) on unlocked topics — not immediately after flipping those cards.  
3. Jordan misses a passage-style item and selects **`passage_mapping`**.  
4. Dashboard shows **memory vs performance gap** for BB; readiness range is **wide**, confidence **low**.  
5. **Next action:** “5 passage-mapping drills in glycolysis” — not “review 50 more cards.”  

**Outcome:** Jordan discovers recall ≠ application **before** an AAMC FL.

---

#### Journey 3 — Mobile + continuous readiness signal  
**BrainLift:** SPOV 1, Insight 4

1. Jordan reviews cards on **Android** between classes (offline).  
2. Scores sync to desktop; **memory score** updates on both.  
3. Jordan completes performance questions on desktop later; **performance** and **readiness** update with coverage and range.  
4. Readiness still **abstains** if coverage &lt; 50%; otherwise shows e.g. “Projected 505–512, confidence low, 42% outline covered.”  

**Outcome:** One engine, one signal across devices — readiness as a **live** proxy, not a last-week surprise.

---

#### Journey 4 — Eval participant (friend, one session)  
**Not Jordan’s daily journey** — supports Speedrun proof.

1. Friend receives **held-out** question set only (no app tuning access).  
2. Friend completes set once in a fixed session.  
3. Builder compares friend accuracy to model predictions and **paraphrase gap** vs card recall on linked topics.  

**Outcome:** Independent performance data for held-out eval (document small **n** honestly).

---

### 4.6 Story → requirement traceability

| User story | Primary PRD requirements |
|------------|-------------------------|
| US-M1–M3 | §6.1 Memory mode (M-1–M-6) |
| US-P1–P4 | §6.2 Performance mode (P-1–P-10); §7 eligibility |
| US-D1–D4 | §6.3 Dashboard (D-1–D-7); §9 error typing |
| US-S1–S3 | §6.7 Sync; §6.8 Android |
| US-A1–A2 | §7 give-up rules; §6.4 Readiness (R-1–R-6) |

---

## 5. Product principles

1. **Honesty over flattery** — automatic fail for fake readiness  
2. **Three scores, never blended**  
3. **Separate sessions** for memory vs performance measurement  
4. **Topic-gated performance** — only on memory-covered content (except CARS)  
5. **Named sources** on every performance question  
6. **Abstain** when coverage or attempt counts are insufficient  
7. **Report the gap** — paraphrase / topic-linked eval shows memory ≠ performance  

---

## 6. Functional requirements

### 6.1 Memory mode

| ID | Requirement |
|----|-------------|
| M-1 | Standard Anki review loop (show → reveal → Again/Hard/Good/Easy) |
| M-2 | FSRS scheduling; revlog persisted in collection |
| M-3 | Cards tagged with `topic_id` aligned to outline |
| M-4 | **Memory score:** FSRS retrievability + calibration; range displayed |
| M-5 | Memory score **abstains** below review count threshold (e.g. &lt; 200 total) |
| M-6 | Updates topic stats consumed by eligibility engine |

### 6.2 Performance mode

| ID | Requirement |
|----|-------------|
| P-1 | Separate UI/session from memory reviews |
| P-2 | Questions only from topics where **performance_unlocked** (see §7) |
| P-3 | **CARS lane:** always available; no memory gate |
| P-4 | Questions loaded from local bank — **no live API at runtime** |
| P-5 | Each question: stem, choices, correct answer, topic, section, **source metadata** |
| P-6 | Session config: **interleaved** vs **blocked by topic** (study feature flag) |
| P-7 | On incorrect answer: user selects error type: `content_gap`, `passage_mapping`, `reasoning`, `misread` |
| P-8 | **Performance score:** accuracy on attempts; not derived as `memory × k` |
| P-9 | Performance score abstains below attempt threshold (e.g. &lt; 30) |
| P-10 | Optional timing capture per question |

### 6.3 Dashboard

| ID | Requirement |
|----|-------------|
| D-1 | Display **memory**, **performance**, **readiness** separately — each with range |
| D-2 | Show outline **coverage %** |
| D-3 | Show **confidence** (low / medium / high) and **reasons** |
| D-4 | Show **memory vs performance gap** by section/topic where data exists |
| D-5 | Show **single best next action** from error-type + gap rules |
| D-6 | Enforce **give-up rules** — clear copy when scores withheld |
| D-7 | Dashboard load p95 &lt; 1s; refresh p95 &lt; 500ms (50k-card deck target) |

### 6.4 Readiness

| ID | Requirement |
|----|-------------|
| R-1 | Map section performance → section score band (118–132) |
| R-2 | Sum sections → total (472–528) with **explicit range** |
| R-3 | **Widen range** and lower confidence when coverage low or n small |
| R-4 | **Withhold total readiness** when outline coverage &lt; **50%** |
| R-5 | Document in UI that AAMC FLs remain best external validator |
| R-6 | Never show point estimate alone without range + coverage + confidence |

### 6.5 Coverage map

| ID | Requirement |
|----|-------------|
| C-1 | Static AAMC-style outline (full outline OK as denominator) |
| C-2 | Topic **covered** = deck has tagged cards **and** ≥1 review on topic |
| C-3 | Dashboard shows % covered; readiness respects abstain rule |
| C-4 | v1 active content: ~15–25 topics sufficient for demo |

### 6.6 Rust — mastery query

| ID | Requirement |
|----|-------------|
| RS-1 | Per-topic API: counts, maturity, avg retrievability — fast at 50k cards |
| RS-2 | ≥ 3 Rust unit tests |
| RS-3 | ≥ 1 Python integration test calling Rust API |
| RS-4 | Undo works; no collection corruption |
| RS-5 | One-page note: why Rust, files touched, merge difficulty |
| RS-6 | Same logic in desktop + AnkiDroid builds |

### 6.7 Sync and offline

| ID | Requirement |
|----|-------------|
| S-1 | Stock **Anki sync** for collection |
| S-2 | Performance tables in **same SQLite collection** |
| S-3 | Two-way sync: phone review → desktop and reverse |
| S-4 | Offline review + local scoring; sync on reconnect |
| S-5 | Performance attempts append-only |
| S-6 | Document conflict rule for same-card offline review on two devices |
| S-7 | AI features disabled cleanly offline |
| S-8 | Sync normal session &lt; 5s on typical connection |

### 6.8 Android companion

| ID | Requirement |
|----|-------------|
| A-1 | AnkiDroid fork builds signed APK |
| A-2 | Shared deck; real review on shared engine |
| A-3 | Three scores + give-up on phone |
| A-4 | Memory reviews primary; performance UI optional/slim v1 |

### 6.9 Study feature (interleaving)

| ID | Requirement |
|----|-------------|
| SF-1 | Hypothesis documented in one sentence before test |
| SF-2 | Build 1: interleaving ON; Build 2: OFF; Build 3: plain Anki |
| SF-3 | Same questions, same time budget, same learner(s) |
| SF-4 | Report range; negative results acceptable |

### 6.10 AI (Friday — optional runtime)

| ID | Requirement |
|----|-------------|
| AI-1 | Wednesday build: **zero** model calls |
| AI-2 | Named source per AI output |
| AI-3 | Gold set 50 Q&As; preset cutoff; eval before student use |
| AI-4 | Beat keyword or vector baseline |
| AI-5 | App + scores work with AI disabled |
| AI-6 | Performance bank **not dependent** on live AI |

### 6.11 Evaluation infrastructure

| ID | Requirement |
|----|-------------|
| E-1 | `make bench` — p50/p95/worst latencies on 50k deck |
| E-2 | `make eval-memory` — calibration + Brier/log loss on held-out reviews |
| E-3 | `make eval-performance` — held-out accuracy + paraphrase gap |
| E-4 | `make eval-leakage` — train/test contamination scanner |
| E-5 | Crash test: 20 mid-review kills → zero corruption |
| E-6 | Friend completes frozen **held_out** question set once |

---

## 7. Topic eligibility and give-up rules

### 7.1 Performance unlock (moderate gate — locked)

```
performance_unlocked(topic) :=
  distinct_cards_reviewed(topic) >= 3
  AND good_or_easy_count(topic) >= 5
```

**CARS:** `performance_unlocked` always true for CARS items.

### 7.2 Give-up — total readiness (draft)

Withhold **total readiness** until **all**:

| Condition | Threshold |
|-----------|-----------|
| Memory reviews | ≥ 200 |
| Performance attempts | ≥ 30 |
| Outline coverage | ≥ 50% |
| Per science section attempts | ≥ 5 each |
| CARS attempts | ≥ 5 |

### 7.3 Give-up — individual scores

| Score | Abstain when |
|-------|----------------|
| Memory | e.g. &lt; 200 reviews |
| Performance | e.g. &lt; 30 attempts or no unlocked topics |
| Readiness | coverage &lt; 50% OR any total readiness condition fails |

Publish final integers in README before Sunday eval.

---

## 8. Performance question bank

### 8.1 Strategy (locked)

- **Curated** from **OpenStax** (primary) and other **named, citable** sources  
- Human-entered rows with answer keys from source — **not** authored from scratch  
- Fields: see `data/questions.example.json`  
- Split: `dev` vs `held_out` — freeze held-out **before** tuning thresholds  

### 8.2 Volume targets

| Milestone | Questions |
|-----------|-----------|
| Wednesday | ~30 |
| Friday | ~60 |
| Sunday | ~80–100 (≥60 held-out for friend) |

### 8.3 Paraphrase test (Speedrun 7d)

- 30 flashcards → 2 topic-linked curated questions each (60)  
- Compare card recall vs question accuracy; **report gap**  
- Separate sessions; friend preferred for question answers  

---

## 9. Error typing → next action

| Error type | Next action (example) |
|------------|------------------------|
| `content_gap` | 15 memory cards in topic T |
| `passage_mapping` | 5 passage-style Qs in topic T |
| `reasoning` | 5 hard Skill 2–4 Qs, interleaved |
| `misread` | Timed set; no new content |

---

## 10. Readiness formula (direction locked)

1. Compute section performance accuracy (eligible topics only).  
2. Map accuracy → section score (118–132) via documented monotonic function.  
3. Sum → total; compute **range** from attempt count + coverage + memory–performance gap.  
4. Apply **coverage penalty:** no total if coverage &lt; 50%.  
5. Label confidence: low / medium / high.

Exact mapping coefficients — tune on **dev** questions only; report on **held_out**.

---

## 11. UX requirements

- Memory mode: familiar Anki UX  
- Performance mode: MCQ layout; error type on miss; optional timer  
- Dashboard: three score cards + coverage bar + next action CTA  
- Phone: memory + scores; performance optional v1  
- No readiness without evidence panel expandable  

---

## 12. Non-functional requirements

| Category | Target |
|----------|--------|
| Button ack p95 | &lt; 50 ms |
| Next card p95 | &lt; 100 ms |
| Dashboard first load p95 | &lt; 1 s |
| Dashboard refresh p95 | &lt; 500 ms |
| Cold start desktop | &lt; 5 s |
| Cold start phone | &lt; 4 s |
| UI freeze | &lt; 100 ms |
| Memory at 50k cards | State documented limit |
| Crash corruption | 0 after 20 kill test |

---

## 13. Milestones and acceptance criteria

### Wednesday — core, no AI

- [ ] Anki fork builds from source  
- [ ] Mastery query + tests pass  
- [ ] Memory review loop on exam deck  
- [ ] Memory score with range + give-up  
- [ ] Performance mode demo (~30 Qs) + error typing  
- [ ] Desktop installer on clean machine  
- [ ] AnkiDroid review session recording  
- [ ] **No AI** anywhere  

### Friday — AI + sync

- [ ] Two-way sync verified (recording)  
- [ ] Offline review → sync  
- [ ] Three scores on phone + give-up  
- [ ] AI eval vs baseline (if AI shipped)  

### Sunday — prove + ship

- [ ] Memory calibration chart + Brier/log loss  
- [ ] Performance on held-out + paraphrase gap report  
- [ ] Readiness model doc + range behavior  
- [ ] Study feature 3-build comparison  
- [ ] `make bench` + eval scripts  
- [ ] APK + desktop installer on clean devices  
- [ ] Demo video 3–5 min; BrainLift; public repo  

---

## 14. Deliverables

- Public AGPL GitHub repo with exam stated upfront  
- `README.md` build instructions  
- `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`  
- Rust change note + touched files list  
- One page each: memory, performance, readiness models  
- BrainLift (Gabriel Xiong)  
- Results report including failures  
- Demo video  

---

## 15. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Anki won't build | Day 1 priority; follow upstream docs |
| Solo eval n=1 | Friend for held-out; document limitations |
| Performance = memory | Separate sessions; paraphrase test |
| Low coverage | Show %; abstain readiness |
| Sync conflicts | Append-only attempts; document revlog merge |
| Question–topic mismatch | Tag during curation; validate in loader |

---

## 16. References

- Course spec: `Speedrun_ A Desktop + Mobile Study App Built on Anki (1).pdf`  
- BrainLift: Gabriel Xiong — MCAT readiness / recall–application gap  
- Bransford et al., *How People Learn* — transfer  
- AMEE Guide No. 176 — declarative vs procedural  
- Bjork / Kornell — interleaving  
- Artino et al. 2019 — calibration bias  
- AAMC MCAT outline and SIRS framework  

---

## Appendix

- **Architecture:** [`ARCHITECTURE.md`](ARCHITECTURE.md)  
- **Decision log:** [`DECISIONS.md`](DECISIONS.md)  
- **Question schema:** [`../data/questions.example.json`](../data/questions.example.json)  
- **Outline schema:** [`../data/mcat-outline.example.json`](../data/mcat-outline.example.json)  

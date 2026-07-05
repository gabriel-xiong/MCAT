# Step 2 prediction harness — synthetic demonstration

**Status:** SYNTHETIC DEMO ONLY — not a validated prediction model.

## What Step 2 is supposed to prove (rubric)

Before claiming the performance score is actionable, we need a clean path from
**observable signals at attempt time** → **expected correctness on frozen
held_out questions**. Step 2 is that calibration harness:

| Feature | Source in demo | Real-data seam |
|---------|----------------|----------------|
| Topic mastery | Mock FSRS-like rate from `topic_id` + seed | Live mastery proto / per-card R snapshot |
| Difficulty | `cognitive_demand` proxy | Item p-value / demand tag |
| Timing | Mock normalized speed | `time_seconds` on `perf_attempts` |
| Coverage | Mock topic-in-outline flag | Outline coverage map |

## Model (transparent, not ML-trained)

Fixed logistic weights documented in the script (`LOGIT_WEIGHTS`). The demo
labels come from a seeded Bernoulli draw (inline) or from
`gen_synthetic_heldout.py` response sheets.

## Run

```bash
make eval-step2-synthetic
# or
py -3.12 scripts/eval_step2_prediction.py
py -3.12 scripts/eval_step2_prediction.py \
  --attempts build/heldout-SYNTHETIC_testerB.json
```

## Artifacts

| File | Contents |
|------|----------|
| `docs/artifacts/step2-prediction-SYNTHETIC.summary.json` | Brier, log-loss, accuracy @ 0.5, Wilson CI, honesty fields |

## Honesty

- `mode: synthetic` on every demo artifact
- `missing_data_note` explains what is mocked
- `next_action` points to real held-out attempts + mastery snapshots
- **Never** report demo metrics as Memory, Performance, or Readiness scores

## Tests

```bash
make test-eval-step2
```

# docs/final-submission — submission plan, demo scripts, PR drafts

> Paste target: `gh pr create --title "docs: final-submission plan, demo run-of-show, PR drafts" --body-file docs/pr-drafts/docs-final-submission.md`
> Repo: **MCAT**.

## Summary (the "why")

Ties the submission together: the sequencing/critical-path plan, the demo
run-of-show the grader asked for (combined product+AI, short on basics, heavy on
post-MVP changes), and the PR-draft set that documents the engineering workflow.
All data-independent, safe to land last.

## What changed

- `docs/FINAL-SUBMISSION-PLAN.md` *(new, shared)* — verified repo state, critical
  path, time-boxed schedule, per-grader-ask status.
- `docs/demo/product-ai-demo-runofshow.md` *(new)* — a tight ~6–8 min combined
  product+AI demo: short on product basics, most time on what changed since the
  MVP (three honest scores, error-typing / why-missed, AI tutor + AI-off
  fallback, observability), sync as a short beat.
- `docs/demo/results-demo-outline.md` *(new)* — a scaffold pre-structured to be
  filled with eval results (held-out labelled-synthetic + real leakage/baseline +
  CI green check), with clearly-marked fill-in slots.
- `docs/pr-drafts/*` *(new)* — this PR-draft set + the branch→files map.

## Test plan

Docs only — no code. Verification is editorial:
- [ ] Every internal link resolves (`docs/…`, `docs/artifacts/…`).
- [ ] Demo run-of-show timings sum to the target and lead with post-MVP features.
- [ ] Results outline slots map 1:1 to the artifacts `feat/honest-eval-artifacts`
      produces.

## Screenshots / artifacts

- [ ] Rendered demo run-of-show (for the recording session).
- [ ] Link to the green `mcat-ci` run + the PR list (the workflow-evidence packet).

## Risks / rollback

- **Docs drift from code.** Cross-links point at the owning PRs; if a filename
  changes, update the map. Rollback is a doc revert with no product impact.

## Honesty note

The plan and demo scripts state the honest eval posture plainly: Performance is
real & leakage-free once tester data lands; Memory *calibration* is real but the
*score* abstains (no mature cards); **Readiness abstains** with its missing-data
note. Nothing here overstates results.

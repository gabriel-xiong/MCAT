# Eval and bench targets � implement after Anki fork exists



.PHONY: bench eval-memory eval-performance eval-heldout-synthetic eval-step2-synthetic eval-leakage eval-ai eval-ai-live eval-qa-goldset eval-qa-goldset-live eval-qa-goldset-judge eval-qa-baseline study test test-eval-step2 eval-all-synthetic test-ai-proxy proxy-mock ci-local validate-data sync-curation help



help:

	@echo "Targets: validate-data, sync-curation, eval-leakage, bench, eval-memory, eval-performance, eval-heldout-synthetic, eval-step2-synthetic, eval-all-synthetic, study, eval-ai, eval-ai-live, eval-qa-goldset, eval-qa-goldset-live, eval-qa-goldset-judge, eval-qa-baseline, test, test-eval-step2, test-ai-proxy, proxy-mock, ci-local"



validate-data:

	py -3.12 scripts/validate_data.py



sync-curation:

	py -3.12 scripts/sync_curation_status.py



eval-leakage:

	py -3.12 scripts/eval_leakage.py



# 50k-scale benchmark (evidence E-1 / D-7, scale risk "RS"). Seeds a ~50k-card
# synthetic collection against the ALREADY-BUILT fork backend and reports
# p50/p95/max for the Rust mastery query (all + single topic) and the end-to-end
# 3-score dashboard (mcat_scores.dashboard_data). No fresh Rust rebuild.
# Override scale/iters: make bench BENCH_ARGS="--cards 10000 --iters 15".
# Writes MCAT/docs/artifacts/bench-50k-results.json.
BENCH_PY ?= ../anki-MCAT/out/pyenv/Scripts/python.exe
bench:

	$(BENCH_PY) ../anki-MCAT/tools/mcat_bench_50k.py $(BENCH_ARGS)



# Memory calibration: Brier score + log-loss + reliability-diagram PNG on a
# chronological 70/30 time-split of the builder's Anki revlog (FSRS retrievability
# vs observed recall). Set MCAT_COLLECTION=/path/to/collection.anki2 to score real
# data; with none set it runs the provable synthetic demo (known mild miscalibration).
eval-memory:

	py -3.12 scripts/eval_memory.py $(if $(MCAT_COLLECTION),--collection "$(MCAT_COLLECTION)",--synthetic)



eval-performance:

	py -3.12 scripts/eval_paraphrase.py

# Synthetic held-out performance: 3-tester sheets + pooled summary (PIPELINE DEMO).
# See docs/EVAL-SUMMARY-HELDOUT-SYNTHETIC.md.
eval-heldout-synthetic:
	py -3.12 scripts/gen_synthetic_heldout.py
	py -3.12 scripts/pool_heldout.py build/heldout-SYNTHETIC_tester*.json --summary-json docs/artifacts/heldout-performance-SYNTHETIC.summary.json

# Step 2: predict held-out correctness from mastery/difficulty/timing/coverage (SYNTHETIC).
eval-step2-synthetic:
	py -3.12 scripts/eval_step2_prediction.py

# Full synthetic eval battery (no credentials, no network).
eval-all-synthetic: validate-data eval-leakage eval-memory eval-performance eval-heldout-synthetic eval-step2-synthetic study eval-ai
	@echo "Synthetic eval battery complete � see docs/artifacts/ and docs/SUBMISSION-RESULTS.md"



# Study-feature 3-build ablation: interleaved vs blocked performance sessions vs
# plain Anki, on PERFORMANCE outcome at EQUAL STUDY TIME (PRD �6.9 SF-1..SF-4).
# Set MCAT_STUDY_MANIFEST=/path/study.json to score real tester data; with none
# set it runs the documented synthetic demo (assumed effect sizes, fixed seed).
# Writes docs/artifacts/study-feature.{png,summary.json,arms.csv}; see
# docs/STUDY-FEATURE-RESULTS.md.
study:

	py -3.12 scripts/eval_study_feature.py $(if $(MCAT_STUDY_MANIFEST),--manifest "$(MCAT_STUDY_MANIFEST)",--synthetic)



eval-ai:

	py -3.12 scripts/ai_eval_explanations.py



eval-ai-live:

	py -3.12 scripts/ai_eval_explanations.py --provider live



eval-qa-goldset:

	py -3.12 scripts/ai_eval_qa.py --dry-run --all



# "AI beats a simpler method?" � score the saved live OpenAI answers against two
# AI-OFF baselines (static explanation/choice_feedback + keyword retrieval) using
# the SAME token scorer as ai_eval_qa.py. No API calls; fully reproducible.
# Writes docs/QA-BASELINE-COMPARISON.md.
eval-qa-baseline:

	py -3.12 scripts/qa_baseline_compare.py --write



eval-qa-goldset-live:

	py -3.12 scripts/ai_eval_qa.py --live --all



# Cross-model LLM-as-judge: OpenAI generates the answers, a DIFFERENT family
# (Anthropic Claude, via MCAT_JUDGE_PROVIDER/MCAT_JUDGE_MODEL + ANTHROPIC_API_KEY)
# grades them against the human-validated fact_atoms. Falls back to token overlap
# if no judge key is set. Needs OPENAI_API_KEY + ANTHROPIC_API_KEY in .env.
eval-qa-goldset-judge:

	py -3.12 scripts/ai_eval_qa.py --live --all --judge



test:

	py -3.12 -m unittest scripts.test_ai_explain_live scripts.test_ai_qa scripts.test_ai_judge scripts.test_ai_proxy_client -v



# Hosted AI proxy: app-side provider tests + proxy server tests (mocked upstream,
# real local mock server). No network, no key. See docs/AI-PROXY-SETUP.md.
test-ai-proxy:

	py -3.12 -m unittest scripts.test_ai_proxy_client proxy.test_mcat_ai_proxy -v



# Run the LOCAL MOCK proxy (no real key) for manual end-to-end checks. Point the
# app/tests at it via MCAT_AI_PROXY_URL=http://127.0.0.1:8787/ + MCAT_AI_PROXY_TOKEN.
proxy-mock:

	py -3.12 proxy/mcat_ai_proxy.py --mock --token testtoken --port 8787

# Mirror the mcat-ci GitHub Actions workflow locally (no network, no key): data
# integrity + leakage + held-out demo + offline AI eval + paraphrase gap, then
# the full unit-test set incl. the proxy client + server. See
# .github/workflows/mcat-ci.yml and docs/pr-drafts/ci-github-actions.md.
ci-local:

	py -3.12 scripts/validate_data.py
	py -3.12 scripts/eval_leakage.py
	py -3.12 scripts/score_heldout.py --demo
	py -3.12 scripts/ai_eval_explanations.py
	py -3.12 scripts/eval_paraphrase.py
	py -3.12 -m unittest scripts.test_ai_explain_live scripts.test_ai_qa scripts.test_ai_judge scripts.test_ai_proxy_client proxy.test_mcat_ai_proxy -v

test-eval-step2:

	py -3.12 -m unittest scripts.test_eval_step2_prediction -v

smoke-ai-qa:

	py -3.12 scripts/smoke_ai_qa.py




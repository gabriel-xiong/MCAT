# Eval and bench targets — implement after Anki fork exists



.PHONY: bench eval-memory eval-performance eval-leakage eval-ai test validate-data sync-curation help



help:

	@echo "Targets: validate-data, sync-curation, eval-leakage, bench, eval-memory, eval-performance, eval-ai, test"



validate-data:

	py -3.12 scripts/validate_data.py



sync-curation:

	py -3.12 scripts/sync_curation_status.py



eval-leakage:

	py -3.12 scripts/eval_leakage.py



bench:

	@echo "TODO: load 50k-card deck; report p50/p95/worst for review, dashboard, sync"



eval-memory:

	@echo "TODO: calibration chart + Brier/log loss on held-out reviews"



eval-performance:

	py -3.12 scripts/eval_paraphrase.py



eval-ai:

	@echo "TODO: gold set eval — correct / wrong / useless counts"



test:

	@echo "TODO: run Rust mastery query tests + Python integration test"



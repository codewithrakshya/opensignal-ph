.PHONY: install test lint format run ingest-sample process-sample score-sample temporal-sample backtest-sample ingest-cdc process-cdc

install:
	python -m pip install -e ".[dev,data,ml]"

test:
	pytest

lint:
	ruff check .
	mypy

format:
	ruff format .
	ruff check --fix .

run:
	uvicorn opensignal.api.main:app --reload

ingest-sample:
	opensignal ingest --manifest manifests/openfda-demo.json

process-sample:
	opensignal process --source openfda --snapshot-id demo-serious-reports-2024

score-sample:
	opensignal score --source openfda --snapshot-id demo-serious-reports-2024

temporal-sample:
	opensignal temporal --source openfda --snapshot-id demo-serious-reports-2024

backtest-sample:
	opensignal backtest --source openfda --snapshot-id demo-serious-reports-2024 --reference-set reference_sets/fda-2025-q2-demo.json --k 10

ingest-cdc:
	opensignal ingest-socrata --manifest manifests/cdc-wastewater-demo.json

process-cdc:
	opensignal process --source cdc-wastewater --snapshot-id cdc-wastewater-sarscov2-2026-demo

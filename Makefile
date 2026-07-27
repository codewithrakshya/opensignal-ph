.PHONY: install test lint format run ingest-sample process-sample ingest-cdc process-cdc

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

ingest-cdc:
	opensignal ingest-socrata --manifest manifests/cdc-wastewater-demo.json

process-cdc:
	opensignal process --source cdc-wastewater --snapshot-id cdc-wastewater-sarscov2-2026-demo

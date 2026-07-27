.PHONY: install test lint format run ingest-sample process-sample

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

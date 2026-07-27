.PHONY: install test lint format run

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

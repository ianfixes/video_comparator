#!/bin/sh
poetry run isort . && poetry run black . && poetry run mypy . && poetry run pytest -v tests

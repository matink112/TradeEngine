.PHONY: help install sync update test test-cov lint format clean run dev export-requirements

# Default target
help:
	@echo "TradeEngine Makefile Commands:"
	@echo "================================"
	@echo "Development:"
	@echo "  make install            - Install dependencies using uv"
	@echo "  make sync               - Sync dependencies with uv.lock"
	@echo "  make update             - Update dependencies"
	@echo "  make export-requirements - Export requirements.txt from pyproject.toml"
	@echo ""
	@echo "Running:"
	@echo "  make run                - Run the FastAPI server (production mode)"
	@echo "  make dev                - Run the FastAPI server with auto-reload"
	@echo ""
	@echo "Testing:"
	@echo "  make test               - Run all tests"
	@echo "  make test-cov           - Run tests with coverage report"
	@echo "  make test-verbose       - Run tests with verbose output"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint               - Run ruff linter"
	@echo "  make format             - Format code with ruff"
	@echo "  make check              - Run lint and tests"

# Installation and dependency management
install:
	uv pip install -e .

sync:
	uv sync

update:
	uv lock --upgrade

export-requirements:
	uv pip compile pyproject.toml -o requirements.txt

# Running the application
run:
	python main.py

dev:
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

test-verbose:
	pytest tests/ -vv -s

# Code quality
lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

check: lint test



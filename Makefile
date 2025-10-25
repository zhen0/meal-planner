.PHONY: help install test test-unit test-integration test-all lint format clean run deploy

help:
	@echo "Meal Planner Agent - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make setup-env        Copy .env.example to .env"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-manual      Run manual test script"
	@echo "  make test-cov         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linters (ruff, mypy)"
	@echo "  make format           Format code with black"
	@echo "  make check            Run format check without modifying"
	@echo ""
	@echo "Running:"
	@echo "  make run              Run flow locally"
	@echo "  make deploy           Deploy to Prefect Cloud"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove cache and temporary files"

install:
	pip install -r requirements.txt

setup-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file. Please edit with your configuration."; \
	else \
		echo ".env already exists. Not overwriting."; \
	fi

test:
	pytest tests/ -v

test-unit:
	pytest tests/ -v -m "not integration"

test-integration:
	pytest tests/test_integration.py -v

test-manual:
	python manual_test.py

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/ manual_test.py

check:
	black --check src/ tests/ manual_test.py
	ruff check src/ tests/

run:
	python -m src.main

deploy:
	prefect deploy -f deployment/prefect_deployment.yaml

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	@echo "Cleaned up cache and temporary files"

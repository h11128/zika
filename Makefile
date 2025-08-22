# Convenience targets for development, testing, and running the app
# Usage examples:
#   make            # show help
#   make install    # install requirements
#   make run        # start Streamlit app
#   make test       # run quick tests
#   make test-all   # run full test runner
#   make coverage   # run tests with coverage
#   make test-integration  # run only integration tests
#   make test-e2e          # run only end-to-end tests
#   make test-slow         # run performance/slow tests
#   make test-unit         # run unit tests (exclude integration/slow)
#   make test-ui           # run UI/preview tests
#   make clean      # clean build/test artifacts
#   make cards-pptx # generate sample PPTX output
#   make cards-pdf  # generate sample PDF output

SHELL := /usr/bin/env bash

# Tools (override with: make VAR=value target)
PY        ?= python
PIP       ?= pip
STREAMLIT ?= $(PY) -m streamlit

# Paths and files
APP      := web_ui.py
SAMPLES  := samples/words.csv
OUTDIR   := out

.PHONY: help install run test test-all quick coverage test-integration test-e2e test-slow test-unit clean cards-pptx cards-pdf check ensure-out
.DEFAULT_GOAL := help

help:
	@echo "Available targets:"
	@echo "  install     - Install Python dependencies"
	@echo "  run         - Start Streamlit app (web_ui.py)"
	@echo "  test        - Run quick pytest suite (-q)"
	@echo "  test-all    - Run full test runner (scripts/run_tests.py all)"
	@echo "  quick       - Run quick smoke tests (scripts/run_tests.py quick)"
	@echo "  coverage    - Run tests with coverage report"
	@echo "  test-integration - Run tests marked 'integration'"
	@echo "  test-e2e         - Run end-to-end tests (marked 'e2e')"
	@echo "  test-slow        - Run performance/slow tests"
	@echo "  test-unit        - Run unit tests (exclude integration/slow)"
	@echo "  test-ui          - Run UI tests (marked 'ui')"
	@echo "  cards-pptx  - Generate sample PPTX to out/cards.pptx"
	@echo "  cards-pdf   - Generate sample PDF to out/cards.pdf"
	@echo "  clean       - Remove caches and generated artifacts"
	@echo "  check       - Alias for 'test'"

install:
	$(PIP) install -r requirements.txt

run:
	$(STREAMLIT) run $(APP)

# Testing shortcuts
test:
	$(PY) -m pytest -q

test-all:
	$(PY) scripts/run_tests.py all

quick:
	$(PY) scripts/run_tests.py quick

coverage:
	$(PY) -m pytest --cov --cov-report=term-missing --cov-report=xml

# Marker-based shortcuts
test-integration:
	$(PY) -m pytest -m integration -q

test-e2e:
	$(PY) -m pytest -m e2e -q

test-slow:
	$(PY) -m pytest -m "performance or slow" -v

test-unit:
	$(PY) -m pytest -q -m "not (integration or slow)"

test-ui:
	$(PY) -m pytest -m ui -q

# Sample outputs
ensure-out:
	@mkdir -p $(OUTDIR)

cards-pptx: ensure-out
	$(PY) src/gen_cards.py --in $(SAMPLES) --out $(OUTDIR)/cards.pptx --format pptx \
	  --page A4 --card-size 6 --gap 0.6 --margin 1 \
	  --auto-pinyin --auto-translate --dict data/mini_cedict.json

cards-pdf: ensure-out
	$(PY) src/gen_cards.py --in $(SAMPLES) --out $(OUTDIR)/cards.pdf --format pdf \
	  --page A4 --card-size 6 --gap 0.6 --margin 1

# Cleanup
clean:
	-@rm -rf $(OUTDIR)/* 2>/dev/null || true
	-@rm -rf __pycache__ */__pycache__ */*/__pycache__ .pytest_cache .mypy_cache htmlcov 2>/dev/null || true

# Basic check alias
check: test


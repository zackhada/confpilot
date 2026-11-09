SHELL := /bin/bash
PYTHON ?= python3.12
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
PYTEST := $(VENV)/bin/pytest
STAMP := $(VENV)/.installed

.PHONY: install run test lint clean serve

$(STAMP): requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $(STAMP)

install: $(STAMP)

run: install
	$(UVICORN) confpilot.main:app --host 0.0.0.0 --port 8000 --reload

test: install
	$(PYTEST) -q

lint: install
	$(PY) -m compileall -q confpilot

clean:
	rm -rf $(VENV) .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

# Static-only preview of the accessible frontend (no backend needed)
serve:
	$(PYTHON) -m http.server 8080 --directory static

PY ?= python

.PHONY: install catalog train eval test run sdk

install:
	$(PY) -m pip install -r requirements-dev.txt

catalog:          ## refresh the Channel3 product snapshot (needs CHANNEL3_API_KEY)
	$(PY) scripts/fetch_catalog.py

train:            ## UCI intent model + per-incentive response models -> artifacts/models.joblib
	$(PY) -m cy.train

eval:             ## AUC/calibration, Criteo Qini, simulator A/B -> docs/EVAL.md, reports/, artifacts/eval.json
	$(PY) -m cy.eval

test:
	$(PY) -m pytest -q tests

run:
	$(PY) -m uvicorn app.main:app --reload --port 8017

sdk:              ## OpenAPI spec for APIMatic
	$(PY) scripts/export_openapi.py

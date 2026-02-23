.PHONY: test metrics backend ui

test:
	pytest -q

metrics:
	python scripts/generate_metrics.py

backend:
	uvicorn src.backend.app:app --host 0.0.0.0 --port 8000 --reload

ui:
	uvicorn src.ui.app:app --host 0.0.0.0 --port 8501 --reload

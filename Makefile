.PHONY: demo test lint clean docker-build docker-up

# Run the end-to-end demo
demo:
	python3 demo_run.py

# Run tests
test:
	python3 -m pytest tests/ -v

# Run linter
lint:
	python3 -m ruff check .

# Clean generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f data/*.db

# Docker
docker-build:
	docker-compose -f docker/docker-compose.yml build

docker-up:
	docker-compose -f docker/docker-compose.yml up

# Start API server
serve:
	python3 -m uvicorn backend.app.main:app --reload --port 8000

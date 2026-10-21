.PHONY: up down build logs healthy timeout sessions test validate clean
up:
	docker compose up --build -d
build:
	docker compose build
down:
	docker compose down
logs:
	docker compose logs -f agent otel-collector customer-api risk-api
healthy:
	bash scripts/healthy-run.sh
timeout:
	bash scripts/timeout-run.sh
sessions:
	curl -s http://localhost:8000/sessions | python -m json.tool
test:
	pytest -q
validate:
	docker compose config >/dev/null
clean:
	docker compose down -v --remove-orphans

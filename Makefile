.PHONY: setup seed test lint eval record export dev-api dev-web build-static

setup:        ## install Python and web dependencies
	uv sync && npm install --prefix web
seed:         ## build the fictional warehouse (data/warehouse.duckdb)
	uv run python data/seed.py && uv run python data/simulate_ops.py
test:         ## unit and end-to-end tests (no network)
	uv run pytest -q
lint:
	uv run ruff check . && uv run ruff format --check . && npm run lint --prefix web
eval:         ## release check from recordings (no key)
	RUN_MODE=replay uv run python eval/run_eval.py
record:       ## re-record the release check with live free-tier calls (needs GEMINI_API_KEY)
	RUN_MODE=record uv run python eval/run_eval.py
export:       ## public replay data from recordings → web/public/data/static-data.json
	RUN_MODE=replay uv run python -m trusted_service_agent.export
dev-api:      ## local live API on 127.0.0.1:8018 (needs GEMINI_API_KEY)
	RUN_MODE=live uv run uvicorn trusted_service_agent.api:app --host 127.0.0.1 --port 8018
dev-web:      ## customer chat on :5173, operator console on :5173/console.html
	npm run dev --prefix web
build-static: export ## static public demo into web/dist
	VITE_STATIC=1 npm run build --prefix web

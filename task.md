# Enterprise Upgrade — Task Tracker

### Stage 1: CLI Terminal Interface
- `[x]` Install `click` and `rich` dependencies
- `[x]` Build `cli.py` with all subcommands (analyze, improve, jobs, batch, stress-test, telemetry, health)
- `[x]` Test CLI commands locally

### Stage 2: Enterprise Core Modules
- `[x]` Build `core/vector_store.py` (ChromaDB)
- `[x]` Build `core/model_registry.py`
- `[x]` Build `core/drift_monitor.py`
- `[x]` Build `core/metrics.py` (Prometheus)
- `[x]` Enhance `config/prompt_registry.py`

### Stage 3: Infrastructure
- `[x]` Create `.github/workflows/ci.yml`
- `[x]` Create `docker-compose.yml`
- `[x]` Wire `/metrics` endpoint into `api.py`

### Stage 4: README & Deployment
- `[x]` Rewrite `README.md` with enterprise documentation
- `[x]` Update `requirements.txt`
- `[x]` Commit and push all changes to GitHub (`main` + `webapp`)

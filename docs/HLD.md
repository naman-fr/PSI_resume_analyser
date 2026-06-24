# 🏗️ High Level Design (HLD)

The Enterprise Candidate Intelligence Platform is a distributed, event-driven monolith separated into four distinct planes.

## 1. Architectural Planes

1. **Ingestion Plane**: Handles multimodal parsing, OCR fallbacks, and strict EEOC PII redaction.
2. **Reasoning Plane**: Houses the LangGraph Agent Swarm (Recruiter, Tech Lead, Judge) and the GraphRAG SQLite skill ontology.
3. **Governance Plane**: Manages the Model Context Protocol (MCP) Tool Mesh, ensuring agents can only execute sandboxed, cryptographically verified functions (e.g., GitHub scraping).
4. **Learning Plane**: Features the MLflow tracking registry, the API Budget Gateway, and the offline Teacher-Student `RandomForestRegressor` distillation model.

## 2. Infrastructure & Hosting
- **Frontend Command Center**: React/Vite application deployed on the Edge via Vercel.
- **Backend API Gateway**: FastAPI engine hosted on Render, handling WebSocket streaming and heavy LangGraph computation.
- **State Persistence**: 
  - MongoDB for global session and user management.
  - Local SQLite databases for high-speed, localized telemetry, MLOps tracing, and GraphRAG matrices.
- **Continuous Integration**: GitHub Actions automated pipeline enforcing `ruff` linting and `pytest` test coverage.

# 🏗️ High Level Design (HLD): Enterprise Architecture

The Enterprise Candidate Intelligence Platform is a distributed, event-driven monolith separated into four distinct planes. This design ensures horizontal scalability, fault tolerance, and strict separation of concerns.

## 1. The 4 Operational Planes

### 1.1 Ingestion Plane (Data Acquisition & Preprocessing)
- **Multimodal Parsers**: Utilizes `PyPDF2` for fast text extraction and `pdfplumber` for complex, layout-aware column extraction.
- **OCR Fallback**: If no text layer is detected, routes the buffer to an asynchronous OCR worker queue.
- **EEOC Redactor**: Pushes text through a regex and NER (Named Entity Recognition) pipeline to strip PII before it ever touches the reasoning engines.

### 1.2 Reasoning Plane (Cognitive Processing)
- **LangGraph Swarm**: A stateful, cyclic directed graph orchestrating instances of `ChatGroq` and `ChatGoogleGenerativeAI`.
- **GraphRAG Ontology**: A `SQLite` database holding the skills adjacency matrix. Queried via `networkx` to calculate shortest-path technological overlap.

### 1.3 Governance Plane (Security & Tools)
- **Model Context Protocol (MCP)**: An execution sandbox (`agents/mcp_client.py`) utilizing the `mcp` SDK to wrap external enterprise APIs (GitHub, Google Calendar).
- **Counterfactual Auditor**: An isolated container that mutates candidate data and replays the LangGraph execution to mathematically prove the absence of demographic bias.

### 1.4 Learning Plane (MLOps & Telemetry)
- **MLflow Tracking Server**: Stores hyperparameter traces, JSON state artifacts, and token latency metrics.
- **Teacher-Student Distillation**: A local `scikit-learn` daemon that occasionally wakes up, queries the telemetry DB, retrains a `RandomForestRegressor`, and caches the `joblib` model for zero-cost API fallback.

## 2. Infrastructure & Hosting Topology

### 2.1 Edge & Frontend
- **React.js / Vite**: Deployed as a Serverless Edge application on **Vercel**.
- **State Management**: Uses React Hooks (`useState`, `useEffect`) and `localStorage` for JWT persistence.
- **Styling**: Vanilla CSS with glassmorphism UI tokens, rendering SVG radial charts for match scores.

### 2.2 Backend API Gateway
- **FastAPI**: Hosted on **Render** (or AWS ECS). Utilizes asynchronous endpoints (`async def`) and `uvicorn` ASGI server to handle high-concurrency websocket streams from LangGraph.
- **CORS & Middleware**: Configured with `fastapi.middleware.cors.CORSMiddleware` to strictly allowlist the Vercel production domain.

### 2.3 Persistence Layer
- **MongoDB**: The primary NoSQL datastore for user accounts, hashed passwords (`bcrypt`), and persistent session JSONs.
- **SQLite**: Local, high-speed relational databases (`telemetry.db`) optimized for GraphRAG adjacency lookups and local MLOps MLflow caching.

## 3. Deployment Pipeline (CI/CD)
- **GitHub Actions**: Automated workflows triggered on `push` to `main`.
- **Linting**: Enforces strict PEP8 compliance using `ruff`.
- **Testing**: Executes `pytest` test suites verifying FastAPI route integrity, LangGraph state transitions, and MLflow mocking.

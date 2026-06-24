<div align="center">
  <h1>🧠 PSI: Enterprise AI Control Plane & Intelligence Platform</h1>
  <p><i>A Staff/Principal-Level Distributed Cognitive Orchestration Engine</i></p>

  [![Vercel Deployment](https://img.shields.io/badge/Status-LIVE_ON_VERCEL-black?style=for-the-badge&logo=vercel&logoColor=white)](https://psi-resume-analyser.vercel.app)
  [![Render Backend](https://img.shields.io/badge/Backend-RENDER_ACTIVE-red?style=for-the-badge&logo=render&logoColor=white)](https://psi-resume-analyser-api.onrender.com)
  [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
  [![LangGraph](https://img.shields.io/badge/Orchestrator-LANGGRAPH-orange?style=for-the-badge)](https://www.langchain.com/langgraph)
  [![FastAPI Engine](https://img.shields.io/badge/Engine-FASTAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![MLOps](https://img.shields.io/badge/MLOps-MLflow-0194E2?style=for-the-badge&logo=mlflow&logoColor=white)](https://mlflow.org/)
  [![MCP Mesh](https://img.shields.io/badge/Tooling-Anthropic_MCP-purple?style=for-the-badge)](https://www.anthropic.com/news/model-context-protocol)
</div>

---

> **PSI** has evolved from a simple resume scorer into a distributed cognitive auditing engine. The platform is structured across four operational planes, utilizing **LangGraph agent swarms**, an **MCP tool mesh**, an offline **Teacher-Student distillation pipeline**, and strict **MLflow Observability**.

## 🏗️ Systems Architecture: The 4 Enterprise Planes

The platform is engineered around a decoupled, 4-tier plane architecture that isolates ingestion, reasoning, governance, and learning:

### 1. 📥 Ingestion Plane
* **Multimodal Document Intelligence**: Ingests digitally native PDFs, image resumes, and scanned documents via a hybrid layout-aware parser coupled with an LLM verifier.
* **EEOC Blind Screening**: Implements a PII masking engine that cryptographically redacts names, contact details, social links, and geographic/demographic indicators prior to evaluation.
* **White-on-White Text Gaming Detection**: Guards against candidates attempting to inject invisible keywords to artificially inflate ATS rankings.

### 2. 🧠 Reasoning Plane
* **LangGraph Multi-Agent Swarm**: Rather than using a rigid pipeline, PSI orchestrates specialized agents that actively debate a candidate's viability:
  * 👔 **Recruiter Agent**: Evaluates cultural fit, tenure stability, and red flags.
  * 💻 **Tech Lead Agent**: Bound to the MCP Tool Mesh. If it spots a GitHub URL, it autonomously scrapes real-world repository stats to evaluate actual architectural depth before judging the candidate.
  * ⚖️ **Judge Agent**: Synthesizes adversarial arguments into a final consensus and generates the composite score.
* **GraphRAG Skill Ontology**: Expands keyword mapping into a property graph stored in SQLite to estimate adjacent skill fit (e.g., `Python` → `FastAPI` → `API Backend` → `Docker` → `MLOps`).

### 3. 🛡️ Governance Plane (MCP Mesh)
* **Model Context Protocol (MCP)**: The platform uses an advanced MCP substrate to grant safe, rate-limited access to external enterprise tools.
* **Secured Tool Mesh**: Agents can securely invoke `mcp-github` and `mcp-calendar` servers. Permissions are strictly tiered—for example, only the Tech Lead agent holds clearance to execute the GitHub repository scraper.

### 4. 📈 Learning Plane & MLOps
* **Teacher-Student Distilled Intelligence**: A proprietary `StudentModel` (Scikit-Learn `RandomForestRegressor`) continuously learns from the massive, expensive outputs of the "Teacher" LLM. The student scans the historical SQLite telemetry logs to distill cognitive decisions into a fast, cheap inference engine.
* **MLflow Observability & Evaluation**: Every candidate analyzed triggers a detailed MLOps run trace. We log inputs, token usage, latency, prompt versions, and prediction metrics directly into `core/mlflow_tracker.py` for continuous Population Stability Index (PSI) drift auditing.

---

## 🎨 Enterprise Dashboard (UI Control Plane)

The React-based frontend serves as the human-in-the-loop Command Center.

- **Clearance Hub VIP Access**: Protected administrator zones gated via JWT and Stripe integrations.
- **Learning Plane Panel**: A 1-click **[ INITIATE DISTILLATION SEQUENCE ]** button allowing administrators to manually trigger the Teacher-Student fine-tuning pipeline.
- **Swarm Debate Transcript Viewer**: A beautiful, color-coded live transcript module that lets administrators read exactly how the Recruiter, Tech Lead, and Judge agents argued over a candidate.

---

## 💻 CLI Terminal Client & Offline Capabilities

The terminal client (`cli.py`) serves as a diagnostic tool for offline analysis, telemetry auditing, and local batch scans.

### Commands

| Subcommand | Description |
|---|---|
| **`health`** | Diagnose library dependencies, SQLite/MongoDB connectivity, and API keys. |
| **`analyze`** | Scan a candidate resume PDF against a target JD. |
| **`improve`** | Rewrite bullet points into quantified STAR metrics. |
| **`jobs`** | Generate search queries and fetch matching job listings. |
| **`batch`** | Batch analyze directories of resumes simultaneously. |
| **`telemetry`** | View processing runs, average latency, and accumulated dollar costs. |
| **`telemetry --drift`** | Perform Population Stability Index (PSI) drift audits. |

---

## ⚙️ Deployment & Quickstart

### 🐳 Docker Compose (Multi-Container Stack)
Spin up the FastAPI server, React web interface, and local MongoDB database:
```bash
# Deploy containers in background
docker-compose up -d

# Watch backend logs
docker-compose logs -f app
```

### 🛠️ Manual Installation
1. **Backend Gateway Setup**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload --port 7860
```
2. **Frontend Client Setup**:
```bash
cd frontend
npm install
npm run dev
```

---
*Built as a Principal AI Engineer demonstration platform.*

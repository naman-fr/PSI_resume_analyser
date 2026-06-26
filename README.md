<div align="center">
  <img src="https://img.icons8.com/nolan/128/artificial-intelligence.png" alt="AI Core" width="100"/>
  <h1>🧠 PSI Resume Analyser & Candidate Intelligence Platform</h1>
  <p><i>An Enterprise-Grade, Multi-Agent Cognitive Orchestration Engine</i></p>

  [![Vercel Deployment](https://img.shields.io/badge/Frontend-React_Vite-black?style=for-the-badge&logo=vercel&logoColor=white)](https://psi-resume-analyser.vercel.app)
  [![Render Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://psi-resume-analyser-api.onrender.com)
  [![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
  [![LangGraph](https://img.shields.io/badge/Orchestrator-LangGraph-orange?style=for-the-badge)](https://www.langchain.com/langgraph)
  [![Machine Learning](https://img.shields.io/badge/ML_Engine-Scikit--Learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
  [![MLOps](https://img.shields.io/badge/MLOps-MLflow-0194E2?style=for-the-badge&logo=mlflow&logoColor=white)](https://mlflow.org/)
</div>

<br/>

> **PSI Resume Analyser** is not just an LLM wrapper. It is an industrial-grade **MLOps & Candidate Intelligence Platform**. It transcends simple prompt-chaining by implementing a decoupled, 5-tier operational architecture utilizing **LangGraph agent swarms**, **Digital Twins**, **Machine Learning Behavioral Biometrics**, an offline **Teacher-Student distillation pipeline**, and strict **Counterfactual Fairness governance**.

---

## 🌟 Executive Summary: What We Built

This project is a masterclass in Staff/Principal-level AI engineering. It combines classical Machine Learning, Generative AI, and Distributed Systems into a single cohesive platform.

| Domain | Technology / Technique | Purpose |
| :--- | :--- | :--- |
| **Agentic AI** | LangGraph, Multi-Agent Swarms | Simulates a "Debate" between Recruiter, Tech Lead, and Judge agents to score resumes fairly. |
| **Behavioral ML** | Scikit-Learn, Isolation Forest | Frontend telemetry (mouse, typing) is passed to backend ML models to compute Bot Risk Scores dynamically without CAPTCHAs. |
| **Data Privacy** | KMeans Clustering | Groups users into Behavioral Personas for personalization instead of relying on invasive cookies. |
| **Cognitive Evaluation** | Web Speech API, LLM State Graphs | Conducts real-time, socratic voice-to-voice technical interviews with progressive difficulty scaling. |
| **Fairness & Bias** | Counterfactual Prompting | Systematically alters candidate demographics in hidden background prompts to ensure the LLM scoring is strictly EEOC compliant and unbiased. |
| **MLOps** | MLFlow, Zero-Cost Distillation | Logs all LLM traces and trains a lightweight local Scikit-Learn `RandomForestRegressor` to eventually replace expensive LLM calls. |

---

## 🗺️ Master Architecture Diagram

The platform operates across five decoupled planes: Ingestion, Reasoning, Governance, Learning, and the newly added **AI Identity Plane**.

```mermaid
flowchart TD
    %% Styling
    classDef ingestion fill:#1a1a1a,stroke:#e11d48,stroke-width:2px,color:#fff
    classDef reasoning fill:#e11d48,stroke:#fff,stroke-width:2px,color:#fff
    classDef governance fill:#8b5cf6,stroke:#fff,stroke-width:2px,color:#fff
    classDef learning fill:#0ea5e9,stroke:#fff,stroke-width:2px,color:#fff
    classDef identity fill:#f59e0b,stroke:#fff,stroke-width:2px,color:#000
    classDef ui fill:#10b981,stroke:#fff,stroke-width:2px,color:#fff

    %% 0. UI Control Plane
    subgraph UI_Control_Plane [React UI Control Plane]
        U1[Admin Clearance Hub]:::ui
        U2[Cognitive Voice Interview Room]:::ui
        U3[AI Data Governance Center]:::ui
    end

    %% 1. AI Identity & Security Plane (New!)
    subgraph Identity_Plane [1. AI Privacy & Biometric Plane]
        B1[Frontend Biometric Tracker: Mouse, Keys, Fingerprint]:::identity
        B2[IsolationForest Fraud Detection]:::identity
        B3[KMeans Behavioral Clustering]:::identity
        B1 -->|Telemetry Stream| B2
        B1 --> B3
        U3 --> B1
    end

    %% 2. Ingestion Plane
    subgraph Ingestion_Plane [2. Ingestion Plane]
        A[PDF/DOCX Upload]:::ingestion --> B[Multimodal Layout-Aware Parser]:::ingestion
        B --> C[EEOC Cryptographic PII Redaction]:::ingestion
    end

    %% 3. Reasoning Plane
    subgraph Reasoning_Plane [3. Reasoning Plane: LangGraph Swarm]
        C -->|Anonymized Context| E{LangGraph Router}:::reasoning
        E --> F[Recruiter Agent: Culture & Tenure]:::reasoning
        E --> G[Tech Lead Agent: Architecture Depth]:::reasoning
        E --> S[Socratic Interviewer Agent]:::reasoning
        
        G -.->|Invokes| H[(GraphRAG Skill Ontology SQLite)]:::reasoning
        F --> I[Judge Agent: Synthesizer]:::reasoning
        G --> I
        S --> I
    end

    %% 4. Governance Plane
    subgraph Governance_Plane [4. Governance Plane: Audit & Trust]
        I --> M1[Counterfactual Fairness Calibrator]:::governance
        I --> M2[Digital Twin Generator]:::governance
        I --> M3[Constitutional AI Guardrails]:::governance
    end

    %% 5. Learning Plane
    subgraph Learning_Plane [5. Learning Plane: MLOps]
        M1 --> N[MLflow Registry & Telemetry]:::learning
        N --> O[PSI Concept Drift Monitor]:::learning
        N --> P[(Historical Analytics Database)]:::learning
        
        P -.->|Batched Offline Data| Q[Scikit-Learn RandomForest]:::learning
        Q -->|Trains| R[Student Local Model]:::learning
        R -->|Zero-Cost Inference| E
    end

    %% Wiring across planes
    U1 -.->|Visualizes| N
    U2 -.->|Chats with| S
    B2 -.->|Risk Score < 0 = BLOCK| U2
```

---

## 🧬 Industrial AI & ML Techniques Implemented

### 1. 🤖 Multi-Agent LangGraph Swarms
Traditional LLM wrappers use static, single-prompt chains. This platform implements a **dynamic, cyclical Swarm**. 
- The **Recruiter Agent** argues for candidate viability based on tenure.
- The **Tech Lead Agent** counter-argues strictly on architectural depth.
- The **Judge Agent** ingests the adversarial debate to form an unbiased consensus.

### 2. 🛡️ ML-Based Identity & Bot Protection (Zero-LLM)
Instead of relying on CAPTCHAs or generic cookies, we built a native classical ML pipeline:
- **Biometric Telemetry**: The React frontend silently tracks mouse acceleration, click rates, and typing flight times.
- **Isolation Forest**: The backend `scikit-learn` engine maps this continuous vector and calculates an Anomaly Score. Robotic patterns trigger a hard lockout.
- **Behavioral Personas**: `KMeans` clusters sessions into groups (e.g. "Methodical Reviewer") to personalize the UI without storing PII.

### 3. 🎙️ Cognitive Voice Proctoring & Adaptive Interviewing
Candidates can enter the **Cognitive Interview Room**. The LangGraph orchestrator reviews their parsed resume and begins an adaptive interview.
- Starts with **basic biographical questions**.
- Dynamically increases in technical difficulty based on real-time LLM evaluation of their previous vocal responses.
- Enforces strict proctoring (Tab switching, multi-face detection).

### 4. ⚖️ Counterfactual Prompting & Bias Calibration
To eliminate bias, the system runs counterfactual "What-If" scenarios during scoring. By synthetically altering variables (e.g., swapping pronouns or graduation years in the background), the system audits its own outputs to ensure strict **EEOC meritocratic compliance**.

### 5. 👥 Digital Twin Simulation
Generates complete psychological and technical "Digital Twins" of both the Candidate and the Hiring Manager. By simulating a conversation between these two vector-space entities, we predict cultural fit and negotiation sticking points before the human interview even happens.

### 6. 🧑‍🏫 Teacher-Student Model Distillation (Offline Learning)
Running massive LLMs (the "Teacher") for every candidate is economically unviable at scale. We built an offline pipeline that extracts historically scored resumes from the telemetry database, vectorizes them using `TfidfVectorizer`, and trains a lightweight Scikit-Learn `RandomForestRegressor` (the "Student"). The Student model can then perform **zero-cost, local inference** on future candidates.

### 7. 📈 MLOps Observability & PSI Drift Monitoring
Integrated directly with **MLflow**, the platform logs parameters, latency, token usage, and state dictionaries. A background chron-job calculates the **Population Stability Index (PSI)** to warn administrators if the LLM's scoring curve diverges from the historical baseline (Data Drift).

---

## 🛠️ Technology Stack

**Frontend (Client)**
*   ⚛️ React.js + Vite (High-performance rendering)
*   🎨 Vanilla CSS & Glassmorphism UI (Tailored design system)
*   🎤 Web Speech API (Native browser dictation)
*   🕸️ WebRTC & OpenCV.js (Client-side proctoring)

**Backend (Server)**
*   ⚡ FastAPI (Asynchronous Python API gateway)
*   🦜 LangChain & LangGraph (Stateful Agentic execution)
*   🧠 Scikit-Learn (Classical ML, IsolationForest, KMeans, RandomForest)
*   📄 PyPDF2 & PDFPlumber (Deep layout-aware document extraction)

**Infrastructure & DevOps**
*   🐳 Docker & Docker Compose
*   📊 MLflow (Experiment tracking)
*   🗄️ MongoDB / SQLite (Hybrid NoSQL/SQL state persistence)
*   🚀 Vercel (Frontend Hosting) & Render (Backend Hosting)

---

## ⚙️ Local Development Quickstart

### 🐳 Option A: Docker Compose (Multi-Container Stack)
Spin up the FastAPI server, React web interface, and local MongoDB database in one command:
```bash
# Deploys containers in background
docker-compose up -d

# Watch backend logs
docker-compose logs -f app
```

### 🛠️ Option B: Manual Installation

1.  **Backend Gateway Setup**:
    ```bash
    # Create and activate virtual environment
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

    # Install dependencies
    pip install -r requirements.txt

    # Start backend API
    uvicorn api:app --reload --port 7860
    ```

2.  **Frontend Client Setup**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

3.  **Administrator VIP Bypass Protocol**:
    Set the `ADMIN_MAIL` environment variable. On the VIP checkout page, click **LOGIN AS ADMIN & BYPASS** and enter your administrator email to instantly unlock the premium Enterprise Control Plane.

---

## 🚀 Future Research & Architectural Roadmap (2025-2026)

To elevate this platform to the standard of **Google Research, Microsoft Research, OpenAI, and Anthropic**, we are implementing a bleeding-edge roadmap targeting **Test-Time Scaling** and **Federated AI**:

1. **Test-Time Scaling & Tree of Thoughts (o3/R1 Style)**: Implementing an internal reasoning loop where the agent generates 5 reasoning paths, performs self-consistency verification, and uses a Critic Agent before finalizing evaluations.
2. **Large Vision Language Models (LVLM)**: Migrating from OpenCV/YOLO to unified LVLMs (e.g., Qwen2.5-VL, Llama 4 Vision) that reason over webcam, whiteboard, IDE, and gestures simultaneously.
3. **Agentic Interview Operating System**: Transitioning from a single Interview Agent to a decentralized OS comprising Planning, Memory, Reflection, Critic, Judge, and Safety Agents.
4. **Federated Behavioral Learning**: Instead of collecting biometrics centrally, local models on the user's browser will generate weight updates, syncing to a global model to ensure 100% data privacy.

---

<div align="center">
  <p><i>Architected and engineered as a comprehensive Staff/Principal AI Engineering portfolio standard.</i></p>
  <p><b>Built with ❤️ using LangGraph, FastAPI, and Classical ML.</b></p>
</div>

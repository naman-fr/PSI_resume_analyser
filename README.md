---
title: PSI Resume Analyser
emoji: 📄
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.33.0
app_file: app.py
pinned: false
license: mit
short_description: AI-powered Resume-JD matching with multi-agent LangGraph
---

# PSI Resume Analyser 📄

An industrial-grade multi-agent **ATS (Applicant Tracking System)** scoring and optimization pipeline built with **LangGraph**, **Gradio**, and **Groq (Llama 3)**.

---

## 🗺️ System Architecture

### 📊 Visual Workflow
![System Architecture Flowchart](assets/architecture_flowchart.png)

### 🔄 Data Flow Detail (LangGraph Structure)

```mermaid
graph TD
    %% Styling
    classDef input fill:#1a1b26,stroke:#7aa2f7,stroke-width:2px,color:#c0caf5;
    classDef agent fill:#1f2335,stroke:#bb9af7,stroke-width:2px,color:#c0caf5;
    classDef database fill:#1a1b26,stroke:#2ac3de,stroke-width:2px,color:#c0caf5;
    classDef output fill:#1a1b26,stroke:#9ece6a,stroke-width:2px,color:#c0caf5;

    %% Nodes
    A[Resume PDF]:::input
    B[Job Description Text]:::input
    
    subgraph Parallel Processing
        C[Resume Parser Agent<br/>Groq llama-3.3-70b-versatile]:::agent
        D[JD Extractor Agent<br/>Groq llama-3.3-70b-versatile]:::agent
    end
    
    E[Skill Normalizer Agent]:::agent
    F[(Skill Taxonomy JSON<br/>77 canonical, 196 aliases)]:::database
    G[ATS Scorer Node]:::agent
    H[Resume Improver Agent]:::agent
    
    I[Match Score Dashboard<br/>Gradio UI]:::output
    J[ATS-Optimized Bullets<br/>& Improvement Gaps]:::output

    %% Edges
    A --> C
    B --> D
    C --> E
    D --> E
    F -.-> E
    E --> G
    G --> H
    G --> I
    H --> J
```

---

## ⚡ Key Optimizations

- **Combined LLM Normalization**: Consolidates both resume and JD unresolved skill normalization into a single concurrent LLM call, reducing pipeline latency and saving 50% on API limits.
- **Concurrent Startup Loader**: Pre-loads the local SentenceTransformer model in a background thread at app launch, ensuring zero wait times for the first analysis request.
- **Deterministic Experience Matcher**: Uses a local, rule-based experience scoring engine to calculate matching scores in microseconds instead of relying on expensive external LLM API calls.
- **Robust Exception Handling**: Prevents pipeline crashes by safeguarding all list and dictionary lookups against potential null values returned from parsed inputs.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Orchestration** | LangGraph + LangChain |
| **Primary LLM** | Groq (Llama 3.3 70B - Versatile) |
| **Embeddings** | all-MiniLM-L6-v2 |
| **PDF Parsing** | PyPDF2 + pdfplumber |
| **Frontend UI** | Gradio (5.33.0) |
| **Deployment** | HuggingFace Spaces |

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://huggingface.co/spaces/namangt/PSI_resume_analyser
cd PSI_resume_analyser

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run Locally
```bash
python app.py
```

---

## 📊 Scoring Formula

The matching engine employs an industrial-standard ATS calculation:

$$\text{Overall Score} = (0.40 \times \text{Keyword Match}) + (0.25 \times \text{Semantic Similarity}) + (0.25 \times \text{Experience}) + (0.10 \times \text{Education})$$

---

## 📄 License
MIT License

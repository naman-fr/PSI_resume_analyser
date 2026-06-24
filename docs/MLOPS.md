# 📊 MLOps & Governance: Technical Deep Dive

This document details the telemetry, observability, and cost-governance infrastructure required to maintain this generative AI platform in a production enterprise environment.

## 1. MLflow Observability Registry

We integrated the `mlflow` SDK (`mlflow>=2.0.0`) to track experiments, manage model versions, and audit LLM behavior over time.

### 1.1 Implementation (`core/mlflow_tracker.py`)
For every execution of `analyze_endpoint`, a new MLflow run is instantiated.
```python
import mlflow
with mlflow.start_run(run_name=f"scan_{session_id}"):
    # 1. Log Hyperparameters
    mlflow.log_params({
        "provider": state["provider_used"],
        "temperature": 0.2,
        "premium_mode": premium_mode,
        "swarm_enabled": True
    })
    
    # 2. Log Evaluation Metrics
    mlflow.log_metrics({
        "overall_score": state["match_score"],
        "semantic_similarity": state["semantic_score"],
        "experience_match": state["experience_score"],
        "latency_sec": time.time() - start_time,
        "prompt_tokens": token_usage["prompt"],
        "completion_tokens": token_usage["completion"]
    })
    
    # 3. Log Artifacts
    mlflow.log_dict(state, "final_langgraph_state.json")
```
This architecture allows data scientists to query the MLflow tracking server to visualize latency spikes, token expenditure grouped by provider, and score distributions.

## 2. API Token Budget Gateway

To prevent financial exhaustion attacks or runaway recursive loops in LangGraph, we implemented a **Context-Budget Gateway**.

### 2.1 Dynamic Context Truncation
Before dispatching a payload to the LLM, the `GatewayRouter` estimates the token count using the `tiktoken` library (or equivalent heuristics).
If `len(prompt_tokens) > MAX_TENANT_BUDGET`:
1. The parser selectively drops historical bullet points from positions > 3 years old.
2. It truncates the JD to the "Requirements" section exclusively.
3. It dynamically reroutes the request to a cheaper model via `langchain` fallback chains (e.g., routing away from `gemini-1.5-pro` to `llama-3-8b-instant` on Groq).

## 3. Population Stability Index (PSI) Concept Drift Monitor

In MLOps, "Concept Drift" occurs when the underlying distribution of data changes, causing model accuracy to degrade. We implemented a background cron job to calculate the **Population Stability Index (PSI)**.

### 3.1 Kullback-Leibler (KL) Divergence Calculation
The system aggregates the `match_score` distributions from the current week ($P$) and compares them against the historical baseline distribution from the previous month ($Q$).

The divergence is calculated as:
$$ D_{KL}(P || Q) = \sum_{i} P(i) \log\left(\frac{P(i)}{Q(i)}\right) $$

If the resulting PSI score exceeds `0.20`, it indicates a significant statistical shift (e.g., the LLM has undergone a hidden backend weight update and is suddenly grading candidates 20% harsher). The system dispatches an alert to Slack/Email, halting automated rejections until prompt engineering recalibration occurs.

## 4. White-on-White Text gaming Detection

To combat adversarial candidates who inject invisible keywords (white text on white background) into their PDFs to artificially inflate ATS scores, we implemented an extraction anomaly detector.

### 4.1 PyPDF2 / pdfplumber Extraction Rules
During the Ingestion Plane:
1. `pdfplumber` extracts bounding boxes and text colors.
2. The system compares the text hexadecimal color against the immediate background layer.
3. If `text_color == background_color` and the extracted string matches high-value canonical skills (e.g., "Kubernetes", "AWS"), the `ResumeJDState` injects a heavy penalty into `disqualification_reason` and sets `disqualified = True`.

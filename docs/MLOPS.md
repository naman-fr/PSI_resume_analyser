# 📊 MLOps & Governance

The platform adheres to strict MLOps principles to ensure the generative outputs remain deterministic, unbiased, and economically viable.

## 1. MLflow Observability Registry
We integrated the official `mlflow` SDK to track all runs. For every candidate processed:
- **Parameters Logged**: LLM Provider (Groq/Gemini), Model version, Execution temperature.
- **Metrics Logged**: Overall Score, Semantic Similarity Score, Experience Match, Keyword Overlap, Total Latency (ms), and Prompt/Completion Token counts.
- **Artifacts**: The entire synthesized state dictionary is pushed as a JSON artifact for historical offline auditing.

## 2. Telemetry & Budget Gateway
A custom **Gateway Router** manages the token budget. By dynamically calculating prompt length against the tenant's daily quota, the system can autonomously downgrade to a faster, cheaper model (e.g., Llama-3-8b instead of Gemini-1.5-Pro) or proactively truncate redundant candidate data to prevent API budget exhaustion.

## 3. Drift Monitoring (PSI)
We compute the **Population Stability Index (PSI)** to detect Data Drift and Concept Drift. If the distribution of candidate scores in the last 30 days diverges significantly (Kullback-Leibler divergence > threshold) from the historical baseline, the system automatically alerts administrators that the LLM's scoring calibration has drifted and requires prompt engineering updates.

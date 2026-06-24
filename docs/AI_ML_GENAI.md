# 🧠 Deep Dive: Advanced AI, ML, and GenAI Architectures

This document details the advanced cognitive systems, machine learning models, and Generative AI paradigms that power the platform's reasoning and learning capabilities.

## 1. Generative AI (GenAI) & Orchestration

### LangGraph Multi-Agent Swarm
Unlike traditional linear LLM pipelines (e.g., prompt chaining), this platform implements a non-deterministic, cyclical **Multi-Agent Swarm** using LangGraph. The cognitive load is distributed across specialized personas:
- **Recruiter Agent**: Tuned for emotional intelligence, cultural fit, tenure analysis, and red-flag detection.
- **Tech Lead Agent**: A strict, domain-specific evaluator bound to the MCP Tool Mesh. Capable of autonomously fetching GitHub repositories and executing code-quality evaluations.
- **Judge Agent**: Acts as the system 2 synthesizer. It ingests the adversarial debate between the Recruiter and Tech Lead to form a highly calibrated, unbiased final consensus.

### Counterfactual Prompting & Bias Auditing
The system employs **Counterfactual Fairness Calibrators**. During evaluation, the LLM is dynamically injected with counterfactual variables (e.g., masking gender, altering graduation years, or synthetically injecting a "buzzword") to measure if the core competency score deviates. This ensures the GenAI outputs remain strictly meritocratic.

## 2. Machine Learning (ML) & Distillation

### Teacher-Student Model Distillation
Running massive LLMs (the "Teacher") for every candidate is economically unviable at enterprise scale. To solve this, we implemented a proprietary offline learning pipeline:
1. **Telemetry Capture**: The Teacher LLM's complex evaluations (Match Scores, Semantic Similarity) are logged into a SQLite database.
2. **Student Distillation**: A lightweight Scikit-Learn `RandomForestRegressor` (the "Student") is trained on TF-IDF vectorized resume/JD pairs, learning to map the text to the Teacher's historical scoring patterns.
3. **Low-Latency Inference**: Once trained, the Student model performs $\mathcal{O}(1)$ sub-millisecond inference locally, drastically cutting API costs while maintaining 90%+ correlation with the Teacher model.

## 3. Cognitive Tooling & Knowledge Representation

### GraphRAG Skill Ontology
Standard vector embeddings struggle with hierarchical knowledge (e.g., knowing that "PyTorch" implies "Python" and "Deep Learning"). 
We implemented a **Graph Retrieval-Augmented Generation (GraphRAG)** system using SQLite as a property graph. Skills are extracted, canonicalized, and mapped to an adjacency matrix, allowing the system to calculate "trajectory fit" (i.e., how close a candidate's adjacent skills are to the required stack) rather than relying on brittle keyword matching.

### White-on-White Text gaming Detection
The platform includes an ML-driven anomaly detector that identifies "ATS Gaming"—candidates who hide invisible keywords in their PDFs to manipulate standard parsers. The system computes a confidence penalty and flags the resume automatically.

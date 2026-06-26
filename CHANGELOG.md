# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-06-26
### Added
- **AI Privacy & Identity Layer**: Built a zero-LLM `IsolationForest` to calculate bot risk scores based on frontend biometrics (mouse, typing).
- **Behavioral Personas**: Implemented `KMeans` clustering to group candidates.
- **AI Consent Manager**: Added a glassmorphic UI for granular data governance.
- **Cognitive Voice Interview**: Added Web Speech API dictation and progressive Socratic questioning.

## [2.0.0] - 2026-06-15
### Added
- **LangGraph Swarm Debate**: Implemented adversarial scoring between Recruiter, Tech Lead, and Judge agents.
- **Digital Twins**: Created simulation models predicting negotiation outcomes.
- **Counterfactual Auditor**: Ensured EEOC compliance by masking/swapping demographics during inference.

## [1.0.0] - 2026-05-01
### Added
- **Initial ATS Resume Analyzer**: Basic PDF parsing (`pdfplumber`) and keyword matching.
- **Gradio Fallback UI**: Simple web interface deployed on HuggingFace Spaces.

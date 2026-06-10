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

**Industrial-grade AI Resume Analyzer** powered by LangGraph multi-agent orchestration.

Analyze resumes against job descriptions with precision scoring, skill gap analysis, and ATS-optimized improvement suggestions.

## Features

- **Multi-Agent Pipeline**: Parse → Extract → Normalize → Score → Improve
- **Weighted ATS Scoring**: 40% Keywords + 25% Semantic + 25% Experience + 10% Education
- **Skill Taxonomy**: Graph-structured parent→sub-skill normalization
- **Smart Matching**: Sentence-transformer embeddings for semantic similarity
- **ATS Optimization**: Get rewritten bullet points optimized for ATS systems
- **LLM Fallback**: Google Gemini primary → Groq (Llama 3) fallback

## Tech Stack

| Component | Technology |
|-----------|------------|
| Orchestration | LangGraph + LangChain |
| Primary LLM | Google Gemini 2.0 Flash |
| Fallback LLM | Groq (Llama 3.3 70B) |
| Embeddings | all-MiniLM-L6-v2 |
| PDF Parsing | PyPDF2 + pdfplumber |
| Frontend | Gradio |
| Deployment | HuggingFace Spaces |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/naman-fr/PSI_resume_analyser.git
cd PSI_resume_analyser

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the app
python app.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |
| `GROQ_API_KEY` | Yes | Groq API key (fallback) |
| `HF_TOKEN` | Optional | HuggingFace access token |

## Scoring Methodology

The system uses an industrial-standard ATS scoring formula:

```
Match Score = 0.4 × Keyword Match + 0.25 × Semantic Similarity + 0.25 × Experience + 0.1 × Education
```

## Architecture

```
Resume PDF → Parse Agent → Extract JD Agent → Normalize Skills → Score Match → Improve Resume
```

Each agent is a node in a LangGraph StateGraph, sharing state through a typed dictionary.

## License

MIT License


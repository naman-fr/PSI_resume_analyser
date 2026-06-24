# 💻 Terminal Client & Automation (CLI)

The platform ships with an advanced, robust Command Line Interface (`cli.py`) built using the `click` and `rich` libraries. It is designed for CI/CD pipelines, offline batch processing, and systems administration.

## Key Features

1. **Interactive API Credentials Infiltration**: 
   If `GROQ_API_KEY` or `GOOGLE_API_KEY` are missing, the CLI gracefully intercepts the execution, prompts the developer, tests the keys, and permanently saves them to the `.env` file automatically.
2. **Beautiful Terminal UI**: 
   Leverages the `rich` library to draw Progress Bars, Spinners, Tables, and Markdown directly in the terminal buffer.

## Command Reference

### `health`
Diagnoses the environment.
- Checks Python/pip dependencies.
- Pings the SQLite telemetry database.
- Verifies LangChain provider authentications.
```bash
python cli.py health
```

### `analyze`
Performs a deep-dive cognitive audit of a single resume against a JD.
```bash
python cli.py analyze data/resume.pdf --jd-file data/jd.txt --premium
```

### `batch`
Triggers the multi-threaded ingestion engine to scan entire directories of resumes concurrently.
```bash
python cli.py batch "data/resumes/*.pdf" --jd-file data/jd.txt --export-csv results.csv
```

### `telemetry`
Opens the MLOps diagnostics panel. Views average latency, token counts, and calculates the total API spend across all historical runs.
```bash
python cli.py telemetry
```

### `telemetry --drift`
Executes the Population Stability Index (PSI) drift audit to calculate the Kullback-Leibler (KL) divergence of candidate scores over time, warning administrators if the LLM's scoring calibration is drifting.
```bash
python cli.py telemetry --drift
```

# 💻 Terminal Client & Automation (CLI): Technical Overview

The CLI suite (`cli.py`) serves as the offline MLOps control center, bypassing the web tier for heavy batch processing and administrative functions.

## 1. Core Architecture (`cli.py`)
Built utilizing the `click` library for argument parsing and `rich` for TUI (Terminal User Interface) rendering, the CLI natively interfaces directly with the `core/` and `agents/` Python modules without launching the `uvicorn` ASGI server.

### 1.1 Secrets Infiltration Protocol
To ensure high availability even when deployed in naked environments, the CLI implements an active interception protocol:
```python
def check_api_keys():
    from dotenv import load_dotenv, set_key
    load_dotenv()
    if not os.environ.get("GROQ_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        print("[red]API Keys Missing![/red]")
        key = input("Enter GROQ_API_KEY: ")
        set_key(".env", "GROQ_API_KEY", key)
        os.environ["GROQ_API_KEY"] = key
```

## 2. Command Implementations

### 2.1 MLOps Drift Audit (`python cli.py telemetry --drift`)
This subcommand queries the SQLite `analysis_logs` table using `sqlite3`. It calculates the Kullback-Leibler divergence between the historical score distribution and the current window using `numpy`:
```python
def calculate_psi(expected, actual, buckets=10):
    # Calculates Population Stability Index mathematically
    import numpy as np
    # ... calculates bin frequencies and PSI formula ...
    return np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
```
The CLI then renders a `rich.Table` highlighting the exact statistical drift metric to the administrator.

### 2.2 Multithreaded Batch Ingestion (`python cli.py batch "*.pdf"`)
Uses `glob` to resolve wildcard paths and utilizes Python's `concurrent.futures.ThreadPoolExecutor` to process multiple resumes concurrently through the LangGraph swarm. Results are aggressively flattened into a CSV using `csv.writer`, capturing token usage per file for auditing.

### 2.3 Local Evaluation (`python cli.py analyze`)
Directly invokes `agents.graph.run_analysis()` offline. It captures the entire `ResumeJDState` return dict and pipes the `match_score` and `debate_log` directly to `rich.console.Console` using `Panel` and `Markdown` components for a visually rich local read-out.

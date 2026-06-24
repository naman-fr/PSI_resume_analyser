# 🔬 Low Level Design (LLD): Code Structures & Bindings

This document provides exact technical mappings of the Python structures, LangGraph implementations, and API bindings used in the core system.

## 1. LangGraph State Management (`agents/state.py`)

The platform uses Python's `typing.TypedDict` to enforce type hints across the asynchronous graph execution.

```python
from typing import TypedDict, Optional, List, Dict

class ResumeJDState(TypedDict, total=False):
    # Inputs
    resume_text: str
    jd_text: str
    
    # Parsed Schemas
    resume_parsed: Dict
    jd_extracted: Dict
    
    # Scoring Metrics
    match_score: float
    semantic_score: float
    experience_score: float
    
    # Multi-Agent Swarm Payloads
    debate_log: List[Dict[str, str]]
    swarm_consensus: str
    mcp_tools_used: List[str]
    
    # MLOps Telemetry
    provider_used: str
    error: Optional[str]
```
*Note: `total=False` allows partial dict updates. LangGraph's channel multiplexer merges these updates sequentially during edge traversal.*

## 2. Multi-Agent Swarm Orchestration (`agents/graph.py`)

We build and compile the graph using `langgraph.graph.StateGraph`.

### 2.1 Node Registration & Wiring
```python
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(ResumeJDState)

# Register pure python functions as cognitive nodes
workflow.add_node("parse", parse_resume)
workflow.add_node("extract", extract_jd)
workflow.add_node("normalize", normalize_skills)
workflow.add_node("score", score_match)
workflow.add_node("swarm_debate", run_swarm_debate)

# Define Edge Flow
workflow.add_edge(START, "parse")
workflow.add_edge("parse", "extract")
workflow.add_edge("extract", "normalize")

# Conditional Router Example
def _should_loop_or_continue(state: ResumeJDState) -> str:
    if state.get("error"): return "abort"
    if not state.get("critic_report", {}).get("is_valid"): return "loop"
    return "continue"

workflow.add_conditional_edges(
    "normalize",
    _should_loop_or_continue,
    {"continue": "score", "loop": "parse", "abort": END}
)

workflow.add_edge("score", "swarm_debate")
workflow.add_edge("swarm_debate", END)

# Compile into an executable Runnable
graph = workflow.compile()
```

## 3. Model Context Protocol (`agents/mcp_client.py`)

The MCP client wraps native Python logic so it can be dynamically injected into the LLM context window using LangChain's `bind_tools`.

### 3.1 Tool Binding Implementation
```python
from langchain_core.tools import tool

@tool
def mcp_github_repos_tool(username: str) -> str:
    """Fetches public repository stats for a GitHub user."""
    import httpx
    response = httpx.get(f"https://api.github.com/users/{username}/repos")
    # Parse and return JSON payload...

def get_tiered_tools(role: str) -> list:
    """RBAC implementation for tool access."""
    if role == "tech_lead":
        return [mcp_github_repos_tool]
    return []
```

### 3.2 Executing Tool Calls (`agents/swarm_debate.py`)
During the Tech Lead's turn, we execute the bound LLM and intercept `tool_calls`:
```python
llm_with_tools = llm.bind_tools(get_tiered_tools("tech_lead"))
tl_response = llm_with_tools.invoke(messages)

if hasattr(tl_response, 'tool_calls') and tl_response.tool_calls:
    for tool_call in tl_response.tool_calls:
        tool_func = next(t for t in tech_lead_tools if t.name == tool_call['name'])
        result = tool_func.invoke(tool_call['args'])
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call['id']))
    
    # Re-invoke LLM with the tool's raw HTTP output
    tl_response = llm_with_tools.invoke(messages)
```

## 4. FastAPI Integration (`api.py`)

The compiled LangGraph `Runnable` is invoked asynchronously within FastAPI endpoints, protected by `JWTBearer` authentication dependencies.
```python
@app.post("/api/analyze")
async def analyze_endpoint(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    jd_text: str = Form(...)
):
    # 1. Parse PDF using pdfplumber
    # 2. Invoke LangGraph
    final_state = graph.invoke({"resume_text": text, "jd_text": jd_text})
    
    # 3. Asynchronously log to MLflow
    background_tasks.add_task(log_to_mlflow, final_state)
    
    return final_state
```

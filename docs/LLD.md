# 🔬 Low Level Design (LLD)

## LangGraph State Management (`agents/state.py`)
The platform uses a `TypedDict` to pass state asynchronously through the graph nodes. 
Keys include:
- `resume_parsed` & `jd_extracted`: Extracted schema dicts.
- `debate_log`: A rolling transcript of the Swarm's arguments.
- `mcp_tools_used`: Audit log of all external API endpoints hit by the agents.

## Multi-Agent Swarm Orchestration (`agents/graph.py`)
```python
workflow = StateGraph(ResumeJDState)

# Node Registry
workflow.add_node("parse", parse_resume)
workflow.add_node("extract", extract_jd)
workflow.add_node("normalize", normalize_skills)
workflow.add_node("score", score_match)
workflow.add_node("swarm_debate", run_swarm_debate)

# Edge Wiring with Conditional Routing
workflow.add_edge("parse", "extract")
workflow.add_edge("extract", "normalize")
workflow.add_edge("normalize", "score")
workflow.add_edge("score", "swarm_debate")
workflow.add_edge("swarm_debate", END)
```

## Model Context Protocol (`agents/mcp_client.py`)
We map internal Python functions to Anthropic-compatible tool bindings:
- `@tool` decorator exposes `fetch_github_repo_stats`.
- `get_tiered_tools("tech_lead")` restricts the agent's available functions based on role-based access control (RBAC).

## Teacher-Student Engine (`core/student_model.py`)
- Extracts all `resume_text` and `jd_text` from the `analysis_logs` table.
- Fits a `TfidfVectorizer(max_features=1000)`.
- Trains a `RandomForestRegressor(n_estimators=50)` mapping text arrays to historical `match_score` targets.
- Serves $\mathcal{O}(1)$ inference via the `/api/admin/distill` gateway.

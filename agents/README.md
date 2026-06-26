# 🤖 LangGraph Agent Swarm

This directory contains the core intelligence logic for the **Reasoning Plane**.

## Architecture Overview
Instead of flat LLM chains, we utilize **LangGraph** to build stateful Directed Acyclic Graphs (DAGs) representing complex cognitive workflows.

### Files
*   `graph.py`: The core Resume Evaluator swarm. It orchestrates a debate between a `RecruiterAgent` (looking for tenure/soft skills), a `TechLeadAgent` (looking for architectural depth), and a `JudgeAgent` (resolving conflicts).
*   `interview_graph.py`: The Socratic Cognitive Interviewer. It tracks conversation history in a state vector, dynamically increasing question difficulty as the candidate answers correctly.
*   `improver.py`: An agent dedicated to rewriting poor resume bullets using the STAR (Situation, Task, Action, Result) method.
*   `prompts.py`: The central repository for all System Prompts.

## State Management
All agents communicate via a shared `TypedDict` state. For example, `InterviewState` tracks `messages`, `difficulty_level`, and `bot_detected` flags.

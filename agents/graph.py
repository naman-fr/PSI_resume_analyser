"""
LangGraph workflow definition for the resume-analysis pipeline.

Orchestrates five agent nodes in sequence::

    START ─► parse_resume ─► extract_jd ─► normalize_skills
          ─► score_match ─► improve_resume ─► END

A conditional edge after ``parse_resume`` short-circuits to END if an error
is detected, preventing downstream nodes from running on bad data.
"""

import logging
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from agents.improver import improve_resume
from agents.jd_extractor import extract_jd
from agents.resume_parser import parse_resume
from agents.scorer import score_match
from agents.skill_normalizer import normalize_skills
from agents.state import ResumeJDState

logger = logging.getLogger(__name__)


def _should_continue_after_parse(state: ResumeJDState) -> str:
    """Conditional router: skip remaining nodes if parsing failed."""
    if state.get("error"):
        logger.warning("Error detected after parse_resume — aborting pipeline.")
        return "abort"
    return "continue"


def create_analysis_graph() -> Any:
    """Build and compile the full analysis LangGraph.

    Returns
    -------
    CompiledGraph
        A compiled LangGraph ready to be invoked with an initial state dict.
    """
    workflow = StateGraph(ResumeJDState)

    # ── Register nodes ───────────────────────────────────────────────────
    workflow.add_node("parse_resume", parse_resume)
    workflow.add_node("extract_jd", extract_jd)
    workflow.add_node("normalize_skills", normalize_skills)
    workflow.add_node("score_match", score_match)
    workflow.add_node("improve_resume", improve_resume)

    # ── Wire edges ───────────────────────────────────────────────────────
    workflow.add_edge(START, "parse_resume")

    # Conditional: continue or abort
    workflow.add_conditional_edges(
        "parse_resume",
        _should_continue_after_parse,
        {
            "continue": "extract_jd",
            "abort": END,
        },
    )

    workflow.add_edge("extract_jd", "normalize_skills")
    workflow.add_edge("normalize_skills", "score_match")
    workflow.add_edge("score_match", "improve_resume")
    workflow.add_edge("improve_resume", END)

    graph = workflow.compile()
    logger.info("Analysis graph compiled successfully.")
    return graph


def run_analysis(resume_text: str, jd_text: str) -> Dict[str, Any]:
    """Convenience wrapper: run the full pipeline end-to-end.

    Parameters
    ----------
    resume_text:
        Raw text extracted from the candidate's resume PDF.
    jd_text:
        Raw job-description text provided by the user.

    Returns
    -------
    dict
        The final ``ResumeJDState`` with all scores, analysis, and
        improvement data populated.  If a fatal error occurred, the
        ``error`` key will contain a description.
    """
    try:
        graph = create_analysis_graph()
        initial_state: ResumeJDState = {
            "resume_text": resume_text,
            "jd_text": jd_text,
        }
        final_state: Dict[str, Any] = graph.invoke(initial_state)
        logger.info("Pipeline completed — overall score: %s", final_state.get("overall_score"))
        return final_state

    except Exception as exc:
        logger.exception("Pipeline execution failed.")
        return {
            "resume_text": resume_text,
            "jd_text": jd_text,
            "error": f"Pipeline execution failed: {exc}",
        }

# refactor: improve workflow routing on node error states

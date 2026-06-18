"""
LangGraph workflow definition for the resume-analysis pipeline.

Orchestrates planner, parse, extract, normalizer, critic, score, and improve nodes.
Incorporates self-reflection loop and evaluation benchmarking.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from langgraph.graph import END, START, StateGraph

from agents.improver import improve_resume
from agents.jd_extractor import extract_jd
from agents.resume_parser import parse_resume
from agents.scorer import score_match
from agents.skill_normalizer import normalize_skills
from agents.state import ResumeJDState

logger = logging.getLogger(__name__)


def plan_pipeline(state: ResumeJDState) -> Dict[str, Any]:
    """Orchestrator node: generates an execution plan."""
    resume_text = state.get("resume_text", "")
    jd_text = state.get("jd_text", "")
    
    # Defaults
    plan = {
        "plan_steps": ["parse_resume", "extract_jd", "normalize_skills", "score_match", "improve_resume"],
        "focus_areas": ["general"],
        "targeted_version": "v1.0.0"
    }
    
    try:
        from agents import resume_parser
        from config.prompt_registry import PromptRegistry
        from core.telemetry import TelemetryLogger

        start_time = time.time()
        llm, provider = resume_parser.get_llm()
        system_prompt = PromptRegistry.get_prompt("planner", version="v1.0.0")
        prompt = system_prompt.format(resume_text=resume_text[:2000], jd_text=jd_text[:2000])
        response = llm.invoke(prompt)
        raw_content: str = response.content  # type: ignore[union-attr]
        
        parsed = resume_parser._extract_json(raw_content)
        if isinstance(parsed, dict) and "plan_steps" in parsed:
            plan = parsed
            
        latency = time.time() - start_time
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(raw_content) // 4
        if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
            usage = response.response_metadata["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

        TelemetryLogger.record_event(
            node_name="plan_pipeline",
            provider=provider,
            latency_sec=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success"
        )
    except Exception as exc:
        logger.warning("Planner node failed (%s); using default plan.", exc)
        
    return {
        "planner_plan": plan,
        "loop_count": 0
    }


def critic_validate(state: ResumeJDState) -> Dict[str, Any]:
    """Critic node: validates extraction and normalizer outputs."""
    resume_parsed = state.get("resume_parsed", {})
    jd_extracted = state.get("jd_extracted", {})
    
    # Heuristic validations
    has_skills = len(resume_parsed.get("skills", [])) > 0
    has_experience = len(resume_parsed.get("experience", [])) > 0
    
    critic_report = {
        "is_valid": True,
        "confidence_score": 0.95,
        "feedback_details": ""
    }
    
    # If heuristic checks fail, flag immediately
    if not has_skills:
        critic_report = {
            "is_valid": False,
            "confidence_score": 0.30,
            "feedback_details": "Candidate skills section is empty. Please locate and extract the candidate's skills."
        }
    elif not has_experience:
        critic_report = {
            "is_valid": False,
            "confidence_score": 0.40,
            "feedback_details": "Candidate experience history is empty. Please locate and extract work roles or projects."
        }
    else:
        # Ask LLM Critic
        try:
            from agents import resume_parser
            from config.prompt_registry import PromptRegistry
            from core.telemetry import TelemetryLogger

            start_time = time.time()
            llm, provider = resume_parser.get_llm()
            system_prompt = PromptRegistry.get_prompt("critic", version="v1.0.0")
            prompt = system_prompt.format(
                resume_parsed=json.dumps(resume_parsed, default=str)[:2000],
                jd_extracted=json.dumps(jd_extracted, default=str)[:2000]
            )
            response = llm.invoke(prompt)
            raw_content: str = response.content  # type: ignore[union-attr]
            
            parsed = resume_parser._extract_json(raw_content)
            if isinstance(parsed, dict) and "is_valid" in parsed:
                critic_report = parsed
                
            latency = time.time() - start_time
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(raw_content) // 4
            if hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
                usage = response.response_metadata["token_usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

            TelemetryLogger.record_event(
                node_name="critic_validate",
                provider=provider,
                latency_sec=latency,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                status="success"
            )
        except Exception as exc:
            logger.warning("Critic node failed (%s); relying on heuristic check.", exc)
            
    # Increment loop count if invalid
    current_loops = state.get("loop_count", 0)
    new_loops = current_loops + 1 if not critic_report.get("is_valid", True) else current_loops
    
    return {
        "critic_report": critic_report,
        "loop_count": new_loops
    }


def _should_continue_after_parse(state: ResumeJDState) -> str:
    """Conditional router: skip remaining nodes if parsing failed."""
    if state.get("error"):
        logger.warning("Error detected after parse_resume — aborting pipeline.")
        return "abort"
    return "continue"


def _should_loop_or_continue(state: ResumeJDState) -> str:
    """Conditional router based on critic report and loop count."""
    if state.get("error"):
        return "abort"
        
    critic_report = state.get("critic_report", {})
    is_valid = critic_report.get("is_valid", True)
    loop_count = state.get("loop_count", 0)
    
    if not is_valid and loop_count < 2:
        logger.info("Critic validation failed. Looping back for parse correction. Loop count: %d", loop_count)
        return "loop"
        
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
    workflow.add_node("planner", plan_pipeline)
    workflow.add_node("parse_resume", parse_resume)
    workflow.add_node("extract_jd", extract_jd)
    workflow.add_node("normalize_skills", normalize_skills)
    workflow.add_node("critic", critic_validate)
    workflow.add_node("score_match", score_match)
    workflow.add_node("improve_resume", improve_resume)

    # ── Wire edges ───────────────────────────────────────────────────────
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "parse_resume")

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
    workflow.add_edge("normalize_skills", "critic")

    # Dynamic reflection loop edge
    workflow.add_conditional_edges(
        "critic",
        _should_loop_or_continue,
        {
            "loop": "parse_resume",
            "continue": "score_match",
            "abort": END,
        }
    )

    workflow.add_edge("score_match", "improve_resume")
    workflow.add_edge("improve_resume", END)

    graph = workflow.compile()
    logger.info("Analysis graph compiled successfully.")
    return graph


def run_analysis(
    resume_text: str,
    jd_text: str,
    pdf_path: Optional[str] = None,
    premium_mode: bool = False
) -> Dict[str, Any]:
    """Convenience wrapper: run the full pipeline end-to-end with validation."""
    try:
        from core.evaluator import SystemEvaluator
        from core.guardrails import detect_invisible_text, validate_links_and_trust
        from core.data_loop import log_finetuning_record
        
        start_eval_time = time.time()
        graph = create_analysis_graph()
        initial_state: ResumeJDState = {
            "resume_text": resume_text,
            "jd_text": jd_text,
            "premium_mode": premium_mode,
        }
        
        # Invoke Graph
        final_state: Dict[str, Any] = graph.invoke(initial_state)
        
        # Ensure premium mode flag is set on state
        final_state["premium_mode"] = premium_mode
        
        # ── 1. Premium Paid Tier Scans ──────────────────────────────────────
        if premium_mode:
            # A. Invisible Text Scan
            if pdf_path:
                flagged, words, penalty = detect_invisible_text(pdf_path)
                final_state["invisible_text_flagged"] = flagged
                final_state["invisible_text_details"] = {"detected_words": words, "penalty": penalty}
                
                if flagged:
                    # Apply penalty to final match score
                    current_match = final_state.get("match_score", 100.0)
                    final_state["match_score"] = max(0.0, current_match + penalty)
                    
                    # Add red flag
                    rf_list = final_state.setdefault("red_flags", [])
                    rf_list.append({
                        "flag": "Invisible Background Text (ATS Gaming)",
                        "penalty": penalty,
                        "evidence": f"Detected white/near-white hidden text keywords: {', '.join(words)}"
                    })
                    
                    # Add to gaps
                    gaps_list = final_state.setdefault("gaps", [])
                    gaps_list.append(f"Red Flag: Invisible Background Text ({', '.join(words)})")
            else:
                final_state["invisible_text_flagged"] = False
                final_state["invisible_text_details"] = {"detected_words": [], "penalty": 0.0}

            # B. Link Verification & Trust Scorer
            trust_results = validate_links_and_trust(resume_text)
            final_state["links_verification"] = trust_results
        else:
            final_state["invisible_text_flagged"] = False
            final_state["invisible_text_details"] = {"detected_words": [], "penalty": 0.0}
            final_state["links_verification"] = {"trust_score": 50.0, "logs": ["Premium Mode Disabled"], "checked_urls": {}}

        # ── 2. Unmask Redacted PII before returning to UI ───────────────────
        redacting_map = final_state.get("redacting_map", {})
        if redacting_map and "resume_parsed" in final_state:
            resume_parsed = final_state["resume_parsed"]
            for key in ["name", "email", "phone", "linkedin"]:
                val = resume_parsed.get(key)
                if val and val in redacting_map:
                    resume_parsed[key] = redacting_map[val]
                    
        # ── 3. Run MLOps Evaluator Benchmarking ─────────────────────────────
        final_state["evaluation_logs"] = SystemEvaluator.run_benchmark(start_eval_time, final_state)
        
        # ── 4. Log continuous fine-tuning data if enabled ───────────────────
        log_finetuning_record(resume_text, jd_text, final_state)
        
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

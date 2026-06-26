"""
Cognitive Interview Orchestrator
LangGraph supervisor handling the Socratic Interview logic.
"""
import logging
import json
from typing import Any, Dict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage

from agents.interview_state import InterviewState

logger = logging.getLogger(__name__)

def build_interview_planner(state: InterviewState) -> Dict[str, Any]:
    """Phase 3: Dynamic Interview Planner. Builds the Interview Tree."""
    logger.info("Building Dynamic Interview Tree...")
    
    resume_text = state.get("resume_text", "")
    jd_text = state.get("jd_text", "")
    focus = state.get("interview_focus", "balanced")
    
    if not resume_text or not jd_text:
        return {"error": "Missing resume or JD context."}
        
    focus_instruction = ""
    if focus == "resume":
        focus_instruction = "FOCUS STRICTLY ON THE CANDIDATE's RESUME EXPERIENCE. Ignore the JD. Ask about their past projects, architectures, and decisions."
    elif focus == "jd":
        focus_instruction = "FOCUS STRICTLY ON THE JOB DESCRIPTION. Ignore their past experience. Grill them on the specific technical requirements listed in the JD."
    else:
        focus_instruction = "BALANCED APPROACH. Connect their past resume experience to the specific requirements of the JD."

    try:
        from agents import resume_parser
        llm, _ = resume_parser.get_llm()
        
        prompt = f"""You are the Principal Interview Architect.
Based on the candidate's resume and the job description, build a 5-step conceptual 'Interview Tree'.
INSTRUCTION: {focus_instruction}
Also, formulate the VERY FIRST question to kick off the interview. Start with a basic question asking them to explain their past experience or a specific project on their resume. Do not start with complex questions. We will slowly increase difficulty based on their answers.

Return ONLY a valid JSON object matching this schema exactly:
{{
  "tree": ["Concept 1", "Concept 2", "Concept 3", "Concept 4", "Concept 5"],
  "first_question": "Your basic introductory technical question here..."
}}

Resume: {resume_text[:2000]}
JD: {jd_text[:2000]}
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw_content = response.content
        
        tree = ["Core Architecture", "Scalability", "System Design", "Failure Recovery", "Behavioral"]
        first_q = "Let's dive right in. Could you start by explaining a recent project from your resume and what your specific role was?"
        
        try:
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            data = json.loads(raw_content)
            if "tree" in data and isinstance(data["tree"], list):
                tree = data["tree"]
            if "first_question" in data:
                first_q = data["first_question"]
        except Exception as parse_e:
            logger.warning(f"Failed to parse interview tree: {parse_e}. Using default.")
            
        return {
            "interview_tree": tree,
            "current_topic": tree[0] if tree else "Core Architecture",
            "difficulty_level": 1,  # Start at Easy (1/10)
            "messages": [{"role": "ai", "content": first_q}]
        }
        
    except Exception as exc:
        logger.exception("Planner failed.")
        return {"error": str(exc)}


def generate_reasoning_paths(state: InterviewState) -> Dict[str, Any]:
    """Single-shot path generation (optimized for free-tier limits)."""
    logger.info("Generating 1 Reasoning Path (Free-Tier Optimized)...")
    messages = state.get("messages", [])
    if len(messages) < 2 or messages[-1].get("role") != "human":
        return {}
        
    human_answer = messages[-1].get("content", "")
    ai_question = messages[-2].get("content", "")
    difficulty = state.get("difficulty_level", 1)
    
    try:
        from agents import resume_parser
        from core.memory_agent import compress_history
        llm, _ = resume_parser.get_llm()
        
        compressed_context = compress_history(messages)
        
        prompt = f"""You are evaluating the candidate.
Context (Compressed Memory):
{compressed_context}

Question Asked (Difficulty {difficulty}/10): {ai_question}
Candidate's Answer: {human_answer}

Generate an evaluation and the NEXT question.
Output ONLY JSON:
{{
  "critique": "Internal reasoning...",
  "proposed_score": 5,
  "proposed_next_question": "..."
}}
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw = response.content
        
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            path_data = json.loads(raw)
            path_data["path_id"] = "path_0"
            path_data["critic_score"] = 10 # Default bypass score
            return {"reasoning_paths": [path_data]}
        except Exception as parse_e:
            logger.error(f"Failed to parse paths JSON: {parse_e}")
                
        return {"reasoning_paths": []}
        
    except Exception as e:
        logger.error(f"Failed to generate paths: {e}")
        return {"reasoning_paths": []}

def critique_reasoning_paths(state: InterviewState) -> Dict[str, Any]:
    """Bypassed for free-tier to save API rate limits."""
    return {}

def select_best_path_and_respond(state: InterviewState) -> Dict[str, Any]:
    """Test-Time Scaling: Verifier selects the best path and appends the message."""
    logger.info("Verifier Agent selecting best path...")
    paths = state.get("reasoning_paths", [])
    messages = state.get("messages", [])
    difficulty = state.get("difficulty_level", 1)
    
    ai_msg_count = len([m for m in messages if m.get("role") == "ai"])
    if ai_msg_count >= 10:
        return {"is_complete": True, "messages": messages + [{"role": "ai", "content": "Thank you for your time. The interview is now complete. Our hiring committee will review your results."}]}
        
    if not paths:
        return {"messages": messages + [{"role": "ai", "content": "I encountered an issue synthesizing my thoughts. Could you expand on that?"}]}
        
    best_path = max(paths, key=lambda x: x.get("critic_score", 0))
    proposed_score = best_path.get("proposed_score", 5)
    next_q = best_path.get("proposed_next_question", "Could you elaborate?")
    
    final_q = f"[GRADE: {proposed_score}/10] {next_q}"
    
    if proposed_score >= 8:
        difficulty = min(10, difficulty + 1)
    elif proposed_score <= 4:
        difficulty = max(1, difficulty - 1)
        
    evals = state.get("evaluations", [])
    evals.append({
        "question": messages[-2].get("content", "") if len(messages)>=2 else "",
        "answer": messages[-1].get("content", "") if len(messages)>=1 else "",
        "scores": {"correctness": proposed_score, "depth": proposed_score}
    })
    
    return {
        "messages": messages + [{"role": "ai", "content": final_q}],
        "difficulty_level": difficulty,
        "evaluations": evals
    }

def hiring_committee(state: InterviewState) -> Dict[str, Any]:
    """Phase 6: Hiring Committee Debate. 5 Agents review the transcript."""
    logger.info("Spawning Hiring Committee Swarm...")
    try:
        from agents import resume_parser
        llm, _ = resume_parser.get_llm()
        
        transcript = "\n".join([f"{m['role']}: {m['content']}" for m in state.get("messages", [])])
        
        prompt = f"""You are a multi-agent Hiring Committee consisting of an HR Manager, a Tech Lead, and a Behavioral Expert.
Review the following interview transcript and debate the candidate's performance.

Transcript:
{transcript}

Output a short JSON debate transcript:
{{
  "debate": [
    {{"agent": "HR Manager", "opinion": "..."}},
    {{"agent": "Tech Lead", "opinion": "..."}},
    {{"agent": "Behavioral Expert", "opinion": "..."}}
  ]
}}
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw = response.content
        
        debate = []
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            debate_data = json.loads(raw)
            debate = debate_data.get("debate", [])
        except Exception:
            debate = [{"agent": "System", "opinion": "Could not parse debate json."}]
            
        # We store the debate log in final_report for now
        return {"final_report": {"debate": debate}}
    except Exception as e:
        logger.error(f"Hiring committee failed: {e}")
        return {"final_report": {"debate": []}}

def judge_agent(state: InterviewState) -> Dict[str, Any]:
    """Phase 6: Judge Agent makes final hiring decision."""
    logger.info("Judge Agent evaluating final score...")
    try:
        from agents import resume_parser
        from agents.constitution import get_ai_constitution
        llm, _ = resume_parser.get_llm()
        
        debate = state.get("final_report", {}).get("debate", [])
        debate_str = json.dumps(debate)
        constitution = get_ai_constitution()
        
        prompt = f"""You are the Final Judge Agent.
{constitution}

Based on the committee debate:
{debate_str}

Output a final JSON report:
{{
  "hiring_probability": 0-100,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "recommendation": "HIRE" or "NO HIRE" or "STRONG HIRE"
}}
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw = response.content
        
        report = {"hiring_probability": 50, "strengths": [], "weaknesses": [], "recommendation": "UNKNOWN"}
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            parsed = json.loads(raw)
            report = parsed
        except Exception:
            pass
            
        final_report = state.get("final_report", {})
        final_report.update(report)
        
        # Feature 5: Knowledge Distillation
        try:
            from core.learning import extract_knowledge_for_distillation
            extract_knowledge_for_distillation(state)
        except Exception as distill_err:
            logger.error(f"Distillation error: {distill_err}")
            
        return {"final_report": final_report}
    except Exception as e:
        logger.error(f"Judge agent failed: {e}")
        return {}

def create_interview_graph():
    """Build and compile the interview supervisor."""
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("planner", build_interview_planner)
    workflow.add_node("generate_paths", generate_reasoning_paths)
    workflow.add_node("critique_paths", critique_reasoning_paths)
    workflow.add_node("select_path", select_best_path_and_respond)
    workflow.add_node("committee", hiring_committee)
    workflow.add_node("judge", judge_agent)
    
    # Conditional routing logic for when to run what
    def route_start(state: InterviewState):
        if not state.get("interview_tree"):
            return "planner"
        return "generate_paths"
        
    def check_complete(state: InterviewState):
        if state.get("is_complete"):
            return "committee"
        # Return END to pause execution and wait for human reply in the next HTTP request
        return END
        
    workflow.add_conditional_edges(START, route_start)
    workflow.add_edge("planner", END) # Planner just initializes the state, we return to the user.
    
    workflow.add_edge("generate_paths", "critique_paths")
    workflow.add_edge("critique_paths", "select_path")
    workflow.add_conditional_edges("select_path", check_complete)
    workflow.add_edge("committee", "judge")
    workflow.add_edge("judge", END)
    
    return workflow.compile()

interview_graph = create_interview_graph()

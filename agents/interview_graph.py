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
Also, formulate the VERY FIRST deeply technical or analytical question to kick off the interview based on their most prominent experience related to the JD. Do not say "Hello" or "Walk me through your resume." Ask a direct, complex question immediately.

Return ONLY a valid JSON object matching this schema exactly:
{{
  "tree": ["Concept 1", "Concept 2", "Concept 3", "Concept 4", "Concept 5"],
  "first_question": "Your highly specific, direct technical question here..."
}}

Resume: {resume_text[:2000]}
JD: {jd_text[:2000]}
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw_content = response.content
        
        tree = ["Core Architecture", "Scalability", "System Design", "Failure Recovery", "Behavioral"]
        first_q = "Let's dive right in. Could you explain the most complex technical architectural decision you made in your recent role, and why?"
        
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


def evaluate_answer(state: InterviewState) -> Dict[str, Any]:
    """Phase 4 & Interview Intelligence: Evaluates the last human answer."""
    messages = state.get("messages", [])
    if len(messages) < 2 or messages[-1].get("role") != "human":
        return {} # Nothing to evaluate yet
        
    human_answer = messages[-1].get("content", "")
    ai_question = messages[-2].get("content", "")
    difficulty = state.get("difficulty_level", 5)
    
    try:
        from agents import resume_parser
        llm, _ = resume_parser.get_llm()
        
        prompt = f"""You are the Technical Evaluator.
Question Asked (Difficulty {difficulty}/10): {ai_question}
Candidate's Answer: {human_answer}

Evaluate the candidate's answer. Output a JSON with:
- "correctness": 0-10
- "depth": 0-10
- "communication": 0-10
- "reasoning": 0-10
- "next_difficulty_delta": -1, 0, or 1 (decrease, maintain, or increase difficulty based on how well they answered)

Return ONLY valid JSON.
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw = response.content
        
        evaluation = {"correctness": 5, "depth": 5, "communication": 5, "reasoning": 5, "next_difficulty_delta": 0}
        try:
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            evaluation = json.loads(raw)
        except Exception:
            pass
            
        new_difficulty = max(1, min(10, difficulty + evaluation.get("next_difficulty_delta", 0)))
        
        evals = state.get("evaluations", [])
        evals.append({
            "question": ai_question,
            "answer": human_answer,
            "scores": evaluation
        })
        
        return {
            "evaluations": evals,
            "difficulty_level": new_difficulty
        }
        
    except Exception as e:
        logger.warning(f"Evaluation failed: {e}")
        return {}


def generate_next_question(state: InterviewState) -> Dict[str, Any]:
    """GenAI Research Feature: Socratic Interview Agent."""
    messages = state.get("messages", [])
    difficulty = state.get("difficulty_level", 5)
    current_topic = state.get("current_topic", "General")
    
    # Check if we should end the interview (e.g., after 10 questions)
    ai_msg_count = len([m for m in messages if m.get("role") == "ai"])
    if ai_msg_count >= 10:
        return {"is_complete": True, "messages": messages + [{"role": "ai", "content": "Thank you for your time. The interview is now complete. Our hiring committee will review your results."}]}
        
    try:
        from agents import resume_parser
        llm, _ = resume_parser.get_llm()
        
        # Build context
        chat_history = ""
        for m in messages[-4:]:  # Last 2 exchanges
            chat_history += f"\n{m['role'].upper()}: {m['content']}"
            
        prompt = f"""You are a Socratic Technical Interviewer (like a real Google interviewer).
Current Topic: {current_topic}
Current Target Difficulty (1-10): {difficulty}

Recent Conversation:
{chat_history}

First, silently evaluate their answer for correctness, depth, and reasoning.
Then, generate the NEXT response to the candidate.
CRITICAL REQUIREMENT: Your response MUST begin with an explicit, harsh, Persona 5 style grade wrapped in brackets like this: [GRADE: X/10] (where X is 1-10). Provide 1 short sentence justifying the grade.
Then, ask ONE deep, focused follow-up question based directly on what they just said. 
DO NOT ask multiple questions at once.
If they answered well, dig deeper into their explanation (e.g., "Why did you choose X over Y?" or "How does that scale?").
If their answer was poor or shallow, challenge their assumptions aggressively.
Keep it concise, conversational, and highly technical.
Example Output:
[GRADE: 4/10] You completely ignored race conditions in your explanation. How exactly would your proposed database schema handle concurrent write transactions at scale?
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        new_q = response.content
        
        new_messages = messages + [{"role": "ai", "content": new_q}]
        return {"messages": new_messages}
        
    except Exception as e:
        logger.error(f"Generate question failed: {e}")
        return {"messages": messages + [{"role": "ai", "content": "I encountered a technical issue. Could you expand more on your last point?"}]}

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
        llm, _ = resume_parser.get_llm()
        
        debate = state.get("final_report", {}).get("debate", [])
        debate_str = json.dumps(debate)
        
        prompt = f"""You are the Final Judge Agent.
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
        return {"final_report": final_report}
    except Exception as e:
        logger.error(f"Judge agent failed: {e}")
        return {}

def create_interview_graph():
    """Build and compile the interview supervisor."""
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("planner", build_interview_planner)
    workflow.add_node("evaluator", evaluate_answer)
    workflow.add_node("socratic", generate_next_question)
    workflow.add_node("committee", hiring_committee)
    workflow.add_node("judge", judge_agent)
    
    # Conditional routing logic for when to run what
    def route_start(state: InterviewState):
        if not state.get("interview_tree"):
            return "planner"
        return "evaluator"
        
    def check_complete(state: InterviewState):
        if state.get("is_complete"):
            return "committee"
        # Return END to pause execution and wait for human reply in the next HTTP request
        return END
        
    workflow.add_conditional_edges(START, route_start)
    workflow.add_edge("planner", END) # Planner just initializes the state, we return to the user.
    
    workflow.add_edge("evaluator", "socratic")
    workflow.add_conditional_edges("socratic", check_complete)
    workflow.add_edge("committee", "judge")
    workflow.add_edge("judge", END)
    
    return workflow.compile()

interview_graph = create_interview_graph()

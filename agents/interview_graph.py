"""
Cognitive Interview Orchestrator
LangGraph supervisor handling the Socratic Interview logic.
"""
import logging
import json
from typing import Any, Dict
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, HumanMessage

from agents.interview_state import InterviewState

logger = logging.getLogger(__name__)

def build_interview_planner(state: InterviewState) -> Dict[str, Any]:
    """Phase 3: Dynamic Interview Planner. Builds the Interview Tree."""
    logger.info("Building Dynamic Interview Tree...")
    
    resume_text = state.get("resume_text", "")
    jd_text = state.get("jd_text", "")
    
    if not resume_text or not jd_text:
        return {"error": "Missing resume or JD context."}
        
    try:
        from agents import resume_parser
        llm, _ = resume_parser.get_llm()
        
        prompt = f"""You are the Principal Interview Architect.
Based on the candidate's resume and the job description, build a 5-step conceptual 'Interview Tree'.
Return ONLY a valid JSON list of strings, representing the concepts to cover sequentially.
Example: ["Authentication", "JWT scaling", "Redis implementation", "Docker", "System Architecture"]

Resume: {resume_text[:2000]}
JD: {jd_text[:2000]}
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        raw_content = response.content
        
        tree = ["Introduction", "Core Experience", "Technical Deep Dive", "System Design", "Behavioral (STAR)"]
        try:
            if "```json" in raw_content:
                extracted = raw_content.split("```json")[1].split("```")[0].strip()
                tree = json.loads(extracted)
            elif "[" in raw_content:
                extracted = raw_content[raw_content.find("["):raw_content.rfind("]")+1]
                tree = json.loads(extracted)
        except Exception as parse_e:
            logger.warning(f"Failed to parse interview tree: {parse_e}. Using default.")
            
        return {
            "interview_tree": tree,
            "current_topic": tree[0] if tree else "Introduction",
            "difficulty_level": 3,  # Start at Medium-Easy
            "messages": [{"role": "ai", "content": f"Hello! I am your AI Interviewer. To start, let's talk about your background. I see your resume. Can you briefly walk me through {tree[0] if tree else 'your experience'}?"}]
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
    tree = state.get("interview_tree", [])
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

Generate the NEXT question to ask the candidate. 
DO NOT ask multiple questions at once. Ask ONE deep, focused follow-up question. 
If they answered well, dig deeper into their explanation (e.g., "Why did you choose X over Y?" or "How does that scale?").
Keep it concise and conversational.
"""
        response = llm.invoke([SystemMessage(content=prompt)])
        new_q = response.content
        
        new_messages = messages + [{"role": "ai", "content": new_q}]
        return {"messages": new_messages}
        
    except Exception as e:
        logger.error(f"Generate question failed: {e}")
        return {"messages": messages + [{"role": "ai", "content": "I encountered a technical issue. Could you expand more on your last point?"}]}

def create_interview_graph():
    """Build and compile the interview supervisor."""
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("planner", build_interview_planner)
    workflow.add_node("evaluator", evaluate_answer)
    workflow.add_node("socratic", generate_next_question)
    
    # Conditional routing logic for when to run what
    def route_start(state: InterviewState):
        if not state.get("interview_tree"):
            return "planner"
        return "evaluator"
        
    def check_complete(state: InterviewState):
        if state.get("is_complete"):
            return END
        return "socratic"
        
    workflow.add_conditional_edges(START, route_start)
    workflow.add_edge("planner", END) # Planner just initializes the state, we return to the user.
    
    workflow.add_edge("evaluator", "socratic")
    workflow.add_conditional_edges("socratic", check_complete)
    
    return workflow.compile()

interview_graph = create_interview_graph()

"""
Multi-Agent Swarm Debate Node.
Simulates a debate between a Recruiter, a Tech Lead, and a Judge.
Agents utilize the MCP Tool Mesh to fetch real external context if needed.
"""
import logging
import json
import time
from typing import Dict, Any
from langchain_core.messages import SystemMessage
from agents.state import ResumeJDState
from core.telemetry import TelemetryLogger

logger = logging.getLogger(__name__)

def run_swarm_debate(state: ResumeJDState) -> Dict[str, Any]:
    """Execute the multi-agent debate and reach consensus."""
    logger.info("Initiating Swarm Debate: Recruiter vs Tech Lead")
    
    start_time = time.time()
    
    resume_parsed = state.get("resume_parsed", {})
    jd_extracted = state.get("jd_extracted", {})
    current_score = state.get("match_score", 50.0)
    
    if not resume_parsed or not jd_extracted:
        return {}
        
    try:
        from agents import resume_parser
        llm, provider = resume_parser.get_llm()
        
        try:
            from agents.mcp_client import get_tiered_tools
            tech_lead_tools = get_tiered_tools("tech_lead")
            llm_with_tools = llm.bind_tools(tech_lead_tools)
        except Exception as e:
            logger.warning(f"Could not bind MCP tools: {e}")
            llm_with_tools = llm
            tech_lead_tools = []
        
        candidate_summary = json.dumps(resume_parsed, indent=2)
        jd_summary = json.dumps(jd_extracted, indent=2)
        
        # 1. Recruiter Agent
        recruiter_prompt = f"""You are a Senior Technical Recruiter.
Evaluate this candidate based on cultural fit, tenure, and red flags. The heuristic system scored them a {current_score}/100.
Job: {jd_summary[:1000]}
Candidate: {candidate_summary[:1000]}
Output a short, punchy paragraph outlining your stance."""
        
        recruiter_response = llm.invoke([SystemMessage(content=recruiter_prompt)])
        recruiter_stance = recruiter_response.content if hasattr(recruiter_response, 'content') else str(recruiter_response)
        
        # 2. Tech Lead Agent Turn
        tl_prompt = f"""You are a strict Principal Staff Engineer.
The recruiter says: "{recruiter_stance}"
Evaluate this candidate purely on technical depth and architecture skills.
Candidate: {candidate_summary[:1000]}
If the candidate has a GitHub username, use your tools to analyze their repositories!
Output a short paragraph outlining your stance, considering any external repo data you fetched."""
        
        messages = [SystemMessage(content=tl_prompt)]
        tl_response = llm_with_tools.invoke(messages)
        
        # Execute tools if requested by Tech Lead
        if hasattr(tl_response, 'tool_calls') and tl_response.tool_calls:
            from langchain_core.messages import ToolMessage
            messages.append(tl_response)
            for tool_call in tl_response.tool_calls:
                # Find the actual tool by name
                tool_func = next((t for t in tech_lead_tools if t.name == tool_call['name']), None)
                if tool_func:
                    try:
                        tool_result = tool_func.invoke(tool_call['args'])
                        messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call['id']))
                    except Exception as e:
                        messages.append(ToolMessage(content=f"Error: {e}", tool_call_id=tool_call['id']))
            # Get final stance after seeing tool outputs
            tl_response = llm_with_tools.invoke(messages)
            
        tl_stance = tl_response.content if hasattr(tl_response, 'content') else str(tl_response)
        
        # 3. Judge Agent
        judge_prompt = f"""You are the VP of Engineering (The Judge).
Heuristic System Score: {current_score}
Recruiter says: {recruiter_stance}
Tech Lead says: {tl_stance}
Synthesize their arguments and decide on the final 'swarm_consensus' text. Provide a 2-3 sentence final verdict.
"""
        judge_response = llm.invoke([SystemMessage(content=judge_prompt)])
        consensus = judge_response.content.strip() if hasattr(judge_response, 'content') else str(judge_response)
            
        debate_log = [
            {"agent": "Recruiter", "stance": recruiter_stance},
            {"agent": "Tech Lead", "stance": tl_stance},
            {"agent": "Judge", "stance": consensus}
        ]
        
        TelemetryLogger.record_event(
            node_name="swarm_debate",
            provider=provider,
            latency_sec=time.time() - start_time,
            prompt_tokens=0,
            completion_tokens=0,
            status="success"
        )
        
        return {
            "debate_log": debate_log,
            "swarm_consensus": consensus
        }
        
    except Exception as exc:
        logger.exception("Swarm Debate failed.")
        return {
            "debate_log": [{"agent": "System", "stance": f"Swarm offline: {exc}"}],
            "swarm_consensus": "Swarm debate could not be completed."
        }

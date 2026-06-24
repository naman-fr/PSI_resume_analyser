"""
Model Context Protocol (MCP) Client Layer
This module acts as the mesh router to interface with our separate MCP servers.
It allows the LangGraph agents to request tools dynamically from the mesh.
"""
import sys
import os
import logging
from typing import List, Dict, Any
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Note: In a production environment with separate instances, these would connect over SSE or stdio to remote servers.
# For this deployment, we dynamically import the tools from the local FastMCP servers to construct our tool mesh.
try:
    from mcp_servers.mcp_github import fetch_github_profile, analyze_github_repos
    from mcp_servers.mcp_calendar import simulate_interview_scheduling
except ImportError as e:
    logger.warning(f"Could not load local MCP servers. Ensure mcp_servers package is accessible: {e}")
    
@tool
def mcp_github_profile_tool(username: str) -> str:
    """Use this tool to fetch a candidate's GitHub profile data from the MCP mesh."""
    # Wrapping async fastmcp tool in sync execution for LangChain tool calling compatibility
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(fetch_github_profile(username))

@tool
def mcp_github_repos_tool(username: str) -> str:
    """Use this tool to fetch and analyze a candidate's top GitHub repositories from the MCP mesh."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(analyze_github_repos(username))

@tool
def mcp_calendar_scheduler_tool(candidate_email: str, interviewer_role: str, date_preference: str) -> str:
    """Use this tool to schedule an interview securely through the Calendar MCP server."""
    # FastMCP synchronous tool
    return simulate_interview_scheduling(candidate_email, interviewer_role, date_preference)

def get_mcp_tool_mesh() -> List[Any]:
    """Returns the full suite of available MCP tools for the LangGraph agents."""
    return [
        mcp_github_profile_tool,
        mcp_github_repos_tool,
        mcp_calendar_scheduler_tool
    ]

def get_tiered_tools(agent_role: str) -> List[Any]:
    """
    Implements Enterprise MCP Permission Tiers.
    Restricts access to tools based on the invoking agent.
    """
    all_tools = get_mcp_tool_mesh()
    
    if agent_role == "recruiter":
        # Recruiter gets scheduling and basic profile tools
        return [mcp_github_profile_tool, mcp_calendar_scheduler_tool]
    elif agent_role == "tech_lead":
        # Tech lead gets deep repository inspection
        return [mcp_github_repos_tool]
    elif agent_role == "admin":
        return all_tools
    else:
        # Default read-only safe tools
        return [mcp_github_profile_tool]

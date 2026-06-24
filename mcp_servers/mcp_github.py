from mcp.server.fastmcp import FastMCP
import httpx
import logging

logger = logging.getLogger(__name__)

# Create an MCP server
mcp = FastMCP("github_server")

@mcp.tool()
async def fetch_github_profile(username: str) -> str:
    """Fetch basic profile data for a given GitHub username."""
    url = f"https://api.github.com/users/{username}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": "MCP-Client-PSI"})
            if response.status_code == 404:
                return f"User {username} not found."
            response.raise_for_status()
            data = response.json()
            return f"User: {data.get('login')} | Repos: {data.get('public_repos')} | Followers: {data.get('followers')} | Bio: {data.get('bio')}"
    except Exception as e:
        logger.error(f"GitHub fetch failed: {e}")
        return f"Could not fetch profile for {username}. Error: {str(e)}"

@mcp.tool()
async def analyze_github_repos(username: str) -> str:
    """Fetch top public repositories for a given GitHub username to estimate technical skill."""
    url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=5"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={"User-Agent": "MCP-Client-PSI"})
            if response.status_code == 404:
                return f"User {username} not found."
            response.raise_for_status()
            repos = response.json()
            if not repos:
                return f"No public repositories found for {username}."
                
            report = f"Top Repositories for {username}:\n"
            for repo in repos:
                report += f"- {repo.get('name')}: {repo.get('language')} | Stars: {repo.get('stargazers_count')} | Desc: {repo.get('description')}\n"
            return report
    except Exception as e:
        return f"Could not fetch repos for {username}. Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()

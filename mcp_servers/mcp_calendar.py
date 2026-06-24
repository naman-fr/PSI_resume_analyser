from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("calendar_server")

@mcp.tool()
def simulate_interview_scheduling(candidate_email: str, interviewer_role: str, date_preference: str) -> str:
    """
    Mock tool to schedule an interview and send calendar invites.
    Use this to simulate booking a meeting between the candidate and a hiring manager/tech lead.
    """
    return json.dumps({
        "status": "Scheduled",
        "candidate": candidate_email,
        "interviewer_role": interviewer_role,
        "time_slot_selected": date_preference,
        "calendar_link": "https://calendar.google.com/mock_event_123",
        "message": f"Calendar invite sent successfully to {candidate_email} for a {interviewer_role} interview."
    })

if __name__ == "__main__":
    mcp.run()

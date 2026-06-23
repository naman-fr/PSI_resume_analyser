"""
Secure Sandboxed MCP Client Connector.
Implements permission-scoped, rate-limited, audited, and revocable tool execution
to guard against remote code execution and prompt injection vectors.
"""

import time
import logging
import hashlib
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class MCPSandbox:
    """
    Sandboxed MCP Client wrapper providing safe execution interfaces for external tools.
    """

    # Allowed tools registry
    ALLOWLIST_TOOLS = {
        "github/list_repos",
        "github/read_file",
        "drive/list_files",
        "drive/download_file",
        "ats/update_candidate_status",
        "ats/add_screening_note"
    }

    # Tool execution rate limiter settings
    RATE_LIMIT_MAX = 10 # calls per minute
    
    def __init__(self, tenant_id: str = "default_enterprise"):
        self.tenant_id = tenant_id
        self.calls_timestamps: List[float] = []
        self.audit_log: List[Dict[str, Any]] = []
        self.revoked_tools: set[str] = set()

    def revoke_tool(self, tool_name: str):
        """Allows administrators to revoke permissions for specific tools dynamically."""
        self.revoked_tools.add(tool_name)
        logger.warning(f"MCP Permission revoked for tool '{tool_name}' under tenant '{self.tenant_id}'.")

    def restore_tool(self, tool_name: str):
        """Restores permissions for a previously revoked tool."""
        if tool_name in self.revoked_tools:
            self.revoked_tools.remove(tool_name)
            logger.info(f"MCP Permission restored for tool '{tool_name}' under tenant '{self.tenant_id}'.")

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """
        Runs the requested tool within the sandbox audit rules.
        """
        audit_entry = {
            "timestamp": time.time(),
            "tool_name": tool_name,
            "tenant_id": self.tenant_id,
            "status": "blocked",
            "reason": ""
        }
        self.audit_log.append(audit_entry)

        # 1. Allowlist Enforcement
        if tool_name not in self.ALLOWLIST_TOOLS:
            audit_entry["reason"] = "Tool is not in the system-wide security allowlist."
            logger.warning(f"Security Alert: Blocked unauthorized tool request '{tool_name}'")
            return {"success": False, "error": audit_entry["reason"]}

        # 2. Revocation Verification
        if tool_name in self.revoked_tools:
            audit_entry["reason"] = "Permission for this tool was revoked by administrator."
            return {"success": False, "error": audit_entry["reason"]}

        # 3. Rate Limiting Check
        current_time = time.time()
        # Clean older stamps
        self.calls_timestamps = [t for t in self.calls_timestamps if current_time - t < 60.0]
        if len(self.calls_timestamps) >= self.RATE_LIMIT_MAX:
            audit_entry["reason"] = "Rate limit threshold breached (Max 10 calls/min)."
            return {"success": False, "error": audit_entry["reason"]}

        # 4. Cryptographic Signature Validation
        # Verify call integrity matches expected tenant signing pattern
        expected_sig = hashlib.sha256(f"{tool_name}:{self.tenant_id}".encode()).hexdigest()[:16]
        if signature != expected_sig:
            audit_entry["reason"] = "Invalid cryptographic access signature. Rejecting connection."
            logger.warning(f"Signature mismatch for {tool_name}. Got {signature}, expected {expected_sig}")
            return {"success": False, "error": audit_entry["reason"]}

        # 5. Argument Sanitization / Safety Scan
        # Block arguments containing shell redirection or prompt injection triggers
        arg_str = str(arguments).lower()
        injection_triggers = ["; rm ", "sudo ", "curl ", "wget ", "chmod ", "<script>", "ignore previous instructions"]
        for trigger in injection_triggers:
            if trigger in arg_str:
                audit_entry["reason"] = f"Adversarial payload detected in tool arguments: '{trigger}'"
                logger.critical(f"Exploit Attempt Blocked on tool {tool_name} arguments!")
                return {"success": False, "error": audit_entry["reason"]}

        # 6. Execute (Simulated sandbox connection)
        self.calls_timestamps.append(current_time)
        audit_entry["status"] = "success"
        
        # Return mock successful output
        return {
            "success": True,
            "data": {
                "message": f"Successfully completed {tool_name} execution inside sandbox.",
                "response_payload": {"records_processed": 1, "mcp_channel": "secure"}
            }
        }

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Returns log entries for compliance exports."""
        return self.audit_log

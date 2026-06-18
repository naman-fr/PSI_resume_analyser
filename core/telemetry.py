"""Telemetry, Latency, and Cost Tracking Engine for MLOps/LLMOps."""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class TelemetryLogger:
    """Enterprise MLOps/LLMOps telemetry recorder."""

    _memory_buffer: List[Dict[str, Any]] = []
    _max_buffer_size: int = 100

    @classmethod
    def calculate_cost(cls, provider: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate LLM transaction costs based on registry rates."""
        cost = 0.0
        p = provider.lower()
        if "groq" in p:
            cost = (prompt_tokens * settings.telemetry.groq_input_cost / 1_000_000) + \
                   (completion_tokens * settings.telemetry.groq_output_cost / 1_000_000)
        elif "gemini" in p:
            cost = (prompt_tokens * settings.telemetry.gemini_input_cost / 1_000_000) + \
                   (completion_tokens * settings.telemetry.gemini_output_cost / 1_000_000)
        else:
            # Baseline estimation if generic
            cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
        return round(cost, 6)

    @classmethod
    def record_event(
        cls,
        node_name: str,
        provider: str,
        latency_sec: float,
        prompt_tokens: int,
        completion_tokens: int,
        status: str = "success",
        error_msg: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record an LLM call event with metadata, latency, and cost estimates.

        Parameters
        ----------
        node_name : str
            The name of the agent node (e.g. 'parse_resume').
        provider : str
            The LLM provider (e.g. 'groq', 'gemini').
        latency_sec : float
            Latency in seconds.
        prompt_tokens : int
            Number of input prompt tokens.
        completion_tokens : int
            Number of output completion tokens.
        status : str
            Operation status ('success' or 'failed').
        error_msg : str, optional
            The error details if status is failed.

        Returns
        -------
        Dict[str, Any]
            The compiled telemetry log entry.
        """
        cost = cls.calculate_cost(provider, prompt_tokens, completion_tokens)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        entry = {
            "timestamp": timestamp,
            "node_name": node_name,
            "provider": provider,
            "latency_sec": round(latency_sec, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated_cost_usd": cost,
            "status": status,
            "error_msg": error_msg or ""
        }

        # Save to memory buffer (for dashboard)
        cls._memory_buffer.append(entry)
        if len(cls._memory_buffer) > cls._max_buffer_size:
            cls._memory_buffer.pop(0)

        # Write to JSONL file asynchronously / sequentially
        log_path = settings.telemetry.telemetry_log_path
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to write telemetry log: %s", str(e))

        return entry

    @classmethod
    def get_summary_metrics(cls) -> Dict[str, Any]:
        """Aggregate total and average metrics across all logged history."""
        log_path = settings.telemetry.telemetry_log_path
        total_cost = 0.0
        total_tokens = 0
        total_latency = 0.0
        success_count = 0
        fail_count = 0
        records = []

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            records.append(json.loads(line))
            except Exception as e:
                logger.error("Failed to read telemetry log: %s", str(e))

        # If file is empty, use memory buffer
        if not records:
            records = cls._memory_buffer

        for r in records:
            total_cost += r.get("estimated_cost_usd", 0.0)
            total_tokens += r.get("total_tokens", 0)
            total_latency += r.get("latency_sec", 0.0)
            if r.get("status") == "success":
                success_count += 1
            else:
                fail_count += 1

        total_runs = len(records)
        avg_latency = total_latency / total_runs if total_runs > 0 else 0.0
        success_rate = (success_count / total_runs * 100) if total_runs > 0 else 100.0

        return {
            "total_runs": total_runs,
            "total_cost_usd": round(total_cost, 5),
            "total_tokens_consumed": total_tokens,
            "average_latency_sec": round(avg_latency, 3),
            "success_rate_pct": round(success_rate, 2),
            "success_count": success_count,
            "fail_count": fail_count
        }

    @classmethod
    def get_recent_logs(cls, count: int = 10) -> List[Dict[str, Any]]:
        """Get the latest N logs for display."""
        if len(cls._memory_buffer) >= count:
            return cls._memory_buffer[-count:]
        
        # Read from file if memory buffer is small
        log_path = settings.telemetry.telemetry_log_path
        records = []
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-count:]:
                        if line.strip():
                            records.append(json.loads(line))
                return records
            except Exception as e:
                logger.error("Failed to read telemetry logs: %s", str(e))
                
        return cls._memory_buffer

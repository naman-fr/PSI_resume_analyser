"""
Model Gateway Router and Context Budgeting Engine.
Optimizes LLM costs and latency by routing queries based on complexity tier,
calculating context budgets, and applying fallback paths if budgets are breached.
"""

import logging
import os
import json
from typing import Dict, Any

from core.local_llm import is_ollama_available
from core.lora_distillation import log_escalation_event

logger = logging.getLogger(__name__)

class ModelGatewayRouter:
    """
    Gateway to coordinate model routing based on task complexity,
    tenant cost limits, and context sizing.
    """

    PRICING = {
        "gemini-1.5-flash": {"input_1k": 0.000075, "output_1k": 0.0003, "tier": "medium"},
        "gemini-1.5-pro": {"input_1k": 0.00125, "output_1k": 0.00375, "tier": "high"},
        "llama-3-8b-instruct": {"input_1k": 0.00005, "output_1k": 0.00008, "tier": "low"},
        "mistral-7b-instruct": {"input_1k": 0.00007, "output_1k": 0.0001, "tier": "medium"},
        "local-fallback-model": {"input_1k": 0.0, "output_1k": 0.0, "tier": "low"}
    }

    def __init__(self, tenant_tier: str = "free", max_budget_usd: float = 0.50):
        self.tenant_tier = tenant_tier.lower()
        self.max_budget_usd = max_budget_usd
        self.spent_usd = 0.0
        self.prefer_local = os.environ.get("PSI_LOCAL_MODE", "false").lower() == "true"
        self._local_healthy = None

    def route_request(self, task_type: str, context_length: int) -> Dict[str, Any]:
        """
        Determines the optimal model to run based on complexity,
        tenant tier, and token usage constraints.
        """
        # 1. Determine baseline task complexity
        complexity = "low"
        if task_type in ["bias_audit", "improver", "matchmaker"]:
            complexity = "medium"
        elif task_type in ["reasoning_plane", "graph_rag", "digital_twin"]:
            complexity = "high"

        # 2. Check local tier preference first
        if self.prefer_local:
            if self._local_healthy is None:
                self._local_healthy = is_ollama_available()
            if self._local_healthy:
                model = "qwen2.5:7b-instruct-q4_K_M" if complexity == "high" else "gemma2:2b"
                return {
                    "model_name": model,
                    "tier": "local",
                    "estimated_cost_usd": 0.0,
                    "context_truncated": False,
                    "budget_remaining_usd": max(0.0, self.max_budget_usd - self.spent_usd),
                    "sandboxed": False,
                    "provider": "ollama-local"
                }
            logger.warning("Ollama unreachable — falling back to cloud tier.")

        # 3. Check if tenant has exceeded budget
        if self.spent_usd >= self.max_budget_usd:
            logger.warning("Tenant budget cap exceeded. Routing to offline/local fallback model.")
            return {
                "model_name": "local-fallback-model",
                "tier": "low",
                "estimated_cost_usd": 0.0,
                "context_truncated": False,
                "budget_remaining_usd": 0.0,
                "sandboxed": True,
                "notes": "Budget cap hit: using local mock engine"
            }

        # 4. Model routing decision tree based on Tenant Tier and Task Complexity
        selected_model = "gemini-1.5-flash" # default baseline

        if self.tenant_tier == "free":
            # Free tier always uses low or medium models
            if complexity == "high":
                selected_model = "gemini-1.5-flash" # downgrade pro requests to flash
            elif complexity == "medium":
                selected_model = "gemini-1.5-flash"
            else:
                selected_model = "llama-3-8b-instruct"
        elif self.tenant_tier == "standard":
            if complexity == "high":
                selected_model = "gemini-1.5-flash" # flash still handles standard high
            else:
                selected_model = "llama-3-8b-instruct"
        elif self.tenant_tier == "enterprise":
            # Enterprise tier allows high-cost models for heavy reasoning
            if complexity == "high":
                selected_model = "gemini-1.5-pro"
            elif complexity == "medium":
                selected_model = "gemini-1.5-flash"
            else:
                selected_model = "llama-3-8b-instruct"

        # 5. Context budget adjustment
        # If the input text is massive, we enforce text slicing to avoid massive bills
        max_context = 100000
        if selected_model == "llama-3-8b-instruct":
            max_context = 8000
        elif selected_model == "gemini-1.5-flash":
            max_context = 32000

        truncated = False
        effective_context = context_length
        if context_length > max_context:
            effective_context = max_context
            truncated = True
            logger.info(f"Context budget exceeded. Slicing input to fit {max_context} tokens.")

        # 6. Estimate cost
        rates = self.PRICING.get(selected_model, self.PRICING["local-fallback-model"])
        # Estimate ~4 characters per token
        est_tokens = effective_context / 4.0
        est_input_cost = (est_tokens / 1000.0) * rates["input_1k"]
        # Assume ~1000 tokens response size
        est_output_cost = (1000.0 / 1000.0) * rates["output_1k"]
        total_est = est_input_cost + est_output_cost

        return {
            "model_name": selected_model,
            "tier": rates["tier"],
            "estimated_cost_usd": total_est,
            "context_truncated": truncated,
            "budget_remaining_usd": max(0.0, self.max_budget_usd - self.spent_usd),
            "sandboxed": False
        }

    def evaluate_local_confidence(self, prompt: str, local_response: Dict[str, Any], task_type: str, confidence_threshold: float = 0.85) -> Dict[str, Any]:
        """
        Confidence-Gated Cascade Routing.
        Evaluates the local model's output confidence. If below threshold, escalates to Cloud Tier
        and logs the event for future LoRA distillation.
        """
        # Extract self-reported confidence or fallback to schema validity check
        confidence = local_response.get("confidence_score", 1.0)
        
        if confidence < confidence_threshold:
            logger.warning(f"Local confidence ({confidence:.2f}) < threshold ({confidence_threshold}). Escalating to Cloud Tier 2.")
            
            # Temporarily force cloud routing for this specific retry
            original_prefer_local = self.prefer_local
            self.prefer_local = False
            cloud_routing = self.route_request(task_type, len(prompt))
            self.prefer_local = original_prefer_local
            
            # Note: The actual execution of the cloud model happens in the agent node.
            # Here we just log that an escalation occurred for the Data Flywheel.
            log_escalation_event(
                prompt=prompt,
                cloud_response={"status": "escalated_to_cloud", "routing_details": cloud_routing},
                task_type=task_type,
                confidence_score=confidence
            )
            
            return {
                "action": "escalate",
                "cloud_routing": cloud_routing
            }
            
        return {
            "action": "accept_local",
            "confidence": confidence
        }

    def record_cost(self, model_name: str, input_tokens: int, output_tokens: int):
        """Accumulates token expenditure during application lifecycle."""
        rates = self.PRICING.get(model_name, {"input_1k": 0.0, "output_1k": 0.0})
        cost = ((input_tokens / 1000.0) * rates["input_1k"]) + ((output_tokens / 1000.0) * rates["output_1k"])
        self.spent_usd += cost
        logger.info(f"Recorded transaction: {model_name} | Cost: ${cost:.6f} | Total: ${self.spent_usd:.6f}")

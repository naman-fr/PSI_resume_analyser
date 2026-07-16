"""
Federated Behavioral Learning Engine
Implements FedAvg (Federated Averaging) for privacy-preserving model updates.
Instead of sending raw PII/telemetry to the server, local browser models train on 
their own behavioral data and only send weight deltas (gradients) to this endpoint.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

class FederatedAggregator:
    def __init__(self):
        self.global_weights = [0.0] * 128  # Example 128-dim embedding space
        self.round_updates = []
        self.aggregation_threshold = 10 # Wait for 10 users before averaging
        
    def receive_local_update(self, client_id: str, weights: List[float], num_samples: int) -> bool:
        """
        Receives a local model update from a client browser.
        """
        if len(weights) != len(self.global_weights):
            logger.warning(f"Invalid weight dimension from client {client_id}")
            return False
            
        self.round_updates.append({
            "client_id": client_id,
            "weights": weights,
            "n": num_samples
        })
        
        logger.info(f"Received federated update from {client_id} (n={num_samples}). Total in pool: {len(self.round_updates)}")
        
        if len(self.round_updates) >= self.aggregation_threshold:
            self.aggregate_fedavg()
            
        return True
        
    def aggregate_fedavg(self):
        """
        Performs Federated Averaging (FedAvg).
        w_global = sum( (n_k / N) * w_k )
        """
        logger.info("Executing FedAvg across local client updates...")
        total_samples = sum(u["n"] for u in self.round_updates)
        if total_samples == 0:
            return
            
        new_global = [0.0] * len(self.global_weights)
        
        for update in self.round_updates:
            weighting_factor = update["n"] / total_samples
            for i in range(len(new_global)):
                new_global[i] += update["weights"][i] * weighting_factor
                
        self.global_weights = new_global
        self.round_updates = [] # Reset for next round
        logger.info("FedAvg complete. Global model updated.")

federated_aggregator = FederatedAggregator()

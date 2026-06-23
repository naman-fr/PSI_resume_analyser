"""
Event-Driven Architecture Engine.
Decouples the candidate intelligence pipeline into separate event tasks
(upload, parse, extract, normalize, score, audit, report, feedback) with retry rules.
"""

import time
import uuid
import logging
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__)

class EventBus:
    """
    Pub-Sub Event Bus for scheduling and processing async resume evaluation tasks.
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.event_stream: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Registers a worker callback to listen for specific pipeline events."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        logger.info(f"Worker subscribed to pipeline event: '{event_type}'")

    def publish(self, event_type: str, data: Dict[str, Any]) -> str:
        """Pushes an event onto the bus and dispatches it to registered listeners."""
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": time.time(),
            "status": "pending",
            "retry_count": 0,
            "payload": data
        }
        self.event_stream.append(event)
        logger.info(f"Published event: [{event_type}] ID: {event_id}")
        
        self._dispatch(event)
        return event_id

    def _dispatch(self, event: Dict[str, Any]):
        """Internal dispatcher that invokes workers and handles errors/retries."""
        event_type = event["event_type"]
        event["status"] = "processing"
        
        listeners = self._listeners.get(event_type, [])
        if not listeners:
            event["status"] = "no_listeners"
            logger.warning(f"No active workers found for event: '{event_type}'")
            return

        for callback in listeners:
            try:
                # Execute subscriber callback
                callback(event["payload"])
                event["status"] = "completed"
            except Exception as e:
                logger.error(f"Error processing event {event['event_id']} under {callback.__name__}: {e}")
                self._handle_retry(event)

    def _handle_retry(self, event: Dict[str, Any]):
        """Implements backoff retries for failed event handlers."""
        max_retries = 3
        if event["retry_count"] < max_retries:
            event["retry_count"] += 1
            event["status"] = "retrying"
            logger.info(f"Retrying event {event['event_id']} (Attempt {event['retry_count']}/{max_retries})")
            
            # Simulated retry delay
            time.sleep(0.1 * event["retry_count"])
            self._dispatch(event)
        else:
            event["status"] = "failed"
            logger.error(f"Event {event['event_id']} exceeded maximum retry threshold of {max_retries}.")

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        """Returns the history of all pipeline events processed during session."""
        return self.event_stream

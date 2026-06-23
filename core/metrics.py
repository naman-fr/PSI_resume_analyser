"""Prometheus Instrumentation and Telemetry Metrics for PSI Resume Analyser."""

import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client package is not installed. Running in no-op metrics mode.")
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    # 1. Total analysis runs counter
    PSI_ANALYSIS_TOTAL = Counter(
        "psi_analysis_total",
        "Total number of resume analysis pipelines executed",
        ["status"]  # e.g., success, error
    )
    
    # 2. Pipeline latency histogram
    PSI_ANALYSIS_LATENCY = Histogram(
        "psi_analysis_latency_seconds",
        "Pipeline execution latency in seconds",
        buckets=(5, 10, 20, 30, 45, 60, 90, 120, 180)
    )
    
    # 3. LLM token counters
    PSI_LLM_TOKENS = Counter(
        "psi_llm_tokens_total",
        "Total number of LLM tokens consumed by agent pipelines",
        ["agent", "token_type"]  # e.g., input, output
    )
    
    # 4. LLM Cost gauge
    PSI_LLM_COST = Counter(
        "psi_llm_cost_usd",
        "Total accumulated LLM costs in USD"
    )
    
    # 5. Active users gauge
    PSI_ACTIVE_USERS = Gauge(
        "psi_active_users",
        "Current count of active sessions or registered users"
    )
    
    # 6. Premium conversions counter
    PSI_PREMIUM_CONVERSIONS = Counter(
        "psi_premium_conversions",
        "Total number of premium pipeline activations"
    )
    
    # 7. Drift severity gauge
    PSI_DRIFT_SCORE = Gauge(
        "psi_drift_score",
        "Current Population Stability Index (PSI) drift score"
    )
else:
    # Simple no-op stubs so the rest of the application doesn't crash
    class DummyMetric:
        def labels(self, *args, **kwargs): return self
        def inc(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def time(self):
            class Timer:
                def __enter__(self): pass
                def __exit__(self, *args): pass
            return Timer()

    PSI_ANALYSIS_TOTAL = DummyMetric()
    PSI_ANALYSIS_LATENCY = DummyMetric()
    PSI_LLM_TOKENS = DummyMetric()
    PSI_LLM_COST = DummyMetric()
    PSI_ACTIVE_USERS = DummyMetric()
    PSI_PREMIUM_CONVERSIONS = DummyMetric()
    PSI_DRIFT_SCORE = DummyMetric()
    def generate_latest():
        return b"# prometheus_client not installed, metrics disabled"
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


def record_analysis_metrics(status: str, duration: float, tokens_in: int = 0, tokens_out: int = 0, is_premium: bool = False):
    """Convenience helper to record multi-metric measurements for an analysis pipeline run."""
    try:
        PSI_ANALYSIS_TOTAL.labels(status=status).inc()
        PSI_ANALYSIS_LATENCY.observe(duration)
        if tokens_in > 0:
            PSI_LLM_TOKENS.labels(agent="pipeline", token_type="input").inc(tokens_in)
        if tokens_out > 0:
            PSI_LLM_TOKENS.labels(agent="pipeline", token_type="output").inc(tokens_out)
        
        # Approximate Gemini-1.5-flash costs: $0.075 / 1M input tokens, $0.30 / 1M output tokens
        cost = (tokens_in * 0.000000075) + (tokens_out * 0.00000030)
        if cost > 0:
            PSI_LLM_COST.inc(cost)
            
        if is_premium:
            PSI_PREMIUM_CONVERSIONS.inc()
            
        # Update drift score on every execution
        try:
            from core.drift_monitor import DriftMonitor
            drift_report = DriftMonitor.analyze_drift()
            if isinstance(drift_report, dict) and "psi_score" in drift_report:
                PSI_DRIFT_SCORE.set(drift_report["psi_score"])
        except Exception:
            pass
            
    except Exception as e:
        logger.warning("Failed to record metrics: %s", e)

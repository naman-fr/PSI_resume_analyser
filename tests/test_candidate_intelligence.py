"""
Unit tests for the Candidate Intelligence Platform modules.
Tests the Multimodal Parser, GraphRAG database, Candidate/Recruiter Twins,
Bias Audits, Model Routers, Event Bus, and MCP Sandbox client.
"""

from core.multimodal_parser import MultimodalParser
from core.graph_rag import generate_temporal_skill_graph, get_federated_weights_payload
from core.digital_twin import CandidateDigitalTwin, RecruiterDigitalTwin
from core.fairness import PIIRedactor, BiasAuditor, CounterfactualCalibrator, RobustnessEvaluator
from core.model_router import ModelGatewayRouter
from core.event_bus import EventBus
from core.mcp_sandbox import MCPSandbox

def test_multimodal_parser_scanned_pdf():
    # Since we don't have a real scanned PDF in tests, check detection returns boolean
    assert not MultimodalParser.is_scanned_pdf(b"Dummy PDF content")

def test_multimodal_parser_layout_extraction():
    # Test simulation extraction output format
    result = MultimodalParser.extract_layout(b"JOHN DOE\nAWS Certified Solutions Architect\nEmail: john.doe@gmail.com")
    assert "raw_text" in result
    assert "layout_elements" in result
    assert result["llm_verified"]

def test_graph_rag_ontology_insertion():
    # Test new temporal graph extraction
    res = generate_temporal_skill_graph("python dev")
    assert "nodes" in res
    assert "edges" in res
    assert len(res["nodes"]) > 0
    
    # Test federated sync payload
    weights = get_federated_weights_payload()
    assert "federated_version" in weights
    assert "gradient_hash" in weights
    assert len(weights["weights_sample"]) > 0

def test_digital_twins():
    resume_parsed = {
        "name": "Alex Mercer",
        "skills": ["Python", "FastAPI", "PyTorch", "Docker"],
        "experience": [
            {
                "title": "Senior MLOps Engineer",
                "bullets": [
                    "Led PyTorch models training pipeline.",
                    "Optimized API backend lowering cost by 15%."
                ]
            }
        ]
    }
    
    candidate = CandidateDigitalTwin.construct_twin(resume_parsed)
    assert candidate["candidate_name"] == "Alex Mercer"
    assert len(candidate["job_families"]) > 0
    assert candidate["interview_risk_score"] > 0
    
    recruiter = RecruiterDigitalTwin.simulate_screening(resume_parsed, "Looking for a Python developer with PyTorch")
    assert len(recruiter["screening_questions"]) > 0
    assert len(recruiter["attention_heatmap"]) > 0

def test_fairness_governance():
    text = "Jane Doe. Email: jane.doe@yahoo.com. Graduated CS in 1999."
    
    # PII Redactor
    redacted = PIIRedactor.redact(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "jane.doe@yahoo.com" not in redacted
    
    # Bias Audit
    audit = BiasAuditor.audit_demographics(text)
    assert not audit["blind_screening_compliant"]
    assert audit["fairness_index"] < 100.0

    # Counterfactual
    calibration = CounterfactualCalibrator.what_if_analysis(75.0, ["python"], text)
    assert len(calibration["what_if_scenarios"]) > 0

    # Robustness
    robustness = RobustnessEvaluator.audit_robustness(text, 75.0)
    assert robustness["robustness_score"] > 0

def test_model_router():
    router = ModelGatewayRouter(tenant_tier="enterprise", max_budget_usd=0.20)
    
    # High complexity routing
    route = router.route_request("reasoning_plane", 10000)
    assert route["model_name"] == "gemini-1.5-pro"
    
    # Cost accumulation
    router.record_cost("gemini-1.5-pro", 10000, 1000)
    assert router.spent_usd > 0.0
    
    # Budget breach routing
    router.record_cost("gemini-1.5-pro", 100000, 50000)
    breached_route = router.route_request("reasoning_plane", 2000)
    assert breached_route["model_name"] == "local-fallback-model"

def test_event_bus():
    bus = EventBus()
    events_triggered = []
    
    bus.subscribe("test_event", lambda p: events_triggered.append(p["val"]))
    bus.publish("test_event", {"val": 42})
    
    assert len(events_triggered) == 1
    assert events_triggered[0] == 42
    assert len(bus.get_audit_trail()) > 0

def test_mcp_sandbox():
    sandbox = MCPSandbox(tenant_id="test_org")
    
    # Allowlisted Succeeded Call
    # Expected signature is sha256 of "github/list_repos:test_org"
    import hashlib
    sig = hashlib.sha256("github/list_repos:test_org".encode()).hexdigest()[:16]
    res1 = sandbox.execute_tool("github/list_repos", {"org": "google"}, sig)
    assert res1["success"]
    
    # Blocked (Wrong Signature)
    res2 = sandbox.execute_tool("github/list_repos", {"org": "google"}, "invalidsig")
    assert not res2["success"]
    assert "access signature" in res2["error"]

    # Blocked (Injection Hack)
    res3 = sandbox.execute_tool("github/list_repos", {"org": "; rm -rf /"}, sig)
    assert not res3["success"]
    assert "Adversarial payload" in res3["error"]

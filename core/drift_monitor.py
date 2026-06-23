"""Data Drift & Monitoring Engine using statistical baseline comparison."""

import os
import json
import logging
import math
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

BASELINE_FILE = os.path.join("data", "drift_baseline.json")
RUNS_FILE = os.path.join("data", "drift_runs.json")

class DriftMonitor:
    """Monitors data distribution drift using statistical benchmarks."""

    # Default baseline statistics (expected distributions of resume/JD characteristics)
    _default_baseline: Dict[str, Any] = {
        "resume_length": {"mean": 2500.0, "std": 800.0, "count": 100},
        "jd_length": {"mean": 1800.0, "std": 600.0, "count": 100},
        "skill_count": {"mean": 15.0, "std": 5.0, "count": 100},
        "composite_score": {
            "bins": {
                "0-20": 0.05,
                "21-40": 0.15,
                "41-60": 0.30,
                "61-80": 0.35,
                "81-100": 0.15
            },
            "mean": 58.0,
            "count": 100
        }
    }

    @classmethod
    def _load_baseline(cls) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
        if not os.path.exists(BASELINE_FILE):
            try:
                with open(BASELINE_FILE, "w", encoding="utf-8") as f:
                    json.dump(cls._default_baseline, f, indent=2, ensure_ascii=False)
                logger.info("Initialized drift baseline statistics at %s", BASELINE_FILE)
            except Exception as e:
                logger.error("Failed to write drift baseline: %s", e)
            return cls._default_baseline
        try:
            with open(BASELINE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read drift baseline: %s", e)
            return cls._default_baseline

    @classmethod
    def _load_runs(cls) -> List[Dict[str, Any]]:
        if not os.path.exists(RUNS_FILE):
            return []
        try:
            with open(RUNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to read drift runs: %s", e)
            return []

    @classmethod
    def _save_runs(cls, runs: List[Dict[str, Any]]):
        os.makedirs(os.path.dirname(RUNS_FILE), exist_ok=True)
        try:
            # Keep only the last 1000 runs to prevent file bloat
            with open(RUNS_FILE, "w", encoding="utf-8") as f:
                json.dump(runs[-1000:], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save drift runs: %s", e)

    @classmethod
    def record_run(cls, resume_text: str, jd_text: str, skill_count: int, composite_score: float):
        """Record input/output attributes of a pipeline execution for drift auditing."""
        runs = cls._load_runs()
        runs.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "resume_length": len(resume_text) if resume_text else 0,
            "jd_length": len(jd_text) if jd_text else 0,
            "skill_count": skill_count,
            "composite_score": composite_score
        })
        cls._save_runs(runs)

    @staticmethod
    def calculate_psi(expected: Dict[str, float], actual: Dict[str, float]) -> float:
        """
        Compute Population Stability Index (PSI).
        PSI = sum((Actual_i - Expected_i) * ln(Actual_i / Expected_i))
        """
        psi = 0.0
        # Ensure all bins from expected are represented
        for bin_name, exp_pct in expected.items():
            act_pct = actual.get(bin_name, 0.0)
            
            # Small correction to avoid log(0) and divide by zero
            exp_pct = max(exp_pct, 0.0001)
            act_pct = max(act_pct, 0.0001)
            
            psi += (act_pct - exp_pct) * math.log(act_pct / exp_pct)
        return psi

    @classmethod
    def analyze_drift(cls) -> Dict[str, Any]:
        """Compare recent runs against baseline stats to detect statistical drift."""
        baseline = cls._load_baseline()
        runs = cls._load_runs()
        
        if len(runs) < 5:
            return {
                "status": "Insufficient Data",
                "message": f"Need at least 5 runs to calculate drift. Current run count: {len(runs)}",
                "psi_score": 0.0,
                "drift_detected": False
            }
        
        # Take the last 50 runs for current population
        recent_runs = runs[-50:]
        num_recent = len(recent_runs)
        
        avg_res_len = sum(r["resume_length"] for r in recent_runs) / num_recent
        avg_jd_len = sum(r["jd_length"] for r in recent_runs) / num_recent
        avg_skills = sum(r["skill_count"] for r in recent_runs) / num_recent
        avg_score = sum(r["composite_score"] for r in recent_runs) / num_recent

        # Score Binning for PSI
        score_bins = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        for run in recent_runs:
            s = run["composite_score"]
            if s <= 20: score_bins["0-20"] += 1
            elif s <= 40: score_bins["21-40"] += 1
            elif s <= 60: score_bins["41-60"] += 1
            elif s <= 80: score_bins["61-80"] += 1
            else: score_bins["81-100"] += 1
        
        actual_score_pct = {k: v / num_recent for k, v in score_bins.items()}
        expected_score_pct = baseline["composite_score"]["bins"]
        
        psi = cls.calculate_psi(expected_score_pct, actual_score_pct)
        
        # Interpret PSI
        drift_detected = psi >= 0.25
        
        # Check input parameter drift (e.g. if average resume length changes by > 50%)
        res_baseline = baseline["resume_length"]["mean"]
        res_drift_warning = abs(avg_res_len - res_baseline) / res_baseline > 0.5
        
        status = "STABLE"
        if drift_detected:
            status = "DRIFT DETECTED"
        elif psi >= 0.1 or res_drift_warning:
            status = "WARNING"
            
        report = {
            "status": status,
            "run_count_analyzed": num_recent,
            "psi_score": round(psi, 4),
            "drift_detected": drift_detected,
            "metrics": {
                "resume_length": {
                    "baseline": baseline["resume_length"]["mean"],
                    "recent": round(avg_res_len, 1),
                    "drift_warning": res_drift_warning
                },
                "jd_length": {
                    "baseline": baseline["jd_length"]["mean"],
                    "recent": round(avg_jd_len, 1)
                },
                "skill_count": {
                    "baseline": baseline["skill_count"]["mean"],
                    "recent": round(avg_skills, 1)
                },
                "composite_score": {
                    "baseline": baseline["composite_score"]["mean"],
                    "recent": round(avg_score, 1)
                }
            }
        }
        
        if drift_detected:
            logger.warning("DATA DRIFT DETECTED: Score distribution PSI is %f", psi)
            
        return report

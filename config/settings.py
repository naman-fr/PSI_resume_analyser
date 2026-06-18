"""Application settings and configuration."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScoringWeights:
    """ATS scoring weight configuration."""
    keyword_match: float = 0.40
    semantic_similarity: float = 0.25
    experience_relevance: float = 0.25
    education_match: float = 0.10


@dataclass
class ModelConfig:
    """LLM model configuration with fallback support."""
    # Primary: Google Gemini
    gemini_model: str = "gemini-2.0-flash"
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 4096

    # Fallback: Groq (Llama 3)
    groq_model: str = "llama-3.3-70b-versatile"
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_temperature: float = 0.1
    groq_max_tokens: int = 4096

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    semantic_alpha: float = 0.6  # Favor semantic over lexical


@dataclass
class JobSearchConfig:
    """Configuration for the Job Finder multi-API search."""
    adzuna_app_id: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_ID", ""))
    adzuna_app_key: str = field(default_factory=lambda: os.getenv("ADZUNA_APP_KEY", ""))
    adzuna_country: str = field(default_factory=lambda: os.getenv("ADZUNA_COUNTRY", "us"))
    rapidapi_key: str = field(default_factory=lambda: os.getenv("RAPIDAPI_KEY", ""))
    max_results_per_source: int = 25
    min_match_score: float = 35.0



@dataclass
class SecurityConfig:
    """Security and compliance guardrails configuration."""
    enable_pii_masking: bool = True
    enable_injection_detection: bool = True
    mask_demographics: bool = True
    injection_threshold: float = 0.75  # Confidence threshold for prompt injection block


@dataclass
class TelemetryConfig:
    """MLOps and LLMOps telemetry configuration."""
    enable_telemetry: bool = True
    telemetry_log_path: str = "data/telemetry_logs.jsonl"
    # Pricing configuration (per 1M tokens)
    groq_input_cost: float = 0.59
    groq_output_cost: float = 0.79
    gemini_input_cost: float = 0.075
    gemini_output_cost: float = 0.30


@dataclass
class MemoryConfig:
    """Long-term memory and knowledge representation configuration."""
    enable_long_term_memory: bool = True
    memory_db_path: str = "data/episodic_memory.json"
    enable_skill_graph: bool = True
    skill_graph_path: str = "data/skill_taxonomy.json"


@dataclass
class PremiumConfig:
    """Premium paid-tier verification configurations."""
    pricing_tiers: dict = field(default_factory=lambda: {
        "free": {"name": "Standard Core", "price": "$0", "desc": "Standard ATS score & multi-agent critique"},
        "premium": {"name": "Premium Verified", "price": "$49", "desc": "ATS audit, link check, and background white-text scan"}
    })
    link_timeout: float = 5.0
    trust_weight_github: float = 0.5
    trust_weight_linkedin: float = 0.3
    trust_weight_portfolio: float = 0.2


@dataclass
class DataLoopConfig:
    """MLOps fine-tuning data collection loop configurations."""
    enable_data_loop: bool = True
    finetuning_dataset_path: str = "data/finetuning_dataset.jsonl"


@dataclass
class AppConfig:
    """Main application configuration."""
    app_name: str = "PSI Resume Analyser"
    app_version: str = "1.0.0"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # File handling
    max_file_size_mb: int = 10
    allowed_extensions: tuple = (".pdf",)

    # Scoring
    scoring: ScoringWeights = field(default_factory=ScoringWeights)

    # Models
    models: ModelConfig = field(default_factory=ModelConfig)

    # Job Search
    job_search: JobSearchConfig = field(default_factory=JobSearchConfig)

    # Security Guardrails
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # MLOps Telemetry
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)

    # Memory & Graph
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # Premium Settings
    premium: PremiumConfig = field(default_factory=PremiumConfig)

    # MLOps Data Loop Settings
    data_loop: DataLoopConfig = field(default_factory=DataLoopConfig)

    # HuggingFace
    hf_token: str = field(default_factory=lambda: os.getenv("HF_TOKEN", ""))

    def has_gemini(self) -> bool:
        """Check if Gemini API key is configured."""
        return False

    def has_groq(self) -> bool:
        """Check if Groq API key is configured."""
        return bool(self.models.groq_api_key)

    def get_available_provider(self) -> str:
        """Get the best available LLM provider."""
        if self.has_groq():
            return "groq"
        else:
            raise ValueError("No LLM API key configured. Set GROQ_API_KEY.")


# Global settings instance
settings = AppConfig()

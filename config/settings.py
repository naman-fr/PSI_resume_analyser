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

    # HuggingFace
    hf_token: str = field(default_factory=lambda: os.getenv("HF_TOKEN", ""))

    def has_gemini(self) -> bool:
        """Check if Gemini API key is configured."""
        return bool(self.models.gemini_api_key)

    def has_groq(self) -> bool:
        """Check if Groq API key is configured."""
        return bool(self.models.groq_api_key)

    def get_available_provider(self) -> str:
        """Get the best available LLM provider."""
        if self.has_gemini():
            return "gemini"
        elif self.has_groq():
            return "groq"
        else:
            raise ValueError("No LLM API key configured. Set GOOGLE_API_KEY or GROQ_API_KEY.")


# Global settings instance
settings = AppConfig()

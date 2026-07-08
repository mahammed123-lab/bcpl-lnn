"""
JARVIS Web Search — Centralised configuration.

Every secret is read from the environment. No fallback literals.
Set your keys via environment variables or a .env loader before
importing this module.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass

log = logging.getLogger("JARVIS.WebSearch.Config")


@dataclass
class SearchGateConfig:
    """Configuration for the entire search-gate pipeline."""

    # ── Search provider API keys (env-only) ──
    tavily_api_key:   str = ""
    serpapi_api_key:  str = ""
    serper_api_key:   str = ""
    newsdata_api_key: str = ""

    # ── LLM provider API keys (env-only) — ANY ONE of these is enough
    # to power classification + synthesis. The router below tries them
    # in priority order and falls through automatically. ──
    nvidia_api_key:     str = ""
    groq_api_key:       str = ""
    openrouter_api_key: str = ""
    together_api_key:   str = ""
    gemini_api_key:     str = ""
    ollama_base_url:    str = ""   # e.g. "http://localhost:11434" — no key needed

    # ── Provider endpoints / models ──
    nvidia_base_url:     str = "https://integrate.api.nvidia.com/v1"
    nvidia_model:        str = "meta/llama-3.2-3b-instruct"
    groq_base_url:       str = "https://api.groq.com/openai/v1"
    groq_model:          str = "llama-3.1-8b-instant"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model:    str = "meta-llama/llama-3.1-8b-instruct:free"
    together_base_url:   str = "https://api.together.xyz/v1"
    together_model:      str = "meta-llama/Llama-3.2-3B-Instruct-Turbo"
    gemini_model:        str = "gemini-1.5-flash"
    ollama_model:        str = "llama3.2"
    newsdata_url:        str = "https://newsdata.io/api/1/latest"
    searxng_url:         str = ""
    searxng_preferences: str = ""

    # ── LLM fallback order. First configured + healthy provider wins.
    # Override with LLM_PROVIDER_PRIORITY="groq,nvidia,openrouter" etc. ──
    llm_provider_priority: str = "nvidia,groq,openrouter,together,gemini,ollama"

    # ── LLM classifier ──
    knowledge_cutoff: str = (
        "unknown — treat any date-, version-, price-, or "
        "role-sensitive fact as possibly stale"
    )

    # ── Circuit breaker ──
    failure_threshold: int = 3
    cooldown_seconds:  int = 300   # 5 minutes

    # ── Session ──
    session_ttl_seconds: int = 600  # 10 minutes

    # ── Behaviour flags ──
    llm_classifier_enabled: bool = True

    # ── Synthesis ──
    synthesis_max_tokens: int = 800
    synthesis_timeout:    int = 12

    @classmethod
    def from_env(cls) -> "SearchGateConfig":
        """Build config from environment variables."""
        cfg = cls(
            tavily_api_key   = os.environ.get("TAVILY_API_KEY", ""),
            serpapi_api_key  = os.environ.get("SERPAPI_API_KEY", ""),
            serper_api_key   = os.environ.get("SERPER_API_KEY", ""),
            newsdata_api_key = os.environ.get("NEWSDATA_API_KEY", ""),

            nvidia_api_key     = os.environ.get("NVIDIA_API_KEY", ""),
            groq_api_key       = os.environ.get("GROQ_API_KEY", ""),
            openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", ""),
            together_api_key   = os.environ.get("TOGETHER_API_KEY", ""),
            gemini_api_key     = os.environ.get("GEMINI_API_KEY", ""),
            ollama_base_url    = os.environ.get("OLLAMA_BASE_URL", ""),

            nvidia_base_url  = os.environ.get(
                "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
            ),
            nvidia_model = os.environ.get(
                "NVIDIA_MODEL", "meta/llama-3.2-3b-instruct"
            ),
            groq_base_url = os.environ.get(
                "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
            ),
            groq_model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
            openrouter_base_url = os.environ.get(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ),
            openrouter_model = os.environ.get(
                "OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"
            ),
            together_base_url = os.environ.get(
                "TOGETHER_BASE_URL", "https://api.together.xyz/v1"
            ),
            together_model = os.environ.get(
                "TOGETHER_MODEL", "meta-llama/Llama-3.2-3B-Instruct-Turbo"
            ),
            gemini_model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"),
            ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2"),

            newsdata_url = os.environ.get(
                "NEWSDATA_URL", "https://newsdata.io/api/1/latest"
            ),
            searxng_url         = os.environ.get("SEARXNG_URL", ""),
            searxng_preferences = os.environ.get("SEARXNG_PREFERENCES", ""),
            llm_provider_priority = os.environ.get(
                "LLM_PROVIDER_PRIORITY",
                "nvidia,groq,openrouter,together,gemini,ollama",
            ),
            knowledge_cutoff = os.environ.get(
                "JARVIS_KNOWLEDGE_CUTOFF",
                "unknown — treat any date-, version-, price-, or "
                "role-sensitive fact as possibly stale",
            ),
            failure_threshold = int(os.environ.get("JARVIS_FAILURE_THRESHOLD", "3")),
            cooldown_seconds  = int(os.environ.get("JARVIS_COOLDOWN_SECONDS", "300")),
            session_ttl_seconds = int(os.environ.get("JARVIS_SESSION_TTL", "600")),
            llm_classifier_enabled = os.environ.get(
                "JARVIS_LLM_CLASSIFIER", "1"
            ).lower() in ("1", "true", "yes"),
            synthesis_max_tokens = int(os.environ.get("JARVIS_SYNTH_TOKENS", "800")),
            synthesis_timeout    = int(os.environ.get("JARVIS_SYNTH_TIMEOUT", "12")),
        )

        if not any(cfg.provider_configured(n) for n in
                   ("tavily", "serper", "serpapi", "searxng", "newsdata")):
            log.warning("[CONFIG] No web search provider key set — search will return no results")
        if not any(cfg.provider_configured(n) for n in
                   ("nvidia", "groq", "openrouter", "together", "gemini", "ollama")):
            log.warning("[CONFIG] No LLM provider key set — classification/synthesis will fall back to regex-only")

        return cfg

    def provider_configured(self, name: str) -> bool:
        """Return True if the named provider has its credentials set."""
        return {
            "tavily":     bool(self.tavily_api_key),
            "serpapi":    bool(self.serpapi_api_key),
            "serper":     bool(self.serper_api_key),
            "searxng":    bool(self.searxng_url),
            "newsdata":   bool(self.newsdata_api_key),
            "nvidia":     bool(self.nvidia_api_key),
            "groq":       bool(self.groq_api_key),
            "openrouter": bool(self.openrouter_api_key),
            "together":   bool(self.together_api_key),
            "gemini":     bool(self.gemini_api_key),
            "ollama":     bool(self.ollama_base_url),
        }.get(name, False)

    def llm_priority_list(self) -> list:
        """Ordered list of LLM provider names to try, filtered to known names."""
        known = {"nvidia", "groq", "openrouter", "together", "gemini", "ollama"}
        names = [n.strip().lower() for n in self.llm_provider_priority.split(",") if n.strip()]
        return [n for n in names if n in known] or list(known)

    def any_llm_configured(self) -> bool:
        return any(self.provider_configured(n) for n in self.llm_priority_list())

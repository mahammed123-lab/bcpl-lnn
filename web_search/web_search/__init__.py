"""
JARVIS Web Search — Intelligent search pipeline.

Three-layer classification: regex → LLM → hallucination detector.
Multi-provider search with circuit breaker.
LLM synthesis grounded in source data.

Usage::

    from web_search import SearchGate

    gate = SearchGate.from_env()
    result = gate.classify("What's the latest NVIDIA GPU?")
    if result.needs_search:
        import asyncio
        search_result = asyncio.run(gate.search(result.search_query))
"""
from __future__ import annotations

import asyncio
from typing import Optional, Callable, Dict, Any, List

from web_search.types import (
    SearchIntent, QueryType, Confidence,
    ClassifierResult, SearchResult, ProviderHealth,
)
from web_search.config import SearchGateConfig
from web_search.classifiers.pipeline import classify
from web_search.classifiers.regex import classify_intent_regex, extract_backtick_query
from web_search.classifiers.llm import llm_needs_search
from web_search.providers.router import ProviderRouter
from web_search.providers.llm_router import call_llm as _multi_llm_call, make_call_llm
from web_search.engine.session import SearchSession
from web_search.engine.orchestrator import quick_search, multi_provider_search
from web_search.engine.synthesizer import call_nvidia, ask_ai
from web_search.engine.query import detect_query_type, expand_query

__version__ = "7.1.0"

__all__ = [
    "SearchGate",
    "SearchIntent", "QueryType", "Confidence",
    "ClassifierResult", "SearchResult", "ProviderHealth",
    "SearchGateConfig",
    "classify", "classify_intent_regex", "llm_needs_search",
    "ProviderRouter", "SearchSession",
    "quick_search", "multi_provider_search",
    "call_nvidia", "ask_ai",
    "call_llm", "make_call_llm",
    "detect_query_type", "expand_query",
]

# Re-exported at module level so `from web_search import call_llm` works.
call_llm = _multi_llm_call


class SearchGate:
    """High-level facade that ties classification, routing, and search together.

    `call_llm` is optional. If you don't supply one, SearchGate builds a
    default that routes across every configured LLM provider (NVIDIA,
    Groq, OpenRouter, Together, Gemini, local Ollama) with automatic
    fallback — so setting just ONE of those env vars is enough for the
    LLM classifier and result synthesis to work end to end. Pass your
    own `call_llm` only if you want to plug in a different model/host
    entirely (e.g. JARVIS's own orchestra.py brain).
    """

    def __init__(
        self,
        config: SearchGateConfig,
        call_llm: Optional[Callable[[List[Dict[str, str]]], str]] = None,
    ):
        self.config = config
        self.router = ProviderRouter(config)
        self.session = SearchSession(ttl=config.session_ttl_seconds)
        self._call_llm = call_llm or make_call_llm(config, self.router)

    @classmethod
    def from_env(
        cls,
        call_llm: Optional[Callable[[List[Dict[str, str]]], str]] = None,
    ) -> "SearchGate":
        return cls(SearchGateConfig.from_env(), call_llm=call_llm)

    def classify(self, text: str) -> ClassifierResult:
        return classify(
            text,
            call_llm=self._call_llm,
            config=self.config,
            has_session=self.session.has_results(),
        )

    async def search(
        self, query: str, *, synthesize: bool = True,
    ) -> Dict[str, Any]:
        return await quick_search(
            query, self.config, self.router, self.session,
            synthesize=synthesize,
        )

    def search_sync(self, query: str, **kwargs) -> Dict[str, Any]:
        return asyncio.run(self.search(query, **kwargs))

    def provider_status(self) -> Dict[str, ProviderHealth]:
        return self.router.get_status()

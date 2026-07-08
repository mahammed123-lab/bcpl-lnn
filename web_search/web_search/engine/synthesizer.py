"""
JARVIS Web Search — Result Synthesis Module.

Takes organic results, formats them as context, and calls whichever
LLM provider is configured (NVIDIA, Groq, OpenRouter, Together, Gemini,
or local Ollama — first healthy one wins) to generate a grounded,
factual response for Hussain.
"""
import logging
from typing import List, Optional
from datetime import datetime

from web_search.types import SearchResult, QueryType
from web_search.config import SearchGateConfig
from web_search.providers.router import ProviderRouter
from web_search.providers.llm_router import call_llm
from web_search.providers.llm.nvidia import chat_complete as _nvidia_chat_complete

log = logging.getLogger("JARVIS.WebSearch.Synthesizer")

_SYNTHESIS_PROMPT = """You are JARVIS, Hussain's personal AI assistant.
Today is {today_date}.

Below are search results for: "{query}"

SOURCES:
{sources}

INSTRUCTIONS:
- Answer the question using ONLY the information from the sources above.
- Be concise, accurate, and cite sources naturally.
- If the sources don't contain enough information, say so.
- For news queries, prioritise the most recent information.
- For comparisons, present a balanced view.
- For product queries, include key specs and pricing if available.
- NEVER fabricate information not present in the sources."""


def call_nvidia(
    msgs: list,
    config: SearchGateConfig,
    max_tokens: int = 800,
    timeout: int = 12,
) -> str:
    """Direct NVIDIA-only call. Kept for backward compatibility —
    prefer `call_llm` (multi-provider, with automatic fallback) for
    new code."""
    return _nvidia_chat_complete(msgs, config, max_tokens=max_tokens, timeout=timeout)


def ask_ai(
    prompt: str,
    config: SearchGateConfig,
    router: Optional[ProviderRouter] = None,
    max_tokens: int = 600,
) -> str:
    """Convenience helper to ask the model a simple text question.

    Routes across every configured LLM provider (any single key —
    NVIDIA, Groq, OpenRouter, Together, Gemini, or a local Ollama URL —
    is enough). Pass an existing `router` to share circuit-breaker
    state with the rest of the app; otherwise an ephemeral one is used.
    """
    r = router if router is not None else ProviderRouter(config)
    return call_llm(
        [{"role": "user", "content": prompt}],
        config,
        r,
        max_tokens=max_tokens,
    )


def synthesize_results(
    query: str,
    results: List[SearchResult],
    config: SearchGateConfig,
    router: Optional[ProviderRouter] = None,
    query_type: QueryType = QueryType.GENERAL,
) -> str:
    """Synthesize multiple SearchResult entries into a unified response."""
    if not results:
        return ""

    sources_block = []
    for i, r in enumerate(results[:6], 1):
        sources_block.append(
            f"[{i}] {r.title}\n"
            f"    Source: {r.source}\n"
            f"    Date: {r.date or 'unknown'}\n"
            f"    Content: {r.content[:500]}"
        )

    prompt = _SYNTHESIS_PROMPT.format(
        today_date=datetime.now().strftime("%B %d, %Y"),
        query=query,
        sources="\n\n".join(sources_block),
    )

    gate_router = router if router is not None else ProviderRouter(config)
    return call_llm(
        [{"role": "system", "content": prompt}],
        config,
        gate_router,
        max_tokens=config.synthesis_max_tokens,
        timeout=config.synthesis_timeout,
    )

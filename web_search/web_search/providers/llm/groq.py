"""JARVIS Web Search — Groq chat provider (very low latency, generous free tier)."""
import logging
from typing import List, Dict
from web_search.config import SearchGateConfig
from web_search.providers.llm._openai_compat import call_openai_compatible

log = logging.getLogger("JARVIS.WebSearch.LLM.Groq")


def chat_complete(
    messages: List[Dict[str, str]],
    config: SearchGateConfig,
    max_tokens: int = 800,
    timeout: int = 12,
) -> str:
    return call_openai_compatible(
        base_url=config.groq_base_url,
        api_key=config.groq_api_key,
        model=config.groq_model,
        messages=messages,
        max_tokens=max_tokens,
        timeout=timeout,
        log=log,
        provider_tag="GROQ",
    )

"""JARVIS Web Search — Together AI chat provider."""
import logging
from typing import List, Dict
from web_search.config import SearchGateConfig
from web_search.providers.llm._openai_compat import call_openai_compatible

log = logging.getLogger("JARVIS.WebSearch.LLM.Together")


def chat_complete(
    messages: List[Dict[str, str]],
    config: SearchGateConfig,
    max_tokens: int = 800,
    timeout: int = 12,
) -> str:
    return call_openai_compatible(
        base_url=config.together_base_url,
        api_key=config.together_api_key,
        model=config.together_model,
        messages=messages,
        max_tokens=max_tokens,
        timeout=timeout,
        log=log,
        provider_tag="TOGETHER",
    )

"""
JARVIS Web Search — Multi-LLM Router.

Mirrors the search-provider ProviderRouter pattern: tries every
*configured* LLM provider in priority order, skipping any that are
in cooldown from repeated failures, and returns the first non-empty
reply. This is what makes "any single API key" possible — set only
GROQ_API_KEY (say) and classification + synthesis both route to Groq
automatically, with no other code changes.
"""
import logging
from typing import List, Dict, Optional

from web_search.config import SearchGateConfig
from web_search.providers.router import ProviderRouter
from web_search.providers.llm import PROVIDER_MODULES

log = logging.getLogger("JARVIS.WebSearch.LLMRouter")


def call_llm(
    messages: List[Dict[str, str]],
    config: SearchGateConfig,
    router: ProviderRouter,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None,
) -> str:
    """Try each configured LLM provider in priority order until one answers.

    Returns "" only if every configured provider failed (or none are
    configured) — callers should treat that as "classifier/synth
    unavailable" and fail open rather than raising.
    """
    max_tokens = max_tokens or config.synthesis_max_tokens
    timeout = timeout or config.synthesis_timeout

    for name in config.llm_priority_list():
        if not config.provider_configured(name):
            continue
        if not router.is_available(name):
            continue

        module = PROVIDER_MODULES.get(name)
        if module is None:
            continue

        try:
            reply = module.chat_complete(messages, config, max_tokens=max_tokens, timeout=timeout)
        except Exception as e:
            log.warning("[LLM_ROUTER] '%s' raised: %s", name, e)
            router.record_failure(name)
            continue

        if reply:
            router.record_success(name)
            return reply
        router.record_failure(name)

    log.warning("[LLM_ROUTER] No LLM provider produced a response")
    return ""


def any_llm_available(config: SearchGateConfig, router: ProviderRouter) -> bool:
    """True if at least one configured LLM provider is not in cooldown."""
    return any(
        config.provider_configured(name) and router.is_available(name)
        for name in config.llm_priority_list()
    )


def make_call_llm(config: SearchGateConfig, router: ProviderRouter):
    """Build a `call_llm(messages) -> str` closure bound to this config/router.

    Handy for passing straight into the classifier pipeline, which only
    knows about the generic `Callable[[messages], str]` shape.
    """
    def _call(messages: List[Dict[str, str]]) -> str:
        return call_llm(messages, config, router)
    return _call

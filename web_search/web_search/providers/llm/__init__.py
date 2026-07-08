"""
JARVIS Web Search — Multi-LLM Provider Package.

Every module here exposes the same tiny contract:

    chat_complete(messages, config, max_tokens=800, timeout=12) -> str

Returns the model's text reply, or "" on any failure (never raises —
the router treats an empty string as "try the next provider").
This lets `llm_router.call_llm()` treat every provider identically,
regardless of which one is actually configured. Any single provider
key (NVIDIA, Groq, OpenRouter, Together, Gemini) or a local Ollama
URL is enough to make classification + synthesis work end to end.
"""
from web_search.providers.llm import (
    nvidia, groq, openrouter, together, gemini, ollama,
)

PROVIDER_MODULES = {
    "nvidia":     nvidia,
    "groq":       groq,
    "openrouter": openrouter,
    "together":   together,
    "gemini":     gemini,
    "ollama":     ollama,
}

__all__ = ["PROVIDER_MODULES", "nvidia", "groq", "openrouter", "together", "gemini", "ollama"]

"""
JARVIS Web Search — Local Ollama chat provider.

No API key required — this is the "works with zero cloud keys" fallback,
for anyone running `ollama serve` locally. Only attempted if
OLLAMA_BASE_URL is set (it's opt-in, since a stray local server
shouldn't be silently queried).
"""
import logging
import requests
from typing import List, Dict
from web_search.config import SearchGateConfig

log = logging.getLogger("JARVIS.WebSearch.LLM.Ollama")


def chat_complete(
    messages: List[Dict[str, str]],
    config: SearchGateConfig,
    max_tokens: int = 800,
    timeout: int = 12,
) -> str:
    if not config.ollama_base_url:
        return ""
    try:
        url = config.ollama_base_url.rstrip("/") + "/api/chat"
        payload = {
            "model": config.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": max_tokens},
        }
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        content = (data.get("message") or {}).get("content", "").strip()
        return content
    except Exception as e:
        log.warning("[OLLAMA] %s", e)
        return ""

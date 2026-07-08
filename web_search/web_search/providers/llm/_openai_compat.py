"""
JARVIS Web Search — Shared helper for OpenAI-compatible chat providers.

NVIDIA NIM, Groq, OpenRouter, and Together AI all speak the same
`POST {base_url}/chat/completions` shape with a Bearer token. This
module implements that call once so each provider file only needs to
supply its own base_url / api_key / model / logger.
"""
import time
import logging
import requests
from typing import List, Dict


def call_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    timeout: int,
    log: logging.Logger,
    provider_tag: str,
    extra_headers: Dict[str, str] = None,
) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint with retries.

    Returns the reply text, or "" on any failure — never raises, so the
    LLM router can move on to the next provider without special-casing.
    """
    if not api_key:
        return ""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    url = base_url.rstrip("/") + "/chat/completions"

    for attempt in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 429:
                wait = 3 * (attempt + 1)
                log.warning("[%s] 429 rate-limited — waiting %ds (attempt %d/3)", provider_tag, wait, attempt + 1)
                time.sleep(wait)
                continue
            if r.status_code in (500, 502, 503):
                log.warning("[%s] %d server error (attempt %d/3)", provider_tag, r.status_code, attempt + 1)
                time.sleep(2)
                continue
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"].strip()
            if content:
                return content
        except requests.exceptions.Timeout:
            log.warning("[%s] Timeout attempt %d/3 (%ds)", provider_tag, attempt + 1, timeout)
            if attempt < 2:
                time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            log.warning("[%s] Connection error attempt %d/3: %s", provider_tag, attempt + 1, e)
            if attempt < 2:
                time.sleep(1)
        except Exception as e:
            log.warning("[%s] Unexpected error attempt %d/3: %s", provider_tag, attempt + 1, e)
            break

    log.warning("[%s] All attempts failed", provider_tag)
    return ""

"""
JARVIS Web Search — Google Gemini chat provider.

Gemini's REST API doesn't speak the OpenAI /chat/completions shape,
so this module translates {"role", "content"} messages into Gemini's
`contents` + `systemInstruction` format before calling generateContent.
"""
import time
import logging
import requests
from typing import List, Dict
from web_search.config import SearchGateConfig

log = logging.getLogger("JARVIS.WebSearch.LLM.Gemini")

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _to_gemini_payload(messages: List[Dict[str, str]], max_tokens: int) -> dict:
    system_parts = []
    contents = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
        else:
            contents.append({
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            })

    if not contents:
        contents = [{"role": "user", "parts": [{"text": " ".join(system_parts) or "Hello"}]}]
        system_parts = []

    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}
    return payload


def chat_complete(
    messages: List[Dict[str, str]],
    config: SearchGateConfig,
    max_tokens: int = 800,
    timeout: int = 12,
) -> str:
    if not config.gemini_api_key:
        return ""

    url = f"{_BASE}/{config.gemini_model}:generateContent?key={config.gemini_api_key}"
    payload = _to_gemini_payload(messages, max_tokens)

    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            if r.status_code == 429:
                wait = 3 * (attempt + 1)
                log.warning("[GEMINI] 429 rate-limited — waiting %ds (attempt %d/3)", wait, attempt + 1)
                time.sleep(wait)
                continue
            if r.status_code in (500, 502, 503):
                log.warning("[GEMINI] %d server error (attempt %d/3)", r.status_code, attempt + 1)
                time.sleep(2)
                continue
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    return text
        except requests.exceptions.Timeout:
            log.warning("[GEMINI] Timeout attempt %d/3 (%ds)", attempt + 1, timeout)
            if attempt < 2:
                time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            log.warning("[GEMINI] Connection error attempt %d/3: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(1)
        except Exception as e:
            log.warning("[GEMINI] Unexpected error attempt %d/3: %s", attempt + 1, e)
            break

    log.warning("[GEMINI] All attempts failed")
    return ""

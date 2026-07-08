"""
JARVIS Web Search — Provider Circuit Breaker Router.

Decides which providers are available based on configuration and past failures,
putting failing providers into a cooldown phase to avoid slow timeouts.
"""

import time
import threading
import logging
from typing import Dict
from web_search.types import ProviderHealth
from web_search.config import SearchGateConfig

log = logging.getLogger("JARVIS.WebSearch.Router")


class ProviderRouter:
    """Manages provider health with circuit-breaker pattern.
    
    Each provider is gated two ways:
      1. Config presence — is a key/URL actually set?
      2. Circuit breaker — has it failed N times in a row?
         If so, it enters cooldown so a dead API doesn't eat
         a network round-trip on every query.
    """
    
    def __init__(self, config: SearchGateConfig):
        self._config = config
        self._lock = threading.Lock()
        self._health: Dict[str, Dict[str, float]] = {}
    
    def is_available(self, name: str) -> bool:
        return self._config.provider_configured(name) and not self._in_cooldown(name)
    
    def record_success(self, name: str) -> None:
        with self._lock:
            self._health[name] = {"fails": 0, "cooldown_until": 0}
    
    def record_failure(self, name: str) -> None:
        with self._lock:
            h = self._health.setdefault(name, {"fails": 0, "cooldown_until": 0})
            h["fails"] += 1
            if h["fails"] >= self._config.failure_threshold:
                h["cooldown_until"] = time.time() + self._config.cooldown_seconds
                log.warning(
                    "[ROUTER] '%s' failed %dx — cooling down for %ds",
                    name, h["fails"], self._config.cooldown_seconds,
                )
    
    def _in_cooldown(self, name: str) -> bool:
        with self._lock:
            h = self._health.get(name)
            if not h:
                return False
            return time.time() < h.get("cooldown_until", 0)
    
    def get_status(self) -> Dict[str, ProviderHealth]:
        names = [
            "tavily", "serper", "serpapi", "searxng", "newsdata",
            "nvidia", "groq", "openrouter", "together", "gemini", "ollama",
        ]
        out = {}
        for n in names:
            out[n] = ProviderHealth(
                name=n,
                configured=self._config.provider_configured(n),
                in_cooldown=self._in_cooldown(n),
                available=self.is_available(n),
                consecutive_failures=int(self._health.get(n, {}).get("fails", 0)),
                cooldown_until=self._health.get(n, {}).get("cooldown_until", 0),
            )
        return out
    
    def reset(self, name: str) -> None:
        with self._lock:
            self._health.pop(name, None)

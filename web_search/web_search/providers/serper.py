"""
JARVIS Web Search — Serper.dev Google Search Provider.
"""

import logging
from typing import List, Tuple
from urllib.parse import urlparse
import aiohttp

from web_search.types import SearchResult
from web_search.config import SearchGateConfig
from web_search.utils.text import clean_text
from web_search.utils.trust import domain_trust

log = logging.getLogger("JARVIS.WebSearch.Serper")


async def search(
    query: str,
    config: SearchGateConfig,
    *,
    max_results: int = 8,
    **kwargs,
) -> Tuple[List[SearchResult], str]:
    """
    Search Serper.dev. Returns (List[SearchResult], "").
    """
    if not config.serper_api_key:
        return [], ""
    try:
        headers = {
            "X-API-KEY": config.serper_api_key,
            "Content-Type": "application/json",
        }
        body = {
            "q": query,
            "num": max_results,
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://google.serper.dev/search",
                headers=headers,
                json=body,
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = await resp.json()
                results = []
                for r in data.get("organic", [])[:max_results]:
                    url = r.get("link", "")
                    snippet = r.get("snippet", "")
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        snippet=clean_text(snippet)[:400],
                        url=url,
                        content=clean_text(snippet)[:800],
                        source=urlparse(url).hostname or "",
                        date=r.get("date", ""),
                        trust=domain_trust(url),
                    ))
                return results, ""
    except Exception as e:
        log.warning("[SERPER] %s: %s", query[:40], e)
        return [], ""

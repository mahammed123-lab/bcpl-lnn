"""
JARVIS Web Search — SerpAPI (Google) Search Provider.
"""

import logging
from typing import List, Tuple
from urllib.parse import urlparse
import aiohttp

from web_search.types import SearchResult
from web_search.config import SearchGateConfig
from web_search.utils.text import clean_text
from web_search.utils.trust import domain_trust

log = logging.getLogger("JARVIS.WebSearch.SerpApi")


async def search(
    query: str,
    config: SearchGateConfig,
    *,
    max_results: int = 8,
    **kwargs,
) -> Tuple[List[SearchResult], str]:
    """
    Search Google via SerpAPI. Returns (List[SearchResult], "").
    """
    if not config.serpapi_api_key:
        return [], ""
    try:
        params = {
            "q": query,
            "api_key": config.serpapi_api_key,
            "num": max_results,
        }
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://serpapi.com/search.json",
                params=params,
                timeout=aiohttp.ClientTimeout(total=14),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = await resp.json()
                results = []
                for r in data.get("organic_results", [])[:max_results]:
                    url = r.get("link", "")
                    snippet_raw = (
                        r.get("snippet", "")
                        or r.get("rich_snippet", {}).get("top", {}).get(
                            "detected_extensions", {}
                        ).get("description", "")
                        or ""
                    )
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        snippet=clean_text(snippet_raw)[:400],
                        url=url,
                        content=clean_text(snippet_raw)[:800],
                        source=urlparse(url).hostname or "",
                        date=r.get("date", ""),
                        trust=domain_trust(url),
                    ))
                return results, ""
    except Exception as e:
        log.warning("[SERPAPI] %s: %s", query[:40], e)
        return [], ""

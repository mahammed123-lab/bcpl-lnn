"""
JARVIS Web Search — SearXNG Meta-Search Provider.
"""

import logging
from typing import List, Tuple
from urllib.parse import urlparse
import aiohttp

from web_search.types import SearchResult
from web_search.config import SearchGateConfig
from web_search.utils.text import clean_text
from web_search.utils.trust import domain_trust

log = logging.getLogger("JARVIS.WebSearch.Searxng")


async def search(
    query: str,
    config: SearchGateConfig,
    *,
    max_results: int = 8,
    **kwargs,
) -> Tuple[List[SearchResult], str]:
    """
    Search a SearXNG instance. Returns (List[SearchResult], "").
    """
    if not config.searxng_url:
        return [], ""
    try:
        url = config.searxng_url.rstrip("/") + "/search"
        params = {
            "q": query,
            "format": "json",
            "categories": "general",
        }
        headers = {}
        if config.searxng_preferences:
            headers["Cookie"] = f"preferences={config.searxng_preferences}"

        async with aiohttp.ClientSession() as s:
            async with s.get(
                url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = await resp.json()
                results = []
                for r in data.get("results", [])[:max_results]:
                    res_url = r.get("url", "")
                    content = r.get("content", "")
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        snippet=clean_text(content)[:400],
                        url=res_url,
                        content=clean_text(content)[:800],
                        source=urlparse(res_url).hostname or "",
                        date=r.get("publishedDate", ""),
                        trust=domain_trust(res_url),
                    ))
                return results, ""
    except Exception as e:
        log.warning("[SEARXNG] %s: %s", query[:40], e)
        return [], ""

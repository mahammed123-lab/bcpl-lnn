"""
JARVIS Web Search — NewsData.io News Search Provider.
"""

import logging
from typing import List, Tuple
from urllib.parse import urlparse
import aiohttp

from web_search.types import SearchResult
from web_search.config import SearchGateConfig
from web_search.utils.text import clean_text
from web_search.utils.trust import domain_trust

log = logging.getLogger("JARVIS.WebSearch.NewsData")


async def search(
    query: str,
    config: SearchGateConfig,
    *,
    max_results: int = 8,
    **kwargs,
) -> Tuple[List[SearchResult], str]:
    """
    Search NewsData.io. Returns (List[SearchResult], "").
    """
    if not config.newsdata_api_key:
        return [], ""
    try:
        url = config.newsdata_url
        params = {
            "apikey": config.newsdata_api_key,
            "q": query,
            "language": "en",
        }
        async with aiohttp.ClientSession() as s:
            async with s.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = await resp.json()
                results = []
                for r in data.get("results", [])[:max_results]:
                    link = r.get("link", "")
                    content = r.get("description", "") or r.get("content", "") or ""
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        snippet=clean_text(content)[:400],
                        url=link,
                        content=clean_text(content)[:800],
                        source=urlparse(link).hostname or "",
                        date=r.get("pubDate", ""),
                        trust=domain_trust(link),
                    ))
                return results, ""
    except Exception as e:
        log.warning("[NEWSDATA] %s: %s", query[:40], e)
        return [], ""

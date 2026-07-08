"""
JARVIS Web Search — Tavily Search Provider.

Wired into Tavily REST API to fetch organic results and a direct answer.
"""

import logging
from typing import List, Optional, Tuple, Dict, Any
from urllib.parse import urlparse
import aiohttp

from web_search.types import SearchResult
from web_search.config import SearchGateConfig
from web_search.utils.text import clean_text
from web_search.utils.trust import domain_trust

log = logging.getLogger("JARVIS.WebSearch.Tavily")


async def search(
    query: str,
    config: SearchGateConfig,
    *,
    depth: str = "advanced",
    max_results: int = 8,
    days: Optional[int] = None,
) -> Tuple[List[SearchResult], str]:
    """
    Search Tavily. Returns (List[SearchResult], direct_answer).
    """
    try:
        body: Dict[str, Any] = {
            "query": query,
            "search_depth": depth,
            "max_results": max_results,
            "api_key": config.tavily_api_key,
            "include_answer": True,
        }
        if days:
            body["days"] = days
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.tavily.com/search",
                json=body,
                timeout=aiohttp.ClientTimeout(total=18),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                data = await resp.json()
                direct = data.get("answer", "")
                results = []
                for r in data.get("results", []):
                    url = r.get("url", "")
                    results.append(SearchResult(
                        title=r.get("title", ""),
                        snippet=clean_text(r.get("content", ""))[:400],
                        url=url,
                        content=clean_text(r.get("content", ""))[:800],
                        source=urlparse(url).hostname or "",
                        date=r.get("published_date", ""),
                        trust=domain_trust(url),
                    ))
                return results, direct
    except Exception as e:
        log.warning("[TAVILY] %s: %s", query[:40], e)
        return [], ""

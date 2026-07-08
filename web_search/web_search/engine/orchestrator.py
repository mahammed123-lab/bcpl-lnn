"""
JARVIS Web Search — Search Orchestrator.

Triggers provider queries in parallel, dedups and ranks results by trust,
handles fallbacks, and triggers LLM synthesis.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple

from web_search.types import SearchResult, QueryType
from web_search.config import SearchGateConfig
from web_search.providers.router import ProviderRouter
from web_search.providers import tavily, serpapi, serper, searxng, newsdata
from web_search.engine.query import detect_query_type, expand_query
from web_search.engine.session import SearchSession
from web_search.engine.synthesizer import synthesize_results

log = logging.getLogger("JARVIS.WebSearch.Orchestrator")


def _deduplicate(results: List[SearchResult]) -> List[SearchResult]:
    """Remove duplicate URLs, keeping highest-trust version."""
    seen: Dict[str, SearchResult] = {}
    for r in results:
        url = r.url.rstrip("/")
        if url not in seen or r.trust > seen[url].trust:
            seen[url] = r
    return sorted(seen.values(), key=lambda r: r.trust, reverse=True)


async def multi_provider_search(
    query: str,
    config: SearchGateConfig,
    router: ProviderRouter,
    *,
    max_results: int = 8,
    news_days: Optional[int] = None,
) -> Tuple[List[SearchResult], str]:
    """Run all available providers in parallel, merge and deduplicate."""
    tasks = []
    provider_names = []
    
    if router.is_available("tavily"):
        tasks.append(tavily.search(query, config, max_results=max_results, days=news_days))
        provider_names.append("tavily")
    if router.is_available("serper"):
        tasks.append(serper.search(query, config, max_results=max_results))
        provider_names.append("serper")
    if router.is_available("serpapi"):
        tasks.append(serpapi.search(query, config, max_results=max_results))
        provider_names.append("serpapi")
    
    if not tasks:
        log.warning("[ORCHESTRATOR] No search providers available")
        # Last-resort: try SearXNG
        if router.is_available("searxng"):
            results, _ = await searxng.search(query, config, max_results=max_results)
            if results:
                router.record_success("searxng")
            else:
                router.record_failure("searxng")
            return results, ""
        return [], ""
    
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_results: List[SearchResult] = []
    direct_answer = ""
    
    for name, raw in zip(provider_names, raw_results):
        if isinstance(raw, Exception):
            log.warning("[ORCHESTRATOR] %s raised: %s", name, raw)
            router.record_failure(name)
            continue
        results, direct = raw
        if results:
            router.record_success(name)
            all_results.extend(results)
            if direct and not direct_answer:
                direct_answer = direct
        else:
            router.record_failure(name)
    
    # Sequential fallback: if all parallel providers returned empty, try SearXNG
    if not all_results and router.is_available("searxng"):
        log.info("[ORCHESTRATOR] All parallel providers empty — trying SearXNG fallback")
        fallback_results, _ = await searxng.search(query, config, max_results=max_results)
        if fallback_results:
            router.record_success("searxng")
            all_results.extend(fallback_results)
        else:
            router.record_failure("searxng")
    
    deduped = _deduplicate(all_results)
    return deduped[:max_results], direct_answer


async def quick_search(
    query: str,
    config: SearchGateConfig,
    router: ProviderRouter,
    session: Optional[SearchSession] = None,
    *,
    synthesize: bool = True,
) -> Dict[str, Any]:
    """Full search pipeline: detect type → expand → search → synthesize."""
    query_type = detect_query_type(query)
    angles = expand_query(query, query_type)
    
    news_days = 30 if query_type == QueryType.NEWS else None
    primary_query = angles[0]
    
    # Search with primary query
    results, direct = await multi_provider_search(
        primary_query, config, router, news_days=news_days
    )
    
    # If primary returned few results, try additional angles
    if len(results) < 3 and len(angles) > 1:
        for angle in angles[1:]:
            extra, _ = await multi_provider_search(
                angle, config, router, max_results=4, news_days=news_days
            )
            results.extend(extra)
        results = _deduplicate(results)[:8]
    
    # Synthesize
    summary = ""
    if synthesize and results and config.any_llm_configured():
        summary = synthesize_results(query, results, config, router, query_type)
    
    # Store in session
    if session is not None:
        session.store(
            query=query,
            results=results,
            summary=summary,
            direct=direct,
            refined_query=primary_query,
        )
    
    return {
        "query": query,
        "query_type": query_type.value,
        "results": [r.to_dict() for r in results],
        "summary": summary,
        "direct_answer": direct,
        "angles_used": angles,
        "result_count": len(results),
    }

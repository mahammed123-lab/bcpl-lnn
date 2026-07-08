"""
JARVIS Web Search — Providers layer.

Exposes the circuit-breaker SourceRouter and available search backend functions.
"""

from web_search.providers.router import ProviderRouter
from web_search.providers.tavily import search as tavily_search
from web_search.providers.serpapi import search as serpapi_search
from web_search.providers.serper import search as serper_search
from web_search.providers.searxng import search as searxng_search
from web_search.providers.newsdata import search as newsdata_search

__all__ = [
    "ProviderRouter",
    "tavily_search",
    "serpapi_search",
    "serper_search",
    "searxng_search",
    "newsdata_search",
]

"""
JARVIS Web Search — Engine Layer.

Exposes query parsing/expansion, SearchSession, synthesis, and search orchestration.
"""

from web_search.engine.query import detect_query_type, expand_query, extract_subject
from web_search.engine.session import SearchSession
from web_search.engine.synthesizer import call_nvidia, ask_ai, synthesize_results
from web_search.engine.orchestrator import quick_search, multi_provider_search

__all__ = [
    "detect_query_type",
    "expand_query",
    "extract_subject",
    "SearchSession",
    "call_nvidia",
    "ask_ai",
    "synthesize_results",
    "quick_search",
    "multi_provider_search",
]

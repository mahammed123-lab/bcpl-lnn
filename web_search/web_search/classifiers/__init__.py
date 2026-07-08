"""
JARVIS Web Search — Classifiers layer.

Exposes Layer 1 (Regex) and Layer 2 (LLM) classification helpers.
"""

from web_search.classifiers.regex import classify_intent_regex, extract_backtick_query
from web_search.classifiers.llm import llm_needs_search
from web_search.classifiers.pipeline import classify, needs_search

__all__ = [
    "classify_intent_regex",
    "extract_backtick_query",
    "llm_needs_search",
    "classify",
    "needs_search",
]

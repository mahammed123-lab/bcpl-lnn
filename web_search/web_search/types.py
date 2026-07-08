"""
JARVIS Web Search — Shared types, enums, and dataclasses.

Every module in the package imports from here. Keep this file
free of business logic — it defines the vocabulary, not the rules.
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List


class SearchIntent(Enum):
    """What the user wants to do with their query."""
    NEW_SEARCH     = "new_search"
    REFINE         = "refine_search"
    SHOW_RESULTS   = "show_results"
    OPEN_RESULT    = "open_result"
    READ_RESULT    = "read_result"
    VIDEO          = "video"
    SHOW_PANEL     = "show_panel"
    DEEP_RESEARCH  = "deep_research"
    CONVERSATIONAL = "conversational"


class QueryType(Enum):
    """Category of search query — drives expansion strategy."""
    NEWS       = "news"
    PRODUCT    = "product"
    COMPARISON = "comparison"
    PERSON     = "person"
    HOWTO      = "howto"
    TECHNICAL  = "technical"
    GENERAL    = "general"


class Confidence(Enum):
    """How sure the classifier is about its verdict."""
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"

    def __lt__(self, other: "Confidence") -> bool:
        order = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
        return order[self] < order[other]

    def __le__(self, other: "Confidence") -> bool:
        return self == other or self < other


@dataclass(frozen=True)
class ClassifierResult:
    """Immutable result from the search-necessity classification pipeline."""
    needs_search: bool
    confidence: Confidence
    reason: str
    search_query: str
    intent: SearchIntent = SearchIntent.CONVERSATIONAL
    source: str = "regex"   # "regex" | "llm" | "backtick" | "blocklist"


@dataclass
class SearchResult:
    """A single search result from any provider."""
    title:   str   = ""
    snippet: str   = ""
    url:     str   = ""
    content: str   = ""
    source:  str   = ""
    date:    str   = ""
    trust:   float = 1.0

    def to_dict(self) -> dict:
        return {
            "title": self.title, "snippet": self.snippet,
            "url": self.url, "content": self.content,
            "source": self.source, "date": self.date,
            "trust": self.trust,
        }


@dataclass
class ProviderHealth:
    """Health / circuit-breaker state for a single search provider."""
    name:                 str
    configured:           bool  = False
    in_cooldown:          bool  = False
    available:            bool  = False
    consecutive_failures: int   = 0
    cooldown_until:       float = 0.0

"""
JARVIS Web Search — Search Session Management.

Provides thread-safe caching of query results, summaries, and metadata to enable
context-aware refactoring, quick result listings, and back-reference navigation.
"""

import time
import threading
from typing import List
from urllib.parse import urlparse
from web_search.types import SearchResult


class SearchSession:
    def __init__(self, ttl: int = 600):
        self._results: List[SearchResult] = []
        self._query: str = ""
        self._refined_query: str = ""
        self._summary: str = ""
        self._direct_answer: str = ""
        self._timestamp: float = 0.0
        self._ttl: int = ttl
        self._lock = threading.Lock()

    def store(self, query: str, results: List[SearchResult], summary: str,
              direct: str = "", refined_query: str = "") -> None:
        """Cache results in session."""
        with self._lock:
            self._query = query
            self._refined_query = refined_query or query
            self._results = results
            self._summary = summary
            self._direct_answer = direct
            self._timestamp = time.time()

    @property
    def query(self) -> str:
        with self._lock:
            return self._query

    @property
    def summary(self) -> str:
        with self._lock:
            return self._summary

    @property
    def direct_answer(self) -> str:
        with self._lock:
            return self._direct_answer

    @property
    def results(self) -> List[SearchResult]:
        with self._lock:
            return list(self._results)

    def has_results(self) -> bool:
        """Return True if session has results that are not stale."""
        with self._lock:
            return bool(self._results) and (time.time() - self._timestamp) < self._ttl

    def get_top_url(self, index: int = 0) -> str:
        """Retrieve top URL at given index."""
        with self._lock:
            if self._results and index < len(self._results):
                return self._results[index].url
        return ""

    def formatted_list(self) -> str:
        """Format top cached results as readable text."""
        with self._lock:
            if not self._results:
                return "No results cached, sir."
            lines = []
            for i, r in enumerate(self._results[:8], 1):
                host = urlparse(r.url).hostname or ""
                lines.append(f"[{i}] {r.title}\n    {r.snippet[:120]}\n    {host}")
            return "\n\n".join(lines)

    def clear(self) -> None:
        """Reset session."""
        with self._lock:
            self._results = []
            self._query = ""
            self._refined_query = ""
            self._summary = ""
            self._direct_answer = ""
            self._timestamp = 0.0

"""
JARVIS Web Search — Domain trust scoring.

Assigns a multiplier (1.0–2.0) to search results based on how
reliable their source domain is.
"""
from urllib.parse import urlparse

_TRUST_HIGH: frozenset[str] = frozenset({
    "arxiv.org", "nature.com", "science.org", "pubmed", "scholar.google",
    "ieee.org", "acm.org", "openai.com", "anthropic.com", "deepmind.com",
    "mit.edu", "stanford.edu", "berkeley.edu", "wikipedia.org",
})

_TRUST_MEDIUM: frozenset[str] = frozenset({
    "nytimes", "bbc", "reuters", "wired", "techcrunch", "arstechnica",
    "technologyreview", "microsoft.com", "aws.amazon", "huggingface",
    "tomsguide", "gsmarena", "theverge", "engadget", "androidauthority",
    "nvidia.com", "amd.com", "intel.com", "tomshardware",
})


def domain_trust(url: str) -> float:
    """Return a trust multiplier for *url* based on its hostname."""
    host = urlparse(url).hostname or ""
    if any(h in host for h in _TRUST_HIGH):
        return 2.0
    if any(h in host for h in _TRUST_MEDIUM):
        return 1.5
    if host.endswith(".edu") or host.endswith(".gov"):
        return 1.8
    return 1.0

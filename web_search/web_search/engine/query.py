"""
JARVIS Web Search — Query Type and Expansion Module.

Detects query intent types (e.g. news, comparison, technical) and expands
single queries into multiple search engine targets to improve retrieval breadth.
"""

import re
from datetime import datetime
from web_search.types import QueryType

_TECHNICAL_SHORT_KW = ["api", "rag", "llm", "sdk", "orm", "cdn", "cli", "ide"]

_TECHNICAL_LONG_KW = [
    "python", "javascript", "typescript", "golang", "rust", "kotlin",
    "code", "library", "architecture", "algorithm", "exception",
    "parameter", "function", "class", "transformer", "fine-tune",
    "fine tuning", "embedding", "neural network", "inference", "training",
    "deployment", "microservice", "docker", "kubernetes", "database",
    "sql", "nosql", "regex", "recursion", "data structure",
]


def _is_technical(text: str) -> bool:
    t = text.lower()
    for kw in _TECHNICAL_SHORT_KW:
        if re.search(r"\b" + re.escape(kw) + r"\b", t):
            return True
    for kw in _TECHNICAL_LONG_KW:
        if kw in t:
            return True
    return False


def detect_query_type(query: str) -> QueryType:
    """
    Detects the query type to determine expansion strategy.
    """
    t = query.lower()

    # 1. Comparison
    if any(w in t for w in [
        "vs ", "versus", " vs.", "compare", "difference between",
        "better or", "or better", "which is better", "pros and cons",
        "vs\n", " or the ",
    ]):
        return QueryType.COMPARISON

    # 2. News
    news_patterns = [
        "latest", "breaking", "today", "yesterday", "this week", "this month",
        "just released", "just announced", "just launched", "just dropped",
        "announced", "release", "released", "launched", "dropped",
        "new model", "new version", "new ai", "new gpu", "new cpu",
        "update", "2025", "2026", "recently", "upcoming", "preview",
        "revealed", "unveil", "unveiled",
    ]
    if any(w in t for w in news_patterns):
        return QueryType.NEWS

    # 3. Product (guarded by not _is_technical)
    if any(w in t for w in [
        "buy", "best ", "top ", "under ₹", "under $", "under rs",
        "review", "specs", "laptop", "phone", "gpu", "cpu",
        "headphone", "tablet", "monitor", "keyboard", "mouse",
        "earbuds", "camera", "smartwatch", "router", "tv ",
        "budget", "affordable", "premium", "mid-range",
    ]) and not _is_technical(t):
        return QueryType.PRODUCT

    # 4. Person
    if any(w in t for w in [
        "who is", "who are", "who was", "who were",
        "ceo", "founder", "director", "actor", "singer",
        "politician", "scientist", "author", "biography",
    ]):
        return QueryType.PERSON

    # 5. How-to
    if any(w in t for w in [
        "how to", "how do i", "how can i", "how do you",
        "steps to", "tutorial", "guide to", "install",
        "setup", "configure", "enable", "fix ", "repair",
    ]):
        return QueryType.HOWTO

    # 6. Technical
    if _is_technical(t):
        return QueryType.TECHNICAL

    return QueryType.GENERAL


def extract_subject(query: str) -> str:
    """
    Extract the core subject from a verbose query.
    """
    t = query.lower().strip()

    prefixes = [
        r"^did\s+", r"^does\s+", r"^has\s+", r"^have\s+", r"^is\s+there\s+",
        r"^are\s+there\s+", r"^can\s+you\s+(tell\s+me\s+)?", r"^what\s+is\s+the?\s*",
        r"^what\s+are\s+the?\s*", r"^tell\s+me\s+(about\s+)?",
        r"^show\s+me\s+", r"^find\s+",
    ]
    for p in prefixes:
        t = re.sub(p, "", t).strip()

    t = re.sub(r"\b(any|some)\b", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()

    return t[:80] if t else query[:80]


def expand_query(query: str, query_type: QueryType) -> list[str]:
    """
    Generate 2–3 targeted search query angles.
    """
    q = query.strip()
    subj = extract_subject(q)
    yr = str(datetime.now().year)
    angles = [q]

    if query_type == QueryType.NEWS:
        news_verbs = r"\b(release|released|launch|launched|announce|announced|drop|dropped|unveil|unveiled)\b"
        noun_subj = re.sub(news_verbs, "", subj, flags=re.IGNORECASE)
        noun_subj = re.sub(r"\s{2,}", " ", noun_subj).strip()
        angles += [
            f"{noun_subj} {yr}",
            f"{noun_subj} announcement {yr}",
        ]

    elif query_type == QueryType.COMPARISON:
        parts = re.split(
            r"\s+vs\.?\s+|\s+versus\s+|\s+or\s+|\s+compare\s+to\s+",
            q, flags=re.IGNORECASE
        )
        if len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            angles = [q, f"{a} review benchmarks {yr}", f"{b} review benchmarks {yr}"]
        else:
            angles += [f"{subj} review analysis {yr}"]

    elif query_type == QueryType.PRODUCT:
        angles += [
            f"{subj} review {yr} pros cons",
            f"{subj} price specifications comparison",
        ]

    elif query_type == QueryType.PERSON:
        angles += [
            f"{subj} biography career achievements",
            f"{subj} news {yr}",
        ]

    elif query_type == QueryType.HOWTO:
        angles += [
            f"{subj} step by step {yr}",
        ]

    elif query_type == QueryType.TECHNICAL:
        angles += [
            f"{subj} documentation official",
            f"{subj} example tutorial {yr}",
        ]

    else:
        angles += [f"{subj} explained overview"]

    seen = set()
    unique = []
    for a in angles:
        key = a.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(a)

    return unique[:3]

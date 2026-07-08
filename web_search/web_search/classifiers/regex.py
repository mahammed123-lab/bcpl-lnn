"""
JARVIS Web Search — Layer 1 Regex Classifier.

Performs fast, free regex matches to identify conversational queries,
special commands (show results, open link, watch video), and obvious
search queries, assigning confidence levels to avoid LLM calls when possible.
"""

import re
from typing import Optional, List, Tuple
from web_search.types import SearchIntent, Confidence, ClassifierResult

_CONV_BLOCKLIST = [
    r"^(hi|hello|hey|thanks|thank you|ok|okay|sure|yes|no|bye|exit|stop|done|cool|nice|great|alright|fine)[\s!?.]*$",
    r"^what (are|were|is|was) (we|you|i) (doing|discussing|talking|working on|building|saying)$",
    r"^what (topic|topics|subject|thing|things|stuff) (are|were|was) (we|you|i) (discussing|talking|working|doing)$",
    r"^(sorry|excuse me|pardon|my bad|oops)[\s!?.]*$",
    r"^what happened to you$",
    r"^why are (you|u) (talking|saying|acting|behaving)$",
    r"(i think|you are|you're|ur) (broken|not working|weird|confused|wrong)",
    r"^(fix|repair|debug|help) (it|you|yourself|that)[\s!?.]*$",
    r"^tell me (your|the) problem$",
    r"^how (are|r) (you|u)(\?|$)",
    r"^are you (ok|okay|fine|working|there)[\s?]*$",
    r"^what (is|are) (my|your|our) (conversation|discussion|chat) about$",
    r"^(you and i|we) (are|were|have been) (discussing|talking|working)",
    r"^what (did|do) (we|you|i) (say|talk|discuss|do) (before|earlier|just now|last time)$",
    r"^(open notepad|type|write) ",
    r"^(amy|any|what)\s+updates?[\s!?.]*$",
    r"^(anything|what)(s|'s)?\s+new(\s+today)?[\s!?.]*$",
    # Time-of-day greetings ("good morning", "good night", etc.) — always
    # conversational, never search-worthy. Kept separate from the basic
    # greeting list above since they take a required second word.
    r"^good (morning|afternoon|evening|night)[\s!?.]*$",
    # Media/device commands. These are control instructions for JARVIS
    # itself (play/pause music, set a timer/alarm/reminder) and should
    # never trigger a web search or burn an LLM classifier call.
    r"^(play|pause|resume|stop|skip) (some |the |my )?(music|song|track|playlist)[\s!?.]*$",
    r"^(play|pause|resume|stop) (it|that|this)[\s!?.]*$",
    r"^(next|previous) (song|track)[\s!?.]*$",
    r"^(set|start) (a |an )?(timer|alarm|reminder|stopwatch)( for .+)?[\s!?.]*$",
    r"^(cancel|clear|delete|stop) (the |my )?(timer|alarm|reminder|stopwatch)[\s!?.]*$",
]

_SHOW_RESULTS_PATTERNS = [
    r"show (them|those|the results?|me those|me them|me the results?)",
    r"give me (the results?|them|those|what you found)",
    r"(list|display|show) (them|those|results?|the results?|findings?)",
    r"what did you find",
    r"what('s| is| are) (there|the results?|what you found)",
    r"^results?[\s!?.]*$",
]

_OPEN_RESULT_PATTERNS = [
    r"open (it|that|the (first|top|link)|result)",
    r"go (to it|there|to that)",
    r"visit (it|that|the (link|site|page))",
    r"^open it[\s!?.]*$",
]

_READ_PATTERNS = [
    r"(explain|elaborate|expand|summarize|summarise|read) it",
    r"(more details?|tell me more|full article|read more|in depth)",
    r"^(explain|elaborate|read|summarize|summarise)[\s!?.]*$",
]

_VIDEO_PATTERNS = [
    r"^video[\s!?.]*$",
    r"(show|find|open|play|watch|explain).{0,30}(video|youtube)",
    r"youtube (it|for this|for that|search|lookup|what|who|how|where|when|find|show)",
    r"youtube (?:what|who|how|where|when|why|is|are|do|does).{0,30}",
    r"^youtube\s+.+",
    r"watch (it|a video|on youtube)",
    r"in a video|in video|as video|via video",
    r".{0,20}video.{0,10}$",
]

_PANEL_PATTERNS = [
    r"^show panel[\s!?.]*$",
    r"^panel[\s!?.]*$",
    r"(open|show|launch) (the )?(panel|news panel|news|articles?)",
]

_REFINE_PATTERNS = [
    r"^i mean (for|in|under|above|below|with|about|only|just|at|specifically|gaming|budget|work|india|inr)\b",
    r"^but (for|in|under|above|with|specifically|what about)\b",
    r"^under [\d,]+\b",
    r"^above [\d,]+\b",
    r"^below [\d,]+\b",
    r"^for (gaming|work|students?|home|office|business|budget|college)\b",
    r"^in (india|usa|uk|budget|rupees?|inr|dollars?)\b",
    r"^(more|less) (expensive|cheap|budget|premium|affordable)\b",
    r"^(with|having|including) (good|better|best|fast|large|small)\b",
    r"^(only|just) (gaming|budget|premium|portable)\b",
    r"^(what about|how about)\b",
]

_DEEP_TRIGGERS = [
    "comprehensive", "deep dive", "deep research", "research on",
    "detailed analysis", "thorough", "exhaustive", "in-depth",
    "compare and contrast", "pros and cons", "buying guide",
    "complete guide", "everything about", "full breakdown",
]

_SEARCH_STARTERS = [
    "what is", "who is", "who are", "when did", "when was", "where is",
    "how to", "how do", "how does", "how can", "how much", "how many",
    "why is", "why does", "why did", "find", "search", "look up",
    "latest", "recent", "news", "update", "today", "current",
]

# Common English words that end up capitalized purely because they open a
# sentence (question words, modal/aux verbs, imperatives), not because
# they're a proper noun. Used to keep queries like "Can you help me?" or
# "Show me the menu" from being mistaken for "has a proper noun" (e.g.
# a person/product/company name), which otherwise skews toward search.
_COMMON_SENTENCE_WORDS = {
    "can", "could", "would", "should", "will", "shall", "do", "does", "did",
    "is", "are", "was", "were", "have", "has", "had",
    "what", "who", "why", "how", "when", "where", "which", "whose",
    "tell", "show", "give", "let", "please", "get", "find", "set", "play",
    "the", "this", "that", "these", "those", "and", "but", "not", "yes", "no",
}


def _is_proper_noun_like(word: str) -> bool:
    """True if `word` looks like a proper noun (capitalized, not a common
    sentence-starter word that only happens to be capitalized)."""
    w = word.strip(".,!?;:'\"")
    if len(w) <= 2 or not w[0].isupper():
        return False
    return w.lower() not in _COMMON_SENTENCE_WORDS


def _match_any(text: str, patterns: List[str]) -> bool:
    t = text.strip().lower()
    return any(re.search(p, t) for p in patterns)


def extract_backtick_query(text: str) -> Optional[str]:
    """
    Extract a search query wrapped in backticks (e.g. `latest Ryan Gosling movie`).
    Serves as an explicit, high-priority manual override.
    """
    if not text:
        return None
    # Strip multi-line code blocks first
    stripped = re.sub(r"```[\s\S]+?```", "", text)
    match = re.search(r"`([^`]+)`", stripped)
    if match:
        query = match.group(1).strip()
        return query or None
    return None


def _needs_web_search(text: str) -> Tuple[bool, Confidence]:
    """
    Detects if web search is needed based on patterns and proper nouns.
    Returns (needs_search, confidence).
    """
    t = text.lower().strip()

    if _match_any(t, _CONV_BLOCKLIST):
        return False, Confidence.HIGH

    # Business/product terms — combined with a proper noun (a company or
    # product name), these strongly imply a query about current, real-world
    # state (e.g. "Anthropic layoffs", "is Zepto legit").
    company_keywords = [
        "jobs", "job", "careers", "hiring", "vacancy", "opening", "positions",
        "stock", "share", "price", "revenue", "earnings", "quarterly", "fiscal",
        "ceo", "founder", "employee", "employees", "layoff", "layoffs",
        "product", "products", "launch", "launches", "release", "releases",
        "ai model", "ai ", " gpu", "cpu", "chip", "processor", "graphics",
        "real or fake", "fake", "scam", "legit", "legitimate", "review", "reviews",
        "vs code", "vscode", "extension", "plugin", "software", "app",
    ]

    words = text.split()
    has_proper = any(_is_proper_noun_like(w) for w in words)
    has_company_kw = any(kw in t for kw in company_keywords)

    if has_proper and has_company_kw:
        return True, Confidence.HIGH

    # "Is <AI product> real/fake/legit" and "<AI product> extension/plugin"
    # patterns — these are almost always about a specific, current tool.
    words_lower = t.split()
    first_word_has_ai = bool(words_lower) and (words_lower[0] == "ai" or words_lower[0].startswith("ai "))
    if " ai " in t or t.endswith(" ai") or first_word_has_ai:
        if any(w in t for w in ["real", "fake", "scam", "legit", "real or fake", "legit or fake"]):
            return True, Confidence.HIGH
    if " ai" in t and any(w in t for w in ["extension", "vscode", "vs code", "plugin", "app", "software"]):
        return True, Confidence.HIGH

    # Very short queries (<=2 words) with no search-starter phrase and no
    # obvious factual keyword are more likely a fragment/command than a
    # real search ("music please", "lights off") — treat as non-search but
    # only at MEDIUM confidence, so the LLM layer still gets a look.
    if len(t.split()) <= 2 and not any(s in t for s in _SEARCH_STARTERS):
        if not any(kw in t for kw in ["price", "score", "news", "stock", "weather", "jobs", "real", "fake", "space", "launch", "rocket", "satellite", "isro", "nasa", "spacex"]):
            return False, Confidence.MEDIUM

    # Time-sensitive keywords that are almost never answerable from static
    # knowledge alone (scores, prices, elections, current events, etc.).
    live_signals = [
        "today", "yesterday", "this week", "this month", "right now", "currently",
        "latest", "recent", "breaking", "new ", "just released", "just launched",
        "score", "result", "won", "lost", "election", "stock", "price", "market",
        "weather", "news", "update", "release", "version", "2024", "2025", "2026",
        "announced", "launched", "launching", "dropped", "trending", "live", "streaming",
        "space mission", "rocket", "satellite", "spacecraft", "isro", "nasa", "spacex",
    ]
    if any(sig in t for sig in live_signals):
        return True, Confidence.HIGH

    # Question/lookup phrasings that imply the user wants a specific,
    # verifiable fact rather than a general explanation.
    lookup_signals = [
        "who is", "who are", "who was", "who were",
        "where is", "where are", "where was",
        "when did", "when was", "when is",
        "what is the latest", "what's the latest", "whats the latest",
        "is there", "are there",  # covers "is there any/a", "are there any/a", etc.
        "did any", "did the", "did they", "did nvidia", "did openai", "did google", "did microsoft",
        "has any", "has the", "have any", "have the",
        "best ", "top ", "vs ", "versus ", "compare",
        "review", "specs", "features", "alternatives",
        "how to ", "tutorial", "guide", "buy", "price of", "cost of",
        "difference between", "what does",
        "does ", "can ",
        "any jobs", "any job", "any opening", "any position",
        "any new", "any release", "any update", "any announcement",
        "is it real", "is this real", "is it fake", "is this fake",
        "real or fake", "legit or fake", "scam or real",
        "vscode extension", "vs code extension", "chrome extension",
        "plugin available", "extension available", "app available",
        "search for ", "search ", "find ", "look up ", "look for ",
    ]
    if any(sig in t for sig in lookup_signals):
        casual_can = [
            "can you do", "can you help", "can you tell me about yourself",
            "can you hear", "can you see", "can i talk", "can i ask",
            "can you explain yourself", "can you work",
        ]
        if any(cc in t for cc in casual_can):
            return False, Confidence.HIGH
        return True, Confidence.HIGH

    # A named entity (proper noun) paired with an action verb ("did X
    # release", "check Y") suggests a query about that entity's current
    # state — weaker signal than the checks above, so only MEDIUM.
    proper_count = sum(1 for w in words if _is_proper_noun_like(w))
    has_verb = any(v in t for v in [
        "release", "launch", "announce", "update", "drop", "buy", "get", "find",
        "check", "verify", "confirm", "list", "show", "available"
    ])
    if proper_count >= 1 and has_verb:
        return True, Confidence.MEDIUM

    if re.search(r"\b(anything|something|everything)\s+(about|on|related to|regarding)\s+", t):
        return True, Confidence.MEDIUM

    # Timeless/definitional topics — explicitly non-search even if they
    # superficially resemble a "lookup" phrasing.
    static_topics = [
        "what is python", "explain quantum", "define", "meaning of",
        "history of", "origin of", "theory of", "concept of",
    ]
    if any(st in t for st in static_topics):
        return False, Confidence.HIGH

    # If it didn't match any obvious search patterns but is not on the conversational blocklist,
    # it's ambiguous. Return false but with LOW confidence so the LLM can classify it.
    return False, Confidence.LOW


def classify_intent_regex(text: str, has_session: bool = False) -> ClassifierResult:
    """
    Classify the query using regex rules.
    Assigns SearchIntent and confidence.
    """
    t = text.strip().lower()

    # 1. Blocklist check
    if _match_any(t, _CONV_BLOCKLIST):
        return ClassifierResult(
            needs_search=False,
            confidence=Confidence.HIGH,
            reason="matched conversation blocklist",
            search_query="",
            intent=SearchIntent.CONVERSATIONAL,
            source="regex",
        )

    # 2. Command Checks
    if _match_any(t, _PANEL_PATTERNS):
        return ClassifierResult(
            needs_search=False,
            confidence=Confidence.HIGH,
            reason="matched panel command pattern",
            search_query="",
            intent=SearchIntent.SHOW_PANEL,
            source="regex",
        )

    if _match_any(t, _SHOW_RESULTS_PATTERNS):
        intent = SearchIntent.SHOW_RESULTS if has_session else SearchIntent.CONVERSATIONAL
        return ClassifierResult(
            needs_search=False,
            confidence=Confidence.HIGH if has_session else Confidence.MEDIUM,
            reason="matched show results pattern",
            search_query="",
            intent=intent,
            source="regex",
        )

    if _match_any(t, _OPEN_RESULT_PATTERNS):
        intent = SearchIntent.OPEN_RESULT if has_session else SearchIntent.NEW_SEARCH
        needs_search = not has_session
        return ClassifierResult(
            needs_search=needs_search,
            confidence=Confidence.HIGH,
            reason="matched open result pattern",
            search_query=text if needs_search else "",
            intent=intent,
            source="regex",
        )

    if _match_any(t, _VIDEO_PATTERNS):
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.HIGH,
            reason="matched video query pattern",
            search_query=text,
            intent=SearchIntent.VIDEO,
            source="regex",
        )

    if _match_any(t, _READ_PATTERNS):
        intent = SearchIntent.READ_RESULT if has_session else SearchIntent.NEW_SEARCH
        needs_search = not has_session
        return ClassifierResult(
            needs_search=needs_search,
            confidence=Confidence.HIGH,
            reason="matched read content pattern",
            search_query=text if needs_search else "",
            intent=intent,
            source="regex",
        )

    if has_session and _match_any(t, _REFINE_PATTERNS):
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.HIGH,
            reason="matched search refinement pattern",
            search_query=text,
            intent=SearchIntent.REFINE,
            source="regex",
        )

    if any(trigger in t for trigger in _DEEP_TRIGGERS):
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.HIGH,
            reason="matched deep research trigger words",
            search_query=text,
            intent=SearchIntent.DEEP_RESEARCH,
            source="regex",
        )

    # 3. Factual search-necessity checks
    needs_web, confidence = _needs_web_search(text)
    intent = SearchIntent.NEW_SEARCH if needs_web else SearchIntent.CONVERSATIONAL

    return ClassifierResult(
        needs_search=needs_web,
        confidence=confidence,
        reason="evaluated factual indicators",
        search_query=text if needs_web else "",
        intent=intent,
        source="regex",
    )

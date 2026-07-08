"""
JARVIS Web Search — Layer 2 LLM-based Classifier.

Runs when the regex pre-check (Layer 1) cannot confidently decide.
Decoupled from specific API providers via a callable interface.
"""

import re
import json
import logging
from datetime import datetime
from typing import Callable, Dict, Any, List, Optional
from web_search.types import ClassifierResult, Confidence, SearchIntent
from web_search.config import SearchGateConfig

log = logging.getLogger("JARVIS.WebSearch.LLMClassifier")

SEARCH_CLASSIFIER_SYSTEM_PROMPT = """You are a search-necessity classifier for JARVIS, Hussain's personal AI assistant.
You do not answer the user's question. Your only job is to decide whether
answering it requires a live web search, or whether it can be answered
accurately from existing knowledge alone.

CONTEXT
- Today's date: {today_date}
- Your knowledge cutoff: {knowledge_cutoff}
- Anything that could plausibly have changed, been released, updated, or
  happened between your knowledge cutoff and today is a candidate for
  search — even if you feel confident you know the answer.
{regex_hint_block}
DECISION RULE
Set needs_search = true if ANY of these apply:
1. The answer depends on a fact that changes over time (current holder of
   a role/title, latest version/release of a product, current price,
   current score/standings, an ongoing situation, a recent announcement).
2. The question explicitly asks about "latest," "current," "recent,"
   "today," "this week," or references a date at/after your knowledge
   cutoff.
3. You would have to guess a specific number, name, date, or version that
   you are not highly confident is still accurate today.
4. The topic is specific enough (a named person, product, company, event)
   that being wrong would matter, and your knowledge might be stale or
   incomplete.

Set needs_search = false if ALL of these apply:
1. The answer is timeless or extremely slow-changing (math, definitions,
   established history, how something fundamentally works, code syntax,
   general concepts, well-known static facts).
2. You are not relying on any date-sensitive fact to answer.
3. The question is conversational, opinion-based, or about JARVIS/Hussain's
   own prior context rather than the outside world.

When genuinely uncertain, prefer needs_search = true. A wasted search costs
a few seconds; a wrong answer stated with confidence costs trust.

EXAMPLES
Query: "What's the latest NVIDIA GPU?"
{{"needs_search": true, "confidence": "high", "reason": "product releases change after cutoff", "search_query": "latest NVIDIA GPU release"}}

Query: "Who is the current Prime Minister of the UK?"
{{"needs_search": true, "confidence": "high", "reason": "political roles change", "search_query": "current UK Prime Minister"}}

Query: "Explain how binary search works"
{{"needs_search": false, "confidence": "high", "reason": "timeless algorithm concept", "search_query": ""}}

Query: "What's the capital of France?"
{{"needs_search": false, "confidence": "high", "reason": "static geographic fact", "search_query": ""}}

Query: "Is Python 3.13 out yet?"
{{"needs_search": true, "confidence": "medium", "reason": "release status may have changed since cutoff", "search_query": "Python 3.13 release status"}}

Query: "Write me a function to reverse a linked list"
{{"needs_search": false, "confidence": "high", "reason": "stable programming task, no external facts needed", "search_query": ""}}

Query: "How are you doing today?"
{{"needs_search": false, "confidence": "high", "reason": "conversational, not factual", "search_query": ""}}

Query: "What did we talk about earlier?"
{{"needs_search": false, "confidence": "high", "reason": "refers to conversation history, not the web", "search_query": ""}}

OUTPUT
Respond with ONLY valid JSON, no other text, no markdown fences:
{{"needs_search": true or false, "confidence": "high"|"medium"|"low", "reason": "one short clause", "search_query": "a clean minimal query if needs_search is true, else empty string"}}"""


def _build_system_prompt(knowledge_cutoff: str, regex_hint: Optional[ClassifierResult] = None) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    
    if regex_hint is not None:
        hint_block = (
            f"PRE-CHECK HINT\n"
            f"A fast regex pre-check classified this query as:\n"
            f"  needs_search={regex_hint.needs_search}, confidence={regex_hint.confidence.value}, reason=\"{regex_hint.reason}\"\n"
            f"Use this as a weak prior — override it if your analysis disagrees.\n\n"
        )
    else:
        hint_block = ""
        
    return SEARCH_CLASSIFIER_SYSTEM_PROMPT.format(
        today_date=today,
        knowledge_cutoff=knowledge_cutoff,
        regex_hint_block=hint_block,
    )


def llm_needs_search(
    query: str,
    call_llm: Callable[[List[Dict[str, str]]], str],
    config: Optional[SearchGateConfig] = None,
    regex_hint: Optional[ClassifierResult] = None,
) -> ClassifierResult:
    """
    Ask an LLM whether `query` needs a live web search.

    `call_llm` must accept a list of {"role": "system"|"user", "content": str}
    messages and return the model's raw text response.
    """
    knowledge_cutoff = (
        config.knowledge_cutoff
        if config is not None
        else "unknown — treat any date-, version-, price-, or role-sensitive fact as possibly stale"
    )

    system_prompt = _build_system_prompt(knowledge_cutoff, regex_hint=regex_hint)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    try:
        raw = call_llm(messages)
    except Exception as e:
        log.warning(f"[LLM_CLASSIFIER] call_llm failed: {e} — failing open (search)")
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.LOW,
            reason=f"classifier call failed ({e}) — failing open",
            search_query=query,
            intent=SearchIntent.NEW_SEARCH,
            source="llm",
        )

    if not raw:
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.LOW,
            reason="empty classifier response — failing open",
            search_query=query,
            intent=SearchIntent.NEW_SEARCH,
            source="llm",
        )

    cleaned = re.sub(r"```(?:json)?", "", raw).strip("` \n")

    try:
        data = json.loads(cleaned)
        needs_search = bool(data.get("needs_search", True))
        
        conf_str = (data.get("confidence") or "low").lower()
        if conf_str == "high":
            confidence = Confidence.HIGH
        elif conf_str == "medium":
            confidence = Confidence.MEDIUM
        else:
            confidence = Confidence.LOW
            
        reason = data.get("reason", "")
        search_query = (data.get("search_query") or "").strip() or query
        intent = SearchIntent.NEW_SEARCH if needs_search else SearchIntent.CONVERSATIONAL

        return ClassifierResult(
            needs_search=needs_search,
            confidence=confidence,
            reason=reason,
            search_query=search_query,
            intent=intent,
            source="llm",
        )
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        log.warning(f"[LLM_CLASSIFIER] unparseable output: {cleaned[:200]!r} ({e}) — failing open")
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.LOW,
            reason="classifier output unparseable — failing open",
            search_query=query,
            intent=SearchIntent.NEW_SEARCH,
            source="llm",
        )

"""
JARVIS Web Search — Classifier Pipeline Orchestrator.

Combines Layer 1 (Regex) and Layer 2 (LLM) classification.
Handles explicit user backtick overrides and routes ambiguous cases to the LLM.
"""

from typing import Callable, List, Dict, Optional
from web_search.types import SearchIntent, Confidence, ClassifierResult
from web_search.config import SearchGateConfig
from web_search.classifiers.regex import classify_intent_regex, extract_backtick_query
from web_search.classifiers.llm import llm_needs_search


def classify(
    text: str,
    call_llm: Optional[Callable[[List[Dict[str, str]]], str]] = None,
    config: Optional[SearchGateConfig] = None,
    has_session: bool = False,
) -> ClassifierResult:
    """
    Classifies a query using a staged pipeline:
      1. Backtick Override Check (Bypasses LLM, 100% confidence search)
      2. Layer 1: Regex pre-check
         - Matches blocklist/commands -> HIGH confidence non-search, terminates
         - Matches obvious search signals -> HIGH confidence search, terminates
      3. Layer 2: LLM classifier (if regex confidence is MEDIUM/LOW, LLM enabled, call_llm present)
         - Refines the classification with full contextual awareness
      4. Fallback: return regex pre-check result
    """
    # 1. Backtick override check
    backtick_query = extract_backtick_query(text)
    if backtick_query is not None:
        return ClassifierResult(
            needs_search=True,
            confidence=Confidence.HIGH,
            reason="explicit user backtick override",
            search_query=backtick_query,
            intent=SearchIntent.NEW_SEARCH,
            source="backtick",
        )

    # Resolve config if not passed
    cfg = config if config is not None else SearchGateConfig.from_env()

    # 2. Run regex classifier
    regex_res = classify_intent_regex(text, has_session=has_session)

    # If regex is highly confident (e.g. conversational blocklist, commands, strong signals)
    if regex_res.confidence == Confidence.HIGH:
        return regex_res

    # 3. Layer 2: LLM check
    if cfg.llm_classifier_enabled and call_llm is not None:
        return llm_needs_search(
            query=text,
            call_llm=call_llm,
            config=cfg,
            regex_hint=regex_res,
        )

    # 4. Fallback to regex result
    return regex_res


def needs_search(
    text: str,
    call_llm: Optional[Callable[[List[Dict[str, str]]], str]] = None,
    config: Optional[SearchGateConfig] = None,
) -> bool:
    """
    Convenience helper to check if text requires search.
    """
    res = classify(text, call_llm=call_llm, config=config)
    return res.needs_search

import json
import pytest
from web_search.types import SearchIntent, Confidence, ClassifierResult
from web_search.classifiers.regex import classify_intent_regex, extract_backtick_query
from web_search.classifiers.llm import llm_needs_search
from web_search.classifiers.pipeline import classify, needs_search
from web_search.config import SearchGateConfig


class TestBacktickExtraction:
    def test_simple_backtick(self):
        assert extract_backtick_query("search `latest NVIDIA GPU`") == "latest NVIDIA GPU"

    def test_no_backtick(self):
        assert extract_backtick_query("hello world") is None

    def test_triple_backtick_ignored(self):
        assert extract_backtick_query("```python\ncode```") is None

    def test_empty_backtick(self):
        assert extract_backtick_query("``") is None


class TestRegexClassifier:
    def test_conversational_blocked(self):
        for q in ["hi", "hello!", "thanks", "bye", "how are you?"]:
            r = classify_intent_regex(q)
            assert r.intent == SearchIntent.CONVERSATIONAL, f"Failed for: {q}"
            assert not r.needs_search

    def test_search_queries(self):
        for q in ["What's the latest NVIDIA GPU?", "Who is the current CEO of OpenAI?"]:
            r = classify_intent_regex(q)
            assert r.needs_search, f"Should need search: {q}"
            assert r.intent == SearchIntent.NEW_SEARCH

    def test_static_knowledge(self):
        r = classify_intent_regex("Explain how binary search works")
        # May or may not need search, but should not be high-confidence search
        assert isinstance(r, ClassifierResult)

    def test_show_results_with_session(self):
        r = classify_intent_regex("show me the results", has_session=True)
        assert r.intent == SearchIntent.SHOW_RESULTS

    def test_show_results_without_session(self):
        r = classify_intent_regex("show me the results", has_session=False)
        assert r.intent == SearchIntent.CONVERSATIONAL

    def test_video_intent(self):
        r = classify_intent_regex("show me a video about this")
        assert r.intent == SearchIntent.VIDEO

    def test_deep_research(self):
        r = classify_intent_regex("give me a comprehensive deep dive")
        assert r.intent == SearchIntent.DEEP_RESEARCH

    def test_greeting_and_device_commands_blocked(self):
        for q in ["good morning", "good night", "play some music", "pause the music",
                  "set a timer for 5 minutes", "set an alarm", "cancel the timer",
                  "next song"]:
            r = classify_intent_regex(q)
            assert not r.needs_search, f"Should not search: {q}"
            assert r.confidence == Confidence.HIGH, f"Should be HIGH confidence: {q}"
            assert r.intent == SearchIntent.CONVERSATIONAL, f"Failed for: {q}"

    def test_sentence_initial_capital_not_treated_as_proper_noun(self):
        # These start with a capitalized command/question word ("Show",
        # "Tell") that should NOT be mistaken for a proper noun (person/
        # product/company name).
        for q in ["Show me the menu", "Tell me a joke"]:
            r = classify_intent_regex(q)
            assert r.confidence != Confidence.MEDIUM, f"Should not be MEDIUM via false proper-noun match: {q}"

    def test_real_proper_nouns_still_detected(self):
        r = classify_intent_regex("What is the latest Ryan Gosling movie")
        assert r.needs_search
        r2 = classify_intent_regex("is Sundar Pichai still CEO of Google")
        assert r2.needs_search


class TestLLMClassifier:
    def _make_fake_llm(self, response: dict):
        def fake(msgs):
            return json.dumps(response)
        return fake

    def test_needs_search_true(self):
        llm = self._make_fake_llm({
            "needs_search": True, "confidence": "high",
            "reason": "test", "search_query": "test query",
        })
        r = llm_needs_search("test", llm)
        assert r.needs_search is True
        assert r.source == "llm"

    def test_needs_search_false(self):
        llm = self._make_fake_llm({
            "needs_search": False, "confidence": "high",
            "reason": "static", "search_query": "",
        })
        r = llm_needs_search("test", llm)
        assert r.needs_search is False

    def test_fails_open_on_exception(self):
        def bad_llm(msgs):
            raise RuntimeError("boom")
        r = llm_needs_search("test", bad_llm)
        assert r.needs_search is True
        assert r.confidence == Confidence.LOW

    def test_fails_open_on_bad_json(self):
        def bad_json_llm(msgs):
            return "not json at all"
        r = llm_needs_search("test", bad_json_llm)
        assert r.needs_search is True

    def test_fails_open_on_empty(self):
        r = llm_needs_search("test", lambda m: "")
        assert r.needs_search is True


class TestPipeline:
    def test_backtick_override(self):
        r = classify("`latest NVIDIA GPU`")
        assert r.needs_search is True
        assert r.source == "backtick"
        assert r.search_query == "latest NVIDIA GPU"

    def test_conversational_no_llm(self):
        r = classify("hello!")
        assert not r.needs_search
        assert r.intent == SearchIntent.CONVERSATIONAL

    def test_search_no_llm(self):
        r = classify("What's the latest NVIDIA GPU?")
        assert r.needs_search

    def test_needs_search_convenience(self):
        assert needs_search("latest NVIDIA GPU") is True
        assert needs_search("hi") is False

    def test_with_llm(self):
        def fake_llm(msgs):
            return json.dumps({
                "needs_search": True, "confidence": "high",
                "reason": "test", "search_query": "test",
            })
        config = SearchGateConfig(llm_classifier_enabled=True)
        # Even with LLM, high-confidence regex should short-circuit
        r = classify("hello!", call_llm=fake_llm, config=config)
        assert not r.needs_search  # blocklist wins

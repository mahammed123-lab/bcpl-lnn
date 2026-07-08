import pytest
from web_search.types import QueryType, SearchResult
from web_search.engine.query import detect_query_type, expand_query, extract_subject
from web_search.engine.session import SearchSession


class TestQueryType:
    def test_comparison(self):
        assert detect_query_type("iPhone vs Samsung") == QueryType.COMPARISON

    def test_news(self):
        assert detect_query_type("latest NVIDIA announcement") == QueryType.NEWS

    def test_product(self):
        assert detect_query_type("best budget laptop") == QueryType.PRODUCT

    def test_person(self):
        assert detect_query_type("who is the CEO of Google") == QueryType.PERSON

    def test_howto(self):
        assert detect_query_type("how to install Docker") == QueryType.HOWTO

    def test_technical(self):
        assert detect_query_type("what is the best API for payments") == QueryType.TECHNICAL

    def test_general(self):
        assert detect_query_type("what is the meaning of life") == QueryType.GENERAL


class TestQueryExpansion:
    def test_returns_list(self):
        angles = expand_query("latest GPU", QueryType.NEWS)
        assert isinstance(angles, list)
        assert len(angles) >= 2

    def test_deduplicates(self):
        angles = expand_query("test", QueryType.GENERAL)
        assert len(angles) == len(set(a.lower().strip() for a in angles))

    def test_max_three(self):
        angles = expand_query("test vs other test", QueryType.COMPARISON)
        assert len(angles) <= 3


class TestSubjectExtraction:
    def test_strips_prefix(self):
        s = extract_subject("did nvidia release any new AI model")
        assert "nvidia" in s.lower()
        assert not s.lower().startswith("did")

    def test_max_length(self):
        s = extract_subject("x " * 100)
        assert len(s) <= 80


class TestSession:
    def test_empty_session(self):
        s = SearchSession()
        assert not s.has_results()
        assert s.formatted_list() == "No results cached, sir."

    def test_store_and_retrieve(self):
        s = SearchSession()
        results = [SearchResult(title="Test", url="https://example.com")]
        s.store("test", results, "summary")
        assert s.has_results()
        assert s.get_top_url() == "https://example.com"
        assert s.query == "test"
        assert s.summary == "summary"

    def test_clear(self):
        s = SearchSession()
        s.store("q", [SearchResult(title="T")], "s")
        s.clear()
        assert not s.has_results()

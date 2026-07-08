from web_search.config import SearchGateConfig
from web_search.providers.router import ProviderRouter
from web_search.providers import llm_router
from web_search.providers.llm import PROVIDER_MODULES


def _cfg(**overrides):
    cfg = SearchGateConfig()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


class TestConfigLLMHelpers:
    def test_no_llm_configured(self):
        cfg = _cfg()
        assert cfg.any_llm_configured() is False

    def test_single_key_is_enough(self):
        cfg = _cfg(groq_api_key="test-key")
        assert cfg.any_llm_configured() is True
        assert cfg.provider_configured("groq") is True
        assert cfg.provider_configured("nvidia") is False

    def test_priority_list_respects_env_order(self):
        cfg = _cfg(llm_provider_priority="together,groq,nvidia")
        assert cfg.llm_priority_list() == ["together", "groq", "nvidia"]

    def test_priority_list_filters_unknown_names(self):
        cfg = _cfg(llm_provider_priority="groq,bogus,nvidia")
        assert cfg.llm_priority_list() == ["groq", "nvidia"]


class TestLLMRouterFallback:
    def test_falls_through_to_second_configured_provider(self, monkeypatch):
        cfg = _cfg(
            llm_provider_priority="nvidia,groq",
            nvidia_api_key="key1",
            groq_api_key="key2",
        )
        router = ProviderRouter(cfg)

        monkeypatch.setattr(
            PROVIDER_MODULES["nvidia"], "chat_complete",
            lambda messages, config, max_tokens=800, timeout=12: "",
        )
        monkeypatch.setattr(
            PROVIDER_MODULES["groq"], "chat_complete",
            lambda messages, config, max_tokens=800, timeout=12: "groq answered",
        )

        reply = llm_router.call_llm([{"role": "user", "content": "hi"}], cfg, router)
        assert reply == "groq answered"

    def test_returns_empty_when_nothing_configured(self):
        cfg = _cfg()
        router = ProviderRouter(cfg)
        reply = llm_router.call_llm([{"role": "user", "content": "hi"}], cfg, router)
        assert reply == ""

    def test_skips_provider_in_cooldown(self, monkeypatch):
        cfg = _cfg(
            llm_provider_priority="nvidia,groq",
            nvidia_api_key="key1",
            groq_api_key="key2",
            failure_threshold=1,
        )
        router = ProviderRouter(cfg)
        router.record_failure("nvidia")  # threshold=1 -> immediately cooling down

        calls = []

        def nvidia_stub(messages, config, max_tokens=800, timeout=12):
            calls.append("nvidia")
            return "should not be called"

        def groq_stub(messages, config, max_tokens=800, timeout=12):
            calls.append("groq")
            return "groq answered"

        monkeypatch.setattr(PROVIDER_MODULES["nvidia"], "chat_complete", nvidia_stub)
        monkeypatch.setattr(PROVIDER_MODULES["groq"], "chat_complete", groq_stub)

        reply = llm_router.call_llm([{"role": "user", "content": "hi"}], cfg, router)
        assert reply == "groq answered"
        assert calls == ["groq"]

    def test_make_call_llm_closure_works(self, monkeypatch):
        cfg = _cfg(llm_provider_priority="groq", groq_api_key="key")
        router = ProviderRouter(cfg)
        monkeypatch.setattr(
            PROVIDER_MODULES["groq"], "chat_complete",
            lambda messages, config, max_tokens=800, timeout=12: "ok",
        )
        call_llm = llm_router.make_call_llm(cfg, router)
        assert call_llm([{"role": "user", "content": "hi"}]) == "ok"

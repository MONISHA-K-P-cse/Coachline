"""
Pytest coverage for GraniteClient provider selection (item 1): watsonx.ai as
the production path, Ollama Granite as the offline/dev path, and automatic
fallback from watsonx -> Ollama on error. The Ollama call itself is mocked
in every test so this suite runs without a live Ollama daemon or watsonx
credentials.
"""
from ai.agents.granite_client import GraniteClient


def test_ollama_provider_never_calls_watsonx(monkeypatch):
    watsonx_calls = {"count": 0}

    def fake_watsonx(self, prompt):
        watsonx_calls["count"] += 1
        return "should not be reached"

    def fake_ollama(self, prompt):
        return "ollama response"

    monkeypatch.setattr(GraniteClient, "_generate_watsonx", fake_watsonx)
    monkeypatch.setattr(GraniteClient, "_generate_ollama", fake_ollama)

    client = GraniteClient(provider="ollama")
    result = client.generate("hello")

    assert result == "ollama response"
    assert watsonx_calls["count"] == 0


def test_watsonx_provider_used_directly_when_it_succeeds(monkeypatch):
    ollama_calls = {"count": 0}

    def working_watsonx(self, prompt):
        return "watsonx response"

    def fake_ollama(self, prompt):
        ollama_calls["count"] += 1
        return "should not be reached"

    monkeypatch.setattr(GraniteClient, "_generate_watsonx", working_watsonx)
    monkeypatch.setattr(GraniteClient, "_generate_ollama", fake_ollama)

    client = GraniteClient(provider="watsonx")
    result = client.generate("hello")

    assert result == "watsonx response"
    assert ollama_calls["count"] == 0


def test_watsonx_provider_falls_back_to_ollama_on_error(monkeypatch):
    def failing_watsonx(self, prompt):
        raise RuntimeError("simulated watsonx outage")

    def fake_ollama(self, prompt):
        return "fallback response"

    monkeypatch.setattr(GraniteClient, "_generate_watsonx", failing_watsonx)
    monkeypatch.setattr(GraniteClient, "_generate_ollama", fake_ollama)

    client = GraniteClient(provider="watsonx")
    result = client.generate("hello")

    assert result == "fallback response"


def test_watsonx_provider_falls_back_to_ollama_on_timeout(monkeypatch):
    import concurrent.futures

    def timing_out_watsonx(self, prompt):
        raise concurrent.futures.TimeoutError("simulated watsonx timeout")

    def fake_ollama(self, prompt):
        return "fallback response"

    monkeypatch.setattr(GraniteClient, "_generate_watsonx", timing_out_watsonx)
    monkeypatch.setattr(GraniteClient, "_generate_ollama", fake_ollama)

    client = GraniteClient(provider="watsonx")
    result = client.generate("hello")

    assert result == "fallback response"


def test_missing_watsonx_credentials_falls_back_to_ollama(monkeypatch):
    # No WATSONX_API_KEY / WATSONX_PROJECT_ID set -> _get_watsonx_model()
    # raises KeyError immediately, which generate() must catch and recover
    # from rather than propagate.
    monkeypatch.delenv("WATSONX_API_KEY", raising=False)
    monkeypatch.delenv("WATSONX_PROJECT_ID", raising=False)

    def fake_ollama(self, prompt):
        return "fallback response"

    monkeypatch.setattr(GraniteClient, "_generate_ollama", fake_ollama)

    client = GraniteClient(provider="watsonx")
    result = client.generate("hello")

    assert result == "fallback response"


def test_default_ollama_model_is_a_granite_model():
    client = GraniteClient(provider="ollama")
    assert "granite" in client.ollama_model.lower()

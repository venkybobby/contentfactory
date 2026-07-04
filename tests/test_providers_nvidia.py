import pytest

from content_factory.providers import NvidiaEditorialProvider, editorial_provider, source_excerpts


def test_nvidia_provider_requires_environment_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
        NvidiaEditorialProvider()


def test_provider_factory_selects_nvidia(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-only")
    assert isinstance(editorial_provider("nvidia"), NvidiaEditorialProvider)


@pytest.mark.parametrize("url", ["http://example.com", "https://127.0.0.1/private", "https://[::1]/private"])
def test_source_fetcher_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        source_excerpts([url])

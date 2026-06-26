"""Characterization tests for the canonical provider response objects.

See alttprbot/alttprgen/provider_response.py.
"""

from alttprbot.alttprgen.provider_response import ProviderMetadata, ProviderResponse


def make_meta(**overrides):
    kwargs = dict(provider="alttpr", operation="generate", attempt_count=2, latency_ms=1234)
    kwargs.update(overrides)
    return ProviderMetadata(**kwargs)


def test_metadata_to_dict_includes_all_fields():
    meta = make_meta(surface="discord")
    assert meta.to_dict() == {
        "provider": "alttpr",
        "operation": "generate",
        "attempt_count": 2,
        "latency_ms": 1234,
        "surface": "discord",
    }


def test_metadata_to_dict_surface_defaults_to_none():
    assert make_meta().to_dict()["surface"] is None


def test_response_to_dict_minimal_omits_optionals():
    resp = ProviderResponse(
        url="https://alttpr.com/h/ABCDE",
        hash_or_id="ABCDE",
        provider_meta=make_meta(),
    )
    result = resp.to_dict()
    assert result["url"] == "https://alttpr.com/h/ABCDE"
    assert result["hash_or_id"] == "ABCDE"
    assert result["provider_meta"] == make_meta().to_dict()
    # Optional fields are omitted entirely when None.
    assert "code" not in result
    assert "spoiler_url" not in result
    assert "version" not in result


def test_response_to_dict_includes_optionals_when_set():
    resp = ProviderResponse(
        url="https://example/seed",
        hash_or_id="42",
        provider_meta=make_meta(),
        code=["Bow", "Boomerang", "Hookshot"],
        spoiler_url="https://example/spoiler",
        version="1.0.0",
    )
    result = resp.to_dict()
    assert result["code"] == ["Bow", "Boomerang", "Hookshot"]
    assert result["spoiler_url"] == "https://example/spoiler"
    assert result["version"] == "1.0.0"

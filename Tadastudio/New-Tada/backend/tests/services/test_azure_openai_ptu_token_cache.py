"""Tests for the shared PTU OAuth token cache.

These verify that :meth:`AzureOpenAIPTUProvider.get_cached_token` (the new
classmethod exposed for the OCR service) hits and refreshes the process-wide
cache correctly and that the legacy instance wrapper still delegates to it.
"""

from unittest.mock import patch

import pytest

from backend.services.llm_models.providers import azure_openai_ptu as ptu_module
from backend.services.llm_models.providers.azure_openai_ptu import (
    AzureOpenAIPTUProvider,
)


@pytest.fixture(autouse=True)
def _reset_token_cache():
    """Ensure each test starts with an empty token cache."""
    ptu_module._TOKEN_CACHE.clear()
    yield
    ptu_module._TOKEN_CACHE.clear()


def _kwargs(**overrides):
    base = dict(
        token_url="https://gw.example.com/oauth/token",
        client_id="client-abc",
        client_secret="secret-xyz",
        scope="CORP",
        grant_type="client_credentials",
        verify_ssl=False,
        deployment="gpt-4.1",
    )
    base.update(overrides)
    return base


def test_get_cached_token_fetches_and_caches():
    with patch.object(
        AzureOpenAIPTUProvider,
        "_fetch_oauth_token",
        return_value=("tok-1", 3600.0),
    ) as mock_fetch:
        first = AzureOpenAIPTUProvider.get_cached_token(**_kwargs())
        second = AzureOpenAIPTUProvider.get_cached_token(**_kwargs())

    assert first == "tok-1"
    assert second == "tok-1"
    # Cache hit on second call — only one fetch overall.
    assert mock_fetch.call_count == 1
    cache_key = ("https://gw.example.com/oauth/token", "client-abc")
    assert cache_key in ptu_module._TOKEN_CACHE


def test_get_cached_token_refreshes_when_near_expiry():
    # Set a token that's already inside the skew window.
    cache_key = ("https://gw.example.com/oauth/token", "client-abc")
    ptu_module._TOKEN_CACHE[cache_key] = {
        "token": "stale",
        # expires 1 second in the future, well inside the 300 s skew.
        "expires_at": ptu_module.time.time() + 1,
    }

    with patch.object(
        AzureOpenAIPTUProvider,
        "_fetch_oauth_token",
        return_value=("tok-fresh", 3600.0),
    ) as mock_fetch:
        token = AzureOpenAIPTUProvider.get_cached_token(**_kwargs())

    assert token == "tok-fresh"
    assert mock_fetch.call_count == 1


def test_cache_key_partitions_by_url_and_client_id():
    with patch.object(
        AzureOpenAIPTUProvider,
        "_fetch_oauth_token",
        side_effect=[("t-a", 3600.0), ("t-b", 3600.0)],
    ) as mock_fetch:
        a = AzureOpenAIPTUProvider.get_cached_token(**_kwargs(client_id="one"))
        b = AzureOpenAIPTUProvider.get_cached_token(**_kwargs(client_id="two"))

    assert a == "t-a"
    assert b == "t-b"
    assert mock_fetch.call_count == 2


def test_legacy_instance_method_delegates_to_classmethod():
    """The pre-existing agent path uses the instance ``_get_cached_token``."""
    with patch.object(
        AzureOpenAIPTUProvider,
        "get_cached_token",
        return_value="tok-delegated",
    ) as mock_cls:
        provider = AzureOpenAIPTUProvider.__new__(AzureOpenAIPTUProvider)
        result = provider._get_cached_token(**_kwargs())

    assert result == "tok-delegated"
    mock_cls.assert_called_once()
    # Ensure the arguments were forwarded verbatim.
    forwarded = mock_cls.call_args.kwargs
    for key, value in _kwargs().items():
        assert forwarded[key] == value

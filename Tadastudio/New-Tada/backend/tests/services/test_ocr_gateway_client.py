"""Tests for the OCR service's Mashreq gateway (PTU) client path.

Verifies :meth:`GPT4oOCRService._initialize_gateway_client` builds an
``AzureOpenAI`` client with:

* an ``azure_ad_token_provider`` sourced from the shared PTU token cache,
* an ``httpx.Client`` carrying the required gateway headers (``clientid``,
  ``X-USER-ID``, ``Content-Type``),
* the deployment's ``verify_ssl`` flag applied to that http client,
* raises :class:`OCRConfigError` when required fields are missing.
"""

from unittest.mock import patch

import pytest

from backend.services.llm_models.providers import azure_openai_ptu as ptu_module
from backend.services.ocr.exceptions import OCRConfigError
from backend.services.ocr.service import GPT4oOCRService


@pytest.fixture(autouse=True)
def _reset_token_cache():
    ptu_module._TOKEN_CACHE.clear()
    yield
    ptu_module._TOKEN_CACHE.clear()


def _ptu_config(**overrides):
    cfg = {
        "provider": "azure_openai_ptu",
        "model_name": "gpt-4.1",
        "api_key": None,
        "endpoint": "https://gw.example.com/mashreqtest/sandbox/azureopenai_msapi/v2",
        "api_version": "2024-02-01",
        "use_managed_identity": False,
        "managed_identity_client_id": None,
        "token_url": "https://gw.example.com/mashreqtest/sandbox/oauth-v6/oauth2/token",
        "client_id": "client-abc",
        "client_secret": "secret-xyz",
        "oauth_scope": "CORP",
        "grant_type": "client_credentials",
        "x_user_id": "TADAUSER",
        "verify_ssl": False,
    }
    cfg.update(overrides)
    return cfg


def _build_service(model_config):
    """Bypass ``__init__`` to isolate the client-init logic under test."""
    svc = GPT4oOCRService.__new__(GPT4oOCRService)
    svc.model_config = model_config
    svc.detail = "high"
    svc.config = None
    return svc


@pytest.mark.parametrize(
    "missing_field",
    ["token_url", "client_id", "client_secret", "endpoint"],
)
def test_gateway_client_missing_required_fields_raises(missing_field):
    cfg = _ptu_config(**{missing_field: None})
    svc = _build_service(cfg)
    with pytest.raises(OCRConfigError) as exc_info:
        svc._initialize_gateway_client()
    assert missing_field in str(exc_info.value)


def test_gateway_client_uses_shared_ptu_token_cache_and_headers():
    cfg = _ptu_config()
    svc = _build_service(cfg)

    with (
        patch(
            "backend.services.llm_models.providers.azure_openai_ptu."
            "AzureOpenAIPTUProvider._fetch_oauth_token",
            return_value=("tok-live", 3600.0),
        ) as mock_fetch,
        patch("backend.services.ocr.service.AzureOpenAI") as mock_azure,
        patch("httpx.Client") as mock_httpx_cls,
    ):
        mock_httpx_cls.return_value = object()
        svc._initialize_gateway_client()

        # httpx client built with verify=False (verify_ssl was False in config)
        # and the three required gateway headers.
        httpx_kwargs = mock_httpx_cls.call_args.kwargs
        assert httpx_kwargs["verify"] is False
        headers = httpx_kwargs["headers"]
        assert headers["clientid"] == "client-abc"
        assert headers["X-USER-ID"] == "TADAUSER"
        assert headers["Content-Type"] == "application/json"

        # AzureOpenAI called with a token provider (callable), api_key=None,
        # the gateway endpoint, and our custom httpx client.
        azure_kwargs = mock_azure.call_args.kwargs
        assert azure_kwargs["api_key"] is None
        assert azure_kwargs["api_version"] == "2024-02-01"
        assert azure_kwargs["azure_endpoint"] == cfg["endpoint"]
        assert callable(azure_kwargs["azure_ad_token_provider"])
        assert azure_kwargs["http_client"] is mock_httpx_cls.return_value

        # Invoking the token provider should return the fetched token and hit
        # the shared PTU cache (only one underlying fetch).
        provider_fn = azure_kwargs["azure_ad_token_provider"]
        assert provider_fn() == "tok-live"
        assert provider_fn() == "tok-live"
        assert mock_fetch.call_count == 1


def test_gateway_client_defaults_x_user_id_and_scope_when_absent():
    cfg = _ptu_config(x_user_id=None, oauth_scope=None, grant_type=None)
    svc = _build_service(cfg)

    with (
        patch(
            "backend.services.llm_models.providers.azure_openai_ptu."
            "AzureOpenAIPTUProvider._fetch_oauth_token",
            return_value=("tok", 3600.0),
        ) as mock_fetch,
        patch("backend.services.ocr.service.AzureOpenAI") as mock_azure,
        patch("httpx.Client") as mock_httpx_cls,
    ):
        mock_httpx_cls.return_value = object()
        svc._initialize_gateway_client()
        # Trigger the token provider to make the fetch happen with the
        # defaulted scope/grant_type.
        mock_azure.call_args.kwargs["azure_ad_token_provider"]()

    headers = mock_httpx_cls.call_args.kwargs["headers"]
    assert headers["X-USER-ID"] == "TADAUSER"

    fetch_kwargs = mock_fetch.call_args.kwargs
    assert fetch_kwargs["scope"] == "CORP"
    assert fetch_kwargs["grant_type"] == "client_credentials"


def test_initialize_client_routes_ptu_provider_to_gateway_branch():
    cfg = _ptu_config()
    svc = _build_service(cfg)
    sentinel = object()
    with patch.object(
        GPT4oOCRService,
        "_initialize_gateway_client",
        return_value=sentinel,
    ) as mock_gw:
        client = svc._initialize_client()
    assert client is sentinel
    mock_gw.assert_called_once_with()


def test_initialize_client_azure_api_key_branch_unchanged():
    """Regression: non-PTU azure deployments still use the api-key path."""
    cfg = {
        "provider": "azure",
        "model_name": "gpt-4o",
        "api_key": "sk-real",
        "endpoint": "https://myacct.openai.azure.com",
        "api_version": "2024-02-01",
        "use_managed_identity": False,
        "managed_identity_client_id": None,
    }
    svc = _build_service(cfg)

    with patch("backend.services.ocr.service.AzureOpenAI") as mock_azure:
        svc._initialize_client()

    kwargs = mock_azure.call_args.kwargs
    assert kwargs["api_key"] == "sk-real"
    assert kwargs["azure_endpoint"] == cfg["endpoint"]
    assert "azure_ad_token_provider" not in kwargs
    assert "http_client" not in kwargs


def test_initialize_client_azure_managed_identity_branch_unchanged():
    """Regression: managed-identity path still fires for azure w/o api_key."""
    cfg = {
        "provider": "azure",
        "model_name": "gpt-4o",
        "api_key": None,
        "endpoint": "https://myacct.openai.azure.com",
        "api_version": "2024-02-01",
        "use_managed_identity": True,
        "managed_identity_client_id": "mi-1",
    }
    svc = _build_service(cfg)

    with (
        patch("backend.services.ocr.service.AzureOpenAI") as mock_azure,
        patch.object(
            GPT4oOCRService,
            "_get_token_provider",
            return_value=lambda: "mi-token",
        ) as mock_mi,
    ):
        svc._initialize_client()

    mock_mi.assert_called_once_with("mi-1")
    kwargs = mock_azure.call_args.kwargs
    assert kwargs["azure_endpoint"] == cfg["endpoint"]
    assert callable(kwargs["azure_ad_token_provider"])
    # No custom http_client added on the MI path.
    assert "http_client" not in kwargs


def test_initialize_client_openai_branch_unchanged():
    cfg = {
        "provider": "openai",
        "model_name": "gpt-4o",
        "api_key": "sk-openai",
        "base_url": "https://api.openai.com/v1",
    }
    svc = _build_service(cfg)

    with patch("backend.services.ocr.service.OpenAI") as mock_openai:
        svc._initialize_client()

    kwargs = mock_openai.call_args.kwargs
    assert kwargs["api_key"] == "sk-openai"
    assert kwargs["base_url"] == "https://api.openai.com/v1"

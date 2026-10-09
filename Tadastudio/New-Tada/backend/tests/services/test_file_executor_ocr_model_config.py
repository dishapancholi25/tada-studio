"""Tests for the OCR model_config assembled by ``FileNodeExecutor._extract_with_ocr``.

These verify that the executor:

1. Preserves ``azure_openai_ptu`` as the provider (does *not* collapse it to
   ``azure``) and copies all PTU-specific settings/credentials.
2. Still collapses generic ``azure_openai`` to ``azure`` for backward
   compatibility with the pre-existing OCR client init.
3. Passes through non-azure providers verbatim with a ``base_url`` mapping.

We patch out the OCR service and the extraction factory so no real network or
disk work happens — the assertions are purely on the ``model_config`` dict
constructed by the executor.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.services.nodes.executors.file import FileNodeExecutor


def _make_config(**overrides):
    """Build a minimal :class:`FileReadConfig`-shaped stand-in."""
    cfg = SimpleNamespace(
        model_deployment_id="deploy-1",
        ocr_prompt=None,
        doc_type="auto",
        max_pages=None,
        chunk_by_page=False,
        max_tokens_per_request=4000,
        skip_on_error=False,
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def _run(deployment_dict, file_ext=".pdf"):
    """Invoke ``_extract_with_ocr`` and return the model_config passed to OCR."""
    executor = FileNodeExecutor()
    config = _make_config()

    captured = {}

    class _FakeOCR:
        def __init__(self, model_config=None, detail="high"):
            captured["model_config"] = model_config
            captured["detail"] = detail

        def process_pdf(self, **kwargs):
            return {"success": True, "content": "ok"}

        def process_docx(self, **kwargs):
            return {"success": True, "content": "ok"}

        def process_image(self, **kwargs):
            return {"success": True, "content": "ok"}

        def process_file(self, **kwargs):
            return {"success": True, "content": "ok"}

    fake_service = MagicMock()
    fake_service.get_deployment.return_value = deployment_dict

    with (
        patch(
            "backend.services.nodes.executors.file.ModelDeploymentService",
            return_value=fake_service,
        ),
        patch(
            "backend.services.document_extraction.get_extraction_provider",
            return_value="model_ocr",
        ),
        patch(
            "backend.services.document_extraction.factory._read_db_setting",
            return_value="high",
        ),
        patch(
            "backend.services.ocr.GPT4oOCRService",
            _FakeOCR,
        ),
    ):
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            executor._extract_with_ocr("/tmp/fake.pdf", file_ext, config)
        )

    return captured["model_config"]


@pytest.fixture(autouse=True)
def _event_loop():
    """Provide a fresh event loop for each test to avoid asyncio pollution."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()


def test_ptu_provider_preserved_and_settings_copied():
    deployment = {
        "provider": "azure_openai_ptu",
        "display_name": "Mashreq Gateway GPT-4.1",
        "name": "gw-gpt41",
        "model_name": "gpt-4.1",
        "settings": {
            "endpoint": "https://gw.example.com/mashreqtest/sandbox/azureopenai_msapi/v2",
            "deployment_name": "gpt-4.1",
            "api_version": "2024-02-01",
            "token_url": "https://gw.example.com/mashreqtest/sandbox/oauth-v6/oauth2/token",
            "client_id": "client-abc",
            "oauth_scope": "CORP",
            "grant_type": "client_credentials",
            "x_user_id": "MYUSER",
            "verify_ssl": False,
        },
        "credentials": {
            "client_secret": "secret-xyz",
            # PTU deployments generally have no api_key.
        },
    }

    model_config = _run(deployment)

    assert model_config["provider"] == "azure_openai_ptu"
    assert model_config["model_name"] == "gpt-4.1"
    assert model_config["endpoint"] == deployment["settings"]["endpoint"]
    assert model_config["api_version"] == "2024-02-01"
    # PTU-specific fields must be present.
    assert model_config["token_url"] == deployment["settings"]["token_url"]
    assert model_config["client_id"] == "client-abc"
    assert model_config["client_secret"] == "secret-xyz"
    assert model_config["oauth_scope"] == "CORP"
    assert model_config["grant_type"] == "client_credentials"
    assert model_config["x_user_id"] == "MYUSER"
    assert model_config["verify_ssl"] is False
    # api_key stays None (PTU has none).
    assert model_config["api_key"] is None


def test_ptu_defaults_scope_and_grant_and_user_id():
    """When the deployment omits scope/grant/x_user_id, defaults kick in."""
    deployment = {
        "provider": "azure_openai_ptu",
        "model_name": "gpt-4.1",
        "settings": {
            "endpoint": "https://gw.example.com/v2",
            "deployment_name": "gpt-4.1",
            "token_url": "https://gw.example.com/token",
            "client_id": "client-abc",
        },
        "credentials": {"client_secret": "secret"},
    }

    model_config = _run(deployment)

    assert model_config["oauth_scope"] == "CORP"
    assert model_config["grant_type"] == "client_credentials"
    assert model_config["x_user_id"] == "TADAUSER"
    # verify_ssl defaults to False when omitted.
    assert model_config["verify_ssl"] is False


def test_plain_azure_openai_still_collapses_to_azure_with_api_key():
    """Regression: non-PTU azure deployments still route to the api-key path."""
    deployment = {
        "provider": "azure_openai",
        "model_name": "gpt-4o",
        "settings": {
            "endpoint": "https://myacct.openai.azure.com",
            "deployment_name": "gpt-4o",
            "api_version": "2024-02-01",
            "use_managed_identity": False,
        },
        "credentials": {"api_key": "sk-real"},
    }

    model_config = _run(deployment)

    assert model_config["provider"] == "azure"
    assert model_config["api_key"] == "sk-real"
    assert model_config["endpoint"] == deployment["settings"]["endpoint"]
    # PTU fields should NOT leak into non-PTU configs.
    assert "token_url" not in model_config
    assert "client_secret" not in model_config
    assert "oauth_scope" not in model_config
    assert "x_user_id" not in model_config


def test_openai_provider_passes_through_with_base_url():
    """Regression: plain openai provider gets base_url, not the azure branch."""
    deployment = {
        "provider": "openai",
        "model_name": "gpt-4o",
        "settings": {
            "base_url": "https://api.openai.com/v1",
            "deployment_name": "gpt-4o",
        },
        "credentials": {"api_key": "sk-openai"},
    }

    model_config = _run(deployment)

    assert model_config["provider"] == "openai"
    assert model_config["base_url"] == "https://api.openai.com/v1"
    assert model_config["api_key"] == "sk-openai"
    assert "endpoint" not in model_config
    assert "token_url" not in model_config

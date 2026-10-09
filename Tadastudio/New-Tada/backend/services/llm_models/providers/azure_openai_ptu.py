"""Azure OpenAI PTU provider implementation.

This provider targets Azure OpenAI deployments fronted by the Mashreq API
gateway. The gateway differs from standard Azure OpenAI in three important
ways:

1. **Authentication** uses an OAuth2 ``client_credentials`` flow. A bearer
   token is fetched from a token endpoint and passed as ``azure_ad_token``
   (no API key is used).
2. **Custom gateway headers** (``clientid``, ``X-USER-ID``, ``Content-Type``)
   must accompany every request; these are attached to the underlying
   ``httpx`` client.
3. **Streaming is not supported.** LangGraph drives execution with streaming
   internally, so a non-streaming chat-model variant is used that performs a
   single non-streaming call and yields the result as one chunk.

The gateway typically presents an internal-CA certificate, so TLS
verification defaults to disabled (configurable via the ``verify_ssl``
deployment setting).

Endpoint mapping (from the gateway cURL examples)::

    token_url   = https://.../mashreqtest/sandbox/oauth-v6/oauth2/token
    endpoint    = https://.../mashreqtest/sandbox/azureopenai_msapi/v2
    deployment  = gpt-4.1
    # client builds: {endpoint}/openai/deployments/{deployment}/chat/completions

Configuration is read from the deployment record at runtime:
- credentials (encrypted): ``client_secret`` (and optionally ``client_id``)
- settings (plain): ``token_url``, ``oauth_scope``, ``x_user_id``,
  ``grant_type``, ``client_id``, ``endpoint`` (gateway base),
  ``deployment_name``, ``api_version``, ``verify_ssl``
"""

import logging
import threading
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
import urllib3
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import AzureChatOpenAI

from backend.models.workflow.configs.llm import LLMConfig
from ..constants import LOG_PREFIX
from ..exceptions import CredentialMissingError, ManagedIdentityError
from .azure_openai import AzureOpenAIProvider

logger = logging.getLogger(__name__)

# Refresh the token this many seconds before its declared expiry.
_TOKEN_EXPIRY_SKEW_SECONDS = 300
# Fallback lifetime when the token endpoint omits ``expires_in``.
_DEFAULT_TOKEN_TTL_SECONDS = 3600
# Timeout for the OAuth token request.
_TOKEN_REQUEST_TIMEOUT_SECONDS = 30

# Process-wide token cache keyed by (token_url, client_id). Mirrors the
# singleton token-manager pattern used by other gateway integrations so a
# single token is shared across LLM builds rather than re-fetched each time.
_TOKEN_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_TOKEN_CACHE_LOCK = threading.Lock()


class NonStreamingAzureChatOpenAI(AzureChatOpenAI):
    """AzureChatOpenAI variant that never streams over the wire.

    The Mashreq gateway does not support streaming responses, but LangGraph
    invokes models with ``astream`` internally. With ``streaming=False`` the
    ``ainvoke``/``_agenerate`` path already performs a single non-streaming
    call; this override ensures explicit ``astream`` calls also degrade to a
    single non-streaming chunk instead of attempting to stream.
    """

    # LangGraph may try to set this; we ignore streaming regardless.
    stream_usage: bool = False

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Perform a non-streaming call and yield the result as one chunk."""
        kwargs.pop("stream", None)
        kwargs.pop("stream_options", None)

        result = await self._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )
        generation = result.generations[0]
        message = generation.message

        message_chunk = AIMessageChunk(
            content=message.content or "",
            additional_kwargs=dict(getattr(message, "additional_kwargs", {}) or {}),
            response_metadata=dict(getattr(message, "response_metadata", {}) or {}),
            tool_calls=list(getattr(message, "tool_calls", []) or []),
            usage_metadata=getattr(message, "usage_metadata", None),
            id=getattr(message, "id", None),
        )
        chunk = ChatGenerationChunk(
            message=message_chunk,
            generation_info=generation.generation_info,
        )

        if run_manager:
            await run_manager.on_llm_new_token(chunk.text, chunk=chunk)

        yield chunk


class AzureOpenAIPTUProvider(AzureOpenAIProvider):
    """Azure OpenAI provider for the Mashreq gateway (OAuth + non-streaming).

    Reuses the base :class:`AzureOpenAIProvider` for endpoint resolution and
    parameter transformation, overriding only authentication, the chat-model
    class, and the constructor params (custom http client, non-streaming).
    """

    _chat_model_cls = NonStreamingAzureChatOpenAI

    def _describe_key_source(self, config: LLMConfig) -> str:
        """Return a non-sensitive label describing the auth source."""
        return "oauth_client_credentials"

    def _customize_constructor_params(
        self, constructor_params: Dict[str, Any], config: LLMConfig
    ) -> None:
        """Force non-streaming and attach a gateway http client with headers."""
        settings = getattr(config, "config", None) or {}
        creds = getattr(config, "credentials", None) or {}

        client_id = settings.get("client_id") or creds.get("client_id")
        x_user_id = settings.get("x_user_id") or "TADAUSER"
        verify_ssl_raw = settings.get("verify_ssl", False)
        verify_ssl = verify_ssl_raw in (True, "true", "True", "TRUE") if isinstance(verify_ssl_raw, (str, bool)) else bool(verify_ssl_raw)

        if not verify_ssl:
            urllib3.disable_warnings()

        headers = {
            "clientid": client_id or "",
            "X-USER-ID": x_user_id,
            "Content-Type": "application/json",
        }
        timeout = float(getattr(config, "timeout", None) or 60.0)

        constructor_params["streaming"] = False
        constructor_params["http_client"] = httpx.Client(
            verify=verify_ssl, timeout=timeout, headers=headers
        )
        constructor_params["http_async_client"] = httpx.AsyncClient(
            verify=verify_ssl, timeout=timeout, headers=headers
        )

    def _get_auth_params(self, config: LLMConfig, deployment: str) -> Dict[str, Any]:
        """Resolve the OAuth bearer token as an Azure AD token.

        Returns:
            Auth kwargs for AzureChatOpenAI: a static ``azure_ad_token`` and an
            explicit ``api_key=None`` to prevent the SDK using a fallback key.
        """
        creds = getattr(config, "credentials", None) or {}
        settings = getattr(config, "config", None) or {}

        client_id = settings.get("client_id") or creds.get("client_id")
        client_secret = creds.get("client_secret")
        token_url = settings.get("token_url") or creds.get("token_url")
        scope = settings.get("oauth_scope") or settings.get("scope") or "CORP"
        grant_type = settings.get("grant_type") or "client_credentials"
        verify_ssl_raw = settings.get("verify_ssl", False)
        verify_ssl = verify_ssl_raw in (True, "true", "True", "TRUE") if isinstance(verify_ssl_raw, (str, bool)) else bool(verify_ssl_raw)

        if not client_id or not client_secret:
            raise CredentialMissingError(
                "Azure OpenAI PTU requires client_id and client_secret"
            )
        if not token_url:
            raise CredentialMissingError(
                "Azure OpenAI PTU requires token_url in deployment settings"
            )

        token = self._get_cached_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            grant_type=grant_type,
            verify_ssl=verify_ssl,
            deployment=deployment,
        )

        return {"azure_ad_token": token, "api_key": None}

    def _get_cached_token(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
        grant_type: str,
        verify_ssl: bool,
        deployment: Optional[str],
    ) -> str:
        """Instance wrapper delegating to :meth:`get_cached_token`."""
        return self.get_cached_token(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            grant_type=grant_type,
            verify_ssl=verify_ssl,
            deployment=deployment,
        )

    @classmethod
    def get_cached_token(
        cls,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
        grant_type: str,
        verify_ssl: bool,
        deployment: Optional[str],
    ) -> str:
        """Return a valid cached token, refreshing it shortly before expiry.

        Exposed as a classmethod so other subsystems (e.g. the OCR service)
        can reuse the same process-wide token cache without instantiating a
        provider.
        """
        cache_key = (token_url, client_id)
        now = time.time()

        cached = _TOKEN_CACHE.get(cache_key)
        if cached and now < cached["expires_at"] - _TOKEN_EXPIRY_SKEW_SECONDS:
            return cached["token"]

        with _TOKEN_CACHE_LOCK:
            cached = _TOKEN_CACHE.get(cache_key)
            now = time.time()
            if cached and now < cached["expires_at"] - _TOKEN_EXPIRY_SKEW_SECONDS:
                return cached["token"]

            token, ttl = cls._fetch_oauth_token(
                token_url=token_url,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
                grant_type=grant_type,
                verify_ssl=verify_ssl,
                deployment=deployment,
            )
            _TOKEN_CACHE[cache_key] = {
                "token": token,
                "expires_at": time.time() + ttl,
            }
            return token

    @staticmethod
    def _fetch_oauth_token(
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
        grant_type: str,
        verify_ssl: bool,
        deployment: Optional[str],
    ) -> Tuple[str, float]:
        """Request a bearer token from the OAuth token endpoint.

        Returns:
            Tuple of (access_token, ttl_seconds).

        Raises:
            ManagedIdentityError: If the token request fails or is malformed.
        """
        if not verify_ssl:
            urllib3.disable_warnings()

        try:
            response = httpx.post(
                token_url,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": grant_type,
                    "scope": scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=_TOKEN_REQUEST_TIMEOUT_SECONDS,
                verify=verify_ssl,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.error(
                "%s Failed to acquire OAuth token from %s (deployment=%s): %s",
                LOG_PREFIX,
                token_url,
                deployment,
                exc,
            )
            raise ManagedIdentityError(
                "Azure OpenAI PTU configured for OAuth client credentials but "
                "failed to acquire a token. Verify token_url, client_id, "
                "client_secret, and scope."
            ) from exc

        access_token = payload.get("access_token")
        if not access_token:
            raise ManagedIdentityError(
                "OAuth token endpoint response did not contain an access_token"
            )

        try:
            ttl = float(payload.get("expires_in", _DEFAULT_TOKEN_TTL_SECONDS))
        except (TypeError, ValueError):
            ttl = float(_DEFAULT_TOKEN_TTL_SECONDS)

        logger.info(
            "%s Acquired OAuth token for Azure OpenAI PTU (deployment=%s, ttl=%ss)",
            LOG_PREFIX,
            deployment,
            int(ttl),
        )
        return access_token, ttl

    def validate(self, config: LLMConfig) -> list[str]:
        """Validate Azure OpenAI PTU configuration."""
        errors: list[str] = []

        creds = getattr(config, "credentials", None) or {}
        settings = getattr(config, "config", None) or {}

        if not (settings.get("client_id") or creds.get("client_id")):
            errors.append("Azure OpenAI PTU requires client_id")
        if not creds.get("client_secret"):
            errors.append("Azure OpenAI PTU requires client_secret in credentials")
        if not (settings.get("token_url") or creds.get("token_url")):
            errors.append("Azure OpenAI PTU requires token_url in deployment settings")

        endpoint = (
            settings.get("endpoint")
            or settings.get("azure_endpoint")
            or settings.get("base_url")
            or settings.get("api_base")
        )
        if not endpoint:
            errors.append(
                "Azure OpenAI PTU requires an endpoint (gateway base URL) in settings"
            )

        return errors

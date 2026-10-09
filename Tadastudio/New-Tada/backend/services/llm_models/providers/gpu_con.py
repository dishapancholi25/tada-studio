"""GPU CON provider implementation.

Same OAuth client_credentials + token-cache flow as ``azure_openai_ptu``, but
for gateways that are OpenAI-compatible (plain ``/chat/completions``, no
Azure ``api-version``/``/openai/deployments`` URL convention) rather than
Azure-OpenAI-shaped. All connection details (token_url, endpoint, headers)
come from deployment settings/credentials at runtime; nothing is hardcoded.

Configuration (mirrors azure_openai_ptu):
- credentials (encrypted): ``client_secret`` (and optionally ``client_id``)
- settings (plain): ``token_url``, ``oauth_scope``, ``x_user_id``,
  ``grant_type``, ``client_id``, ``endpoint`` (base URL up to the deployment,
  e.g. ``.../deployments/{model}``, no ``/chat/completions`` suffix),
  ``verify_ssl``
"""

from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_openai import ChatOpenAI

from backend.models.workflow.configs.llm import LLMConfig
from ..exceptions import CredentialMissingError
from .azure_openai_ptu import AzureOpenAIPTUProvider
from .base import LLMProvider


class NonStreamingChatOpenAI(ChatOpenAI):
    """ChatOpenAI that does one non-streaming call and yields it as a single chunk.

    The gateway omits token usage from streamed deltas, so streaming loses
    usage_metadata; a single non-streaming response carries the full usage block.
    """

    stream_usage: bool = False

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        kwargs.pop("stream", None)
        kwargs.pop("stream_options", None)
        result = await self._agenerate(
            messages, stop=stop, run_manager=run_manager, **kwargs
        )
        generation = result.generations[0]
        message = generation.message
        chunk = ChatGenerationChunk(
            message=AIMessageChunk(
                content=message.content or "",
                additional_kwargs=dict(getattr(message, "additional_kwargs", {}) or {}),
                response_metadata=dict(getattr(message, "response_metadata", {}) or {}),
                tool_calls=list(getattr(message, "tool_calls", []) or []),
                usage_metadata=getattr(message, "usage_metadata", None),
                id=getattr(message, "id", None),
            ),
            generation_info=generation.generation_info,
        )
        if run_manager:
            await run_manager.on_llm_new_token(chunk.text, chunk=chunk)
        yield chunk


class GPUConProvider(LLMProvider):
    """OpenAI-compatible gateway behind OAuth client_credentials (e.g. Mashreq msgpuai-api)."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        """Create a ChatOpenAI instance pointed at the gateway's OpenAI-compatible endpoint."""
        settings = getattr(config, "config", None) or {}
        creds = getattr(config, "credentials", None) or {}

        endpoint = (
            settings.get("endpoint")
            or settings.get("base_url")
            or settings.get("api_base")
        )
        if not endpoint:
            raise CredentialMissingError("GPU CON requires an endpoint (gateway base URL) in settings")

        verify_ssl_raw = settings.get("verify_ssl", False)
        verify_ssl = (
            verify_ssl_raw in (True, "true", "True", "TRUE")
            if isinstance(verify_ssl_raw, (str, bool))
            else bool(verify_ssl_raw)
        )

        # Reuses the shared PTU token cache; token fetch/refresh logic is unchanged.
        token = AzureOpenAIPTUProvider.get_cached_token(
            token_url=settings.get("token_url") or creds.get("token_url"),
            client_id=settings.get("client_id") or creds.get("client_id"),
            client_secret=creds.get("client_secret"),
            scope=settings.get("oauth_scope") or settings.get("scope") or "CORP",
            grant_type=settings.get("grant_type") or "client_credentials",
            verify_ssl=verify_ssl,
            deployment=config.model_name,
        )

        constructor_params: Dict[str, Any] = {
            "model": config.model_name,
            "base_url": endpoint,
            "api_key": token,
            "timeout": config.timeout,
            "http_client": httpx.Client(
                verify=verify_ssl, timeout=float(config.timeout or 60.0)
            ),
            "http_async_client": httpx.AsyncClient(
                verify=verify_ssl, timeout=float(config.timeout or 60.0)
            ),
            "default_headers": {
                "ClientId": settings.get("client_id") or creds.get("client_id") or "",
                "X-USER-ID": settings.get("x_user_id") or "TADAUSER",
            },
        }
        if config.temperature is not None:
            constructor_params["temperature"] = config.temperature
        if config.max_tokens is not None:
            constructor_params["max_tokens"] = config.max_tokens
        if config.top_p is not None:
            constructor_params["top_p"] = config.top_p

        if "enable_thinking" in settings:  # extra_body, not model_kwargs: avoids unexpected-kwarg error on create()
            constructor_params["extra_body"] = {"enable_thinking": bool(settings["enable_thinking"])}

        return NonStreamingChatOpenAI(**constructor_params)

    def validate(self, config: LLMConfig) -> list[str]:
        """Validate GPU CON configuration."""
        errors: list[str] = []

        creds = getattr(config, "credentials", None) or {}
        settings = getattr(config, "config", None) or {}

        if not (settings.get("client_id") or creds.get("client_id")):
            errors.append("GPU CON requires client_id")
        if not creds.get("client_secret"):
            errors.append("GPU CON requires client_secret in credentials")
        if not (settings.get("token_url") or creds.get("token_url")):
            errors.append("GPU CON requires token_url in deployment settings")

        endpoint = (
            settings.get("endpoint")
            or settings.get("base_url")
            or settings.get("api_base")
        )
        if not endpoint:
            errors.append("GPU CON requires an endpoint (gateway base URL) in settings")

        return errors

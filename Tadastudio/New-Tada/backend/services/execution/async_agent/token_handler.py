"""Token counting handler for async agent execution.

This module handles token counting for inputs and outputs, including
extraction of token metadata from various LLM response formats.
"""

from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

from backend.services.config import get_logger
from backend.services.token_counting import get_token_counter

from .models import TokenCounts
from .utils import safe_dict_get


# Get logger for this module
token_handler_logger = get_logger("async_agent.token_handler")


class TokenHandler:
    """Handles token counting and metadata extraction.

    This class provides methods for counting tokens in messages and
    extracting token usage information from LLM responses, supporting
    multiple metadata formats from different LLM providers.
    """

    def __init__(self):
        """Initialize the token handler."""
        self.logger = token_handler_logger
        self.token_counter = None

    def _get_token_counter(self):
        """Lazy load token counter.

        Returns:
            Token counter instance
        """
        if self.token_counter is None:
            self.token_counter = get_token_counter()
        return self.token_counter

    def count_input_tokens(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
    ) -> TokenCounts:
        """Count tokens in input messages.

        Args:
            messages: List of messages to count
            model_name: Model identifier for accurate counting

        Returns:
            TokenCounts with input_tokens populated
        """
        try:
            token_counter = self._get_token_counter()

            if not token_counter:
                self.logger.warning("[TOKEN] Token counter not available")
                return TokenCounts(model=model_name)

            # Count tokens using the counter
            result = token_counter.count_messages(messages)
            input_tokens = result.get("total", 0)

            self.logger.debug(f"[TOKEN] Input tokens: {input_tokens}")

            return TokenCounts(
                input_tokens=input_tokens,
                total_tokens=input_tokens,
                model=model_name,
            )

        except Exception as e:
            self.logger.warning(
                f"[TOKEN] Failed to count input tokens: {str(e)}",
                exc_info=True,
            )
            return TokenCounts(model=model_name)

    def extract_token_metadata(
        self,
        response: AIMessage,
        input_counts: Optional[TokenCounts] = None,
    ) -> TokenCounts:
        """Extract token usage from LLM response metadata.

        Tries multiple metadata sources in order of preference:
        1. usage_metadata (preferred, clean format)
        2. response_metadata.token_usage (fallback)
        3. Manual counting (last resort)

        Args:
            response: AI message response from LLM
            input_counts: Previously counted input tokens (for fallback)

        Returns:
            TokenCounts with complete usage information
        """
        if not isinstance(response, AIMessage):
            self.logger.debug(
                "[TOKEN] Response is not AIMessage, cannot extract metadata"
            )
            return input_counts or TokenCounts()

        counts = input_counts or TokenCounts()

        try:
            # Try usage_metadata first (preferred format)
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                self._extract_from_usage_metadata(response.usage_metadata, counts)
                self.logger.debug(
                    f"[TOKEN] Extracted from usage_metadata: {counts.dict()}"
                )
            elif hasattr(response, "response_metadata") and response.response_metadata:
                # Fallback to response_metadata
                token_usage = response.response_metadata.get("token_usage")
                if token_usage:
                    self._extract_from_token_usage(token_usage, counts)
                    self.logger.debug(
                        f"[TOKEN] Extracted from response_metadata: {counts.dict()}"
                    )
            else:
                # Last resort: manual counting
                self.logger.debug(
                    "[TOKEN] No metadata available, using manual counting"
                )
                self._manual_count_output(response, counts)

            # Extract LLM response metadata (finish_reason, model_version, etc.)
            self._extract_response_metadata(response, counts)

            return counts

        except Exception as e:
            self.logger.warning(
                f"[TOKEN] Failed to extract token metadata: {str(e)}",
                exc_info=True,
            )
            return counts

    def _extract_from_usage_metadata(
        self,
        usage_metadata: dict,
        counts: TokenCounts,
    ) -> None:
        """Extract token counts from usage_metadata.

        Args:
            usage_metadata: Usage metadata dict from response
            counts: TokenCounts to populate (modified in place)
        """
        counts.input_tokens = usage_metadata.get("input_tokens", counts.input_tokens)
        counts.output_tokens = usage_metadata.get("output_tokens", 0)
        counts.total_tokens = usage_metadata.get(
            "total_tokens",
            counts.input_tokens + counts.output_tokens,
        )

    def _extract_from_token_usage(
        self,
        token_usage: dict,
        counts: TokenCounts,
    ) -> None:
        """Extract token counts from token_usage metadata.

        Args:
            token_usage: Token usage dict from response_metadata
            counts: TokenCounts to populate (modified in place)
        """
        # Different providers use different keys
        counts.input_tokens = safe_dict_get(
            token_usage, "prompt_tokens", "input_tokens", default=counts.input_tokens
        )
        counts.output_tokens = safe_dict_get(
            token_usage, "completion_tokens", "output_tokens", default=0
        )
        counts.total_tokens = safe_dict_get(
            token_usage,
            "total_tokens",
            default=counts.input_tokens + counts.output_tokens,
        )

    def _extract_response_metadata(
        self,
        response: AIMessage,
        counts: TokenCounts,
    ) -> None:
        """Extract LLM response metadata (finish_reason, model_version, etc.).

        Reads from response_metadata which most LLM providers populate with
        additional information about the response.

        Args:
            response: AI message response from LLM
            counts: TokenCounts to populate metadata on (modified in place)
        """
        resp_meta = getattr(response, "response_metadata", None)
        if not resp_meta or not isinstance(resp_meta, dict):
            return

        metadata = {}

        # finish_reason: why the LLM stopped generating
        finish_reason = resp_meta.get("finish_reason")
        if finish_reason:
            metadata["finish_reason"] = finish_reason

        # model_name/model: the actual model version used by the provider
        model_version = resp_meta.get("model_name") or resp_meta.get("model")
        if model_version:
            metadata["model_version"] = model_version

        # system_fingerprint: provider-specific build identifier
        system_fingerprint = resp_meta.get("system_fingerprint")
        if system_fingerprint:
            metadata["system_fingerprint"] = system_fingerprint

        # time_to_first_token: TTFT in milliseconds (captured during streaming)
        ttft = resp_meta.get("time_to_first_token")
        if ttft is not None:
            metadata["time_to_first_token"] = ttft

        if metadata:
            counts.metadata = metadata

    def _manual_count_output(
        self,
        response: AIMessage,
        counts: TokenCounts,
    ) -> None:
        """Manually count output tokens.

        Args:
            response: AI message to count
            counts: TokenCounts to populate (modified in place)
        """
        token_counter = self._get_token_counter()

        if not token_counter:
            self.logger.warning("[TOKEN] Cannot manually count - no token counter")
            return

        try:
            result = token_counter.count_messages([response])
            output_tokens = result.get("total", 0)

            counts.output_tokens = output_tokens
            counts.total_tokens = counts.input_tokens + output_tokens

            self.logger.debug(f"[TOKEN] Manual output count: {output_tokens}")

        except Exception as e:
            self.logger.warning(
                f"[TOKEN] Manual counting failed: {str(e)}",
                exc_info=True,
            )

    def initialize_counts(self, llm: Optional[BaseChatModel] = None) -> TokenCounts:
        """Initialize empty token counts with model name.

        Args:
            llm: LLM instance to extract model name from

        Returns:
            Empty TokenCounts with model name set
        """
        model_name = None
        if llm:
            candidate = getattr(llm, "model_name", None) or getattr(llm, "model", None)
            if isinstance(candidate, str):
                model_name = candidate

        return TokenCounts(model=model_name)

"""LLM builder for async agent execution.

This module handles building and configuring LLM instances for agent execution,
including model deployment integration and configuration enrichment.
"""

from functools import wraps
from typing import TYPE_CHECKING, Any, Optional

from langchain_core.language_models import BaseChatModel

from backend.models.workflow import AgentConfig, LLMConfig
from backend.services.config import get_logger
from backend.services.evaluation.eval_context import is_evaluation_context

from .exceptions import LLMBuildError

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService


# Get logger for this module
llm_builder_logger = get_logger("async_agent.llm_builder")


class AsyncLLMBuilder:
    """Builds LLM instances asynchronously for agent execution.

    This class handles the complexities of LLM instantiation including
    configuration validation, model deployment integration, and managed
    identity support.
    """

    def __init__(
        self,
        llm_factory: "LLMFactory",
        model_service: "ModelDeploymentService",
    ):
        """Initialize the LLM builder.

        Args:
            llm_factory: Factory for creating LLM instances
            model_service: Service for model deployment management
        """
        self.llm_factory = llm_factory
        self.model_service = model_service
        self.logger = llm_builder_logger

    async def build_llm(
        self,
        agent_config: AgentConfig,
        agent_name: str = "unknown",
    ) -> BaseChatModel:
        """Build an LLM instance asynchronously.

        Uses the same pattern as synchronous agent execution to support
        model deployments and managed identity.

        Args:
            agent_config: Agent configuration containing LLM settings
            agent_name: Name of the agent (for logging)

        Returns:
            Configured LLM instance

        Raises:
            LLMBuildError: If LLM construction fails
        """
        try:
            self.logger.info(f"[LLM-BUILDER] Building LLM for agent: {agent_name}")

            # Get LLM config from agent config
            llm_config = agent_config.llm_config

            if not llm_config:
                raise LLMBuildError(
                    f"Agent {agent_name} has no LLM configuration",
                    agent_name=agent_name,
                )

            # Convert dict to LLMConfig if needed
            if isinstance(llm_config, dict):
                self.logger.debug(
                    f"[LLM-BUILDER] Converting dict to LLMConfig for {agent_name}"
                )
                llm_config = LLMConfig(**llm_config)

            # Enrich config with model deployment settings
            self.logger.debug(f"[LLM-BUILDER] Enriching LLM config for {agent_name}")
            enriched_config = self.model_service.enrich_llm_config(llm_config)

            # Create LLM instance using factory
            self.logger.debug(f"[LLM-BUILDER] Creating LLM instance for {agent_name}")
            llm_instance = self.llm_factory.create_llm_instance(enriched_config)

            if not llm_instance or not llm_instance.llm:
                raise LLMBuildError(
                    f"LLM factory returned invalid instance for {agent_name}",
                    agent_name=agent_name,
                )

            llm = llm_instance.llm

            # Log model information
            model_name = getattr(llm, "model_name", None)
            if not isinstance(model_name, str):
                model_name = "unknown"
            self.logger.info(
                f"[LLM-BUILDER] Successfully built LLM for {agent_name} (model: {model_name})"
            )

            # When running inside an evaluation context, wrap the LLM's
            # ainvoke/agenerate to route through the bounded dispatch queue
            # so cross-run provider bursts are throttled.
            if is_evaluation_context():
                llm = self._wrap_with_dispatch_queue(llm, agent_name)

            return llm

        except LLMBuildError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Wrap other exceptions
            error_msg = f"Failed to build LLM for agent {agent_name}: {str(e)}"
            self.logger.error(f"[LLM-BUILDER] {error_msg}", exc_info=True)
            raise LLMBuildError(error_msg, agent_name=agent_name) from e

    def _wrap_with_dispatch_queue(
        self, llm: BaseChatModel, agent_name: str
    ) -> BaseChatModel:
        """Wrap an LLM so its async invocations are submitted via the dispatch queue.

        This ensures evaluation-context LLM calls go through the bounded queue,
        providing process-level backpressure across concurrent evaluation runs.

        Args:
            llm: The original LLM instance.
            agent_name: Agent name (for logging).

        Returns:
            The same LLM instance with ``ainvoke`` and ``agenerate`` wrapped.
        """
        from backend.services.evaluation.llm_dispatch_queue import (
            get_llm_dispatch_queue,
        )

        original_ainvoke = llm.ainvoke
        original_agenerate = llm.agenerate

        @wraps(original_ainvoke)
        async def _queued_ainvoke(*args: Any, **kwargs: Any) -> Any:
            queue = get_llm_dispatch_queue()
            return await queue.submit(original_ainvoke(*args, **kwargs))

        @wraps(original_agenerate)
        async def _queued_agenerate(*args: Any, **kwargs: Any) -> Any:
            queue = get_llm_dispatch_queue()
            return await queue.submit(original_agenerate(*args, **kwargs))

        object.__setattr__(llm, "ainvoke", _queued_ainvoke)
        object.__setattr__(llm, "agenerate", _queued_agenerate)

        self.logger.info(
            f"[LLM-BUILDER] Wrapped LLM for {agent_name} with evaluation dispatch queue"
        )
        return llm

    def get_model_name(self, llm: BaseChatModel) -> Optional[str]:
        """Extract model name from LLM instance.

        Args:
            llm: LLM instance

        Returns:
            Model name if available, None otherwise
        """
        candidate = getattr(llm, "model_name", None) or getattr(llm, "model", None)
        return candidate if isinstance(candidate, str) else None

"""Giskard integration adapter for external evaluation scans.

Provides a non-fatal wrapper around the Giskard library. When the
``giskard`` package is not installed the adapter returns a placeholder
result so that the scoring pipeline is never blocked.
"""

from typing import Any, Dict, Optional

from backend.services.config import get_logger

logger = get_logger("evaluation.giskard_adapter")


class GiskardEvaluationAdapter:
    """Adapter for running Giskard evaluation scans."""

    async def scan(
        self,
        target_id: Optional[str],
        target_type: str,
        actual_output: Optional[str],
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run a Giskard scan against the target.

        This is a best-effort integration. If the ``giskard`` package is
        not installed or an error occurs, a safe fallback dict is
        returned instead of raising.

        Args:
            target_id: Identifier of the evaluation target.
            target_type: One of ``"agent"``, ``"model"``, ``"tool"``,
                ``"workflow"``.
            actual_output: The output produced by the target.
            config: Giskard-specific configuration from the run snapshot.

        Returns:
            Dict with ``status`` and ``findings`` keys, or ``None``.
        """
        try:
            import giskard  # noqa: F401

            logger.info(
                "Giskard package available — running scan for target_type=%s, target_id=%s",
                target_type,
                target_id,
            )
            # Placeholder: full implementation will use giskard.scan()
            # once the package is installed and configured.
            return {"status": "giskard_available", "findings": []}

        except ImportError:
            logger.debug("Giskard package not installed; skipping external evaluation")
            return {"status": "giskard_not_installed", "findings": []}

        except Exception as e:
            logger.warning("Giskard scan failed: %s", e)
            return {"status": "error", "error": str(e), "findings": []}

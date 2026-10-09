"""Narrow compatibility shim kept for the provider content-filter edge case.

Only `select_first_active_config` remains — it is used by a single inline
import in AsyncAgentExecutor to supply a single GuardrailsConfig to
`GuardrailCheckpoint.report_prebuilt_violations()`.

TODO: Remove once report_prebuilt_violations() accepts a pipeline list.
"""

import logging
from typing import List, Optional

from backend.models.workflow.configs.guardrails import GuardrailsConfig

logger = logging.getLogger(__name__)


def select_first_active_config(
    pipeline: List[GuardrailsConfig],
) -> Optional[GuardrailsConfig]:
    """Return the first enabled, non-disabled config from a pipeline."""
    for cfg in pipeline:
        if cfg.enabled and cfg.enforcement_mode != "disabled":
            return cfg
    return None

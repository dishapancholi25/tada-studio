"""Shared utility for resolving API endpoint references in node configs.

Used by both the HTTP action executor and the agent tool creator to
resolve an endpoint_id into a full configuration, merging saved endpoint
defaults with node-level overrides.
"""

from typing import Any, Dict, Optional

from backend.services.config import get_logger

logger = get_logger("api_endpoint.resolver")


def resolve_endpoint_config(
    node_config: Dict[str, Any], user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Resolve endpoint_id to a full config, merging with node-level overrides.

    The saved endpoint provides base values; any non-empty values set
    directly on the node config take precedence.

    Args:
        node_config: The HTTP request node configuration dict.
        user_id: The executing user's ID for endpoint visibility checks.

    Returns:
        Merged configuration dict, or original node_config if no endpoint_id
        or resolution fails.
    """
    endpoint_id = node_config.get("endpoint_id")
    if not endpoint_id:
        return node_config

    try:
        from backend.services.api_endpoint import get_api_endpoint_service
        from backend.services.database import get_db

        with get_db() as db:
            service = get_api_endpoint_service()
            base_config = service.get_endpoint_config_dict(
                db, endpoint_id, user_id=user_id
            )

        if not base_config:
            logger.warning(
                f"API endpoint {endpoint_id} not found, using node config only"
            )
            return node_config

        # Merge: node-level non-empty values override endpoint defaults
        merged = {**base_config}
        _empty = (None, "", {}, [])
        for key, value in node_config.items():
            if key == "endpoint_id":
                continue
            if value not in _empty:
                merged[key] = value

        return merged

    except Exception as e:
        logger.error(f"Failed to resolve API endpoint {endpoint_id}: {e}")
        return node_config

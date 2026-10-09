"""Wrapper for ms-fabric-mcp-server with OAuth token injection.

When the ``FABRIC_ACCESS_TOKEN`` environment variable is set, this wrapper
monkey-patches the upstream ``FabricClient._setup_credential`` method so
that the MCP server uses the pre-obtained OAuth token instead of
``DefaultAzureCredential``.

When ``FABRIC_SQL_TOKEN`` is also set, the wrapper patches
``FabricSQLService._get_token_bytes`` so that SQL queries use a token
scoped to ``https://database.windows.net`` (a different audience than the
REST API).

If neither env var is set, the upstream behaviour is preserved and
``DefaultAzureCredential`` is used (e.g. ``az login`` for local dev).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class StaticTokenCredential:
    """A minimal credential that returns a fixed access token.

    Implements the same interface as ``azure.identity.DefaultAzureCredential``
    — specifically the ``get_token(*scopes)`` method that returns an
    ``AccessToken``-like object.
    """

    def __init__(self, token: str) -> None:
        self._token = token

    def get_token(self, *scopes: str, **kwargs: Any):  # noqa: ARG002
        """Return the static token wrapped in an AccessToken namedtuple."""
        from azure.core.credentials import AccessToken

        # Set expiry 1 hour from now; the real token lifetime is managed
        # by the OAuth handler which refreshes before expiry.
        return AccessToken(self._token, int(time.time()) + 3600)


def _patch_fabric_client() -> None:
    """Monkey-patch FabricClient to use a static token credential."""
    token = os.environ.get("FABRIC_ACCESS_TOKEN", "").strip()
    if not token:
        return

    logger.info("FABRIC_ACCESS_TOKEN found — patching FabricClient to use delegated token")

    try:
        from ms_fabric_mcp_server.client.http_client import FabricClient
    except ImportError:
        logger.error("ms-fabric-mcp-server is not installed — cannot patch")
        return

    credential = StaticTokenCredential(token)

    _original_setup = FabricClient._setup_credential

    def _patched_setup(self: Any) -> None:  # noqa: ARG001
        self._credential = credential

    FabricClient._setup_credential = _patched_setup
    logger.info("FabricClient._setup_credential patched successfully")


def _patch_sql_service() -> None:
    """Monkey-patch FabricSQLService._get_token_bytes to use a static SQL token."""
    token = os.environ.get("FABRIC_SQL_TOKEN", "").strip()
    if not token:
        return

    logger.info("FABRIC_SQL_TOKEN found — patching FabricSQLService for SQL auth")

    try:
        from ms_fabric_mcp_server.services.sql import FabricSQLService
    except ImportError:
        logger.warning("FabricSQLService not available — SQL patch skipped")
        return

    import struct
    from itertools import chain, repeat

    # Pre-compute the ODBC token bytes once
    token_bytes = bytes(token, "UTF-8")
    token_bytes = bytes(chain.from_iterable(zip(token_bytes, repeat(0))))
    token_bytes = struct.pack("<i", len(token_bytes)) + token_bytes

    def _patched_get_token_bytes(self: Any) -> bytes:  # noqa: ARG001
        return token_bytes

    FabricSQLService._get_token_bytes = _patched_get_token_bytes
    logger.info("FabricSQLService._get_token_bytes patched successfully")


def _normalize_notebook_content(content: dict) -> dict:
    """Normalise notebook JSON so Fabric's API accepts it.

    Fixes two common issues produced by LLMs:

    1. ``source`` must be a **list of strings** (one per line, each line
       ending with ``\\n`` except possibly the last).  LLMs often produce a
       single string with embedded ``\\n``.
    2. ``nbformat`` / ``nbformat_minor`` must be **top-level** keys, not
       nested inside ``metadata``.
    """
    import copy

    content = copy.deepcopy(content)

    # Ensure nbformat at top level
    if "nbformat" not in content:
        meta = content.get("metadata", {})
        content["nbformat"] = meta.pop("nbformat", 4)
        content["nbformat_minor"] = meta.pop("nbformat_minor", 5)

    # Normalise cell sources to list-of-lines
    for cell in content.get("cells", []):
        src = cell.get("source")
        if src is None:
            continue
        if isinstance(src, str):
            # Split into lines, preserving trailing \n on each line
            lines = src.split("\n")
            cell["source"] = [
                line + "\n" if i < len(lines) - 1 else line
                for i, line in enumerate(lines)
            ]
        elif isinstance(src, list) and len(src) == 1 and isinstance(src[0], str):
            # Single-element array with embedded newlines — same fix
            text = src[0]
            lines = text.split("\n")
            cell["source"] = [
                line + "\n" if i < len(lines) - 1 else line
                for i, line in enumerate(lines)
            ]

    return content


def _patch_notebook_service() -> None:
    """Monkey-patch FabricNotebookService.create_notebook to normalise content."""
    try:
        from ms_fabric_mcp_server.services.notebook import FabricNotebookService
    except ImportError:
        return

    _original_create = FabricNotebookService.create_notebook

    def _patched_create(self: Any, *args: Any, **kwargs: Any):
        # Normalise positional or keyword notebook_content
        if "notebook_content" in kwargs and kwargs["notebook_content"] is not None:
            kwargs["notebook_content"] = _normalize_notebook_content(kwargs["notebook_content"])
        elif len(args) >= 3 and args[2] is not None:
            args = list(args)
            args[2] = _normalize_notebook_content(args[2])
            args = tuple(args)
        return _original_create(self, *args, **kwargs)

    FabricNotebookService.create_notebook = _patched_create
    logger.info("FabricNotebookService.create_notebook patched for content normalisation")


def run() -> None:
    """Patch credentials (if needed) and start the MCP server."""
    _patch_fabric_client()
    _patch_sql_service()
    _patch_notebook_service()

    from ms_fabric_mcp_server.server import create_fabric_server

    server = create_fabric_server()
    server.run()

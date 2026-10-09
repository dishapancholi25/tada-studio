"""Runtime references for large file content.

This module lets FILE_READ nodes expose a compact token to LLM-facing prompts
while keeping the original file payload available to runtime tools.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.services.config import get_logger


logger = get_logger("file_content_references")

REFERENCE_TTL_SECONDS = 60 * 60 * 2
MAX_REFERENCES = 256
REFERENCE_TOKEN_PATTERN = re.compile(r"\{\{file_content_ref:([a-f0-9]{32})\}\}")
BARE_REFERENCE_KEY_PATTERN = re.compile(r"^[a-f0-9]{32}$")


@dataclass
class FileContentReference:
    """Stored file content for a runtime-only reference token."""

    token: str
    content: str
    created_at: float
    execution_id: Optional[str] = None
    node_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


_references: Dict[str, FileContentReference] = {}
_lock = threading.Lock()


def register_file_content_reference(
    content: str,
    *,
    execution_id: Optional[str] = None,
    node_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Register file content and return a compact LLM-safe token."""

    _prune_expired_references()
    key = uuid.uuid4().hex
    token = f"{{{{file_content_ref:{key}}}}}"
    reference = FileContentReference(
        token=token,
        content=content,
        created_at=time.time(),
        execution_id=execution_id,
        node_id=node_id,
        metadata=metadata or {},
    )

    with _lock:
        _references[key] = reference
        _trim_reference_store_locked()

    logger.info(
        "[FILE-REF] Registered file content reference "
        f"for execution_id={execution_id}, node_id={node_id}, "
        f"content_length={len(content)}"
    )
    return token


def resolve_file_content_references(value: Any, *, strict: bool = False) -> Any:
    """Resolve file content reference tokens inside strings, lists, and dicts."""

    if isinstance(value, str):
        return _resolve_references_in_string(value, strict=strict)
    if isinstance(value, list):
        return [resolve_file_content_references(item, strict=strict) for item in value]
    if isinstance(value, tuple):
        return tuple(
            resolve_file_content_references(item, strict=strict) for item in value
        )
    if isinstance(value, dict):
        return {
            key: resolve_file_content_references(item, strict=strict)
            for key, item in value.items()
        }
    return value


def get_file_content_reference_metadata(value: Any) -> Optional[Dict[str, Any]]:
    """Return metadata for a full token or exact bare reference id."""

    if not isinstance(value, str):
        return None

    reference = _get_reference_from_string(value)
    if reference is None:
        return None
    return dict(reference.metadata)


def get_file_content_reference_token(value: Any) -> Optional[str]:
    """Return the canonical token for a full token or exact bare reference id."""

    if not isinstance(value, str):
        return None

    reference = _get_reference_from_string(value)
    if reference is None:
        return None
    return reference.token


def clear_file_content_references(execution_id: Optional[str] = None) -> None:
    """Clear references for one execution, or all references when omitted."""

    with _lock:
        if execution_id is None:
            _references.clear()
            return

        stale_keys = [
            key for key, ref in _references.items() if ref.execution_id == execution_id
        ]
        for key in stale_keys:
            _references.pop(key, None)


def _resolve_references_in_string(value: str, *, strict: bool) -> str:
    exact_reference = _get_reference_from_string(value)
    if exact_reference is not None:
        return exact_reference.content
    # Only raise in strict mode for the explicit, unambiguous token format
    # ({{file_content_ref:<key>}}). A bare 32-hex-char string is NOT treated as a
    # missing reference because that pattern collides with many legitimate values
    # (client IDs, API keys, MD5 hashes, dashless GUIDs). Bare keys still resolve
    # above when they are actually present in the store.
    if strict and REFERENCE_TOKEN_PATTERN.fullmatch(value):
        raise KeyError(
            "File content reference is no longer available. Re-run the workflow."
        )

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        with _lock:
            reference = _references.get(key)

        if reference is None:
            if strict:
                raise KeyError(
                    "File content reference is no longer available. Re-run the workflow."
                )
            return match.group(0)

        return reference.content

    return REFERENCE_TOKEN_PATTERN.sub(replace, value)


def _get_reference_from_string(value: str) -> Optional[FileContentReference]:
    key = _get_reference_key_from_string(value)
    if key is None:
        return None

    with _lock:
        return _references.get(key)


def _get_reference_key_from_string(value: str) -> Optional[str]:
    token_match = REFERENCE_TOKEN_PATTERN.fullmatch(value)
    if token_match:
        return token_match.group(1)
    if BARE_REFERENCE_KEY_PATTERN.fullmatch(value):
        return value
    return None


def _prune_expired_references() -> None:
    cutoff = time.time() - REFERENCE_TTL_SECONDS
    with _lock:
        stale_keys = [
            key for key, ref in _references.items() if ref.created_at < cutoff
        ]
        for key in stale_keys:
            _references.pop(key, None)


def _trim_reference_store_locked() -> None:
    if len(_references) <= MAX_REFERENCES:
        return

    oldest_keys = sorted(_references, key=lambda key: _references[key].created_at)
    for key in oldest_keys[: len(_references) - MAX_REFERENCES]:
        _references.pop(key, None)

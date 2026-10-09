"""Violation retention service for purging old violation records.

Implements a rolling 1-year retention policy for guardrail_violations.
Intended to be called from a nightly background task.
"""

import logging

from sqlalchemy import text

from backend.services.database import get_db

logger = logging.getLogger(__name__)


def purge_old_violations() -> int:
    """Delete violation rows older than 1 year. Returns count deleted.

    This function is synchronous and should be called from a background task
    or a scheduled job. It is idempotent and safe to run multiple times.
    """
    try:
        with get_db() as db:
            result = db.execute(
                text("""
                    DELETE FROM guardrail_violations
                    WHERE created_at < NOW() - INTERVAL '1 year'
                """)
            )
            count = result.rowcount
            db.commit()
            logger.info("[GUARDRAIL-RETENTION] Purged %d old violation records", count)
            return count
    except Exception as e:
        logger.warning("[GUARDRAIL-RETENTION] Failed to purge old violations: %s", e)
        return 0

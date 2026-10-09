"""Seed built-in guardrail policy packs into the database."""

import logging

from backend.models.guardrails.guardrail_policy import GuardrailPolicy
from backend.services.database import get_db

from .financial_services import FINANCIAL_SERVICES_PACK
from .general_safety import GENERAL_SAFETY_PACK
from .pii_protection import PII_PROTECTION_PACK

logger = logging.getLogger(__name__)

BUILT_IN_PACKS = [
    GENERAL_SAFETY_PACK,
    PII_PROTECTION_PACK,
    FINANCIAL_SERVICES_PACK,
]


def seed_built_in_packs() -> None:
    """Upsert built-in policy packs.

    For each pack, if a policy with the same ID already exists and was
    created by ``__system__``, its name/description/config are updated.
    Otherwise a new policy row is inserted.
    """
    seeded = 0
    for pack in BUILT_IN_PACKS:
        with get_db() as db:
            existing = (
                db.query(GuardrailPolicy)
                .filter(GuardrailPolicy.id == pack["id"])
                .first()
            )
            if existing and (existing.created_by is None or existing.created_by == "__system__" or existing.is_builtin):
                existing.name = pack["name"]
                existing.description = pack["description"]
                existing.config = pack["config"]
                existing.is_builtin = True
                existing.is_template = True
                # Fix legacy __system__ FK violation
                if existing.created_by == "__system__":
                    existing.created_by = None
                db.flush()
            elif not existing:
                policy = GuardrailPolicy(
                    id=pack["id"],
                    name=pack["name"],
                    description=pack["description"],
                    config=pack["config"],
                    created_by=None,
                    is_template=True,
                    is_builtin=True,
                    scope="global",
                    is_compulsory=False,
                    applies_to=[],
                    shared_with=[],
                    tags=[],
                )
                db.add(policy)
                db.flush()
            seeded += 1

    logger.info("[GUARDRAILS-PACKS] Seeded %d built-in policy packs", seeded)

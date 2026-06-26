"""Shared pytest fixtures for the SahasrahBot test suite.

The suite is a characterization safety net written ahead of the three-tier
migration: it documents current behavior while mocking external services
aggressively. See docs/plans/three_tier_migration.md for the migration these
tests are meant to protect.

Conventions
-----------
* Mocking uses stdlib ``unittest.mock`` (``AsyncMock`` / ``MagicMock``) to match
  the original reference test (tests/unit/services/test_audit_service.py).
* Tests that exercise the repository tier or model properties use the
  ``tortoise_db`` fixture, which spins up a throwaway in-memory SQLite database
  per test. Service tests mock their repositories instead of touching a DB.
* Pure functions that read ``config.*`` at call time are exercised by patching
  the attribute, e.g. ``monkeypatch.setattr("config.TELEMETRY_HASH_SALT", "x")``.
"""

import pytest_asyncio
from tortoise import Tortoise


@pytest_asyncio.fixture
async def tortoise_db():
    """Provide a fresh in-memory SQLite database backed by the real ORM models.

    Each test gets an isolated database: schemas are generated from
    ``alttprbot.models`` up front and all connections are closed on teardown.
    Use this for repository round-trips and for model-property tests that need
    a live ORM context.
    """
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["alttprbot.models"]},
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()

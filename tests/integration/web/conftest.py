"""Fixtures for Quart web (BFF) route tests.

``alttprbot.presentation.web.web`` builds the Quart app at import time and reads
config (``int(config.DISCORD_CLIENT_ID)``, ``APP_SECRET_KEY``...), so we seed
placeholder values before importing it. The test client does not trigger
``before_serving`` hooks, so no real database connection is opened; every route
under test has its model/bot access mocked.
"""

import config

for _key, _value in {
    "DISCORD_CLIENT_ID": "123456",
    "DISCORD_CLIENT_SECRET": "test-secret",
    "APP_SECRET_KEY": "test-app-secret",
    "APP_URL": "http://localhost:5001",
}.items():
    if not getattr(config, _key, None):
        setattr(config, _key, _value)

import pytest_asyncio  # noqa: E402
from alttprbot.presentation.web.web import sahasrahbotapi  # noqa: E402


@pytest_asyncio.fixture
async def client():
    async with sahasrahbotapi.test_client() as test_client:
        yield test_client

"""Fixtures for REST API route tests.

``alttprbot.presentation.api.blueprints`` has no dependency on Discord OAuth or
the session cookie — it is pure REST (public or API-key-gated via
``auth.authorized_key()``). This conftest builds a throwaway Quart app and
registers only the REST blueprints, so no OAuth config seeding is needed.
"""

import pytest_asyncio
from quart import Quart

from alttprbot.presentation.api.blueprints import REST_BLUEPRINTS


@pytest_asyncio.fixture
async def client():
    app = Quart(__name__)
    for blueprint, kwargs in REST_BLUEPRINTS:
        app.register_blueprint(blueprint, **kwargs)
    async with app.test_client() as test_client:
        yield test_client

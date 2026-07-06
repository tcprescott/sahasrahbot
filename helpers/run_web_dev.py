#!/usr/bin/env python3
"""Run ONLY the Quart web + REST API surface, for frontend / Playwright testing.

Unlike ``sahasrahbot.py`` (which boots all four subsystems — Discord, audit,
RaceTime and the web app — and therefore needs valid Discord/RaceTime tokens),
this runner starts just the web-owned Quart app plus the REST blueprints, backed
by the database. That is enough to exercise the SPA end-to-end without connecting
any bots.

Prerequisites:
  * ``poetry install`` has been run.
  * A MySQL database is reachable using the DB_* settings (``.env`` / env vars)
    and the schema is migrated (``poetry run aerich upgrade``).

Usage:
    poetry run python helpers/run_web_dev.py                 # http://127.0.0.1:5001
    poetry run python helpers/run_web_dev.py --port 5001     # explicit port

See docs/guides/frontend_playwright_testing.md for the full workflow.
"""

import os
import sys
from pathlib import Path

# Make the repository root importable (``config.py``, ``migrations/``) when this
# script is launched directly as ``python helpers/run_web_dev.py`` — running a
# script file puts ``helpers/`` on sys.path, not the project root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# On a bare checkout with no ``.env``, provide import-safe placeholders so the web
# app can boot for frontend testing (``web.py`` does ``int(DISCORD_CLIENT_ID)`` at
# import time, and the OAuth client needs a secret key). A real ``.env`` is always
# respected — we only fill gaps when no ``.env`` file exists.
if not Path(".env").exists():
    os.environ.setdefault("DEBUG", "true")
    os.environ.setdefault("APP_SECRET_KEY", "dev-secret-not-for-production")
    os.environ.setdefault("DISCORD_CLIENT_ID", "0")
    os.environ.setdefault("DISCORD_CLIENT_SECRET", "dev")
    os.environ.setdefault("DISCORD_TOKEN", "dev")

import argparse  # noqa: E402
import asyncio  # noqa: E402
import logging  # noqa: E402

from tortoise import Tortoise  # noqa: E402

import config  # noqa: E402
from migrations.tortoise_config import TORTOISE_ORM  # noqa: E402
from alttprbot.presentation.web.web import sahasrahbotapi  # noqa: E402

logger = logging.getLogger(__name__)

# Compose the REST API surface onto the web-owned Quart app. This mirrors the
# wiring in ``sahasrahbot.py`` (the one place ``presentation.api`` and
# ``presentation.web`` are combined onto a single app/port).
#
# The REST blueprints transitively import ``racetime_bot`` (a GitHub-sourced
# dependency). If it isn't installed, we still want the SPA and the web
# blueprints to serve, so registration degrades gracefully — the SPA and all
# non-RaceTime pages remain fully testable.
try:
    from alttprbot.presentation.api.blueprints import REST_BLUEPRINTS

    for _rest_blueprint, _rest_kwargs in REST_BLUEPRINTS:
        sahasrahbotapi.register_blueprint(_rest_blueprint, **_rest_kwargs)
except ImportError as exc:
    logger.warning(
        "REST API blueprints unavailable (%s); serving the SPA + web blueprints only. "
        "Install all dependencies (`poetry install`) for the full REST surface.",
        exc,
    )


async def _serve(host: str, port: int) -> None:
    db_ready = False
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        db_ready = True
    except Exception as exc:  # noqa: BLE001 — DB is optional for pure frontend testing
        logger.warning(
            "Database unavailable (%s). Serving the SPA + static assets anyway; "
            "DB-backed endpoints will error until a MySQL is reachable and migrated "
            "(`poetry run aerich upgrade`).",
            exc,
        )

    logger.info(
        "Web-only dev server on http://%s:%d — Discord/audit/RaceTime bots are NOT running.",
        host,
        port,
    )
    logger.info("Serving the built SPA from alttprbot/presentation/web/spa/dist/ (run `npm run build` first).")
    try:
        await sahasrahbotapi.run_task(host=host, port=port, debug=config.DEBUG)
    finally:
        if db_ready:
            await Tortoise.close_connections()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=5001, help="Bind port (default: 5001).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        asyncio.run(_serve(args.host, args.port))
    except KeyboardInterrupt:
        logger.info("Shutting down web-only dev server.")


if __name__ == "__main__":
    main()

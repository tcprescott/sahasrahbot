"""``python -m devserver``: start the standalone web app. ``./scripts/dev.sh`` wraps this."""
import argparse
import asyncio
import logging


def main():
    parser = argparse.ArgumentParser(description="Run the SahasrahBot web app with fake services.")
    parser.add_argument("--host", default="127.0.0.1", help="address to bind (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5001, help="port to bind (default 5001)")
    parser.add_argument("--url", help="public base URL the browser uses (default http://localhost:<port>)")
    parser.add_argument("--reset", action="store_true", help="drop every table and reseed before starting")
    parser.add_argument("--no-seed", action="store_true", help="don't seed an empty database")
    parser.add_argument("--seed-only", action="store_true", help="prepare the database, then exit")
    args = parser.parse_args()

    app_url = (args.url or f"http://localhost:{args.port}").rstrip("/")

    from devserver.bootstrap import create_app

    app = create_app(app_url)
    # alttprbot_racetime.bot installs a root log handler on import; add one only if it didn't.
    if not logging.getLogger().handlers:
        logging.basicConfig(format="[%(asctime)s] %(name)s (%(levelname)s) :: %(message)s")
    logging.getLogger().setLevel(logging.INFO)

    from devserver import db

    async def run():
        await db.prepare(reset_first=args.reset, seed=not args.no_seed)
        logging.getLogger("devserver").info("Database: %s", db.describe(db.db_url()))
        if args.seed_only:
            return
        logging.getLogger("devserver").info("SahasrahBot dev server on %s (dev tools: %s/_dev/)", app_url, app_url)
        await app.run_task(host=args.host, port=args.port, debug=False)

    asyncio.run(run())


if __name__ == "__main__":
    main()

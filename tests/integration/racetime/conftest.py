"""Import-order shim for racetime handler tests.

Importing ``alttprbot_racetime.handlers.core`` cold triggers a circular import
(handlers.core -> alttprbot.tournaments -> ... -> alttprbot_racetime.config ->
handlers.core). Importing ``alttprbot_racetime.bot`` first walks the chain in
the order the running app uses, so the handler modules import cleanly afterward.
"""

import config

# Minimal placeholder config so the import chain does not trip on blank values.
for _key, _value in {
    "DISCORD_CLIENT_ID": "123456",
    "DISCORD_CLIENT_SECRET": "test-secret",
    "APP_SECRET_KEY": "test-app-secret",
    "APP_URL": "http://localhost:5001",
}.items():
    if not getattr(config, _key, None):
        setattr(config, _key, _value)

import alttprbot_racetime.bot  # noqa: E402,F401  (establishes module import order)

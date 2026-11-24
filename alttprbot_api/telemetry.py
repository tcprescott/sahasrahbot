"""Sentry for the web app: who made the request, and every request counted and timed.

The Quart integration (``alttprbot/observability/sentry.py``) already traces a
share of requests and reports unhandled errors. This adds, for **every** request:

* ``http.requests`` (counter) and ``http.request_duration`` (distribution, ms),
  by ``route`` (the URL rule, ``/api/v1/ranked-choice/<int:election_id>``, never
  the filled-in path), ``method`` and ``status`` (``2xx``...). The React app's
  pages share ``app page`` and its built files ``static file``, so their names
  stay bounded.
* The signed-in Discord user's id on the request's Sentry scope, read from the
  session cookie (no Discord API call), so an issue says who hit it.
* A ``route`` tag on any event the request raises.

``install(app)`` is called once in ``api.py``. Safe with Sentry off.
"""

import time

import sentry_sdk
from quart import Quart, g, request

from alttprbot.observability import metrics

_APP_RULE = '/<path:path>'


def route_label() -> str:
    rule = request.url_rule.rule if request.url_rule is not None else None
    if rule is None:
        return 'unmatched'
    if rule == _APP_RULE or rule == '/':
        last = request.path.rsplit('/', 1)[-1]
        return 'static file' if '.' in last else 'app page'
    return rule


def _discord_user_id():
    from quart import session
    try:
        return session.get('DISCORD_USER_ID')
    except Exception:
        return None


async def _before_request() -> None:
    g.telemetry_started = time.perf_counter()
    try:
        scope = sentry_sdk.get_isolation_scope()
        scope.set_tag('route', route_label())
        user_id = _discord_user_id()
        if user_id:
            scope.set_user({'id': str(user_id)})
    except Exception:
        pass


async def _after_request(response):
    started = getattr(g, 'telemetry_started', None)
    if started is not None and metrics.enabled():
        attrs = {
            'route': route_label(),
            'method': request.method,
            'status': f'{response.status_code // 100}xx',
        }
        metrics.count('http.requests', attributes=attrs)
        metrics.distribution('http.request_duration', (time.perf_counter() - started) * 1000,
                             unit='millisecond', attributes=attrs)
    return response


def install(app: Quart) -> None:
    app.before_request(_before_request)
    app.after_request(_after_request)

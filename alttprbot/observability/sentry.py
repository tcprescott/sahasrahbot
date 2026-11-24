"""Sentry for the whole process: errors, logs, traces, profiles and metrics.

``sahasrahbot.py`` (and ``devserver/bootstrap.py``) call :func:`init_sentry` first
thing, before the bots and the web app are built. With no DSN
(``config.SENTRY_URL``) it does nothing, so tests and local runs never report.

What reaches Sentry, modelled on Wizzrobe (``application/utils/sentry.py``):

* **Error events**: unhandled exceptions in web requests (Quart integration) and
  every ``logger.error`` / ``logger.exception`` anywhere, which is how the Discord
  bot, the racetime.gg bots, the scheduler and the event bus report failures.
  ``SahasrahBotException`` (a message for the user, not a bug) is dropped.
* **Breadcrumbs and Sentry Logs**: every INFO-and-up record
  (``SENTRY_LOGS_LEVEL``), so the lines around an error are readable in Sentry.
  Per-request access logs are left out.
* **Traces**: web requests at ``SENTRY_TRACES_SAMPLE_RATE`` (0.1 in production);
  scheduled jobs, Discord commands and racetime.gg commands at
  ``SENTRY_COMMAND_TRACES_SAMPLE_RATE`` (all of them in production: there are few).
  Inside a trace: MySQL queries (aiomysql), outbound HTTP (aiohttp), and a span per
  service, API-client and seed-generator call (:mod:`.instrument`).
* **Profiles**: ``SENTRY_PROFILES_SAMPLE_RATE`` (1.0 in production) of the traced
  work is profiled, which names the function that burned the CPU.
* **Metrics**: :mod:`.metrics`, on unless ``SENTRY_METRICS = False``.
* **Browser errors, replays and page-load traces**: the React app reports to the
  same project with the settings :func:`browser_config` hands it
  (``GET /api/v1/telemetry``). Server events carry ``surface: server``, browser
  ones ``surface: browser``.

Every event carries ``environment`` and ``release`` (``SENTRY_RELEASE``, else
``sahasrahbot@<git sha>``: production deploys with ``git pull``). Work outside a web
request tags itself with :func:`sentry_tags`, which also stamps its logs and
metrics, so a Sentry issue says which job, command or room it came from.

All settings are optional in ``config.py``: production's file predates them, so
each one falls back to a default (see ``config.example.py``).
"""

from __future__ import annotations

import logging
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger

import config
from alttprbot.observability import metrics

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent

_SENSITIVE_HEADERS = {'authorization', 'cookie', 'set-cookie', 'x-api-key', 'x-requested-with'}
_NOISY_FOR_SENTRY_LOGS = ('hypercorn.access', 'aiohttp.access', 'quart.serving')

# Web paths never worth a trace: health probes and the built app's static files.
_UNTRACED_PATHS = ('/healthcheck', '/assets/', '/favicon', '/manifest', '/sw.js', '/icons/')

# Span ops for work that isn't a web request; see the module docstring.
COMMAND_OPS = frozenset({'job', 'discord.command', 'discord.interaction', 'racetime.command'})

_initialized = False


# --- Settings -----------------------------------------------------------------------


def setting(name: str, default: Any = None) -> Any:
    """``config.<name>``, or ``default`` when production's ``config.py`` hasn't got it."""
    return getattr(config, name, default)


def dsn() -> Optional[str]:
    value = setting('SENTRY_URL')
    return value.strip() if isinstance(value, str) and value.strip() else None


def is_production() -> bool:
    return not setting('DEBUG', False)


def environment() -> str:
    return setting('SENTRY_ENVIRONMENT') or ('production' if is_production() else 'development')


def _fraction(raw: Any) -> float:
    try:
        return min(max(float(raw), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.0


def _rate(name: str, production_default: float) -> float:
    """A 0-1 sample rate from config; unset means ``production_default`` in production, else 0."""
    raw = setting(name)
    if raw is None:
        return production_default if is_production() else 0.0
    return _fraction(raw)


def traces_sample_rate() -> float:
    return _rate('SENTRY_TRACES_SAMPLE_RATE', 0.1)


def command_traces_sample_rate() -> float:
    return _rate('SENTRY_COMMAND_TRACES_SAMPLE_RATE', 1.0)


def profiles_sample_rate() -> float:
    return _rate('SENTRY_PROFILES_SAMPLE_RATE', 1.0)


def logs_level() -> Optional[int]:
    """The minimum level shipped to Sentry Logs; ``None`` turns them off."""
    raw = setting('SENTRY_LOGS_LEVEL', 'INFO')
    if raw is None or str(raw).strip().lower() in ('off', 'none', 'false', '0', ''):
        return None
    level = logging.getLevelName(str(raw).strip().upper())
    return level if isinstance(level, int) else logging.INFO


def metrics_requested() -> bool:
    return bool(setting('SENTRY_METRICS', True))


def _git_sha() -> Optional[str]:
    try:
        out = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True,
                             text=True, timeout=5, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


_release_cache: Dict[str, Optional[str]] = {}


def release() -> Optional[str]:
    """``SENTRY_RELEASE``, else ``sahasrahbot@<first 12 of the checked-out commit>``."""
    if 'value' not in _release_cache:
        explicit = setting('SENTRY_RELEASE')
        sha = None if explicit else _git_sha()
        _release_cache['value'] = explicit or (f'sahasrahbot@{sha[:12]}' if sha else None)
    return _release_cache['value']


# --- Hooks ------------------------------------------------------------------------------


def _scrub_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Strip auth headers and cookies, whatever an integration attached."""
    request = event.get('request')
    if isinstance(request, dict):
        headers = request.get('headers')
        if isinstance(headers, dict):
            for name in headers:
                if name.lower() in _SENSITIVE_HEADERS:
                    headers[name] = '[Filtered]'
        request.pop('cookies', None)
        request.pop('data', None)
    return event


def before_send(event: Dict[str, Any], hint: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Drop user-facing errors, tag the surface, scrub what's left."""
    from alttprbot.exceptions import SahasrahBotException

    exc_info = (hint or {}).get('exc_info')
    if exc_info and isinstance(exc_info[1], SahasrahBotException):
        return None
    tags = event.setdefault('tags', {})
    if isinstance(tags, dict):
        tags.setdefault('surface', 'server')
    return _scrub_event(event)


def _sampler(http_rate: float, command_rate: float) -> Callable[[Dict[str, Any]], float]:
    """Web requests at ``http_rate``, jobs and bot commands at ``command_rate``.

    A trace continued from the browser keeps the browser's decision, so a sampled
    page load links to the server work it caused. Health checks and static files
    are never traced.
    """
    def sampler(sampling_context: Dict[str, Any]) -> float:
        context = sampling_context.get('transaction_context') or {}
        name = context.get('name') or ''
        data = context.get('data') or {}
        path = data.get('url.path') or name
        if any(marker in path for marker in _UNTRACED_PATHS):
            return 0.0
        parent = sampling_context.get('parent_sampled')
        if parent is not None:
            return float(parent)
        if context.get('op') in COMMAND_OPS:
            return command_rate
        return http_rate
    return sampler


# --- Init -----------------------------------------------------------------------------------


def integrations() -> list:
    found = [
        LoggingIntegration(level=logs_level(), event_level=logging.ERROR, breadcrumb_level=logging.INFO),
        AioHttpIntegration(),
    ]
    try:
        from sentry_sdk.integrations.quart import QuartIntegration
        found.append(QuartIntegration())
    except Exception:  # DidNotEnable
        pass
    try:
        from sentry_sdk.integrations.aiomysql import AioMySQLIntegration
        found.append(AioMySQLIntegration())
    except Exception:
        pass
    return found


def init_sentry(instrument: bool = True) -> bool:
    """Start Sentry when a DSN is configured. Returns whether it did. Safe to call twice."""
    global _initialized
    if _initialized:
        return True
    if dsn() is None:
        logger.debug('SENTRY_URL not set; Sentry is off.')
        return False

    for name in _NOISY_FOR_SENTRY_LOGS:
        ignore_logger(name)

    sentry_sdk.init(
        dsn=dsn(),
        environment=environment(),
        release=release(),
        data_collection={
            'user_info': False,  # we set id and name ourselves, never IPs or emails
            'cookies': {'mode': 'off'},
            'http_bodies': [],  # presets, ballots and submissions stay out of Sentry
        },
        before_send=before_send,
        traces_sampler=_sampler(traces_sample_rate(), command_traces_sample_rate()),
        profile_session_sample_rate=profiles_sample_rate(),
        profile_lifecycle='trace',
        project_root=str(ROOT),
        in_app_exclude=['utils'],
        integrations=integrations(),
    )
    metrics.configure(metrics_requested())
    _initialized = True

    if instrument:
        from alttprbot.observability import instrument as _instrument
        wrapped = _instrument.instrument_all()
    else:
        wrapped = 0
    level = logs_level()
    logger.info(
        'Sentry initialized (environment=%s, release=%s, traces=%s, command traces=%s, profiles=%s, '
        'logs=%s, metrics=%s, instrumented calls=%s).',
        environment(), release() or 'unset', traces_sample_rate(), command_traces_sample_rate(),
        profiles_sample_rate(), logging.getLevelName(level) if level is not None else 'off',
        'on' if metrics.enabled() else 'off', wrapped,
    )
    return True


def enabled() -> bool:
    return _initialized


def flush(timeout: float = 2.0) -> None:
    """Send what's queued before the process exits. Blocks; call it off the loop or at exit."""
    if _initialized:
        sentry_sdk.flush(timeout)


def browser_config() -> Optional[Dict[str, Any]]:
    """What the React app hands the browser SDK, or ``None`` to not load it.

    The browser shares the server's DSN (one Sentry project, as in Wizzrobe).
    ``SENTRY_BROWSER = False`` keeps it off with the server still reporting.
    """
    value = dsn()
    if value is None or not setting('SENTRY_BROWSER', True):
        return None
    return {
        'dsn': value,
        'environment': environment(),
        'release': release(),
        'sample_rate': _fraction(setting('SENTRY_BROWSER_SAMPLE_RATE', 1.0)),
        'traces_sample_rate': _rate('SENTRY_BROWSER_TRACES_SAMPLE_RATE', traces_sample_rate()),
        'replay': bool(setting('SENTRY_BROWSER_REPLAY', True)),
    }


# --- Scope helpers ------------------------------------------------------------------------


@contextmanager
def sentry_tags(**tags: Any) -> Iterator[None]:
    """Tag every Sentry event, log and metric raised inside the block.

    Forks the current scope, so the tags vanish when the block exits and never
    leak onto the next unrelated event (a job's next run, the room's next
    message). ``None`` values are skipped. Safe with Sentry off.
    """
    with sentry_sdk.new_scope() as scope:
        _apply(scope, tags)
        yield


def tag_current_scope(**tags: Any) -> None:
    """Add tags to the scope already in effect, for a value learned mid-block.

    Meant for use inside :func:`sentry_tags`, whose forked scope bounds them.
    """
    _apply(sentry_sdk.get_current_scope(), tags)


def _apply(scope: Any, tags: Dict[str, Any]) -> None:
    for key, value in tags.items():
        if value is None:
            continue
        scope.set_tag(key, str(value))
        try:
            scope.set_attribute(key, str(value))
        except Exception:
            pass

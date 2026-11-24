"""Tests for Sentry wiring (alttprbot/observability/ and the front ends' telemetry).

Nothing here talks to Sentry. Metrics are captured by swapping the SDK's
``sentry_sdk.metrics`` module for a recorder (``recorded`` fixture); Sentry
itself is never initialised in this process, so spans are no-ops and the code
must behave exactly as it does with Sentry off.
"""

import asyncio
import logging
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest import mock

import pytest

import config
from alttprbot import events
from alttprbot.events import bus
from alttprbot.exceptions import NotFoundError, SahasrahBotException
from alttprbot.observability import instrument, metrics, runtime, watchdog
from alttprbot.observability import sentry as obs
from alttprbot.services.scheduler import Scheduler


class Recorder:
    def __init__(self):
        self.calls = []

    def _add(self, kind, name, value, unit=None, attributes=None):
        self.calls.append((kind, name, value, unit, dict(attributes or {})))

    def count(self, name, value, unit=None, attributes=None):
        self._add('count', name, value, unit, attributes)

    def gauge(self, name, value, unit=None, attributes=None):
        self._add('gauge', name, value, unit, attributes)

    def distribution(self, name, value, unit=None, attributes=None):
        self._add('distribution', name, value, unit, attributes)

    def named(self, name):
        return [c for c in self.calls if c[1] == name]


@pytest.fixture
def recorded(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(metrics, '_metrics', recorder)
    monkeypatch.setattr(metrics, '_enabled', True)
    return recorder


# --- metrics --------------------------------------------------------------------------


def test_metrics_are_noops_until_enabled(monkeypatch):
    recorder = Recorder()
    monkeypatch.setattr(metrics, '_metrics', recorder)
    monkeypatch.setattr(metrics, '_enabled', False)
    metrics.count('x')
    metrics.gauge('y', 1)
    metrics.distribution('z', 1)
    assert recorder.calls == []


def test_metrics_never_raise(recorded, monkeypatch):
    monkeypatch.setattr(recorded, 'count', mock.Mock(side_effect=RuntimeError('sdk broke')))
    metrics.count('x')  # no exception


def test_outcome_of():
    assert metrics.outcome_of(None) == 'ok'
    assert metrics.outcome_of(NotFoundError('nope')) == 'rejected'
    assert metrics.outcome_of(asyncio.CancelledError()) == 'cancelled'
    assert metrics.outcome_of(ValueError()) == 'error'


def test_timed_records_and_reraises(recorded):
    with pytest.raises(ValueError):
        with metrics.timed('thing', {'target': 't'}):
            raise ValueError()
    (call,) = recorded.named('thing.calls')
    assert call[4] == {'target': 't', 'outcome': 'error'}
    (dist,) = recorded.named('thing.duration')
    assert dist[3] == 'millisecond'


# --- instrument ---------------------------------------------------------------------


def _fake_module():
    module = ModuleType('alttprbot.services.fakesvc')

    async def get_thing(x):
        return x * 2

    async def missing():
        raise NotFoundError('no such thing')

    def sync_helper():
        return 1

    async def _private():
        return 1

    class Client:
        async def generate(self, n):
            return n

        @classmethod
        async def build(cls):
            return cls()

        def plain(self):
            return 'plain'

    class SubClient(Client):
        pass

    for obj in (get_thing, missing, sync_helper, _private, Client, SubClient):
        obj.__module__ = module.__name__
        setattr(module, obj.__name__, obj)
    return module


async def test_instrument_module_wraps_public_async_functions_and_methods(recorded):
    module = _fake_module()
    original_sync, original_private = module.sync_helper, module._private
    wrapped = instrument.instrument_module(module, 'service', 'service')
    assert wrapped == 4  # get_thing, missing, Client.generate, Client.build
    assert module.sync_helper is original_sync and module._private is original_private

    assert await module.get_thing(2) == 4
    with pytest.raises(NotFoundError):
        await module.missing()
    assert await module.SubClient().generate(3) == 3
    assert isinstance(await module.Client.build(), module.Client)
    assert module.Client().plain() == 'plain'

    calls = {(c[4]['target'], c[4]['outcome']) for c in recorded.named('service.calls')}
    assert calls == {
        ('fakesvc.get_thing', 'ok'),
        ('fakesvc.missing', 'rejected'),
        ('SubClient.generate', 'ok'),  # named after the class it was called on
        ('Client.build', 'ok'),
    }
    assert len(recorded.named('service.duration')) == 4


def test_instrument_is_idempotent():
    module = _fake_module()
    instrument.instrument_module(module, 'service', 'service')
    first = module.get_thing
    instrument.instrument_module(module, 'service', 'service')
    assert module.get_thing is first


def test_instrument_targets_import(monkeypatch):
    """Every package instrument_all walks exists (a rename would silently drop its metrics)."""
    import importlib
    for dotted, _, _ in instrument.TARGETS:
        importlib.import_module(dotted)
    for dotted in instrument.SKIPPED_MODULES:
        importlib.import_module(dotted)


# --- sentry settings and hooks ------------------------------------------------------------


def test_init_sentry_without_dsn_does_nothing(monkeypatch):
    monkeypatch.setattr(config, 'SENTRY_URL', None)
    init = mock.Mock()
    monkeypatch.setattr(obs.sentry_sdk, 'init', init)
    assert obs.init_sentry() is False
    init.assert_not_called()
    assert obs.browser_config() is None


def test_init_sentry_options(monkeypatch):
    monkeypatch.setattr(config, 'SENTRY_URL', 'https://key@o1.ingest.sentry.io/1')
    monkeypatch.setattr(config, 'DEBUG', False)
    monkeypatch.setattr(config, 'SENTRY_RELEASE', 'sahasrahbot@test')
    monkeypatch.setattr(obs, '_initialized', False)
    monkeypatch.setattr(obs, '_release_cache', {})
    monkeypatch.setattr(metrics, '_enabled', False)
    init = mock.Mock()
    monkeypatch.setattr(obs.sentry_sdk, 'init', init)
    assert obs.init_sentry(instrument=False) is True
    kwargs = init.call_args.kwargs
    assert kwargs['dsn'] == 'https://key@o1.ingest.sentry.io/1'
    assert kwargs['environment'] == 'production'
    assert kwargs['release'] == 'sahasrahbot@test'
    assert kwargs['data_collection']['user_info'] is False
    assert kwargs['data_collection']['http_bodies'] == []
    assert kwargs['profile_session_sample_rate'] == 1.0
    assert metrics.enabled()
    names = {type(i).__name__ for i in kwargs['integrations']}
    assert {'LoggingIntegration', 'AioHttpIntegration', 'QuartIntegration', 'AioMySQLIntegration'} <= names
    monkeypatch.setattr(metrics, '_enabled', False)


def test_settings_missing_from_config_fall_back(monkeypatch):
    """Production's config.py predates these settings; each must have a default."""
    for name in ('SENTRY_ENVIRONMENT', 'SENTRY_TRACES_SAMPLE_RATE', 'SENTRY_COMMAND_TRACES_SAMPLE_RATE',
                 'SENTRY_PROFILES_SAMPLE_RATE', 'SENTRY_LOGS_LEVEL', 'SENTRY_METRICS', 'SENTRY_BROWSER',
                 'SENTRY_BROWSER_SAMPLE_RATE', 'SENTRY_BROWSER_TRACES_SAMPLE_RATE', 'SENTRY_BROWSER_REPLAY'):
        monkeypatch.delattr(config, name, raising=False)
    monkeypatch.setattr(config, 'DEBUG', False)
    monkeypatch.setattr(config, 'SENTRY_URL', 'https://key@o1.ingest.sentry.io/1')
    assert obs.environment() == 'production'
    assert obs.traces_sample_rate() == 0.1
    assert obs.command_traces_sample_rate() == 1.0
    assert obs.logs_level() == logging.INFO
    assert obs.metrics_requested()
    browser = obs.browser_config()
    assert browser['sample_rate'] == 1.0 and browser['traces_sample_rate'] == 0.1 and browser['replay'] is True

    monkeypatch.setattr(config, 'DEBUG', True)
    assert obs.environment() == 'development'
    assert obs.traces_sample_rate() == 0.0


def test_logs_level_off(monkeypatch):
    monkeypatch.setattr(config, 'SENTRY_LOGS_LEVEL', 'off')
    assert obs.logs_level() is None
    monkeypatch.setattr(config, 'SENTRY_LOGS_LEVEL', 'warning')
    assert obs.logs_level() == logging.WARNING


def test_before_send_drops_user_facing_errors_and_scrubs():
    assert obs.before_send({}, {'exc_info': (SahasrahBotException, SahasrahBotException('hi'), None)}) is None
    event = {'request': {'headers': {'Cookie': 'session=1', 'Accept': 'json'}, 'cookies': {'a': 1}, 'data': 'ballot'}}
    out = obs.before_send(event, {})
    assert out['tags']['surface'] == 'server'
    assert out['request']['headers'] == {'Cookie': '[Filtered]', 'Accept': 'json'}
    assert 'cookies' not in out['request'] and 'data' not in out['request']


def test_traces_sampler():
    sampler = obs._sampler(0.1, 1.0)

    def ctx(name, op=None, parent=None, path=None):
        data = {'url.path': path} if path else {}
        return {'transaction_context': {'name': name, 'op': op, 'data': data}, 'parent_sampled': parent}

    assert sampler(ctx('GET /api/v1/session', 'http.server')) == 0.1
    assert sampler(ctx('daily.check_for_new_daily', 'job')) == 1.0
    assert sampler(ctx('/preset', 'discord.command')) == 1.0
    assert sampler(ctx('!seed', 'racetime.command')) == 1.0
    assert sampler(ctx('GET /healthcheck', 'http.server')) == 0.0
    assert sampler(ctx('GET', 'http.server', path='/assets/index-abc.js')) == 0.0
    assert sampler(ctx('GET /api/v1/me', 'http.server', parent=True)) == 1.0
    assert sampler(ctx('GET /api/v1/me', 'http.server', parent=False)) == 0.0


def test_sentry_tags_safe_without_sentry():
    with obs.sentry_tags(job='x', skipped=None):
        obs.tag_current_scope(more='y')


# --- scheduler and event bus --------------------------------------------------------------


async def test_scheduler_records_each_run(recorded, caplog):
    scheduler = Scheduler()

    async def ok():
        pass

    async def broken():
        raise ValueError('nope')

    scheduler.add_interval_job('test.ok', ok, seconds=60)
    scheduler.add_interval_job('test.broken', broken, seconds=60)
    await scheduler.run_now('test.ok')
    with caplog.at_level(logging.ERROR):
        await scheduler.run_now('test.broken')
    assert 'Scheduled job test.broken failed' in caplog.text
    outcomes = {(c[4]['job'], c[4]['outcome']) for c in recorded.named('job.calls')}
    assert outcomes == {('test.ok', 'ok'), ('test.broken', 'error')}
    assert scheduler.jobs['test.broken'].failures == 1


async def test_event_bus_records_publish_and_delivery(recorded, caplog):
    seen = []

    async def good(event):
        seen.append(event)

    async def bad(event):
        raise RuntimeError('subscriber broke')

    tokens = [bus.subscribe(events.Event, good), bus.subscribe(events.Event, bad)]
    try:
        event = events.Event()
        with caplog.at_level(logging.ERROR):
            bus.publish(event)
            assert bus.pending_count() == 2
            await bus.drain()
    finally:
        for token in tokens:
            bus.unsubscribe(token)
    assert seen == [event]
    assert bus.pending_count() == 0
    (published,) = recorded.named('events.published')
    assert published[4] == {'event': event.name}
    outcomes = {(c[4]['subscriber'].rsplit('.', 1)[-1], c[4]['outcome']) for c in recorded.named('event.calls')}
    assert outcomes == {('good', 'ok'), ('bad', 'error')}


# --- runtime sampler and watchdog -------------------------------------------------------------


async def test_collect_includes_sources_and_skips_broken_ones(monkeypatch):
    monkeypatch.setattr(runtime, '_sources', {})
    runtime.add_source('fine', lambda: [('thing.count', 3, {'kind': 'a'})])
    runtime.add_source('broken', mock.Mock(side_effect=RuntimeError('nope')))
    runtime._lags_ms.extend([1.0, 2.0, 3.0, 50.0])
    samples = {name: (value, attrs) for name, value, attrs in runtime.collect()}
    assert samples['thing.count'] == (3, {'kind': 'a'})
    assert samples['loop.lag_max'][0] == 50.0
    assert samples['loop.lag_p50'][0] == 2.5
    assert samples['events.pending'][0] == 0
    assert isinstance(samples['process.asyncio_tasks'][0], int)
    assert len(runtime._lags_ms) == 0


async def test_emit_sends_gauges_gc_and_stalls(recorded, monkeypatch):
    monkeypatch.setattr(runtime, '_sources', {})
    monkeypatch.setattr(runtime, '_stalls', 2)
    monkeypatch.setattr(runtime, '_last_stalls', 0)
    runtime._gc_pauses.extend([(2, 0.05), (0, 0.001)])
    runtime.emit()
    assert recorded.named('loop.stalls')[0][2] == 2
    assert [c[4] for c in recorded.named('gc.pause')] == [{'generation': '2'}]
    assert len(recorded.named('gc.seconds')) == 2
    (rss,) = recorded.named('process.memory_rss')
    assert rss[3] == 'megabyte'


async def test_heartbeat_runs_and_stops():
    await runtime.stop()
    runtime.start()
    try:
        before = runtime.last_heartbeat()
        await asyncio.sleep(runtime.HEARTBEAT_SECONDS * 2.5)
        assert runtime.last_heartbeat() > before
    finally:
        await runtime.stop()


def test_watchdog_culprit_names_our_innermost_frame():
    frame = sys._getframe()
    assert watchdog.culprit(frame).startswith('tests/test_observability.py:') is False  # tests aren't "our code"
    from alttprbot.services import scheduler as scheduler_module
    code = compile('import sys\nresult = sys._getframe()', scheduler_module.__file__, 'exec')
    namespace = {}
    exec(code, namespace)
    assert watchdog.culprit(namespace['result']) == 'alttprbot/services/scheduler.py:2 in <module>'


def test_watchdog_reports_a_stall_once(monkeypatch, caplog):
    import threading
    dog = watchdog.Watchdog(threading.get_ident())
    monkeypatch.setattr(runtime, '_last_beat', time.monotonic() - 5)
    with caplog.at_level(logging.ERROR, logger=watchdog.logger.name):
        assert dog.check() is not None
        assert dog.check() is None  # same stall
    assert caplog.text.count('Event loop blocked') == 1
    monkeypatch.setattr(runtime, '_last_beat', time.monotonic())
    assert dog.check() is None


# --- web app ------------------------------------------------------------------------------------


@pytest.fixture
def client(db):
    from alttprbot_api import api
    return api.sahasrahbotapi.test_client()


async def test_telemetry_endpoint_off_without_dsn(client, monkeypatch):
    monkeypatch.setattr(config, 'SENTRY_URL', None)
    resp = await client.get('/api/v1/telemetry')
    assert resp.status_code == 200
    assert await resp.get_json() == {'sentry': None}


async def test_telemetry_endpoint_hands_the_browser_its_settings(client, monkeypatch):
    monkeypatch.setattr(config, 'SENTRY_URL', 'https://key@o1.ingest.sentry.io/1')
    monkeypatch.setattr(config, 'SENTRY_RELEASE', 'sahasrahbot@abc')
    monkeypatch.setattr(config, 'SENTRY_BROWSER_TRACES_SAMPLE_RATE', 0.25)
    monkeypatch.setattr(obs, '_release_cache', {})
    body = await (await client.get('/api/v1/telemetry')).get_json()
    assert body['sentry'] == {
        'dsn': 'https://key@o1.ingest.sentry.io/1',
        'environment': 'development',
        'release': 'sahasrahbot@abc',
        'sample_rate': 1.0,
        'traces_sample_rate': 0.25,
        'replay': True,
    }
    monkeypatch.setattr(config, 'SENTRY_BROWSER', False)
    assert (await (await client.get('/api/v1/telemetry')).get_json()) == {'sentry': None}


async def test_every_request_is_counted_by_route(client, recorded):
    await client.get('/api/v1/telemetry')
    await client.get('/api/v1/ranked-choice/999999')
    await client.get('/some/page')
    routes = {(c[4]['route'], c[4]['status']) for c in recorded.named('http.requests')}
    assert ('/api/v1/telemetry', '2xx') in routes
    assert ('/api/v1/ranked-choice/<int:election_id>', '4xx') in routes
    assert ('app page', '4xx') in routes or ('app page', '2xx') in routes
    assert all(c[3] == 'millisecond' for c in recorded.named('http.request_duration'))


# --- racetime.gg ------------------------------------------------------------------------------


async def test_racetime_commands_are_timed_in_every_handler(recorded):
    from alttprbot_racetime import telemetry as rt_telemetry
    from alttprbot_racetime.handlers import alttpr, core

    assert getattr(core.SahasrahBotCoreHandler.ex_lock, rt_telemetry._MARK)
    own = [n for n in vars(alttpr.GameHandler) if n.startswith(('ex_', 'ex2_'))]
    assert own and all(getattr(getattr(alttpr.GameHandler, n), rt_telemetry._MARK, False) for n in own)

    class Handler(core.SahasrahBotCoreHandler):
        async def ex_boom(self, args, message):
            raise ValueError('boom')

        async def ex_fine(self, args, message):
            return 'done'

    handler = Handler.__new__(Handler)
    handler.bot = SimpleNamespace(category_slug='alttpr')
    handler.data = {'name': 'alttpr/room-1'}
    assert await handler.ex_fine([], {}) == 'done'
    with pytest.raises(ValueError):
        await handler.ex_boom([], {})
    calls = {(c[4]['command'], c[4]['outcome'], c[4]['category']) for c in recorded.named('racetime.commands.calls')}
    assert calls == {('fine', 'ok', 'alttpr'), ('boom', 'error', 'alttpr')}


async def test_racetime_room_scope_counts_messages(recorded):
    from alttprbot_racetime import telemetry as rt_telemetry
    handler = SimpleNamespace(bot=SimpleNamespace(category_slug='smz3'), data={'name': 'smz3/x'})
    with rt_telemetry.room_scope(handler, 'race.data'):
        pass
    (call,) = recorded.named('racetime.messages')
    assert call[4] == {'category': 'smz3', 'type': 'race.data'}


def test_racetime_rooms_source():
    from alttprbot_racetime import gateways
    with mock.patch.dict(gateways.racetime_bots, {'alttpr': SimpleNamespace(handlers={'a': 1, 'b': 2})}, clear=True):
        assert gateways.rooms_source() == [('racetime.rooms', 2, {'category': 'alttpr'})]


# --- Discord ----------------------------------------------------------------------------------


def test_discord_bot_uses_the_sentry_command_tree():
    from alttprbot_discord import telemetry
    from alttprbot_discord.bot import discordbot
    assert isinstance(discordbot.tree, telemetry.SentryCommandTree)


async def test_sentry_command_tree_times_commands(recorded, monkeypatch):
    import discord
    from discord import app_commands

    from alttprbot_discord import telemetry

    tree = telemetry.SentryCommandTree.__new__(telemetry.SentryCommandTree)
    interaction = SimpleNamespace(
        command=SimpleNamespace(qualified_name='preset roll', name='roll'),
        data={'name': 'preset', 'type': 1},
        type=discord.InteractionType.application_command,
        created_at=discord.utils.utcnow(),
        guild_id=1, channel_id=2, user=SimpleNamespace(id=3, __str__=lambda self: 'someone'),
        command_failed=False,
    )
    monkeypatch.setattr(app_commands.CommandTree, '_call', mock.AsyncMock())
    await tree._call(interaction)
    interaction.command_failed = True
    await tree._call(interaction)
    outcomes = [(c[4]['command'], c[4]['kind'], c[4]['outcome']) for c in recorded.named('discord.commands.calls')]
    assert outcomes == [('preset roll', 'slash', 'ok'), ('preset roll', 'slash', 'error')]
    assert len(recorded.named('discord.commands.delay')) == 2


def test_discord_runtime_source():
    from alttprbot_discord import telemetry
    client = SimpleNamespace(is_ready=lambda: True, latency=0.0425, guilds=[1, 2, 3])
    assert telemetry.runtime_source(client)() == [
        ('discord.ready', 1, None), ('discord.guilds', 3, None), ('discord.latency', 42.5, None)]
    client = SimpleNamespace(is_ready=lambda: False, latency=float('inf'), guilds=[])
    assert telemetry.runtime_source(client)() == [
        ('discord.ready', 0, None), ('discord.guilds', None, None), ('discord.latency', None, None)]


async def test_app_pages_inline_the_browser_settings(client, monkeypatch, tmp_path):
    from alttprbot_api import api
    (tmp_path / 'index.html').write_text('<html><head><title>x</title></head><body><div id=root></div></body></html>')
    monkeypatch.setattr(api, 'WEB_DIST', tmp_path)

    monkeypatch.setattr(config, 'SENTRY_URL', None)
    html = await (await client.get('/ranked_choice/4')).get_data(as_text=True)
    assert '<script>window.__SAHASRAHBOT_SENTRY__=null;</script></head>' in html

    monkeypatch.setattr(config, 'SENTRY_URL', 'https://key@o1.ingest.sentry.io/1')
    monkeypatch.setattr(config, 'SENTRY_RELEASE', '</script><b>')
    monkeypatch.setattr(obs, '_release_cache', {})
    resp = await client.get('/')
    html = await resp.get_data(as_text=True)
    assert resp.headers['Content-Type'].startswith('text/html')
    assert '"dsn": "https://key@o1.ingest.sentry.io/1"' in html
    assert '</script><b>' not in html  # inlined JSON can't close the script tag

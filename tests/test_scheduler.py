"""Tests for the in-process scheduler, the job event shim and the scheduled job logic."""
import asyncio
import datetime
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from alttprbot.services import job_events as events
from alttprbot.services.scheduler import Scheduler

# Imported at collection time, before any test closes an event loop: importing the
# tournament modules builds the racetime bots, which call asyncio.get_event_loop().
from alttprbot.services import scheduled_jobs  # noqa: E402
from alttprbot.services import asynctournament as asynctournament_service  # noqa: E402
from alttprbot.services import asynctournament_jobs  # noqa: E402
from alttprbot.services.tournament_jobs import scheduling_needs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def run(coro):
    return asyncio.run(coro)


# --- Scheduler ----------------------------------------------------------------

def test_job_runs_immediately_then_on_interval():
    calls = []

    async def job():
        calls.append(asyncio.get_running_loop().time())

    async def main():
        scheduler = Scheduler()
        scheduler.add_interval_job('job', job, seconds=0.05)
        scheduler.start()
        await asyncio.sleep(0.18)
        await scheduler.stop()

    run(main())
    assert 3 <= len(calls) <= 5


def test_failing_job_keeps_running_and_records_error():
    async def job():
        raise RuntimeError("boom")

    async def main():
        scheduler = Scheduler()
        scheduler.add_interval_job('job', job, seconds=0.02)
        scheduler.start()
        await asyncio.sleep(0.07)
        await scheduler.stop()
        return scheduler.jobs['job']

    job_state = run(main())
    assert job_state.runs >= 2
    assert job_state.failures == job_state.runs
    assert isinstance(job_state.last_error, RuntimeError)


def test_job_waits_for_gate():
    calls = []
    gate = None

    async def job():
        calls.append(1)

    async def main():
        nonlocal gate
        gate = asyncio.Event()
        scheduler = Scheduler()
        scheduler.add_interval_job('job', job, seconds=10, wait_for=gate.wait)
        scheduler.start()
        await asyncio.sleep(0.03)
        before = len(calls)
        gate.set()
        await asyncio.sleep(0.03)
        await scheduler.stop()
        return before

    assert run(main()) == 0
    assert calls == [1]


def test_run_now_does_not_overlap_a_running_job():
    active = 0
    max_active = 0

    async def job():
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1

    async def main():
        scheduler = Scheduler()
        scheduler.add_interval_job('job', job, seconds=10)
        scheduler.start()
        await asyncio.sleep(0.01)
        await scheduler.run_now('job')
        await scheduler.stop()
        return scheduler.jobs['job'].runs

    assert run(main()) == 2
    assert max_active == 1


def test_duplicate_and_invalid_jobs_are_rejected():
    async def job():
        pass

    scheduler = Scheduler()
    scheduler.add_interval_job('job', job, seconds=1)
    with pytest.raises(ValueError):
        scheduler.add_interval_job('job', job, seconds=1)
    with pytest.raises(ValueError):
        scheduler.add_interval_job('other', job, seconds=0)


def test_register_jobs_registers_every_job():
    scheduler = Scheduler()
    scheduled_jobs.register_jobs(scheduler)
    assert set(scheduler.jobs) == {
        'daily.check_for_new_daily',
        'tournament.create_races',
        'tournament.week_races',
        'tournament.record_races',
        'tournament.find_races_with_bad_discord',
        'asynctournament.timeout_pending_races',
        'asynctournament.timeout_in_progress_races',
        'asynctournament.calculate_scores',
    }


# --- Async tournament timeouts -------------------------------------------------------

def _timeout_action(kind):
    race = SimpleNamespace(id=1, thread_id=2, user=SimpleNamespace(discord_user_id=3))
    return asynctournament_service.TimeoutAction(
        race, kind, datetime.datetime(2026, 11, 24, tzinfo=datetime.timezone.utc))


@pytest.mark.parametrize("kind, told, forfeited", [
    (asynctournament_service.WARN, True, False),
    (asynctournament_service.FORFEIT_PENDING, True, True),
    (asynctournament_service.FORFEIT_IN_PROGRESS, True, True),
    # A runner who couldn't be told (thread gone) is left alone.
    (asynctournament_service.FORFEIT_PENDING, False, False),
])
def test_timeout_forfeits_only_after_runner_is_told(monkeypatch, kind, told, forfeited):
    action = _timeout_action(kind)
    notified, applied = [], []

    async def find():
        return [action]

    async def notifier(a):
        notified.append(a)
        return told

    async def apply(a):
        applied.append(a)

    monkeypatch.setattr(asynctournament_service, 'find_pending_timeouts', find)
    monkeypatch.setattr(asynctournament_service, 'apply_timeout_forfeit', apply)
    monkeypatch.setattr(asynctournament_jobs, '_timeout_notifier', notifier)

    run(asynctournament_jobs.timeout_pending_races())
    assert notified == [action]
    assert applied == ([action] if forfeited else [])


def test_timeout_without_notifier_forfeits_nothing(monkeypatch):
    applied = []

    async def find():
        return [_timeout_action(asynctournament_service.FORFEIT_IN_PROGRESS)]

    async def apply(a):
        applied.append(a)

    monkeypatch.setattr(asynctournament_service, 'find_in_progress_timeouts', find)
    monkeypatch.setattr(asynctournament_service, 'apply_timeout_forfeit', apply)
    monkeypatch.setattr(asynctournament_jobs, '_timeout_notifier', None)

    run(asynctournament_jobs.timeout_in_progress_races())
    assert applied == []


def test_timeout_notifier_error_skips_that_run(monkeypatch):
    actions = [_timeout_action(asynctournament_service.FORFEIT_PENDING) for _ in range(2)]
    applied = []

    async def find():
        return actions

    async def notifier(a):
        if a is actions[0]:
            raise RuntimeError("Discord is down")
        return True

    async def apply(a):
        applied.append(a)

    monkeypatch.setattr(asynctournament_service, 'find_pending_timeouts', find)
    monkeypatch.setattr(asynctournament_service, 'apply_timeout_forfeit', apply)
    monkeypatch.setattr(asynctournament_jobs, '_timeout_notifier', notifier)

    run(asynctournament_jobs.timeout_pending_races())
    assert applied == [actions[1]]


# --- Event shim -----------------------------------------------------------------

def test_publish_delivers_to_matching_subscribers_and_survives_errors():
    received = []

    async def handler(event):
        received.append(event)

    async def broken(event):
        raise RuntimeError("subscriber failed")

    async def main():
        tokens = [
            events.subscribe(events.DailyChallengeAvailable, handler),
            events.subscribe((events.DailyChallengeAvailable, events.UnmatchedPlayersFound), broken),
        ]
        try:
            events.publish(events.DailyChallengeAvailable(hash_id='abc'))
            events.publish(events.TournamentRoomCreationFailed(event_slug='x', episode_id=1, error='e'))
            await events.drain()
        finally:
            for token in tokens:
                events.unsubscribe(token)

    run(main())
    assert received == [events.DailyChallengeAvailable(hash_id='abc')]


def test_publish_without_subscribers_or_loop_does_not_raise():
    events.publish(events.DailyChallengeAvailable(hash_id='abc'))


# --- Scheduling needs -------------------------------------------------------------

def _episode(episode_id, channel='ALTTPRandomizer', commentators=0, trackers=0, broadcasters=0, players=2):
    def staff(n):
        return [{'approved': True, 'language': 'en'} for _ in range(n)]
    return {
        'id': episode_id,
        'when': '2026-11-24T18:00:00+00:00',
        'channels': [{'id': 100, 'slug': channel, 'language': 'en'}],
        'commentators': staff(commentators),
        'trackers': staff(trackers),
        'broadcasters': staff(broadcasters),
        'match1': {'players': [{} for _ in range(players)]},
    }


def test_scheduling_needs():
    needs = scheduling_needs('alttpr', [
        _episode(1, commentators=1),
        _episode(2, commentators=2, trackers=1, broadcasters=1),
        _episode(3, channel='SomeoneElse', players=4),
        {**_episode(4), 'channels': [{'id': 0, 'slug': 'ALTTPRandomizer', 'language': 'en'}]},
    ])

    assert [(n.signup_url.rsplit('/', 2)[-2], n.count) for n in needs.commentators] == [('1', 1), ('3', 2)]
    assert [(n.signup_url.rsplit('/', 2)[-2], n.count) for n in needs.trackers] == [('1', 1), ('3', 2)]
    assert [n.signup_url for n in needs.broadcasters] == ['https://speedgaming.org/broadcaster/signup/1/']
    assert needs.commentators[0].start_time == datetime.datetime(2026, 11, 24, 18, tzinfo=datetime.timezone.utc)

    without_trackers = scheduling_needs('alttpr', [_episode(1)], include_trackers=False)
    assert without_trackers.trackers == ()


# --- Guardrail: no new discord.py task loops ----------------------------------------

# Keep this empty: periodic jobs go in alttprbot/services/scheduled_jobs.py.
TASK_LOOP_ALLOWLIST = set()


def test_no_discord_task_loops_outside_allowlist():
    offenders = set()
    for package in ('alttprbot', 'alttprbot_discord', 'alttprbot_racetime', 'alttprbot_api'):
        for path in (ROOT / package).rglob('*.py'):
            if re.search(r'^\s*@tasks\.loop\(', path.read_text(encoding='utf-8'), re.M):
                offenders.add(path.relative_to(ROOT).as_posix())
    assert offenders <= TASK_LOOP_ALLOWLIST, (
        "Periodic jobs belong in alttprbot/services/scheduled_jobs.py, not discord.ext.tasks loops: "
        f"{sorted(offenders - TASK_LOOP_ALLOWLIST)}")

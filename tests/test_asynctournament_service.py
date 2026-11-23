"""Behaviour tests for alttprbot/services/asynctournament.py.

These run against an in-memory SQLite database, so they need no MySQL, Discord or
network. Each test gets a fresh schema.
"""

import ast
import asyncio
import datetime
from pathlib import Path

import pytest
from tortoise import Tortoise

from alttprbot import models
from alttprbot.services import asynctournament as service

ROOT = Path(__file__).resolve().parent.parent
UTC = datetime.timezone.utc


def run(coro):
    return asyncio.run(coro)


async def _setup_db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["alttprbot.models"]},
        use_tz=True,
        timezone="UTC",
        _enable_global_fallback=True,
    )
    await Tortoise.generate_schemas()


def db_test(fn):
    """Run an async test body inside a fresh in-memory database."""
    def wrapper(*args, **kwargs):
        async def body():
            await _setup_db()
            try:
                await fn(*args, **kwargs)
            finally:
                service.set_member_role_lookup(None)
                await Tortoise.close_connections()
        run(body())
    wrapper.__name__ = fn.__name__
    return wrapper


async def make_tournament(runs_per_pool=1, active=True, pools=("Pool A",), seeds_per_pool=2):
    tournament = await models.AsyncTournament.create(
        name="Test", guild_id=1, channel_id=2, owner_id=3, active=active, runs_per_pool=runs_per_pool)
    for name in pools:
        pool = await models.AsyncTournamentPermalinkPool.create(tournament=tournament, name=name, preset="open")
        for i in range(seeds_per_pool):
            await models.AsyncTournamentPermalink.create(pool=pool, url=f"https://example.com/{name}/{i}",
                                                         live_race=False)
    return tournament


async def make_user(discord_user_id, linked=True):
    return await models.Users.create(discord_user_id=discord_user_id, display_name=f"u{discord_user_id}",
                                     rtgg_id=f"rt{discord_user_id}" if linked else None)


async def make_race(tournament, user, status="finished", reattempted=False, thread_id=None, **kwargs):
    permalink = await models.AsyncTournamentPermalink.filter(pool__tournament=tournament).first()
    return await models.AsyncTournamentRace.create(
        tournament=tournament, user=user, permalink=permalink, status=status, reattempted=reattempted,
        thread_id=thread_id, **kwargs)


async def audit_actions(tournament):
    return [a.action for a in await models.AsyncTournamentAuditLog.filter(tournament=tournament).order_by("id")]


# --- Website reattempts and reviews now write the audit log ---------------------

@db_test
async def test_reattempt_writes_audit_log():
    tournament = await make_tournament()
    player = await make_user(10)
    race = await make_race(tournament, player)

    await service.reattempt(tournament, player, str(race.id), "controller died")

    await race.refresh_from_db()
    assert race.reattempted is True
    assert race.reattempt_reason == "controller died"
    log = await models.AsyncTournamentAuditLog.get(tournament=tournament, action="reattempt")
    assert log.user_id == player.id
    assert str(race.id) in log.details


@db_test
async def test_only_one_reattempt_per_tournament():
    tournament = await make_tournament(pools=("Pool A", "Pool B"))
    player = await make_user(10)
    first = await make_race(tournament, player)
    second = await make_race(tournament, player)

    await service.reattempt(tournament, player, first.id, None)
    with pytest.raises(service.AsyncTournamentError) as e:
        await service.reattempt(tournament, player, second.id, None)
    assert e.value.status == 403
    assert await audit_actions(tournament) == ["reattempt"]


@db_test
async def test_cannot_reattempt_someone_elses_race():
    tournament = await make_tournament()
    owner = await make_user(10)
    other = await make_user(11)
    race = await make_race(tournament, owner)

    with pytest.raises(service.AsyncTournamentError):
        await service.reattempt(tournament, other, race.id, None)
    with pytest.raises(service.AsyncTournamentError) as e:
        await service.reattempt(tournament, other, None, None)
    assert e.value.status == 400


@db_test
async def test_review_writes_audit_log():
    tournament = await make_tournament()
    player = await make_user(10)
    reviewer = await make_user(20)
    await models.AsyncTournamentPermissions.create(tournament=tournament, user=reviewer, role="mod")
    race = await make_race(tournament, player)

    fetched = await service.get_race_for_review(tournament, reviewer, race.id)
    assert await service.claim_review(fetched, reviewer) is True
    assert await service.claim_review(fetched, reviewer) is False  # already claimed

    await service.submit_review(tournament, reviewer, race.id, "accepted", "looks good")

    await race.refresh_from_db()
    assert race.review_status == "accepted"
    assert race.reviewed_by_id == reviewer.id
    assert race.reviewed_at is not None
    assert await audit_actions(tournament) == ["review_claim", "review"]


@db_test
async def test_review_rules():
    tournament = await make_tournament()
    mod = await make_user(20)
    outsider = await make_user(30)
    await models.AsyncTournamentPermissions.create(tournament=tournament, user=mod, role="mod")

    own_run = await make_race(tournament, mod)
    in_progress = await make_race(tournament, outsider, status="in_progress")
    reattempted = await make_race(tournament, outsider, reattempted=True)

    for race_id in (own_run.id, in_progress.id, reattempted.id):
        with pytest.raises(service.AsyncTournamentError):
            await service.submit_review(tournament, mod, race_id, "accepted", None)

    with pytest.raises(service.AsyncTournamentError):  # not a mod
        await service.submit_review(tournament, outsider, own_run.id, "accepted", None)
    with pytest.raises(service.AsyncTournamentError) as e:
        await service.submit_review(tournament, mod, 9999, "accepted", None)
    assert e.value.status == 404
    assert await audit_actions(tournament) == []


# --- Permissions ---------------------------------------------------------------

@db_test
async def test_permissions_direct_role_and_public():
    tournament = await make_tournament()
    admin = await make_user(20)
    via_role = await make_user(21)
    nobody = await make_user(22)
    await models.AsyncTournamentPermissions.create(tournament=tournament, user=admin, role="admin")
    await models.AsyncTournamentPermissions.create(tournament=tournament, discord_role_id=555, role="mod")

    assert await service.is_async_tournament_user(admin, tournament, ["admin"])
    assert not await service.is_async_tournament_user(admin, tournament, ["mod"])
    assert not await service.is_async_tournament_user(None, tournament, ["admin", "mod"])

    # Without a registered lookup, role-based permissions don't apply.
    assert not await service.is_async_tournament_user(via_role, tournament, ["mod"])

    async def lookup(guild_id, discord_user_id):
        assert guild_id == tournament.guild_id
        return [555] if discord_user_id == 21 else []

    service.set_member_role_lookup(lookup)
    assert await service.is_async_tournament_user(via_role, tournament, ["mod"])
    assert not await service.is_async_tournament_user(nobody, tournament, ["mod"])

    tournament.active = False
    assert await service.is_async_tournament_user(None, tournament, ["public"])


# --- Starting and running a Discord run ----------------------------------------

@db_test
async def test_start_race_flow_and_pool_limit():
    tournament = await make_tournament(runs_per_pool=1, pools=("Pool A", "Pool B"))
    player = await make_user(10)
    old_account = datetime.datetime(2000, 1, 1, tzinfo=UTC)

    _, pools = await service.check_can_start(tournament, 10, old_account)
    assert sorted(p.name for p in pools) == ["Pool A", "Pool B"]

    user, pool = await service.check_new_race(tournament, 10, "Pool A")
    race, permalink = await service.start_race(tournament, user, pool, thread_id=1234)
    assert race.user_id == player.id and permalink.pool_id == pool.id
    assert await audit_actions(tournament) == ["create_thread"]

    with pytest.raises(service.AsyncTournamentError, match="active race"):
        await service.check_new_race(tournament, 10, "Pool B")

    race.status = "finished"
    await race.save()
    with pytest.raises(service.AsyncTournamentError, match="maximum number"):
        await service.check_new_race(tournament, 10, "Pool A")

    _, pools = await service.check_can_start(tournament, 10, old_account)
    assert [p.name for p in pools] == ["Pool B"]


@db_test
async def test_check_can_start_rules():
    tournament = await make_tournament()
    await make_user(10, linked=False)
    old_account = datetime.datetime(2000, 1, 1, tzinfo=UTC)

    with pytest.raises(service.AsyncTournamentError, match="RaceTime"):
        await service.check_can_start(tournament, 10, old_account)
    with pytest.raises(service.AsyncTournamentError, match="too new"):
        await service.check_can_start(tournament, 11, datetime.datetime.now(UTC))
    with pytest.raises(service.AsyncTournamentError) as e:
        await service.check_can_start(None, 10, old_account)
    assert e.value.status == 404


@db_test
async def test_run_lifecycle_audits_each_step():
    tournament = await make_tournament()
    player = await make_user(10)
    race = await make_race(tournament, player, status="pending", thread_id=99)
    await race.fetch_related("user")

    with pytest.raises(service.AsyncTournamentError):
        await service.mark_ready(race, 11)  # not the runner

    user = await service.mark_ready(race, 10)
    with pytest.raises(service.AsyncTournamentError, match="pending"):
        await service.mark_ready(race, 10)  # second click is refused
    await service.record_start(race, user)
    await service.finish(race, 10)
    await service.submit_vod(race, 10, "https://youtu.be/x", "gg")

    await race.refresh_from_db()
    assert race.status == "finished" and race.runner_vod_url == "https://youtu.be/x"
    assert await audit_actions(tournament) == [
        "race_ready", "race_countdown", "race_started", "race_finish", "submit_vod"]


@db_test
async def test_forfeit_and_extend_timeout():
    tournament = await make_tournament()
    player = await make_user(10)
    mod = await make_user(20)
    await models.AsyncTournamentPermissions.create(tournament=tournament, user=mod, role="mod")
    opened = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    race = await make_race(tournament, player, status="pending", thread_id=99, thread_open_time=opened)
    await race.fetch_related("user")

    with pytest.raises(service.AsyncTournamentError):
        await service.extend_timeout(race, 10, 30)  # the runner isn't a mod
    deadline = await service.extend_timeout(race, 20, 30)
    assert deadline == opened + datetime.timedelta(minutes=50)

    await service.forfeit(race, 10)
    with pytest.raises(service.AsyncTournamentError):
        await service.forfeit(race, 10)
    assert await audit_actions(tournament) == ["extend_timeout", "runner_forfeit"]


# --- Timeout sweep -------------------------------------------------------------

def test_pending_timeout_action():
    deadline = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    race = models.AsyncTournamentRace(thread_timeout_time=deadline)
    minutes = datetime.timedelta(minutes=1)

    assert service.pending_timeout_action(race, deadline - 11 * minutes) is None
    assert service.pending_timeout_action(race, deadline - 5 * minutes).kind == service.WARN
    action = service.pending_timeout_action(race, deadline + minutes)
    assert action.kind == service.FORFEIT_PENDING and action.forfeits


def test_in_progress_timeout_action():
    start = datetime.datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    race = models.AsyncTournamentRace(start_time=start)
    assert service.in_progress_timeout_action(race, start + datetime.timedelta(hours=11)) is None
    assert service.in_progress_timeout_action(
        race, start + datetime.timedelta(hours=13)).kind == service.FORFEIT_IN_PROGRESS
    assert service.in_progress_timeout_action(models.AsyncTournamentRace(start_time=None), start) is None


@db_test
async def test_timeout_sweep_forfeits_and_audits():
    tournament = await make_tournament()
    player = await make_user(10)
    opened = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    race = await make_race(tournament, player, status="pending", thread_id=99, thread_open_time=opened)

    actions = await service.find_pending_timeouts(now=opened + datetime.timedelta(minutes=15))
    assert [a.kind for a in actions] == [service.WARN]
    await race.refresh_from_db()
    assert race.thread_timeout_time == opened + service.PENDING_GRACE_PERIOD  # default filled in

    actions = await service.find_pending_timeouts(now=opened + datetime.timedelta(minutes=25))
    assert [a.kind for a in actions] == [service.FORFEIT_PENDING]
    await service.apply_timeout_forfeit(actions[0])
    await race.refresh_from_db()
    assert race.status == "forfeit"
    assert await audit_actions(tournament) == ["timeout_forfeit"]


# --- Layering ------------------------------------------------------------------

def test_services_do_not_import_front_ends():
    """Services in alttprbot/ never import the Discord, racetime, web or audit packages."""
    for path in (ROOT / "alttprbot" / "services").glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith(("alttprbot_", "discord")), f"{path.name} imports {name}"

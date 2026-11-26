"""Racer verification managed from the website: the service
(alttprbot/services/racer_verification.py), its scheduled recheck, the /api/v1 routes,
the Discord gateway (alttprbot_discord/racer_verification.py) and the audit-channel report."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import events, models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import racer_verification as rv
from alttprbot_discord import notifications
from alttprbot_discord import racer_verification as rv_discord
from tests.test_api import CSRF, client, get_json, login, send_json  # noqa: F401  (fixtures)

ADMIN, OWNER, OUTSIDER = 7, 1, 11
GUILD, OTHER_GUILD = 5, 6
ROLE, OTHER_ROLE = 77, 78
CHANNEL, LOG_CHANNEL, NEW_CHANNEL = 300, 301, 302
NOW = datetime(2026, 11, 26, 12, tzinfo=timezone.utc)


class FakeGateway:
    def __init__(self):
        self.posted, self.edited, self.deleted, self.removed = [], [], [], []
        self.members = {}  # discord id -> username; missing means they left
        self.message_gone = False
        self.post_error = None
        self.next_id = 9000

    async def post_message(self, channel_id, content):
        if self.post_error:
            raise self.post_error
        self.next_id += 1
        self.posted.append((channel_id, self.next_id, content))
        return self.next_id

    async def edit_message(self, channel_id, message_id, content):
        if self.message_gone:
            return False
        self.edited.append((channel_id, message_id, content))
        return True

    async def delete_message(self, channel_id, message_id):
        self.deleted.append((channel_id, message_id))

    async def member_name(self, guild_id, user_id):
        return self.members.get(user_id)

    async def remove_role(self, guild_id, user_id, role_id, reason):
        self.removed.append((guild_id, user_id, role_id))


@pytest.fixture
def gateway(monkeypatch):
    fake = FakeGateway()
    monkeypatch.setattr(rv, "_gateway", fake)
    return fake


@pytest.fixture
def published(monkeypatch):
    sent = []
    monkeypatch.setattr(events, "publish", sent.append)
    return sent


@pytest.fixture
def server(directory):
    directory.owner = OWNER
    directory.add_guild(GUILD, name="Racing", admins=[ADMIN],
                        channels=[(CHANNEL, "get-verified"), (LOG_CHANNEL, "mod-log"), (NEW_CHANNEL, "roles")],
                        roles=[(ROLE, "Verified Racer"), (OTHER_ROLE, "Mystery Racer")])
    directory.add_guild(OTHER_GUILD, name="Elsewhere", admins=[OUTSIDER], channels=[(400, "x")], roles=[(79, "Y")])
    return directory


def form(**overrides):
    values = dict(role_id=ROLE, channel_id=CHANNEL, racetime_categories=["alttpr"], minimum_races=5,
                  time_period_days=365)
    values.update(overrides)
    return rv.VerificationInput(**values)


async def make_racer(verification, discord_id, name, last=NOW - timedelta(days=100), count=10):
    user = await models.Users.create(discord_user_id=discord_id, display_name=name, rtgg_id=f"rt{discord_id}")
    return await models.VerifiedRacer.create(user=user, racer_verification_id=verification["id"],
                                             last_verified=last, estimated_count=count)


async def audit_actions():
    return [e.action for e in await models.AuditLog.all().order_by('id')]


# --- Managing ---------------------------------------------------------------------

async def test_create_posts_the_message_and_records_it(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form(reverify_period_days=90, revoke_ineligible=True,
                                                 audit_channel_id=LOG_CHANNEL, use_alttpr_ladder=True))
    assert created["role_name"] == "Verified Racer"
    assert created["channel_name"] == "get-verified"
    assert created["audit_channel_name"] == "mod-log"
    assert created["requirement"] == "5 races in 365 days"
    assert created["message_id"] == 9001
    assert created["verified_count"] == 0
    channel, _, content = gateway.posted[0]
    assert channel == CHANNEL
    assert "at least 5 races played in the last 365 days" in content
    assert "alttpr or ALTTPR Ladder races" in content
    assert "counted again every 90 days" in content
    assert await audit_actions() == ['racer_verification.configured']


async def test_create_refuses_what_it_should(db, server, gateway):
    with pytest.raises(PermissionDeniedError):
        await rv.create(GUILD, OUTSIDER, form())
    with pytest.raises(InvalidInputError, match="role isn't in this server"):
        await rv.create(GUILD, ADMIN, form(role_id=79))
    with pytest.raises(InvalidInputError, match="can't post in that channel"):
        await rv.create(GUILD, ADMIN, form(channel_id=400))
    with pytest.raises(InvalidInputError, match="channel for reports"):
        await rv.create(GUILD, ADMIN, form(audit_channel_id=400))
    with pytest.raises(InvalidInputError, match="at least one racetime.gg category"):
        await rv.create(GUILD, ADMIN, form(racetime_categories=[]))
    with pytest.raises(InvalidInputError, match="isn't a racetime.gg category"):
        await rv.create(GUILD, ADMIN, form(racetime_categories=["al ttpr"]))
    with pytest.raises(InvalidInputError, match="Races needed"):
        await rv.create(GUILD, ADMIN, form(minimum_races=0))
    with pytest.raises(InvalidInputError, match="counting period"):
        await rv.create(GUILD, ADMIN, form(time_period_days=0))
    with pytest.raises(InvalidInputError, match="Recheck every"):
        await rv.create(GUILD, ADMIN, form(reverify_period_days=0))

    await rv.create(GUILD, ADMIN, form())
    with pytest.raises(InvalidInputError, match="already has racer verification"):
        await rv.create(GUILD, OWNER, form())


async def test_create_keeps_nothing_when_discord_refuses_the_post(db, server, gateway):
    gateway.post_error = InvalidInputError("SahasrahBot isn't allowed to post in that channel.")
    with pytest.raises(InvalidInputError):
        await rv.create(GUILD, ADMIN, form())
    assert not await models.RacerVerification.exists()


async def test_revoke_needs_rechecks(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form(revoke_ineligible=True))
    assert created["revoke_ineligible"] is False


async def test_list_and_get(db, server, gateway):
    first = await rv.create(GUILD, ADMIN, form())
    await rv.create(GUILD, ADMIN, form(role_id=OTHER_ROLE, racetime_categories=["alttpr", "smz3", "alttpr"]))
    await make_racer(first, 100, "Linkle")
    listed = await rv.list_for_guild(GUILD, ADMIN)
    assert [(v["role_name"], v["verified_count"]) for v in listed] == [("Verified Racer", 1), ("Mystery Racer", 0)]
    assert listed[1]["racetime_categories"] == ["alttpr", "smz3"]
    assert (await rv.get_for_admin(first["id"], OWNER))["id"] == first["id"]
    with pytest.raises(PermissionDeniedError):
        await rv.list_for_guild(GUILD, OUTSIDER)
    with pytest.raises(PermissionDeniedError):
        await rv.get_for_admin(first["id"], OUTSIDER)
    with pytest.raises(NotFoundError):
        await rv.get_for_admin(999, ADMIN)


async def test_update_edits_the_message_and_audits_the_changes(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form())
    updated = await rv.update(created["id"], ADMIN, form(minimum_races=3, reverify_period_days=30))
    assert updated["requirement"] == "3 races in 365 days"
    assert gateway.edited[0][:2] == (CHANNEL, 9001)
    assert "counted again every 30 days" in gateway.edited[0][2]
    entry = await models.AuditLog.filter(action='racer_verification.updated').first()
    assert entry.details["changes"]["minimum_races"] == [5, 3]

    # No change, no audit entry.
    await rv.update(created["id"], ADMIN, form(minimum_races=3, reverify_period_days=30))
    assert await models.AuditLog.filter(action='racer_verification.updated').count() == 1


async def test_update_reposts_a_deleted_message_or_a_moved_one(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form())
    gateway.message_gone = True
    again = await rv.update(created["id"], ADMIN, form())
    assert again["message_id"] == 9002

    moved = await rv.update(created["id"], ADMIN, form(channel_id=NEW_CHANNEL))
    assert moved["channel_id"] == NEW_CHANNEL and moved["message_id"] == 9003
    assert gateway.deleted == [(CHANNEL, 9002)]


async def test_update_refuses_a_role_already_set_up(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form())
    await rv.create(GUILD, ADMIN, form(role_id=OTHER_ROLE))
    with pytest.raises(InvalidInputError, match="already has racer verification"):
        await rv.update(created["id"], ADMIN, form(role_id=OTHER_ROLE))


async def test_repost_and_delete(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form())
    await make_racer(created, 100, "Linkle")
    reposted = await rv.repost(created["id"], ADMIN)
    assert reposted["message_id"] == 9002
    assert gateway.deleted == [(CHANNEL, 9001)]

    await rv.delete(created["id"], ADMIN)
    assert gateway.deleted[-1] == (CHANNEL, 9002)
    assert not await models.RacerVerification.exists()
    assert not await models.VerifiedRacer.exists()
    assert gateway.removed == []  # nobody loses the role
    assert (await audit_actions())[-2:] == ['racer_verification.reposted', 'racer_verification.deleted']


# --- Verified racers ----------------------------------------------------------------

async def test_list_racers_shows_their_status(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form(reverify_period_days=90))
    await make_racer(created, 100, "Linkle", last=NOW - timedelta(days=10))
    await make_racer(created, 101, "Overdue", last=NOW - timedelta(days=100))
    await make_racer(created, 102, "Slowpoke", last=NOW - timedelta(days=20), count=2)
    racers = await rv.list_racers(created["id"], ADMIN, now=NOW)
    assert [(r["name"], r["status"]) for r in racers] == [
        ("Linkle", rv.OK), ("Slowpoke", rv.FAILING), ("Overdue", rv.DUE)]
    assert racers[0]["next_check"] == NOW + timedelta(days=80)
    assert racers[0]["racetime_url"].endswith("/user/rt100/")


async def test_racers_never_come_due_without_rechecks(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form())
    await make_racer(created, 100, "Linkle", last=NOW - timedelta(days=1000))
    [racer] = await rv.list_racers(created["id"], ADMIN, now=NOW)
    assert (racer["status"], racer["next_check"]) == (rv.OK, None)


async def test_remove_racer_takes_the_role(db, server, gateway):
    created = await rv.create(GUILD, ADMIN, form())
    racer = await make_racer(created, 100, "Linkle")
    with pytest.raises(PermissionDeniedError):
        await rv.remove_racer(created["id"], racer.id, OUTSIDER)
    await rv.remove_racer(created["id"], racer.id, ADMIN)
    assert gateway.removed == [(GUILD, 100, ROLE)]
    assert not await models.VerifiedRacer.exists()
    with pytest.raises(NotFoundError):
        await rv.remove_racer(created["id"], racer.id, ADMIN)
    entry = await models.AuditLog.filter(action='racer_verification.revoked').first()
    assert entry.details["reason"] == "removed"


@pytest.fixture
def counts(monkeypatch):
    """Race counts by discord id for determine_eligibility."""
    table = {}

    async def eligibility(username, user, verification):
        count = table[user.discord_user_id]
        return count >= verification.minimum_races, count

    monkeypatch.setattr(rv, "determine_eligibility", eligibility)
    return table


async def test_recheck_due_keeps_revokes_and_forgets(db, server, gateway, counts, published):
    created = await rv.create(GUILD, ADMIN, form(reverify_period_days=90, revoke_ineligible=True,
                                                 audit_channel_id=LOG_CHANNEL))
    keep = await make_racer(created, 100, "Keeper")
    await make_racer(created, 101, "Lapsed")
    await make_racer(created, 102, "Gone")
    fresh = await make_racer(created, 103, "Fresh", last=NOW - timedelta(days=5))
    gateway.members = {100: "keeper", 101: "lapsed", 103: "fresh"}
    counts.update({100: 9, 101: 1, 103: 0})

    await rv.recheck_due(now=NOW)

    assert gateway.removed == [(GUILD, 101, ROLE)]
    remaining = {r.id: r for r in await models.VerifiedRacer.all()}
    assert set(remaining) == {keep.id, fresh.id}
    assert remaining[keep.id].estimated_count == 9
    assert remaining[keep.id].last_verified == NOW
    [event] = published
    assert event == events.RacerVerificationRechecked(
        racer_verification_id=created["id"], guild_id=GUILD, role_id=ROLE, audit_channel_id=LOG_CHANNEL,
        revoked=("Lapsed",), not_qualified=(), left=("Gone",))


async def test_recheck_without_revoke_only_reports(db, server, gateway, counts, published):
    created = await rv.create(GUILD, ADMIN, form(reverify_period_days=90))
    await make_racer(created, 101, "Lapsed")
    gateway.members = {101: "lapsed"}
    counts[101] = 1

    await rv.recheck_due(now=NOW)

    assert gateway.removed == []
    racer = await models.VerifiedRacer.get()
    assert (racer.estimated_count, racer.last_verified) == (1, NOW)
    assert published[0].not_qualified == ("Lapsed",)
    [view] = await rv.list_racers(created["id"], ADMIN, now=NOW)
    assert view["status"] == rv.FAILING

    # Checked now, so not due again until the next period: nothing more is reported.
    published.clear()
    await rv.recheck_due(now=NOW + timedelta(days=1))
    assert published == []


async def test_recheck_skips_verifications_without_rechecks_and_survives_errors(db, server, gateway, counts,
                                                                                published, monkeypatch):
    plain = await rv.create(GUILD, ADMIN, form())
    await make_racer(plain, 100, "Untouched")
    checked = await rv.create(GUILD, ADMIN, form(role_id=OTHER_ROLE, reverify_period_days=30))
    await make_racer(checked, 101, "Broken")
    await make_racer(checked, 102, "Fine", last=NOW - timedelta(days=60))
    gateway.members = {100: "u", 101: "b", 102: "f"}
    counts.update({100: 0, 102: 7})  # 101 raises KeyError, like racetime.gg failing

    await rv.recheck_due(now=NOW)

    racers = {r.user_id: r for r in await models.VerifiedRacer.all().prefetch_related('user')}
    assert len(racers) == 3
    fine = next(r for r in racers.values() if r.user.display_name == "Fine")
    assert fine.last_verified == NOW
    assert published == []


async def test_recheck_racer_now(db, server, gateway, counts, published):
    created = await rv.create(GUILD, ADMIN, form(reverify_period_days=90, revoke_ineligible=True))
    racer = await make_racer(created, 100, "Linkle", last=NOW - timedelta(days=3))
    gateway.members = {100: "linkle"}
    counts[100] = 6
    view = await rv.recheck_racer(created["id"], racer.id, ADMIN, now=NOW)
    assert (view["race_count"], view["last_checked"]) == (6, NOW)

    counts[100] = 0
    assert await rv.recheck_racer(created["id"], racer.id, ADMIN, now=NOW) is None
    assert gateway.removed == [(GUILD, 100, ROLE)]
    assert published[0].revoked == ("Linkle",)


# --- The audit channel report -------------------------------------------------------

def test_recheck_report_messages():
    event = events.RacerVerificationRechecked(racer_verification_id=1, guild_id=GUILD, role_id=ROLE,
                                              revoked=("a_b",), not_qualified=("C", "D"), left=())
    assert notifications.racer_recheck_messages(event) == [
        "**1** person lost the <@&77> role: they no longer meet the requirements:\n- a\\_b",
        "**2** people no longer meet the requirements for <@&77> but kept it (removing the role is off):\n- C\n- D",
    ]


def test_long_recheck_reports_are_split():
    names = tuple(f"racer{i:03}" for i in range(300))
    event = events.RacerVerificationRechecked(racer_verification_id=1, guild_id=GUILD, role_id=ROLE, left=names)
    messages = notifications.racer_recheck_messages(event)
    assert len(messages) > 1
    assert all(len(m) <= 1900 for m in messages)
    assert sum(m.count("racer") for m in messages) == 300


async def test_recheck_report_goes_to_the_audit_channel(monkeypatch):
    channel = SimpleNamespace(send=mock.AsyncMock())
    bot = SimpleNamespace(get_channel=lambda cid: channel if cid == LOG_CHANNEL else None)
    monkeypatch.setattr(notifications, "wait_until_ready", mock.AsyncMock())
    jobs = notifications.ScheduledJobDiscordOutput(bot)
    await jobs.report_racer_recheck(events.RacerVerificationRechecked(
        racer_verification_id=1, guild_id=GUILD, role_id=ROLE, audit_channel_id=LOG_CHANNEL, left=("X",)))
    assert channel.send.await_args.args[0].startswith("**1** person left the server")

    channel.send.reset_mock()
    await jobs.report_racer_recheck(events.RacerVerificationRechecked(
        racer_verification_id=1, guild_id=GUILD, role_id=ROLE, left=("X",)))
    channel.send.assert_not_awaited()


# --- The Discord gateway ------------------------------------------------------------

def _not_found():
    return discord.NotFound(SimpleNamespace(status=404, reason="Not Found"), "gone")


def _forbidden():
    return discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), "no")


async def test_gateway_posts_edits_and_deletes():
    message = SimpleNamespace(edit=mock.AsyncMock(), delete=mock.AsyncMock())
    channel = SimpleNamespace(send=mock.AsyncMock(return_value=SimpleNamespace(id=55)),
                              get_partial_message=lambda mid: message)
    bot = SimpleNamespace(get_channel=lambda cid: channel)
    gw = rv_discord.DiscordGateway(bot)

    assert await gw.post_message(CHANNEL, "hi") == 55
    assert isinstance(channel.send.await_args.kwargs["view"], rv_discord.RacerVerificationView)
    assert await gw.edit_message(CHANNEL, 55, "new") is True
    message.edit.side_effect = _not_found()
    assert await gw.edit_message(CHANNEL, 55, "new") is False
    message.delete.side_effect = _not_found()
    await gw.delete_message(CHANNEL, 55)  # already gone is fine

    channel.send.side_effect = _forbidden()
    with pytest.raises(InvalidInputError, match="isn't allowed to post"):
        await gw.post_message(CHANNEL, "hi")


async def test_gateway_members_and_roles():
    member = SimpleNamespace(name="linkle", remove_roles=mock.AsyncMock())
    guild = SimpleNamespace(id=GUILD, get_member=lambda uid: None, fetch_member=mock.AsyncMock(return_value=member))
    bot = SimpleNamespace(get_guild=lambda gid: guild)
    gw = rv_discord.DiscordGateway(bot)

    assert await gw.member_name(GUILD, 100) == "linkle"
    await gw.remove_role(GUILD, 100, ROLE, reason="x")
    assert member.remove_roles.await_args.args[0].id == ROLE

    guild.fetch_member.side_effect = _not_found()
    assert await gw.member_name(GUILD, 100) is None
    await gw.remove_role(GUILD, 100, ROLE, reason="x")  # they left: nothing to do

    guild.fetch_member.side_effect = discord.HTTPException(SimpleNamespace(status=500, reason="x"), "boom")
    with pytest.raises(discord.HTTPException):
        await gw.member_name(GUILD, 100)  # an outage is never taken for leaving

    guild.fetch_member.side_effect = None
    member.remove_roles.side_effect = _forbidden()
    with pytest.raises(InvalidInputError, match="isn't allowed to remove"):
        await gw.remove_role(GUILD, 100, ROLE, reason="x")


def test_gateway_registers():
    rv_discord.register(SimpleNamespace())
    assert isinstance(rv.gateway(), rv_discord.DiscordGateway)


# --- The API ------------------------------------------------------------------------

async def test_api_round_trip(client, login, server, gateway, counts):  # noqa: F811
    login(ADMIN)
    body = {"role_id": str(ROLE), "channel_id": str(CHANNEL), "racetime_categories": ["alttpr"],
            "minimum_races": 2, "reverify_period_days": 30, "revoke_ineligible": True,
            "audit_channel_id": str(LOG_CHANNEL)}
    status, created = await send_json(client, "POST", f"/api/v1/servers/{GUILD}/racer-verifications", body)
    assert status == 201, created
    assert (created["role_id"], created["message_id"], created["revoke_ineligible"]) == (str(ROLE), "9001", True)
    vid = created["id"]

    status, listed = await get_json(client, f"/api/v1/servers/{GUILD}/racer-verifications")
    assert status == 200
    assert [v["id"] for v in listed["verifications"]] == [vid]
    assert "alttpr" in listed["racetime_categories"]

    status, got = await get_json(client, f"/api/v1/racer-verifications/{vid}")
    assert (status, got["requirement"]) == (200, "2 races in 365 days")

    status, updated = await send_json(client, "PUT", f"/api/v1/racer-verifications/{vid}",
                                      {**body, "minimum_races": 4})
    assert (status, updated["minimum_races"]) == (200, 4)

    status, bad = await send_json(client, "PUT", f"/api/v1/racer-verifications/{vid}", {**body, "role_id": "x"})
    assert (status, bad["error"]) == (400, "That role isn't a Discord id.")

    racer = await make_racer(created, 100, "Linkle")
    status, racers = await get_json(client, f"/api/v1/racer-verifications/{vid}/racers")
    assert (status, racers["racers"][0]["discord_user_id"]) == (200, "100")

    gateway.members = {100: "linkle"}
    counts[100] = 8
    status, rechecked = await send_json(client, "POST", f"/api/v1/racer-verifications/{vid}/racers/{racer.id}/recheck")
    assert (status, rechecked["racer"]["race_count"]) == (200, 8)

    status, reposted = await send_json(client, "POST", f"/api/v1/racer-verifications/{vid}/repost")
    assert (status, reposted["message_id"]) == (200, "9002")

    resp = await client.delete(f"/api/v1/racer-verifications/{vid}/racers/{racer.id}", headers=CSRF)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/racer-verifications/{vid}", headers=CSRF)
    assert resp.status_code == 204


async def test_api_refuses_outsiders(client, login, server, gateway):  # noqa: F811
    login(OUTSIDER)
    status, body = await get_json(client, f"/api/v1/servers/{GUILD}/racer-verifications")
    assert status == 403
    assert "administrators" in body["error"]

"""Tests for the services that took over the last direct model queries in the front ends:
the racetime.gg account link and merge, API keys, ranked choice elections run from
Discord, scheduled-event bookkeeping, racetime.gg watchers, preset downloads, tournament
games, inquiry messages and the generated-games audit.

They pin what the blueprints, cogs and notifications did before the move.
"""

import pytest
from tortoise.exceptions import DoesNotExist

import testdata
from alttprbot import models
from alttprbot.exceptions import InvalidInputError, PermissionDeniedError
from alttprbot.services import (accounts, api_keys, generated_games, inquiries, presets, ranked_choice,
                                rtgg_watchers, scheduled_events, tournament_games)

DISCORD_ID = 4242
OWNER = 111
OTHER = 222

# ---------------------------------------------------------------------------
# accounts.link_racetime
# ---------------------------------------------------------------------------


async def test_link_racetime_new_user(db):
    await accounts.link_racetime(DISCORD_ID, "alice", "rt-new", "tok")
    user = await models.Users.get(discord_user_id=DISCORD_ID)
    assert (user.rtgg_id, user.rtgg_access_token, user.display_name) == ("rt-new", "tok", "alice")


async def test_link_racetime_existing_discord_user(db):
    await models.Users.create(discord_user_id=DISCORD_ID, display_name="old")
    await accounts.link_racetime(DISCORD_ID, "alice", "rt-new", "tok")
    assert await models.Users.all().count() == 1
    user = await models.Users.get(discord_user_id=DISCORD_ID)
    assert (user.rtgg_id, user.rtgg_access_token, user.display_name) == ("rt-new", "tok", "alice")


async def test_link_racetime_existing_racetime_user(db):
    await models.Users.create(rtgg_id="rt-1", display_name="racer")
    await accounts.link_racetime(DISCORD_ID, "alice", "rt-1", "tok")
    assert await models.Users.all().count() == 1
    user = await models.Users.get(rtgg_id="rt-1")
    assert (user.discord_user_id, user.rtgg_access_token, user.display_name) == (DISCORD_ID, "tok", "alice")


async def test_link_racetime_same_row_again(db):
    await models.Users.create(discord_user_id=DISCORD_ID, rtgg_id="rt-1", rtgg_access_token="old")
    await accounts.link_racetime(DISCORD_ID, "alice", "rt-1", "new")
    user = await models.Users.get(rtgg_id="rt-1")
    assert (user.discord_user_id, user.rtgg_access_token, user.display_name) == (DISCORD_ID, "new", "alice")


async def test_link_racetime_merges_two_rows_into_the_racetime_one(db):
    """A Discord-only row and a racetime-only row become one; the async tournament rows
    (tables kept after the feature was removed) follow the kept user."""
    await testdata.load("asynctournament")
    victim = await models.Users.get(id=1066)  # the runner with the most async races
    victim.rtgg_id = None
    await victim.save()
    races = await models.AsyncTournamentRace.filter(user_id=1066).count()
    assert races > 0
    kept = await models.Users.create(rtgg_id="rt-merge", rtgg_access_token="kept-token", display_name="x")

    await accounts.link_racetime(victim.discord_user_id, "merged", "rt-merge", "fresh-token")

    assert not await models.Users.filter(id=1066).exists()
    kept = await models.Users.get(id=kept.id)
    assert (kept.discord_user_id, kept.rtgg_id, kept.display_name) == (victim.discord_user_id, "rt-merge", "merged")
    # The merge path keeps the stored token, as it always has.
    assert kept.rtgg_access_token == "kept-token"
    assert await models.AsyncTournamentRace.filter(user_id=kept.id).count() == races


async def test_merge_users_moves_reviews_permissions_and_notes(db):
    await testdata.load("asynctournament")
    reviewer = await models.Users.get(id=1024)
    reviewed = await models.AsyncTournamentRace.filter(reviewed_by_id=1024).count()
    perms = await models.AsyncTournamentPermissions.filter(user_id=1024).count()
    keep = await models.Users.create(display_name="keep")

    await accounts.merge_users(keep, reviewer)

    assert await models.AsyncTournamentRace.filter(reviewed_by_id=keep.id).count() == reviewed
    assert await models.AsyncTournamentPermissions.filter(user_id=keep.id).count() == perms
    assert not await models.Users.filter(id=1024).exists()


# ---------------------------------------------------------------------------
# api_keys
# ---------------------------------------------------------------------------


async def test_racetime_command_key(db):
    key = await models.AuthorizationKeys.create(key="secret", name="tool")
    await models.AuthorizationKeyPermissions.create(auth_key=key, type="racetimecmd", subtype="alttpr")
    await models.AuthorizationKeyPermissions.create(auth_key=key, type="other", subtype="smz3")

    assert await api_keys.can_run_racetime_command("secret", "alttpr") is True
    assert await api_keys.can_run_racetime_command("secret", "smz3") is False
    assert await api_keys.can_run_racetime_command("wrong", "alttpr") is False


# ---------------------------------------------------------------------------
# ranked choice elections from Discord
# ---------------------------------------------------------------------------


async def _election(**overrides):
    kwargs = dict(title="Vote", description=None, candidates=[" Alex", "Blair ", "Casey"], seats=1,
                  guild_id=1, channel_id=2, owner_id=OWNER, voter_role_id=None, show_vote_count=True)
    return await ranked_choice.create_election(**{**kwargs, **overrides})


async def test_create_election(db):
    election = await _election()
    assert (election.active, election.private, election.message_id) == (True, False, None)
    assert [c.name for c in election.candidates] == ["Alex", "Blair", "Casey"]
    assert list(election.votes) == []

    private = await _election(voter_role_id=99)
    assert (private.private, private.voter_role_id) == (True, 99)


async def test_set_message_id_and_get_election(db):
    election = await _election()
    await ranked_choice.set_message_id(election.id, 5555)
    assert (await ranked_choice.get_election(election.id)).message_id == 5555
    assert await ranked_choice.get_election(987654) is None


async def test_end_election(db):
    election = await _election()
    await ranked_choice.set_message_id(election.id, 5555)
    blair = next(c for c in election.candidates if c.name == "Blair")
    alex = next(c for c in election.candidates if c.name == "Alex")
    await models.RankedChoiceVotes.create(election=election, candidate=blair, user_id=1, rank=1)
    await models.RankedChoiceVotes.create(election=election, candidate=blair, user_id=2, rank=1)
    await models.RankedChoiceVotes.create(election=election, candidate=alex, user_id=3, rank=1)

    with pytest.raises(PermissionDeniedError, match="not the owner"):
        await ranked_choice.end_election(5555, OTHER)
    assert (await ranked_choice.get_election(election.id)).active is True

    closed = await ranked_choice.end_election(5555, OWNER)
    assert closed.active is False
    assert closed.results
    assert {c.name for c in await models.RankedChoiceCandidate.filter(election=election, winner=True)} == {"Blair"}

    with pytest.raises(InvalidInputError, match="already closed"):
        await ranked_choice.end_election(5555, OWNER)
    with pytest.raises(DoesNotExist):
        await ranked_choice.end_election(1, OWNER)


# ---------------------------------------------------------------------------
# scheduled events
# ---------------------------------------------------------------------------


async def test_scheduled_events(db):
    await scheduled_events.remember(1, 100, "alttpr")
    await scheduled_events.remember(2, 200, "alttpr")
    await scheduled_events.remember(3, 300, "smz3")

    assert [e.episode_id for e in await scheduled_events.stale("alttpr", [2])] == [1]
    assert (await scheduled_events.for_episode(2)).scheduled_event_id == 200
    assert await scheduled_events.for_episode(9) is None

    await scheduled_events.forget(100)
    assert await scheduled_events.for_episode(1) is None
    assert await models.ScheduledEvents.all().count() == 2


async def test_remember_replaces_a_recreated_guild_event(db):
    """When a mirrored guild event was deleted in Discord, notifications.py creates a new
    one and calls ``remember`` with its id. The row must then point at the new event, or
    every later refresh creates yet another duplicate."""
    await scheduled_events.remember(2, 200, "alttpr")
    await scheduled_events.remember(2, 201, "alttpr")
    assert (await scheduled_events.for_episode(2)).scheduled_event_id == 201
    assert await models.ScheduledEvents.all().count() == 1

    # Remembering the same event again changes nothing.
    await scheduled_events.remember(2, 201, "alttpr")
    assert [(e.scheduled_event_id, e.episode_id) for e in await models.ScheduledEvents.all()] == [(201, 2)]


# ---------------------------------------------------------------------------
# racetime.gg watchers
# ---------------------------------------------------------------------------


async def test_rtgg_watchers(db):
    alttpr = await models.RTGGWatcher.create(guild_id=1, channel_id=10, category="alttpr", notify_on_new_player=True)
    quiet = await models.RTGGWatcher.create(guild_id=2, channel_id=20, category="alttpr")
    await models.RTGGWatcher.create(guild_id=3, channel_id=30, category="smz3", notify_on_new_player=True)
    await models.RTGGWatcherPlayer.create(rtgg_watcher=alttpr, racetime_id="bad1")
    await models.RTGGWatcherPlayer.create(rtgg_watcher=quiet, racetime_id="bad1")
    await models.RTGGWatcherPlayer.create(rtgg_watcher=quiet, racetime_id="bad2")

    hits = await rtgg_watchers.watchlisted_entrants("alttpr", ("bad1", "someone"))
    assert sorted((h.channel_id, h.racetime_id) for h in hits) == [(10, "bad1"), (20, "bad1")]
    assert await rtgg_watchers.watchlisted_entrants("smz3", ["bad1"]) == []

    assert await rtgg_watchers.new_player_channels("alttpr") == [10]
    assert await rtgg_watchers.new_player_channels("ootr") == []


# ---------------------------------------------------------------------------
# preset downloads and JSON
# ---------------------------------------------------------------------------


async def test_preset_content(db):
    await testdata.load("presets")
    preset = await models.Presets.get(id=1001).prefetch_related("namespace")
    content = await presets.preset_content(preset.namespace.name, preset.randomizer, preset.preset_name)
    assert content == preset.content
    assert await presets.preset_content(preset.namespace.name, "smz3", preset.preset_name) is None
    assert await presets.preset_content("nobody", preset.randomizer, preset.preset_name) is None


async def test_namespace_preset_names(db):
    await testdata.load("presets")
    listed = await presets.namespace_preset_names("alttpr")
    expected = {}
    for p in await models.Presets.filter(randomizer="alttpr").prefetch_related("namespace"):
        expected.setdefault(p.namespace.name, set()).add(p.preset_name)
    assert {ns["name"]: set(ns["presets"]) for ns in listed} == expected
    assert all(ns["presets"] for ns in listed)
    assert await presets.namespace_preset_names("nothing") == []


# ---------------------------------------------------------------------------
# tournament games, inquiries, generated games
# ---------------------------------------------------------------------------


async def test_tournament_games_search(db):
    await models.TournamentGames.create(episode_id=1, event="alttpr", preset="open")
    await models.TournamentGames.create(episode_id=2, event="smz3", preset="normal")
    rows = await tournament_games.search({"event": "alttpr"})
    assert [(r["episode_id"], r["preset"]) for r in rows] == [(1, "open")]
    assert len(await tournament_games.search({})) == 2


async def test_inquiries(db):
    await inquiries.register(5555, 77)
    assert await inquiries.role_for_message(5555) == 77
    with pytest.raises(DoesNotExist):
        await inquiries.role_for_message(1)


async def test_generated_games(db):
    await models.AuditGeneratedGames.create(hash_id="abc", randomizer="alttpr", permalink="https://x/abc")
    assert (await generated_games.find_by_hash("abc")).permalink == "https://x/abc"
    assert await generated_games.find_by_hash("zzz") is None

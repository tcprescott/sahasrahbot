"""Elections: the service (alttprbot/services/elections.py) and its Discord side
(alttprbot_discord/elections.py)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import events, models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import discord_directory, elections
from alttprbot.services.elections import ElectionInput
from alttprbot_discord import elections as election_posts
from tests.discord_fakes import FakeDirectory

ADMIN, OWNER, VOTER, MEMBER, OUTSIDER = 7, 1, 9, 10, 11
GUILD, OTHER_GUILD = 5, 6


@pytest.fixture
def published(monkeypatch):
    sent = []
    monkeypatch.setattr(events, "publish", sent.append)
    return sent


@pytest.fixture
def server(directory):
    directory.owner = OWNER
    directory.add_guild(GUILD, name="Community", admins=[ADMIN], members={VOTER: [77], MEMBER: []},
                        channels=[(300, "#votes")], roles=[(77, "@Voters")])
    directory.add_guild(OTHER_GUILD, name="Elsewhere", admins=[], channels=[(400, "#x")])
    return directory


def form(**overrides):
    values = dict(guild_id=GUILD, channel_id=300, title="Committee", candidates=["Andy", "Bea", "Coral"])
    values.update(overrides)
    return ElectionInput(**values)


async def posted(method="stv", **overrides):
    draft = await elections.create_draft(ADMIN, form(method=method, **overrides))
    return await elections.publish(draft["id"], ADMIN)


def later(hours=1):
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# --- who may do what ---------------------------------------------------------


async def test_admins_and_the_owner_manage(db, server):
    assert await elections.is_admin(GUILD, ADMIN)
    assert await elections.is_admin(GUILD, OWNER)
    assert await elections.is_admin(None, OWNER)
    assert not await elections.is_admin(GUILD, VOTER)
    assert not await elections.is_admin(None, ADMIN)
    assert await elections.can_manage_elections(ADMIN)
    assert await elections.can_manage_elections(OWNER)
    assert not await elections.can_manage_elections(VOTER)
    assert await elections.servers(ADMIN) == [{"id": GUILD, "name": "Community"}]


async def test_server_options(db, server):
    options = await elections.server_options(GUILD, ADMIN)
    assert options == {"channels": [{"id": 300, "name": "#votes"}], "roles": [{"id": 77, "name": "@Voters"}]}
    with pytest.raises(PermissionDeniedError):
        await elections.server_options(GUILD, VOTER)


async def test_no_directory_registered_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(discord_directory, "_directory", None)
    with pytest.raises(RuntimeError, match="No Discord directory"):
        discord_directory.get()
    fake = FakeDirectory()
    discord_directory.register(fake)
    assert discord_directory.get() is fake


# --- creating, editing, posting ------------------------------------------------


async def test_create_draft_cleans_and_orders_candidates(db, server):
    draft = await elections.create_draft(ADMIN, form(candidates=[" Coral ", "", "Andy"], description="  "))
    assert draft["status"] == "draft"
    assert [c["name"] for c in draft["candidates"]] == ["Coral", "Andy"]
    assert draft["description"] is None
    assert (draft["guild_name"], draft["locked"], draft["ballots"]) == ("Community", False, 0)
    election = await models.RankedChoiceElection.get(id=draft["id"])
    assert (election.active, election.private, election.owner_id) == (False, False, ADMIN)


@pytest.mark.parametrize("overrides, message", [
    (dict(title="  "), "title"),
    (dict(title="x" * 201), "200 characters"),
    (dict(description="x" * 2001), "2000 characters"),
    (dict(method="borda"), "voting method"),
    (dict(candidates=["A", "a"]), "only be listed once"),
    (dict(candidates=["x" * 201, "B"]), "candidate's name"),
    (dict(candidates=[str(i) for i in range(101)]), "at most 100"),
    (dict(seats=0), "fewer winners"),
    (dict(closes_at=datetime(2030, 1, 1)), "time zone"),
    (dict(channel_id=999), "can't post in that channel"),
    (dict(voter_role_id=12345), "role isn't in this server"),
])
async def test_create_draft_refuses_bad_forms(db, server, overrides, message):
    bad = form(**overrides)
    with pytest.raises(InvalidInputError, match=message):
        await elections.create_draft(ADMIN, bad)


async def test_only_admins_create(db, server):
    mine, elsewhere = form(), form(guild_id=OTHER_GUILD, channel_id=400)
    with pytest.raises(PermissionDeniedError):
        await elections.create_draft(VOTER, mine)
    with pytest.raises(PermissionDeniedError):
        await elections.create_draft(ADMIN, elsewhere)


async def test_drafts_may_be_incomplete_but_posting_needs_everything(db, server):
    draft = await elections.create_draft(ADMIN, form(candidates=["Only one"]))
    with pytest.raises(InvalidInputError, match="at least two"):
        await elections.publish(draft["id"], ADMIN)
    past = await elections.create_draft(ADMIN, form(closes_at=later(-1)))
    with pytest.raises(InvalidInputError, match="already passed"):
        await elections.publish(past["id"], ADMIN)
    many = await elections.create_draft(ADMIN, form(seats=3))
    with pytest.raises(InvalidInputError, match="fewer winners"):
        await elections.publish(many["id"], ADMIN)
    assert not server.posted


async def test_non_ranked_elections_have_one_winner(db, server):
    draft = await elections.create_draft(ADMIN, form(method="approval", seats=3))
    assert draft["seats"] == 1


async def test_publish_posts_and_opens(db, server):
    election = await posted(voter_role_id=77, closes_at=later())
    assert (election["status"], election["message_id"], election["voter_role_id"]) == ("open", 9001, 77)
    row = await models.RankedChoiceElection.get(id=election["id"])
    assert (row.active, row.private) == (True, True)
    with pytest.raises(InvalidInputError, match="already been posted"):
        await elections.publish(election["id"], ADMIN)


async def test_a_failed_post_leaves_it_a_draft(db, server):
    server.post_error = InvalidInputError("SahasrahBot isn't allowed to post in that channel.")
    draft = await elections.create_draft(ADMIN, form())
    with pytest.raises(InvalidInputError, match="isn't allowed"):
        await elections.publish(draft["id"], ADMIN)
    row = await models.RankedChoiceElection.get(id=draft["id"])
    assert (row.status, row.active, row.message_id) == ("draft", False, None)


async def test_edit_a_draft_freely(db, server, published):
    draft = await elections.create_draft(ADMIN, form())
    edited = await elections.update(draft["id"], ADMIN, form(title="New", method="plurality",
                                                             candidates=["X", "Y"]))
    assert (edited["title"], edited["method"]) == ("New", "plurality")
    assert [c["name"] for c in edited["candidates"]] == ["X", "Y"]
    assert published == []  # not posted yet, nothing to refresh


async def test_edit_an_open_election_refreshes_its_post(db, server, published):
    election = await posted()
    edited = await elections.update(election["id"], ADMIN, form(title="Renamed", description="Now with words"))
    assert edited["title"] == "Renamed"
    assert [type(e) for e in published] == [events.ElectionUpdated]
    moved = form(channel_id=301)
    with pytest.raises(InvalidInputError, match="another channel"):
        await elections.update(election["id"], ADMIN, moved)


async def test_moving_servers(db, server):
    server.guilds[OTHER_GUILD]["admins"].add(ADMIN)
    draft = await elections.create_draft(ADMIN, form())
    moved = await elections.update(draft["id"], ADMIN, form(guild_id=OTHER_GUILD, channel_id=400))
    assert moved["guild_id"] == OTHER_GUILD
    election = await posted()
    moved = form(guild_id=OTHER_GUILD, channel_id=400)
    with pytest.raises(InvalidInputError, match="another server"):
        await elections.update(election["id"], ADMIN, moved)


async def test_ballots_lock_candidates_and_method(db, server, published):
    election = await posted()
    andy = election["candidates"][0]["id"]
    await elections.cast_ballot(election["id"], VOTER, [andy])
    for change in (dict(candidates=["Andy", "Bea"]), dict(method="approval")):
        changed = form(**change)
        with pytest.raises(InvalidInputError, match="already voted"):
            await elections.update(election["id"], ADMIN, changed)
    assert (await elections.update(election["id"], ADMIN, form(title="Still fine")))["locked"] is True


async def test_closed_elections_cant_be_edited(db, server, published):
    election = await posted()
    await elections.close(election["id"], ADMIN)
    unchanged = form()
    with pytest.raises(InvalidInputError, match="has closed"):
        await elections.update(election["id"], ADMIN, unchanged)


async def test_missing_election_and_strangers(db, server):
    with pytest.raises(NotFoundError):
        await elections.get_for_admin(404, ADMIN)
    draft = await elections.create_draft(ADMIN, form())
    with pytest.raises(PermissionDeniedError):
        await elections.get_for_admin(draft["id"], VOTER)
    assert (await elections.get_for_admin(draft["id"], OWNER))["id"] == draft["id"]


async def test_list_elections(db, server):
    mine = await elections.create_draft(ADMIN, form())
    other = await models.RankedChoiceElection.create(owner_id=2, title="Theirs", guild_id=OTHER_GUILD, status="open")
    assert [e["id"] for e in await elections.list_elections(ADMIN)] == [mine["id"]]
    assert [e["id"] for e in await elections.list_elections(OWNER)] == [other.id, mine["id"]]
    assert await elections.list_elections(VOTER) == []


async def test_delete_removes_ballots_and_the_post(db, server, published):
    election = await posted()
    await elections.cast_ballot(election["id"], VOTER, [election["candidates"][0]["id"]])
    await elections.delete(election["id"], ADMIN)
    assert not await models.RankedChoiceElection.exists(id=election["id"])
    assert not await models.RankedChoiceVotes.exists()
    assert not await models.RankedChoiceCandidate.exists()
    assert published[-1] == events.ElectionDeleted(election_id=election["id"], channel_id=300, message_id=9001,
                                                   occurred_at=published[-1].occurred_at)


async def test_set_message_id_and_get_election(db, server):
    draft = await elections.create_draft(ADMIN, form())
    await elections.set_message_id(draft["id"], 5555)
    assert (await elections.get_election(draft["id"])).message_id == 5555
    assert await elections.get_election(404) is None


# --- voting ------------------------------------------------------------------


async def test_ranked_ballot_and_changing_it(db, server, published):
    election = await posted()
    a, b, c = (x["id"] for x in election["candidates"])
    assert (await elections.get_ballot(election["id"], VOTER))["ballot"] is None
    assert (await elections.cast_ballot(election["id"], VOTER, [b, a]))["ballot"] == [b, a]
    again = await elections.cast_ballot(election["id"], VOTER, [c])
    assert again["ballot"] == [c]
    assert again["voted_at"] is not None
    assert await elections.ballot_count(election["id"]) == 1
    assert [type(e) for e in published] == [events.ElectionBallotCast, events.ElectionBallotCast]


async def test_approval_ballots_have_no_ranks(db, server, published):
    election = await posted(method="approval")
    a, b, _ = (x["id"] for x in election["candidates"])
    await elections.cast_ballot(election["id"], VOTER, [a, b])
    assert {v.rank for v in await models.RankedChoiceVotes.all()} == {None}


async def test_plurality_takes_exactly_one(db, server, published):
    election = await posted(method="plurality")
    a, b, _ = (x["id"] for x in election["candidates"])
    with pytest.raises(InvalidInputError, match="exactly one"):
        await elections.cast_ballot(election["id"], VOTER, [a, b])
    assert (await elections.cast_ballot(election["id"], VOTER, [b]))["ballot"] == [b]


@pytest.mark.parametrize("choices, message", [([], "at least one"), ([1, 1], "only be chosen once"),
                                               ([999999], "isn't in this election")])
async def test_bad_ballots(db, server, choices, message):
    election = await posted()
    if choices == [1, 1]:
        choices = [election["candidates"][0]["id"]] * 2
    with pytest.raises(InvalidInputError, match=message):
        await elections.cast_ballot(election["id"], VOTER, choices)


async def test_who_can_vote(db, server, published):
    everyone = await posted()
    assert await elections.get_ballot(everyone["id"], MEMBER)
    with pytest.raises(PermissionDeniedError, match="Only members"):
        await elections.get_ballot(everyone["id"], OUTSIDER)
    role_only = await posted(voter_role_id=77)
    assert await elections.get_ballot(role_only["id"], VOTER)
    with pytest.raises(PermissionDeniedError, match="role"):
        await elections.get_ballot(role_only["id"], MEMBER)


async def test_drafts_and_closed_elections_take_no_ballots(db, server, published):
    draft = await elections.create_draft(ADMIN, form())
    with pytest.raises(NotFoundError, match="doesn't exist"):
        await elections.get_ballot(draft["id"], VOTER)
    election = await posted()
    await elections.close(election["id"], ADMIN)
    with pytest.raises(NotFoundError, match="closed"):
        await elections.cast_ballot(election["id"], VOTER, [election["candidates"][0]["id"]])


async def test_old_rows_without_status_use_active(db, server):
    election = await models.RankedChoiceElection.create(owner_id=ADMIN, title="Old", guild_id=GUILD, active=True)
    election.status = ""
    await election.save()
    assert elections._status(election) == "open"
    election.active = False
    assert elections._status(election) == "closed"


# --- closing and results -----------------------------------------------------


async def test_close_counts_and_marks_winners(db, server, published):
    election = await posted()
    a, b, c = (x["id"] for x in election["candidates"])
    for voter, choice in ((VOTER, [b, a]), (MEMBER, [b]), (ADMIN, [a])):
        await elections.cast_ballot(election["id"], voter, choice)

    closed = await elections.close(election["id"], ADMIN)
    assert closed["status"] == "closed"
    assert published[-1] == events.ElectionClosed(election_id=election["id"], occurred_at=published[-1].occurred_at)
    row = await models.RankedChoiceElection.get(id=election["id"])
    assert (row.active, row.tally["winners"], row.closed_at is not None) == (False, [b], True)
    assert {c.id for c in await models.RankedChoiceCandidate.filter(winner=True)} == {b}

    with pytest.raises(InvalidInputError, match="Only an open election"):
        await elections.close(election["id"], ADMIN)

    results = await elections.results(election["id"])
    assert (results["tally"]["winners"], results["guild_name"]) == ([b], "Community")


async def test_end_button_closes_for_any_admin(db, server, published):
    election = await posted()
    with pytest.raises(PermissionDeniedError):
        await elections.close_from_message(9001, VOTER)
    closed = await elections.close_from_message(9001, OWNER)
    assert closed.status == "closed"
    with pytest.raises(InvalidInputError, match="already closed"):
        await elections.close_from_message(9001, ADMIN)
    with pytest.raises(NotFoundError):
        await elections.close_from_message(1234, ADMIN)
    assert election["id"] == closed.id


async def test_close_due_closes_elections_past_their_time(db, server, published, monkeypatch):
    soon = await posted(closes_at=later(1))
    open_ended = await posted()
    assert await elections.close_due() == 0
    monkeypatch.setattr(elections, "_now", lambda: later(2))
    assert await elections.close_due() == 1
    assert (await elections.get_election(soon["id"])).status == "closed"
    assert (await elections.get_election(open_ended["id"])).status == "open"


async def test_close_due_logs_and_carries_on(db, server, published, monkeypatch, caplog):
    await posted(closes_at=later(1))
    monkeypatch.setattr(elections, "_now", lambda: later(2))
    monkeypatch.setattr(elections, "_close", mock.AsyncMock(side_effect=RuntimeError("boom")))
    assert await elections.close_due() == 1
    assert "Couldn't close election" in caplog.text


async def test_results_rules_and_the_lazy_recount(db, server):
    with pytest.raises(NotFoundError):
        await elections.results(404)
    draft = await elections.create_draft(ADMIN, form())
    with pytest.raises(NotFoundError):
        await elections.results(draft["id"])
    election = await posted()
    with pytest.raises(PermissionDeniedError, match="when voting closes"):
        await elections.results(election["id"])

    # Closed before counts were stored: recounted on first view, then kept.
    old = await models.RankedChoiceElection.create(owner_id=ADMIN, title="2023", guild_id=None, status="closed",
                                                   active=False, seats=1)
    x = await models.RankedChoiceCandidate.create(election=old, name="X")
    await models.RankedChoiceVotes.create(election=old, candidate=x, user_id=VOTER, rank=1)
    results = await elections.results(old.id)
    assert (results["tally"]["winners"], results["guild_name"], results["closed_at"]) == ([x.id], None, old.updated)
    assert (await models.RankedChoiceElection.get(id=old.id)).tally["winners"] == [x.id]


async def test_post_view(db, server, published):
    assert await elections.post_view(404) is None
    election = await posted(voter_role_id=77)
    view = await elections.post_view(election["id"])
    assert (view["method_label"], view["status"], view["ballots"], view["winners"]) == ("Ranked (STV)", "open", 0, [])
    await elections.cast_ballot(election["id"], VOTER, [election["candidates"][1]["id"]])
    await elections.close(election["id"], ADMIN)
    assert (await elections.post_view(election["id"]))["winners"] == ["Bea"]

    # Closed before counts were stored: the old winner flags.
    old = await models.RankedChoiceElection.create(owner_id=ADMIN, title="Old", status="closed", active=False)
    await models.RankedChoiceCandidate.create(election=old, name="Kept", winner=True)
    await models.RankedChoiceCandidate.create(election=old, name="Lost", winner=False)
    assert (await elections.post_view(old.id))["winners"] == ["Kept"]


# --- the Discord post ---------------------------------------------------------


def view_data(**overrides):
    data = dict(id=12, title="Committee", description="Pick three.", method="stv", method_label="Ranked (STV)",
                seats=3, status="open", ballots=42, show_vote_count=True, voter_role_id=77, owner_id=ADMIN,
                closes_at=datetime(2026, 12, 1, 20, tzinfo=timezone.utc), closed_at=None, channel_id=300,
                message_id=700, winners=[])
    data.update(overrides)
    return data


def fields(embed):
    return {f.name: f.value for f in embed.fields}


def test_open_embed():
    embed = election_posts.build_embed(view_data())
    assert embed.title == "🗳️ Committee"
    assert fields(embed)["Winners"] == "3"
    assert fields(embed)["Ballots"] == "42"
    assert fields(embed)["Who can vote"] == "<@&77>"
    assert fields(embed)["Closes"].startswith("<t:")
    assert fields(embed)["Run by"] == f"<@{ADMIN}>"
    assert embed.footer.text.endswith("Election #12")


def test_open_embed_options():
    embed = election_posts.build_embed(view_data(method="approval", show_vote_count=False, voter_role_id=None,
                                                 closes_at=None))
    assert "Winners" not in fields(embed)
    assert "Ballots" not in fields(embed)
    assert fields(embed)["Who can vote"] == "Everyone in the server"
    assert fields(embed)["Closes"] == "When an admin ends it"


def test_closed_embed():
    embed = election_posts.build_embed(view_data(status="closed", winners=["Coral", "Andy"],
                                                 closed_at=datetime(2026, 12, 1, tzinfo=timezone.utc)))
    assert embed.title == "✅ Committee (closed)"
    assert fields(embed)["Winners"] == "1. Coral · 2. Andy"
    assert "Closed" in fields(embed)
    one = election_posts.build_embed(view_data(status="closed", winners=["Coral"]))
    assert fields(one)["Winner"] == "1. Coral"
    nobody = election_posts.build_embed(view_data(status="closed", winners=[]))
    assert fields(nobody)["Winners"] == "No ballots were cast."


async def test_message_parts_buttons():
    open_parts = election_posts.message_parts(view_data())
    labels = [(i.label, getattr(i, "url", None)) for i in open_parts["view"].children]
    assert labels == [("Vote", election_posts.vote_url(12)), ("Manage", election_posts.manage_url(12)),
                      ("End election", None)]
    closed_parts = election_posts.message_parts(view_data(status="closed"))
    assert [(i.label, i.url) for i in closed_parts["view"].children] == [
        ("See the full count", election_posts.results_url(12))]


def end_interaction(user_id):
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id), message=SimpleNamespace(id=9001),
        response=SimpleNamespace(defer=mock.AsyncMock()),
        followup=SimpleNamespace(send=mock.AsyncMock()),
    )


async def test_end_button(db, server, published):
    await posted()
    view = election_posts.ElectionView()
    stranger = end_interaction(VOTER)
    await view.end_election.callback(stranger)
    stranger.followup.send.assert_awaited_once_with("Only administrators of that server can manage its elections.",
                                                    ephemeral=True)
    admin = end_interaction(ADMIN)
    await view.end_election.callback(admin)
    admin.followup.send.assert_awaited_once_with("Election ended. The results are posted.", ephemeral=True)


class Channel:
    def __init__(self, error=None):
        self.error = error
        self.sent = []
        self.message = SimpleNamespace(edit=mock.AsyncMock(), delete=mock.AsyncMock())

    async def send(self, **kwargs):
        if self.error:
            raise self.error
        self.sent.append(kwargs)
        return SimpleNamespace(id=777)

    def get_partial_message(self, message_id):
        return self.message


def response(status):
    return SimpleNamespace(status=status, reason="x")


def bot_with(channel, cached=True):
    return SimpleNamespace(get_channel=lambda cid: channel if cached else None,
                           fetch_channel=mock.AsyncMock(return_value=channel))


async def test_post_refresh_and_delete(db, server, published):
    draft = await elections.create_draft(ADMIN, form())
    channel = Channel()
    assert await election_posts.post(bot_with(channel, cached=False), draft["id"]) == 777
    assert channel.sent[0]["embed"].title == "🗳️ Committee"

    await elections.set_message_id(draft["id"], 777)
    await election_posts.refresh(bot_with(channel), draft["id"])
    channel.message.edit.assert_awaited_once()
    assert channel.message.edit.await_args.kwargs["attachments"] == []

    channel.message.edit.side_effect = discord.NotFound(response(404), "gone")
    await election_posts.refresh(bot_with(channel), draft["id"])  # no error
    await election_posts.refresh(bot_with(channel), 404)  # no such election: nothing to do

    await election_posts.delete_post(bot_with(channel), 300, 777)
    channel.message.delete.assert_awaited_once()
    await election_posts.delete_post(bot_with(channel), None, None)
    channel.message.delete.side_effect = discord.NotFound(response(404), "gone")
    await election_posts.delete_post(bot_with(channel), 300, 777)


@pytest.mark.parametrize("error, message", [
    (discord.Forbidden(response(403), "no"), "isn't allowed"),
    (discord.HTTPException(response(500), "down"), "didn't accept"),
])
async def test_post_failures_are_readable(db, server, error, message):
    draft = await elections.create_draft(ADMIN, form())
    bot = bot_with(Channel(error=error))
    with pytest.raises(InvalidInputError, match=message):
        await election_posts.post(bot, draft["id"])


# --- the Discord directory ----------------------------------------------------


class Role:
    def __init__(self, role_id, name, position=1, default=False, managed=False):
        self.id, self.name, self.position, self.managed = role_id, name, position, managed
        self._default = default

    def is_default(self):
        return self._default


class Member:
    def __init__(self, admin=False, roles=()):
        self.guild_permissions = SimpleNamespace(administrator=admin)
        self.roles = list(roles)


class TextChannel:
    type = discord.ChannelType.text

    def __init__(self, channel_id, name, position, can_post=True):
        self.id, self.name, self.position, self._can_post = channel_id, name, position, can_post

    def permissions_for(self, who):
        return SimpleNamespace(send_messages=self._can_post, embed_links=True)


class Guild:
    def __init__(self, guild_id, name, members, me=True):
        self.id, self.name, self._members = guild_id, name, members
        self.me = object() if me else None

    async def fetch_channels(self):
        return [TextChannel(2, "second", 2), TextChannel(1, "first", 1), TextChannel(3, "locked", 3, can_post=False),
                SimpleNamespace(id=4, name="voice", type=discord.ChannelType.voice)]

    async def fetch_roles(self):
        return [Role(1, "@everyone", 0, default=True), Role(2, "Mods", 5), Role(3, "Voters", 2), Role(4, "Bot", 3,
                                                                                                     managed=True)]


@pytest.fixture
def bot(monkeypatch):
    guilds = {
        GUILD: Guild(GUILD, "Community", {ADMIN: Member(admin=True, roles=[Role(77, "Voters")]), VOTER: Member()}),
        OTHER_GUILD: Guild(OTHER_GUILD, "Another", {ADMIN: Member(admin=False)}, me=False),
    }

    async def get_member(guild, user_id):
        return guild._members.get(user_id)

    async def fetch_guild(guild_id):
        if guild_id in guilds:
            return guilds[guild_id]
        raise discord.NotFound(response(404), "no guild")

    monkeypatch.setattr(election_posts.discord_members, "get_member", get_member)
    election_posts.ADMIN_CACHE._cache.clear()
    return SimpleNamespace(
        guilds=list(guilds.values()), get_guild=lambda gid: None if gid == OTHER_GUILD else guilds.get(gid),
        fetch_guild=fetch_guild, is_owner=mock.AsyncMock(side_effect=lambda user: user.id == OWNER),
    )


async def test_directory_lookups(bot):
    d = election_posts.DiscordDirectory(bot)
    assert await d.is_owner(OWNER)
    assert not await d.is_owner(ADMIN)
    assert [g.name for g in await d.admin_guilds(ADMIN)] == ["Community"]
    assert [g.name for g in await d.admin_guilds(ADMIN)] == ["Community"]  # cached
    assert await d.is_admin(GUILD, ADMIN)
    assert not await d.is_admin(OTHER_GUILD, ADMIN)
    assert await d.member_role_ids(GUILD, ADMIN) == [77]
    assert await d.member_role_ids(GUILD, OUTSIDER) is None
    assert await d.member_role_ids(999, ADMIN) is None
    assert await d.guild_name(OTHER_GUILD) == "Another"
    assert await d.guild_name(999) is None
    assert [c.name for c in await d.text_channels(GUILD)] == ["#first", "#second"]
    assert [c.name for c in await d.text_channels(OTHER_GUILD)] == ["#first", "#second", "#locked"]
    assert await d.text_channels(999) == []
    assert [r.name for r in await d.roles(GUILD)] == ["@Mods", "@Voters"]
    assert await d.roles(999) == []


async def test_directory_posts_and_registers(db, bot, monkeypatch):
    post = mock.AsyncMock(return_value=5)
    monkeypatch.setattr(election_posts, "post", post)
    d = election_posts.DiscordDirectory(bot)
    assert await d.post_election(3) == 5
    post.assert_awaited_once_with(bot, 3)
    monkeypatch.setattr(discord_directory, "_directory", None)
    election_posts.register(bot)
    assert isinstance(discord_directory.get(), election_posts.DiscordDirectory)

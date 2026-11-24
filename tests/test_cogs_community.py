"""Community and moderation cogs: server lists, misc commands, voice and reaction
roles, inquiries, racer verification and ranked-choice elections.

Commands run through their callbacks against the fakes in ``tests/discord_fakes.py``;
the database is the ``db`` fixture's SQLite.
"""

import datetime
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

import config
from alttprbot import models
from alttprbot.exceptions import SahasrahBotException
from alttprbot.services import discord_servers as servers_service
from alttprbot.services import guild_config, reaction_roles
from alttprbot_discord.cogs import discord_servers as servers_cog
from alttprbot_discord.cogs import inquiry as inquiry_cog
from alttprbot_discord.cogs import misc as misc_cog
from alttprbot_discord.cogs import racer_verification as rv_cog
from alttprbot_discord.cogs import elections as elections_cog
from alttprbot_discord.elections import ElectionView
from alttprbot_discord.cogs import role as role_cog
from alttprbot_discord.cogs import sgdailies as sg_cog
from alttprbot_discord.cogs import voicerole as voice_cog
from tests.discord_fakes import (FakeBot, FakeChannel, FakeContext, FakeGuild, FakeInteraction, FakeMessage,
                                 FakeRole, FakeUser, call, emoji, permissions)

# ---------------------------------------------------------------------------
# /discordservers
# ---------------------------------------------------------------------------


@pytest.fixture
def guild():
    return FakeGuild(guild_id=1, channels=[FakeChannel(channel_id=100, name="servers"), FakeChannel(channel_id=101)])


async def test_discordservers_categories(db, guild):
    cog = servers_cog.DiscordServers(FakeBot())

    empty = FakeInteraction(guild=guild)
    await call(cog.list_category, cog, empty)
    assert empty.sent().content == "No categories found."

    added = FakeInteraction(guild=guild)
    await call(cog.add_category, cog, added, guild.get_channel(100), "Randomizers", "desc", 2)
    assert added.sent().content == "Added category Randomizers to <#100>"
    [cat] = await servers_service.list_categories(1)

    listed = FakeInteraction(guild=guild)
    await call(cog.list_category, cog, listed)
    [f] = listed.sent().embed.fields
    assert (f.name, f.value) == ("Randomizers", f"_*Id:*_ {cat.id}\n_*Channel:*_ <#100>")

    updated = FakeInteraction(guild=guild)
    await call(cog.update_category, cog, updated, cat.id, "Renamed", "new desc")
    assert (await models.DiscordServerCategories.get(id=cat.id)).category_title == "Renamed"

    removed = FakeInteraction(guild=guild)
    await call(cog.remove_category, cog, removed, cat.id)
    assert removed.sent().content == f"Removed category {cat.id}"
    assert await servers_service.list_categories(1) == []


async def test_discordservers_servers(db, guild):
    bot = FakeBot()
    bot.fetch_invite.return_value = SimpleNamespace(id="abc", guild=SimpleNamespace(name="ALTTPR"))
    cog = servers_cog.DiscordServers(bot)
    cat = await servers_service.add_category(1, 100, "Randomizers")

    added = FakeInteraction(guild=guild)
    await call(cog.add_server, cog, added, cat.id, "https://discord.gg/abc", "The ALTTPR server")
    assert added.sent().content == f"Added server ALTTPR to category {cat.id}"
    bot.fetch_invite.assert_awaited_with("https://discord.gg/abc")

    listed = FakeInteraction(guild=guild)
    await call(cog.list_servers, cog, listed, cat.id)
    [server] = await servers_service.list_servers(cat.id)
    assert [(f.name, f.value) for f in listed.sent().embed.fields] == [("The ALTTPR server", f"_*Id:*_ {server.id}")]

    bot.fetch_invite.return_value = SimpleNamespace(id="xyz", guild=SimpleNamespace(name="ALTTPR"))
    await call(cog.update_server, cog, FakeInteraction(guild=guild), server.id, "https://discord.gg/xyz", cat.id, "Renamed")
    assert (await models.DiscordServerLists.get(id=server.id)).invite_id == "xyz"

    await call(cog.remove_server, cog, FakeInteraction(guild=guild), server.id)
    empty = FakeInteraction(guild=guild)
    await call(cog.list_servers, cog, empty, cat.id)
    assert empty.sent().content == f"No servers found for category {cat.id}"


async def test_discordservers_refresh_posts_each_page(db, guild):
    bot = FakeBot()
    cog = servers_cog.DiscordServers(bot)
    big = await servers_service.add_category(1, 100, "Big")
    small = await servers_service.add_category(1, 101, "Small")
    for i in range(11):
        await servers_service.add_server(1, big.id, f"inv{i}", f"Server {i}")
    await servers_service.add_server(1, small.id, "solo", "Solo")
    interaction = FakeInteraction(guild=guild)

    await call(cog.refresh, cog, interaction)

    for channel in guild.channels:
        channel.purge.assert_awaited_once()
        check = channel.purge.await_args.kwargs["check"]
        assert check(SimpleNamespace(author=bot.user)) and not check(SimpleNamespace(author="someone"))
    big_posts = [m.content for m in guild.get_channel(100).sent]
    assert [p.splitlines()[0] for p in big_posts] == ["**__Big - Part 1__**", "**__Big - Part 2__**"]
    assert big_posts[1].splitlines()[1] == "Server 10: https://discord.gg/inv10"
    assert [m.content for m in guild.get_channel(101).sent] == ["**__Small__**\nSolo: https://discord.gg/solo"]
    assert interaction.sent().content == "Refreshed server list for Test Guild"


# ---------------------------------------------------------------------------
# misc: /welcome, /rom, /holyimage, /datetime, the mention reaction
# ---------------------------------------------------------------------------


async def test_welcome_and_rom():
    cog = misc_cog.Misc(FakeBot())
    welcome = FakeInteraction()
    await call(cog.welcome, cog, welcome, "german")
    rom = FakeInteraction()
    await call(cog.rom, cog, rom)

    assert welcome.sent().content == misc_cog.WELCOME_MESSAGES["german"]
    assert "checkcrc" in rom.sent().content


async def test_mention_reacts_with_sahasrahbot_emoji(monkeypatch):
    monkeypatch.setattr(misc_cog.asyncio, "sleep", mock.AsyncMock())
    bot = FakeBot(emojis=[emoji("SahasrahBot")])
    cog = misc_cog.Misc(bot)
    mentioned = FakeMessage()
    mentioned.mentions = [bot.user]
    ignored = FakeMessage()

    await cog.on_message(mentioned)
    await cog.on_message(ignored)

    mentioned.add_reaction.assert_awaited_once_with(bot.emojis[0])
    ignored.add_reaction.assert_not_awaited()


HOLY_IMAGES = {
    "z3r": [
        {"slug": "fairy", "idx": 1, "title": "Fairy", "url": "images/fairy.png", "desc": "<b>Heal</b>",
         "credit": "someone"},
        {"slug": "fatfairy", "idx": 2, "title": "Fat Fairy", "url": "https://x.test/r", "mode": "redirect"},
    ],
    "smz3": [{"slug": "samus", "idx": 1, "title": "Samus"}],
}


@pytest.fixture
async def holy(monkeypatch):
    from alttprbot.integrations import holyimage as api

    monkeypatch.setattr(api, "get_holy_images", mock.AsyncMock(return_value=HOLY_IMAGES))
    await misc_cog.get_holy_images.cache.clear()
    await misc_cog.holy_game_default.cache.clear()
    yield
    await misc_cog.get_holy_images.cache.clear()
    await misc_cog.holy_game_default.cache.clear()


async def test_holyimage_uses_guild_default_game(db, holy):
    await guild_config.set_value(1, "HolyImageDefaultGame", "smz3")
    cog = misc_cog.Misc(FakeBot())

    in_guild = FakeInteraction(guild=FakeGuild(guild_id=1))
    await call(cog.holyimage, cog, in_guild, "samus")
    in_dm = FakeInteraction()
    await call(cog.holyimage, cog, in_dm, "1")  # idx works as a slug

    assert in_guild.sent().embed.title == "Samus"
    embed = in_dm.sent().embed
    assert embed.title == "Fairy"
    assert embed.description.strip() == "__Heal__"
    assert embed.thumbnail.url == "http://alttp.mymm1.com/holyimage/images/fairy.png"
    assert embed.footer.text == "Created by someone"


async def test_holyimage_autocomplete(db, holy):
    cog = misc_cog.Misc(FakeBot())
    games = await cog.holy_game_autocomplete(FakeInteraction(), "s")
    slugs = await cog.holy_slug_autocomplete(FakeInteraction(namespace={"game": None}), "f")
    smz3 = await cog.holy_slug_autocomplete(FakeInteraction(namespace={"game": "smz3"}), "")

    assert [c.value for c in games] == ["smz3"]
    assert [c.value for c in slugs] == ["fairy", "fatfairy"]
    assert [c.value for c in smz3] == ["samus"]


async def test_known_issue_holy_game_default_is_cached_for_every_guild(db, holy):
    """KNOWN ISSUE, pinned not endorsed: ``holy_game_default`` caches under one fixed
    key, so the first guild's default game is used for every guild for five minutes."""
    await guild_config.set_value(1, "HolyImageDefaultGame", "smz3")
    await guild_config.set_value(2, "HolyImageDefaultGame", "z3r")
    assert await misc_cog.holy_game_default(FakeGuild(guild_id=1)) == "smz3"
    assert await misc_cog.holy_game_default(FakeGuild(guild_id=2)) == "smz3"


async def test_datetime_markdown():
    cog = misc_cog.Misc(FakeBot())
    interaction = FakeInteraction()
    await call(cog.datetime_cmd, cog, interaction, 2024, 3, 9, 20, 30, 0, "UTC")

    sent = interaction.sent()
    stamp = int(datetime.datetime(2024, 3, 9, 20, 30, tzinfo=datetime.timezone.utc).timestamp())
    assert sent.ephemeral is True
    assert sent.embed.title == "Date markdown for 2024-03-09 20:30:00 UTC"
    assert f"<t:{stamp}:R> - `<t:{stamp}:R>`" in sent.embed.description
    assert sent.embed.description.count("\n") == 9


@pytest.mark.parametrize(
    "args, message",
    [
        ((2024, 1, 1, 0, 0, 0, "Mars/Olympus"), "Unknown timezone: Mars/Olympus"),
        ((2023, 2, 30, 0, 0, 0, "UTC"), "Invalid date: 2023-2-30 0:0:0 UTC"),
    ],
)
async def test_datetime_rejects_bad_input(args, message):
    cog = misc_cog.Misc(FakeBot())
    interaction = FakeInteraction()
    await call(cog.datetime_cmd, cog, interaction, *args)
    assert interaction.sent().content == message


async def test_datetime_defaults_to_today_and_autocompletes_timezones():
    cog = misc_cog.Misc(FakeBot())
    interaction = FakeInteraction()
    await call(cog.datetime_cmd, cog, interaction)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    assert interaction.sent().embed.title == f"Date markdown for {today} 00:00:00 America/New_York"

    choices = await cog.datetime_autocomplete_tz(FakeInteraction(), "America/New")
    assert [c.value for c in choices] == ["America/New_York"]
    assert len(await cog.datetime_autocomplete_tz(FakeInteraction(), "")) == 25


# ---------------------------------------------------------------------------
# voice roles
# ---------------------------------------------------------------------------


async def test_voice_roles_follow_the_channel(db):
    await models.VoiceRole.create(guild_id=1, voice_channel_id=10, role_id=501)
    await models.VoiceRole.create(guild_id=1, voice_channel_id=11, role_id=502)
    await models.VoiceRole.create(guild_id=1, voice_channel_id=11, role_id=999)  # role deleted from the guild
    role_a, role_b = FakeRole(501), FakeRole(502)
    member = FakeUser()
    member.guild = FakeGuild(guild_id=1, roles=[role_a, role_b])
    cog = voice_cog.VoiceRole(FakeBot())
    vc = lambda cid: SimpleNamespace(channel=None if cid is None else SimpleNamespace(id=cid))  # noqa: E731

    await cog.on_voice_state_update(member, vc(None), vc(10))
    member.add_roles.assert_awaited_once_with(role_a, reason="Joined voice channel.")

    await cog.on_voice_state_update(member, vc(10), vc(11))
    member.remove_roles.assert_awaited_once_with(role_a, reason="Left voice channel.")
    assert member.add_roles.await_args.args == (role_b,)

    member.add_roles.reset_mock()
    await cog.on_voice_state_update(member, vc(11), vc(11))  # mute/deafen: same channel
    member.add_roles.assert_not_awaited()


# ---------------------------------------------------------------------------
# /sgdaily
# ---------------------------------------------------------------------------


def episode(title, when, channels=()):
    return {
        "event": {"name": "ALTTPR Daily"},
        "match1": {"title": title},
        "when": when,
        "channels": [{"slug": s, "name": n} for s, n in channels],
    }


async def test_sgdaily_next_race(monkeypatch):
    schedule = [episode("", "2024-05-01T20:00:00Z", [("speedgaming", "SpeedGaming"), ("sg2", "SG 2")])]
    monkeypatch.setattr(sg_cog.speedgaming, "get_upcoming_episodes_by_event", mock.AsyncMock(return_value=schedule))
    cog = sg_cog.SgDaily(FakeBot())
    interaction = FakeInteraction()

    await call(cog.sgdaily_cmd, cog, interaction)

    embed = interaction.sent().embed
    assert embed.title == "ALTTPR Daily"
    assert embed.description.startswith("**Mode:** *TBD*")
    assert [f.name for f in embed.fields] == ["Time", "Twitch Channels"]
    assert embed.fields[1].value == "[speedgaming](https://twitch.tv/speedgaming)"  # names with spaces are skipped


async def test_sgdaily_schedule_and_empty(monkeypatch):
    schedule = [episode("Open", "2024-05-01T20:00:00Z"), episode("", "2024-05-02T20:00:00Z"),
                episode("Boots", "2024-05-03T20:00:00Z")]
    get = mock.AsyncMock(return_value=schedule)
    monkeypatch.setattr(sg_cog.speedgaming, "get_upcoming_episodes_by_event", get)
    cog = sg_cog.SgDaily(FakeBot())

    several = FakeInteraction()
    await call(cog.sgdaily_cmd, cog, several, number_of_days=2)
    get.return_value = []
    none = FakeInteraction()
    await call(cog.sgdaily_cmd, cog, none)

    get.assert_awaited_with("alttprdaily", hours_past=0, hours_future=192)
    embed = several.sent().embed
    assert embed.title == "ALTTP Randomizer SG Daily Schedule"
    assert [f.name for f in embed.fields] == ["Open", "TBD"]
    assert "no currently SpeedGaming ALTTPR Daily Races" in none.sent().content


# ---------------------------------------------------------------------------
# reaction roles ($reactionrole / $reactiongroup)
# ---------------------------------------------------------------------------


@pytest.fixture
async def role_world(db):
    """A guild with a bot-managed reaction group on message 700 in channel 300."""
    channel = FakeChannel(channel_id=300)
    message = FakeMessage(message_id=700, channel=channel)
    channel.fetch_message = mock.AsyncMock(return_value=message)
    role = FakeRole(501, name="Runner")
    guild = FakeGuild(guild_id=1, roles=[role], channels=[channel])
    group = await reaction_roles.create_group(1, 300, 700, "Roles", "Pick some", True)
    ctx = FakeContext(guild=guild)
    return SimpleNamespace(channel=channel, message=message, role=role, guild=guild, group=group, ctx=ctx)


async def test_reaction_role_description_fits_production_column(role_world):
    """Production's reaction_role.description is VARCHAR(400), so the model must
    refuse anything longer before MySQL does."""
    from tortoise.exceptions import ValidationError

    assert models.ReactionRole._meta.fields_map["description"].max_length == 400
    await reaction_roles.create_role(1, role_world.group.id, 501, "runner", "🏃", "x" * 400, True)
    with pytest.raises(ValidationError):
        await reaction_roles.create_role(1, role_world.group.id, 502, "racer", "🏁", "x" * 401, True)


async def test_reaction_role_create_update_delete(role_world):
    w = role_world
    cog = role_cog.Role(w.ctx.bot)

    await call(cog.role_create, cog, w.ctx, w.group.id, w.role, "runner", "Racers", "<:custom:123>")
    w.message.add_reaction.assert_awaited_with(":custom:123")
    embed = w.message.edit.await_args.kwargs["embed"]
    assert embed.fields[0].value == "<:custom:123> `runner`: Racers\n"

    [rr] = await reaction_roles.group_roles(w.group.id, 1)
    await call(cog.role_update, cog, w.ctx, rr.id, "racer", "Racers!")
    assert (await models.ReactionRole.get(id=rr.id)).name == "racer"

    await call(cog.role_list, cog, w.ctx, w.group.id)
    listed = w.ctx.reply.await_args.kwargs["embed"]
    assert listed.fields[0].name == f"{rr.id}: racer"

    await call(cog.role_delete, cog, w.ctx, rr.id)
    w.message.remove_reaction.assert_awaited_once_with(":custom:123", w.ctx.bot.user)
    assert await reaction_roles.group_roles(w.group.id, 1) == []


async def test_reaction_group_commands(role_world):
    w = role_world
    cog = role_cog.Role(w.ctx.bot)

    other = FakeChannel(channel_id=301, guild=w.guild)
    w.guild.channels.append(other)
    await call(cog.group_create, cog, w.ctx, other, "New group", "desc")
    assert other.sent[0].content == "temp message"
    await call(cog.group_create, cog, w.ctx, other, "Existing", None, False, 777)
    groups = await reaction_roles.list_groups(1)
    assert [(g.name, g.message_id, bool(g.bot_managed)) for g in groups[1:]] == [
        ("New group", 800, True), ("Existing", 777, False),
    ]

    await call(cog.group_update, cog, w.ctx, w.group.id, "Renamed", "d")
    assert w.message.edit.await_args.kwargs["embed"].title == "Renamed"

    await call(cog.group_list, cog, w.ctx)
    assert len(w.ctx.reply.await_args.kwargs["embed"].fields) == 3
    await call(cog.group_list, cog, w.ctx, w.group.id)
    assert [f.name for f in w.ctx.reply.await_args.kwargs["embed"].fields] == [f"{w.group.id}: Renamed"]
    await call(cog.group_list, cog, w.ctx, 12345)
    assert w.ctx.reply.await_args.kwargs["embed"].fields == []

    w.message.edit.reset_mock()
    await call(cog.group_refresh, cog, w.ctx, w.group.id)
    w.message.edit.assert_awaited_once()

    await call(cog.group_delete, cog, w.ctx, w.group.id)
    assert await reaction_roles.get_group(w.group.id, 1) is None


async def test_reaction_listeners_add_and_remove_roles(role_world):
    w = role_world
    await reaction_roles.create_role(1, w.group.id, 501, "runner", "🏃", "Racers", True)
    # a second mapping for the same emoji whose role was since deleted from the guild
    await models.ReactionRole.create(guild_id=1, reaction_group=w.group, role_id=999, name="gone", emoji="🏃")
    member = FakeUser(user_id=55)
    w.guild.members[55] = member
    bot = FakeBot()
    bot.fetch_guild.return_value = w.guild
    cog = role_cog.Role(bot)
    payload = SimpleNamespace(emoji="🏃", guild_id=1, channel_id=300, message_id=700, user_id=55)

    await cog.on_raw_reaction_add(payload)
    await cog.on_raw_reaction_remove(payload)
    await cog.on_raw_reaction_add(SimpleNamespace(**{**vars(payload), "emoji": "🎉"}))

    member.add_roles.assert_awaited_once_with(w.role, reason="Added by message reaction.")
    member.remove_roles.assert_awaited_once_with(w.role, reason="Removed by message reaction.")
    bot.fetch_guild.assert_awaited_with(1)
    assert bot.fetch_guild.await_count == 2  # the unmapped emoji stops before fetching


async def test_importroles(monkeypatch):
    role, member = FakeRole(501), FakeUser(user_id=55)

    async def role_convert(self, ctx, arg):
        if arg == "Runner":
            return role
        raise discord.ext.commands.BadArgument(arg)

    async def member_convert(self, ctx, arg):
        if arg == "alice":
            return member
        raise discord.ext.commands.BadArgument(arg)

    monkeypatch.setattr(role_cog.commands.RoleConverter, "convert", role_convert)
    monkeypatch.setattr(role_cog.commands.MemberConverter, "convert", member_convert)
    csv_file = SimpleNamespace(read=mock.AsyncMock(return_value=b"role,member\nRunner,alice\nNope,alice\nRunner,bob\n"))
    cog = role_cog.Role(FakeBot())

    dry = FakeContext(attachments=[csv_file])
    await call(cog.importroles, cog, dry, "dry")
    member.add_roles.assert_not_awaited()
    assert dry.reply.await_count == 2

    ctx = FakeContext(attachments=[csv_file])
    await call(cog.importroles, cog, ctx)
    member.add_roles.assert_awaited_once_with(role)
    assert [c.args[0] for c in ctx.reply.await_args_list] == [
        "Failed to find role identified by Nope", "Failed to find member identified by bob",
    ]

    with pytest.raises(SahasrahBotException, match="valid csv"):
        await call(cog.importroles, cog, FakeContext())


def test_strip_custom_emoji():
    assert role_cog.strip_custom_emoji("<:name:123>") == ":name:123"
    assert role_cog.strip_custom_emoji("<a:name:123>") == "a:name:123"
    assert role_cog.strip_custom_emoji("🏃") == "🏃"


# ---------------------------------------------------------------------------
# /inquiry
# ---------------------------------------------------------------------------


def inquiry_channel(guild, user, role):
    """A channel whose permissions pass every /inquiry check."""
    perms = {
        user.id: permissions(manage_threads=True),
        guild.me.id: permissions(create_private_threads=True),
        guild.default_role.id: permissions(send_messages_in_threads=True),
        role.id: permissions(read_messages=True),
    }
    return FakeChannel(guild=guild, perms=perms)


@pytest.mark.parametrize(
    "who, perms, message",
    [
        ("user", permissions(), "You must have manage threads permission"),
        ("me", permissions(), "This bot needs permission to create private threads"),
        ("everyone", permissions(send_messages=True, send_messages_in_threads=True), "should not be allowed to send"),
        ("everyone", permissions(), "needs to be able to send messages in threads"),
        ("role", permissions(), "<@&500> is not allowed to see this channel."),
    ],
)
async def test_inquiry_permission_checks(db, who, perms, message):
    guild, user, role = FakeGuild(), FakeUser(), FakeRole(500)
    ids = {"user": user.id, "me": guild.me.id, "everyone": guild.default_role.id, "role": role.id}
    channel = inquiry_channel(guild, user, role)
    channel.perms[ids[who]] = perms
    interaction = FakeInteraction(user=user, guild=guild, channel=channel)
    cog = inquiry_cog.Inquiry(FakeBot())

    await call(cog.inquiry, cog, interaction, role)

    assert message in interaction.sent().content
    assert not await models.InquiryMessageConfig.exists()


async def test_inquiry_posts_message_and_saves_role(db):
    guild, user, role = FakeGuild(), FakeUser(), FakeRole(500)
    interaction = FakeInteraction(user=user, guild=guild, channel=inquiry_channel(guild, user, role))
    cog = inquiry_cog.Inquiry(FakeBot())

    await call(cog.inquiry, cog, interaction, role)

    sent = interaction.sent()
    assert "<@&500>" in sent.content
    assert isinstance(sent.view, inquiry_cog.ConfirmInquiryThread)
    saved = await models.InquiryMessageConfig.get(message_id=interaction.original.id)
    assert saved.role_id == 500


async def test_inquiry_buttons_lead_to_the_modal(db):
    await models.InquiryMessageConfig.create(message_id=700, role_id=500)
    guild = FakeGuild(roles=[FakeRole(500)])
    interaction = FakeInteraction(guild=guild, message=FakeMessage(message_id=700))

    view = inquiry_cog.ConfirmInquiryThread()
    await view.openthread.callback(interaction)
    sent = interaction.sent()
    assert sent.content.startswith("This will open a private thread to <@&500>")
    assert sent.ephemeral is True

    yes = FakeInteraction(guild=guild)
    await sent.view.yes.callback(yes)
    modal = yes.response.send_modal.await_args.args[0]
    assert isinstance(modal, inquiry_cog.OpenInquiryModal)
    assert modal.role_id == 500


@pytest.mark.parametrize("mentionable, expected_ping", [(True, "<@&500>"), (False, "Unable to add <@&500>")])
async def test_inquiry_modal_opens_thread(monkeypatch, mentionable, expected_ping):
    monkeypatch.setattr(config, "DEBUG", False)
    monkeypatch.setattr(inquiry_cog.random, "randint", lambda a, b: 7)
    role = FakeRole(500, mentionable=mentionable)
    guild = FakeGuild(roles=[role])
    thread = SimpleNamespace(name="t", mention="<#9>", add_user=mock.AsyncMock(), send=mock.AsyncMock(),
                             permissions_for=lambda who: permissions())
    user = FakeUser(name="alice")
    interaction = FakeInteraction(user=user, guild=guild)
    interaction.channel.create_thread.return_value = thread
    modal = inquiry_cog.OpenInquiryModal(500)
    modal.description._value = "My summary of things"

    await modal.on_submit(interaction)

    interaction.channel.create_thread.assert_awaited_once_with(name="Inquiry alice 7", message=None,
                                                               auto_archive_duration=1440)
    thread.add_user.assert_awaited_once_with(user)
    assert interaction.sent().content == "A new thread called <#9> has been opened for this inquiry."
    posts = [c.args[0] for c in thread.send.await_args_list]
    assert posts[0].startswith(expected_ping)
    assert posts[1] == "<@1001> has opened an inquiry.\n\n**Description:** My summary of things"


async def test_persistent_views_are_added_once():
    for module, cog_class, view_class in [
        (inquiry_cog, "Inquiry", inquiry_cog.ConfirmInquiryThread),
        (rv_cog, "RacerVerification", rv_cog.RacerVerificationView),
        (elections_cog, "Elections", ElectionView),
    ]:
        bot = FakeBot()
        cog = getattr(module, cog_class)(bot)
        await cog.on_ready()
        await cog.on_ready()
        bot.add_view.assert_called_once()
        assert isinstance(bot.add_view.call_args.args[0], view_class)


# ---------------------------------------------------------------------------
# /rankedchoice create
# ---------------------------------------------------------------------------


def test_rankedchoice_is_for_admins_in_servers_only():
    group = elections_cog.Elections.rankedchoice
    assert group.guild_only
    assert group.default_permissions == discord.Permissions(administrator=True)
    assert [c.name for c in group.commands] == ["create"]


@pytest.mark.parametrize("channel, picked", [
    (FakeChannel(channel_id=301), 301),
    (SimpleNamespace(id=999, parent_id=301), 301),  # a thread: its channel is picked
])
async def test_rankedchoice_create_links_to_the_prefilled_form(monkeypatch, channel, picked):
    monkeypatch.setattr(config, "APP_URL", "https://sahasrahbot.example")
    cog = elections_cog.Elections(FakeBot())
    interaction = FakeInteraction(guild=FakeGuild(guild_id=123456789012345678), channel=channel)
    await call(cog.create, cog, interaction)

    sent = interaction.sent()
    assert sent.ephemeral is True
    assert f"<#{picked}>" in sent.content
    links = {b.label: b.url for b in sent.view.children}
    assert links == {
        "Create election": f"https://sahasrahbot.example/elections/new?server=123456789012345678&channel={picked}",
        "All elections": "https://sahasrahbot.example/elections",
    }


# ---------------------------------------------------------------------------
# /racerverification and its button
# ---------------------------------------------------------------------------


async def test_racerverification_create_posts_requirements(db):
    bot = FakeBot()
    cog = rv_cog.RacerVerification(bot)
    interaction = FakeInteraction(user=FakeUser(administrator=True), guild=FakeGuild(guild_id=1))
    interaction.original.channel = SimpleNamespace(id=300)

    await call(cog.create_or_update, cog, interaction, FakeRole(501), racetime_categories="alttpr,smz3",
               use_alttpr_ladder=True, minimum_races=5, time_period_days=30)

    content = interaction.sent().content
    assert "at least 5 races played in the last 30 days" in content
    assert "categories: alttpr, smz3 or ALTTPR Ladder races" in content
    saved = await models.RacerVerification.get(role_id=501)
    assert (saved.guild_id, saved.message_id, saved.channel_id, saved.minimum_races) == (1, 4242, 300, 5)


async def test_racerverification_refuses_a_non_admin(db):
    """Only server admins and the bot owner may set up racer verification (see also
    tests/test_admin_checks.py)."""
    bot = FakeBot()
    cog = rv_cog.RacerVerification(bot)
    interaction = FakeInteraction(user=FakeUser(administrator=False), guild=FakeGuild(guild_id=1))

    await call(cog.create_or_update, cog, interaction, FakeRole(501), minimum_races=1, time_period_days=1)

    assert interaction.sent().content == "You are not authorized to use this command."
    assert not await models.RacerVerification.exists(role_id=501)


@pytest.fixture
async def verification(db):
    rv = await models.RacerVerification.create(guild_id=1, role_id=501, message_id=700, channel_id=300,
                                               racetime_categories="alttpr", minimum_races=1, time_period_days=365)
    role = FakeRole(501)
    return SimpleNamespace(rv=rv, role=role, guild=FakeGuild(guild_id=1, roles=[role]))


async def test_verify_button_wrong_message_and_unlinked_user(verification):
    view = rv_cog.RacerVerificationView(FakeBot())

    wrong = FakeInteraction(guild=verification.guild, message=FakeMessage(message_id=1))
    await view.verify_status.callback(wrong)
    assert "not a valid racer verification message" in wrong.sent().content

    unlinked = FakeInteraction(guild=verification.guild, message=FakeMessage(message_id=700))
    await view.verify_status.callback(unlinked)
    assert "/racetime/verification/initiate" in unlinked.sent().content
    unlinked.response.defer.assert_awaited_once_with(ephemeral=True)


@pytest.mark.parametrize("eligible", [True, False])
async def test_verify_button_checks_eligibility(monkeypatch, verification, eligible):
    await models.Users.create(discord_user_id=1001, display_name="runner", rtgg_id="rt1")
    monkeypatch.setattr(rv_cog.verification, "determine_eligibility", mock.AsyncMock(return_value=(eligible, 12)))
    view = rv_cog.RacerVerificationView(FakeBot())
    interaction = FakeInteraction(guild=verification.guild, message=FakeMessage(message_id=700))

    await view.verify_status.callback(interaction)

    if eligible:
        assert "at least **12** races played over the last **365** days" in interaction.sent().content
        interaction.user.add_roles.assert_awaited_once_with(verification.role, reason="Racer Verification")
        assert (await models.VerifiedRacer.get()).estimated_count == 12
    else:
        assert interaction.sent().content.startswith("Sorry, you do not meet the requirements")
        interaction.user.add_roles.assert_not_awaited()
        assert not await models.VerifiedRacer.exists()



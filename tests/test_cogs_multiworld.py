"""The /smmulti multiworld sign-up message (alttprbot_discord/cogs/smmulti.py)."""

from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import models
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.cogs import smmulti as mw_cog
from tests.discord_fakes import FakeBot, FakeChannel, FakeGuild, FakeInteraction, FakeUser, call

OWNER = 7


def field(embed, name):
    return next(f.value for f in embed.fields if f.name == name)


@pytest.fixture
async def signup(db):
    """A fresh /smmulti post (message 4242) owned by user 7, plus its view."""
    cog = mw_cog.SMMulti(FakeBot())
    interaction = FakeInteraction(user=FakeUser(user_id=OWNER), guild=FakeGuild())
    await call(cog.smmulti, cog, interaction)
    message = interaction.original
    message.embeds = [interaction.sent().embed]
    message.guild = interaction.guild
    view = message.edit.await_args.kwargs["view"]
    return SimpleNamespace(message=message, view=view, guild=interaction.guild)


def click(signup, user_id=OWNER):
    return FakeInteraction(user=FakeUser(user_id=user_id), guild=signup.guild, message=signup.message)


def choose(select, value):
    select._values = [value]
    return select


async def test_smmulti_creates_open_game(signup):
    embed = signup.message.embeds[0]
    assert [f.name for f in embed.fields] == ["Owner", "Status", "Randomizer", "Preset", "Players"]
    assert field(embed, "Owner") == f"<@{OWNER}>"
    game = await models.Multiworld.get(message_id=4242)
    assert (game.owner_id, game.status) == (OWNER, "STARTED")
    assert isinstance(signup.view, mw_cog.MultiworldSignupView)


async def test_only_owner_picks_randomizer_and_preset(signup):
    choose(signup.view.randomizer, "smz3")
    stranger = click(signup, user_id=8)
    await signup.view.randomizer.callback(stranger)
    assert stranger.sent().content == "You are not authorized to set the randomizer."

    owner = click(signup)
    await signup.view.randomizer.callback(owner)
    embed = owner.response.edit_message.await_args.kwargs["embed"]
    assert (field(embed, "Randomizer"), field(embed, "Preset")) == ("smz3", mw_cog.NOT_YET_CHOSEN)
    preset_select = signup.view.preset
    assert preset_select.disabled is False
    assert [o.label for o in preset_select.options] == [o.label for o in mw_cog.PRESET_OPTIONS["smz3"]]

    choose(preset_select, "hard")
    stranger = click(signup, user_id=8)
    await preset_select.callback(stranger)
    assert stranger.sent().content == "You are not authorized set the preset."
    owner = click(signup)
    await preset_select.callback(owner)
    assert field(owner.response.edit_message.await_args.kwargs["embed"], "Preset") == "hard"
    game = await models.Multiworld.get(message_id=4242)
    assert (game.randomizer, game.preset) == ("smz3", "hard")


async def test_join_and_leave_update_player_list(signup):
    first = click(signup, user_id=11)
    await signup.view.join.callback(first)
    assert first.sent().content == "You have been added to the multiworld."
    again = click(signup, user_id=11)
    await signup.view.join.callback(again)
    assert again.sent().content == "You are already signed up for this multiworld."
    await signup.view.join.callback(click(signup, user_id=12))
    assert field(signup.message.edit.await_args.kwargs["embed"], "Players") == "<@11>\n<@12>"

    await signup.view.leave.callback(click(signup, user_id=11))
    await signup.view.leave.callback(click(signup, user_id=12))
    assert field(signup.message.edit.await_args.kwargs["embed"], "Players") == "No players yet."


async def test_start_refusals(signup):
    stranger = click(signup, user_id=8)
    await signup.view.start.callback(stranger)
    assert stranger.sent().content == "You are not authorized to start this game."

    owner = click(signup)
    await signup.view.start.callback(owner)
    assert owner.sent().content.startswith("Please ensure you choose both a randomizer and preset")

    await models.Multiworld.filter(message_id=4242).update(randomizer="sm", preset="casual_full")
    signup.guild.members[11] = FakeUser(user_id=11)
    await signup.view.join.callback(click(signup, user_id=11))
    lonely = click(signup)
    await signup.view.start.callback(lonely)
    assert lonely.sent().content == "You must have at least two players to create a multiworld."
    assert field(signup.message.edit.await_args.kwargs["embed"], "Status") == "👍 Open for entry"


async def test_start_rolls_and_dms_players(monkeypatch, signup):
    start = mock.AsyncMock(return_value=SimpleNamespace(url="https://samus.test/multiworld/abc"))
    monkeypatch.setattr(mw_cog.multiworld_service, "start", start)
    await models.Multiworld.filter(message_id=4242).update(randomizer="sm", preset="casual_full")
    alice = FakeUser(user_id=11, name="alice", display_name="Alice the Great!")
    bob = FakeUser(user_id=12, name="bob", display_name="Bob")
    bob.send.side_effect = discord.Forbidden(mock.Mock(status=403), "Cannot send messages to this user")
    signup.guild.members.update({11: alice, 12: bob})
    for player in (alice, bob):
        await signup.view.join.callback(click(signup, user_id=player.id))

    await signup.view.start.callback(click(signup))

    assert start.await_args.args[1] == ["Alice the Great", "Bob"]
    dm = alice.send.await_args.kwargs["embed"]
    assert dm.title == "SM Multiworld Game"
    assert field(dm, "Players") == "alice\nbob"
    assert field(dm, "Game Room") == "https://samus.test/multiworld/abc"
    final = signup.message.edit.await_args.kwargs
    assert field(final["embed"], "Status") == "✅ Game started!  Check your DMs."
    assert all(item.disabled for item in final["view"].children)


async def test_cancel(signup):
    stranger = click(signup, user_id=8)
    await signup.view.cancel.callback(stranger)
    assert stranger.sent().content == "You are not authorized to cancel this game."

    owner = click(signup)
    await signup.view.cancel.callback(owner)
    kwargs = owner.response.edit_message.await_args.kwargs
    assert field(kwargs["embed"], "Status") == "❌ Cancelled."
    assert all(item.disabled for item in kwargs["view"].children)
    assert (await models.Multiworld.get(message_id=4242)).status == "CANCELLED"


def test_smmulti_embed_helpers():
    embed = discord.Embed().add_field(name="A", value="1", inline=False)
    mw_cog.set_embed_field("A", "2", embed)
    mw_cog.set_embed_field("missing", "x", embed)
    assert mw_cog.get_embed_field("A", embed) == "2"
    assert embed.fields[0].inline is False
    assert mw_cog.get_embed_field("missing", embed) is None

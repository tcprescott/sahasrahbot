"""Role menus: the service (alttprbot/services/role_menus.py), the Discord side
(alttprbot_discord/role_menus.py and cogs/role_menus.py), the /api/v1 routes and the
migration that copies the old reaction roles."""

import importlib
from types import SimpleNamespace
from unittest import mock

import discord
import pytest

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.services import role_menus
from alttprbot.services.role_menus import MenuInput, OptionInput
from alttprbot_discord import role_menus as discord_menus
from alttprbot_discord.cogs import role_menus as menus_cog
from tests.discord_fakes import FakeBot, FakeChannel, FakeGuild, FakeInteraction, FakeMessage, FakeRole, FakeUser, call
from tests.test_api import CSRF, get_json, login, send_json  # noqa: F401  (login is a fixture)

GUILD, ADMIN, OTHER = 5, 11, 12


@pytest.fixture
def world(db, directory, role_menu_discord):
    directory.add_guild(GUILD, name="Community", admins=[ADMIN])
    role_menu_discord.add_server(GUILD)
    return SimpleNamespace(directory=directory, discord=role_menu_discord)


def pronouns(style="buttons", **changes) -> MenuInput:
    data = MenuInput(guild_id=GUILD, channel_id=300, title="Pronouns", description="Pick yours", style=style,
                     options=[OptionInput(role_id=501, label="she/her", emoji="💜"),
                              OptionInput(role_id=502, label="he/him", emoji="<:triforce:9001>")])
    for key, value in changes.items():
        setattr(data, key, value)
    return data


# --- emoji -------------------------------------------------------------------------------


@pytest.mark.parametrize("text, stored", [
    ("💜", "💜"),
    ("  <:triforce:9001123456789012>  ", "<:triforce:9001123456789012>"),
    ("<a:spin:9001123456789012>", "<a:spin:9001123456789012>"),
    (":triforce:9001123456789012", "<:triforce:9001123456789012>"),
    ("triforce:9001123456789012", "<:triforce:9001123456789012>"),
    ("", None),
    (None, None),
])
def test_clean_emoji(text, stored):
    assert role_menus.clean_emoji(text) == stored


@pytest.mark.parametrize("text", ["abc", "two words", "x" * 30])
def test_clean_emoji_refuses_text(text):
    with pytest.raises(InvalidInputError, match="isn't an emoji"):
        role_menus.clean_emoji(text)


def test_emoji_key_ignores_custom_names_and_variation_selectors():
    assert role_menus.emoji_key("<:old:123456789012345678>") == role_menus.emoji_key("<:renamed:123456789012345678>")
    assert role_menus.emoji_key("❤️") == role_menus.emoji_key("❤")
    assert role_menus.emoji_key(None) is None


# --- managing menus ------------------------------------------------------------------------


async def test_create_posts_and_audits(world):
    menu = await role_menus.create_menu(ADMIN, pronouns())
    assert (menu['message_id'], menu['guild_name'], menu['channel_name'], menu['problems']) == (
        5001, "Community", "#roles", [])
    assert [(o['label'], o['role_name'], o['emoji']) for o in menu['options']] == [
        ("she/her", "@she/her", "💜"), ("he/him", "@he/him", "<:triforce:9001>")]
    assert world.discord.published[0]['style'] == "buttons"
    [entry] = await models.AuditLog.all()
    assert (entry.action, entry.target, entry.guild_id) == ("role_menu.created", "Pronouns", GUILD)
    assert entry.details['roles'] == ["💜 she/her (501)", "<:triforce:9001> he/him (502)"]


async def test_only_admins_manage(world):
    with pytest.raises(PermissionDeniedError):
        await role_menus.create_menu(OTHER, pronouns())
    menu = await role_menus.create_menu(ADMIN, pronouns())
    for attempt in (role_menus.get_menu(menu['id'], OTHER), role_menus.delete_menu(menu['id'], OTHER),
                    role_menus.update_menu(menu['id'], OTHER, pronouns()), role_menus.repost(menu['id'], OTHER),
                    role_menus.server_options(GUILD, OTHER)):
        with pytest.raises(PermissionDeniedError):
            await attempt
    with pytest.raises(NotFoundError):
        await role_menus.get_menu(9999, ADMIN)
    world.directory.owner = OTHER
    assert (await role_menus.get_menu(menu['id'], OTHER))['id'] == menu['id']


async def test_validation_lists_every_problem(world):
    bad = pronouns(style="reactions", title=" ", options=[
        OptionInput(role_id=501, label="", emoji=None),
        OptionInput(role_id=501, label="x" * 81, emoji="nope"),
        OptionInput(role_id=502, label="ok", emoji="💜", description="d" * 101),
        OptionInput(role_id=503, label="dupe", emoji="💜"),
    ])
    with pytest.raises(InvalidInputError) as e:
        await role_menus.create_menu(ADMIN, bad)
    text = str(e.value)
    for part in ("Give the menu a title.", "Role 1 needs a label.", "Role 1 needs an emoji",
                 "at most 80 characters", "“nope” isn't an emoji", "that role is already on this menu",
                 "a description can be at most 100", "that emoji is already on this menu"):
        assert part in text, part
    with pytest.raises(InvalidInputError, match="Add at least one role"):
        await role_menus.create_menu(ADMIN, pronouns(options=[]))
    with pytest.raises(InvalidInputError, match="at most 20 roles"):
        await role_menus.create_menu(ADMIN, pronouns(style="reactions", options=[
            OptionInput(role_id=i, label=str(i), emoji=chr(0x1F600 + i)) for i in range(21)]))
    with pytest.raises(InvalidInputError, match="Pick reactions, buttons or a dropdown"):
        await role_menus.create_menu(ADMIN, pronouns(style="carousel"))
    assert await models.RoleMenu.all().count() == 0


async def test_roles_and_channels_must_work(world):
    world.discord.add_server(GUILD, roles=((501, "@she/her", True), (502, "@Mods", False)))
    with pytest.raises(InvalidInputError, match="can't give @Mods"):
        await role_menus.create_menu(ADMIN, pronouns())
    with pytest.raises(InvalidInputError, match="pick a role from this server"):
        await role_menus.create_menu(ADMIN, pronouns(options=[OptionInput(role_id=777, label="x")]))
    with pytest.raises(InvalidInputError, match="can't post in that channel"):
        await role_menus.create_menu(ADMIN, pronouns(channel_id=301, options=[OptionInput(role_id=501, label="x")]))


async def test_failed_post_keeps_nothing(world):
    world.discord.publish_error = InvalidInputError("Discord said no")
    with pytest.raises(InvalidInputError, match="Discord said no"):
        await role_menus.create_menu(ADMIN, pronouns())
    assert await models.RoleMenu.all().count() == 0
    assert await models.RoleMenuOption.all().count() == 0


async def test_update_keeps_options_and_redraws(world):
    menu = await role_menus.create_menu(ADMIN, pronouns())
    she, he = menu['options']
    data = pronouns(style="dropdown", single_choice=True, options=[
        OptionInput(id=he['id'], role_id=502, label="he/him", emoji=None),
        OptionInput(role_id=501, label="she/her (new)", emoji="💜"),
    ])
    updated = await role_menus.update_menu(menu['id'], ADMIN, data)
    assert updated['options'][0]['id'] == he['id']
    assert she['id'] not in [o['id'] for o in updated['options']]
    assert (updated['style'], updated['single_choice'], updated['message_id']) == ("dropdown", True, 5001)
    assert world.discord.removed == []  # same channel: redrawn in place
    entry = await models.AuditLog.filter(action="role_menu.updated").first()
    assert entry.details['changes']['style'] == ["buttons", "dropdown"]

    with pytest.raises(InvalidInputError, match="stays in its server"):
        await role_menus.update_menu(menu['id'], ADMIN, pronouns(guild_id=6))


async def test_moving_channel_posts_anew(world):
    world.discord.add_server(GUILD, channels=((300, "#roles"), (301, "#welcome")))
    menu = await role_menus.create_menu(ADMIN, pronouns())
    moved = await role_menus.update_menu(menu['id'], ADMIN, pronouns(channel_id=301))
    assert [m['channel_id'] for m in world.discord.removed] == [300]
    assert (moved['channel_id'], moved['message_id']) == (301, 5002)


async def test_menu_on_someone_elses_message(world):
    """Menus copied from the old reaction roles on another person's message stay reactions until reposted."""
    legacy = await models.RoleMenu.create(guild_id=GUILD, channel_id=300, message_id=42, title="Regions",
                                          style="reactions", posted_by_bot=False)
    await models.RoleMenuOption.create(menu=legacy, role_id=501, label="NA", emoji="🇺🇸")
    with pytest.raises(InvalidInputError, match="can only use reactions"):
        await role_menus.update_menu(legacy.id, ADMIN, pronouns())
    with pytest.raises(InvalidInputError, match="can't move"):
        await role_menus.update_menu(legacy.id, ADMIN, pronouns(style="reactions", channel_id=301))

    reposted = await role_menus.repost(legacy.id, ADMIN)
    assert (reposted['posted_by_bot'], reposted['message_id']) == (True, 5001)
    assert world.discord.removed[0]['message_id'] == 42
    assert (await models.AuditLog.get(action="role_menu.reposted")).target == "Regions"
    # Now it can switch.
    assert (await role_menus.update_menu(legacy.id, ADMIN, pronouns()))['style'] == "buttons"


async def test_delete_takes_it_off_discord(world):
    menu = await role_menus.create_menu(ADMIN, pronouns())
    await role_menus.delete_menu(menu['id'], ADMIN)
    assert world.discord.removed[0]['id'] == menu['id']
    assert await models.RoleMenu.all().count() == 0
    assert await models.RoleMenuOption.all().count() == 0
    assert (await models.AuditLog.get(action="role_menu.deleted")).target == "Pronouns"


async def test_list_and_problems(world, directory):
    directory.add_guild(6, name="Another", admins=[ADMIN])
    await role_menus.create_menu(ADMIN, pronouns())
    await models.RoleMenu.create(guild_id=6, channel_id=1, title="Gone server", style="reactions")
    broken = await models.RoleMenu.create(guild_id=GUILD, channel_id=999, title="Broken", style="reactions")
    await models.RoleMenuOption.create(menu=broken, role_id=777, label="Deleted role", emoji="🙂")
    world.discord.add_server(GUILD, roles=((501, "@she/her", True), (502, "@he/him", False)))
    await models.RoleMenuOption.create(menu=broken, role_id=502, label="he/him", emoji="💙")

    menus = await role_menus.list_menus({GUILD, 6})
    assert [(m['guild_name'], m['title']) for m in menus] == [
        ("Another", "Gone server"), ("Community", "Broken"), ("Community", "Pronouns")]
    assert menus[0]['problems'] == ["SahasrahBot isn't in this server any more."]
    assert menus[1]['problems'] == [
        "SahasrahBot can't post in this menu's channel, or the channel was deleted.",
        "The role for “Deleted role” was deleted.",
        "SahasrahBot can't give @he/him: it's above SahasrahBot's highest role, or SahasrahBot doesn't have "
        "Manage Roles."]
    assert await role_menus.list_menus({7}) == []
    assert [m['title'] for m in await role_menus.menus_in_guild(GUILD)] == ["Broken", "Pronouns"]


async def test_server_options(world):
    options = await role_menus.server_options(GUILD, ADMIN)
    assert options == {
        'channels': [{'id': 300, 'name': '#roles'}],
        'roles': [{'id': 501, 'name': '@she/her', 'assignable': True},
                  {'id': 502, 'name': '@he/him', 'assignable': True}],
        'emojis': [{'id': 9001, 'name': '<:triforce:9001>'}],
    }
    world.directory.add_guild(8, admins=[ADMIN])
    with pytest.raises(NotFoundError):
        await role_menus.server_options(8, ADMIN)


# --- people picking --------------------------------------------------------------------------


async def test_reaction_target(world):
    menu = await role_menus.create_menu(ADMIN, pronouns(style="reactions", single_choice=True, options=[
        OptionInput(role_id=501, label="she/her", emoji="❤️"),
        OptionInput(role_id=502, label="he/him", emoji="<:old_name:123456789012345678>")]))
    target = await role_menus.reaction_target(GUILD, 5001, "<:renamed:123456789012345678>")
    assert (target.role_id, target.single_choice, target.others) == (502, True, ((501, "❤️"),))
    assert (await role_menus.reaction_target(GUILD, 5001, "❤")).role_id == 501
    assert await role_menus.reaction_target(GUILD, 5001, "🎉") is None
    assert await role_menus.reaction_target(6, 5001, "❤") is None
    assert await role_menus.reaction_target(GUILD, 1234, "❤") is None

    # A buttons menu doesn't answer reactions, and the cache follows the change.
    await role_menus.update_menu(menu['id'], ADMIN, pronouns())
    assert await role_menus.reaction_target(GUILD, 5001, "💜") is None


async def test_component_menu(world):
    menu = await role_menus.create_menu(ADMIN, pronouns())
    assert (await role_menus.component_menu(menu['id'], GUILD))['title'] == "Pronouns"
    assert await role_menus.component_menu(menu['id'], 6) is None
    await role_menus.update_menu(menu['id'], ADMIN, pronouns(style="reactions"))
    assert await role_menus.component_menu(menu['id'], GUILD) is None


def test_toggle():
    menu = {'single_choice': False, 'options': [{'id': 1, 'role_id': 501}, {'id': 2, 'role_id': 502},
                                                {'id': 3, 'role_id': 503}]}
    assert role_menus.toggle(menu, [1, 2], [502]) == role_menus.RoleChange(add=(501,), remove=(502,))
    assert role_menus.toggle(menu, [9], []) == role_menus.RoleChange(add=(), remove=())
    single = {**menu, 'single_choice': True}
    assert role_menus.toggle(single, [3], [501, 502, 999]) == role_menus.RoleChange(add=(503,), remove=(501, 502))
    assert role_menus.toggle(single, [1], [501]) == role_menus.RoleChange(add=(), remove=(501,))


# --- Discord -------------------------------------------------------------------------------------


def menu_view(style="buttons", single=False, message_id=None, posted_by_bot=True):
    return {'id': 3, 'guild_id': GUILD, 'channel_id': 300, 'message_id': message_id, 'title': "Pronouns",
            'description': "Pick yours", 'style': style, 'posted_by_bot': posted_by_bot, 'single_choice': single,
            'options': [{'id': 1, 'role_id': 501, 'label': "she/her", 'description': "Ask me", 'emoji': "💜"},
                        {'id': 2, 'role_id': 502, 'label': "he/him", 'description': None,
                         'emoji': "<:triforce:123456789012345678>"}]}


def test_message_for_each_style():
    reactions = discord_menus.message_parts(menu_view("reactions"))
    assert reactions['embed'].fields[0].value == "💜 **she/her** – Ask me\n<:triforce:123456789012345678> **he/him**"
    assert reactions['view'].children == []

    buttons = discord_menus.message_parts(menu_view("buttons", single=True))
    assert buttons['embed'].fields == []
    assert buttons['embed'].footer.text == "You can have one of these roles at a time."
    assert [(b.item.label, b.item.custom_id) for b in buttons['view'].children] == [
        ("she/her", "rolemenu:3:1"), ("he/him", "rolemenu:3:2")]

    dropdown = discord_menus.message_parts(menu_view("dropdown"))
    [select] = dropdown['view'].children
    assert (select.item.custom_id, select.item.max_values) == ("rolemenu:3:pick", 2)
    assert [(o.label, o.value, o.description) for o in select.item.options] == [
        ("she/her", "1", "Ask me"), ("he/him", "2", None)]


class FakeMember(FakeUser):
    def __init__(self, role_ids=()):
        super().__init__(user_id=55)
        self.roles = [FakeRole(r) for r in role_ids]


async def test_button_toggles_and_answers_privately(monkeypatch):
    monkeypatch.setattr(role_menus, "component_menu", mock.AsyncMock(return_value=menu_view("buttons")))
    member = FakeMember(role_ids=[502])
    interaction = FakeInteraction(user=member, guild=FakeGuild(guild_id=GUILD))
    await discord_menus.RoleMenuButton(3, option_id=1).callback(interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    assert [r.id for r in member.add_roles.await_args.args] == [501]
    member.remove_roles.assert_not_awaited()
    assert (interaction.sent().content, interaction.sent().ephemeral) == ("Added <@&501>.", True)


async def test_dropdown_redraws_and_reports_forbidden(monkeypatch):
    monkeypatch.setattr(role_menus, "component_menu", mock.AsyncMock(return_value=menu_view("dropdown")))
    member = FakeMember(role_ids=[501])
    member.remove_roles.side_effect = discord.Forbidden(mock.Mock(status=403), "Missing Permissions")
    interaction = FakeInteraction(user=member, guild=FakeGuild(guild_id=GUILD))
    select = discord_menus.RoleMenuSelect(3)
    select.item._values = ["1"]  # what Discord sent
    monkeypatch.setattr(type(select.item), "values", property(lambda self: ["1"]))
    await select.callback(interaction)
    interaction.response.edit_message.assert_awaited_once()
    assert "isn't allowed to change that role" in interaction.sent().content


async def test_stale_component(monkeypatch):
    monkeypatch.setattr(role_menus, "component_menu", mock.AsyncMock(return_value=None))
    interaction = FakeInteraction(user=FakeMember(), guild=FakeGuild(guild_id=GUILD))
    await discord_menus.RoleMenuButton(3, option_id=1).callback(interaction)
    assert interaction.sent().content == "This role menu isn't in use any more."


def reaction(emoji="💜", user_id=55, member=None):
    return SimpleNamespace(guild_id=GUILD, channel_id=300, message_id=5001, user_id=user_id, emoji=emoji,
                           member=member)


async def test_reactions_add_and_remove_roles(monkeypatch):
    target = role_menus.ReactionTarget(menu_id=3, role_id=501, single_choice=True, others=((502, "💙"),))
    lookup = mock.AsyncMock(return_value=target)
    monkeypatch.setattr(role_menus, "reaction_target", lookup)
    bot = FakeBot()
    bot.http = SimpleNamespace(add_role=mock.AsyncMock(), remove_role=mock.AsyncMock())
    message = FakeMessage(message_id=5001)
    bot.get_partial_messageable = mock.Mock(return_value=SimpleNamespace(
        get_partial_message=mock.Mock(return_value=message)))
    cog = menus_cog.RoleMenus(bot)

    await cog.on_raw_reaction_add(reaction())
    bot.http.add_role.assert_awaited_once_with(GUILD, 55, 501, reason=discord_menus.ADDED_REASON)
    bot.http.remove_role.assert_awaited_once_with(GUILD, 55, 502, reason=discord_menus.REMOVED_REASON)
    assert message.remove_reaction.await_args.args[1].id == 55

    await cog.on_raw_reaction_remove(reaction())
    assert bot.http.remove_role.await_args.args == (GUILD, 55, 501)

    # The bot's own reactions and other bots' are ignored.
    lookup.reset_mock()
    await cog.on_raw_reaction_add(reaction(user_id=999))
    await cog.on_raw_reaction_add(reaction(member=SimpleNamespace(bot=True)))
    lookup.assert_not_awaited()


async def test_reaction_without_permission_is_logged(monkeypatch, caplog):
    target = role_menus.ReactionTarget(menu_id=3, role_id=501, single_choice=False, others=())
    monkeypatch.setattr(role_menus, "reaction_target", mock.AsyncMock(return_value=target))
    bot = FakeBot()
    bot.http = SimpleNamespace(add_role=mock.AsyncMock(side_effect=discord.Forbidden(mock.Mock(status=403), "no")))
    await discord_menus.reaction_changed(bot, reaction(), added=True)
    assert "missing permission" in caplog.text


async def test_rolemenus_command_lists_and_links(world):
    await role_menus.create_menu(ADMIN, pronouns())
    cog = menus_cog.RoleMenus(FakeBot())
    interaction = FakeInteraction(guild=FakeGuild(guild_id=GUILD))
    await call(cog.rolemenus, cog, interaction)
    sent = interaction.sent()
    assert "Pronouns" in sent.content and "Buttons" in sent.content
    assert f"/channels/{GUILD}/300/5001" in sent.content
    assert sent.view.children[0].url.endswith(f"/servers/{GUILD}/role-menus/new?channel=300")
    assert f"/servers/{GUILD}/role-menus/" in sent.content

    empty = FakeInteraction(guild=FakeGuild(guild_id=6))
    await call(cog.rolemenus, cog, empty)
    assert empty.sent().content == "This server has no role menus yet."


# --- the gateway -------------------------------------------------------------------------------


class GatewayChannel(FakeChannel):
    type = discord.ChannelType.text
    position = 0

    def __init__(self, message):
        super().__init__(channel_id=300, name="roles")
        self.message = message
        self.get_partial_message = mock.Mock(return_value=message)
        self.fetch_message = mock.AsyncMock(return_value=message)


def gateway_message(reactions=()):
    message = FakeMessage(message_id=5001)
    message.reactions = list(reactions)
    message.edit = mock.AsyncMock(return_value=message)
    message.delete = mock.AsyncMock()
    return message


async def test_gateway_redraws_and_syncs_reactions():
    stale = SimpleNamespace(emoji="🎉", me=True)
    message = gateway_message([stale, SimpleNamespace(emoji="💜", me=True)])
    channel = GatewayChannel(message)
    message.channel = channel
    bot = FakeBot()
    bot.get_channel = mock.Mock(return_value=channel)
    gateway = discord_menus.RoleMenuGateway(bot)

    assert await gateway.publish(menu_view("reactions", message_id=5001)) == 5001
    message.edit.assert_awaited_once()
    message.remove_reaction.assert_awaited_once_with("🎉", bot.user)
    [added] = message.add_reaction.await_args_list
    assert str(added.args[0]) == "<:triforce:123456789012345678>"


async def test_gateway_posts_when_the_message_is_gone_and_explains_refusals():
    message = gateway_message()
    channel = GatewayChannel(message)
    message.channel = channel
    message.edit.side_effect = discord.NotFound(mock.Mock(status=404), "gone")
    channel.send = mock.AsyncMock(return_value=message)
    bot = FakeBot()
    bot.get_channel = mock.Mock(return_value=channel)
    gateway = discord_menus.RoleMenuGateway(bot)
    assert await gateway.publish(menu_view("buttons", message_id=4000)) == 5001
    channel.send.assert_awaited_once()

    channel.send.side_effect = discord.Forbidden(mock.Mock(status=403), "no")
    with pytest.raises(InvalidInputError, match="isn't allowed to post"):
        await gateway.publish(menu_view("buttons"))

    channel.fetch_message.side_effect = discord.NotFound(mock.Mock(status=404), "gone")
    with pytest.raises(InvalidInputError, match="was deleted"):
        await gateway.publish(menu_view("reactions", message_id=42, posted_by_bot=False))

    channel.fetch_message.side_effect = None
    message.add_reaction.side_effect = discord.HTTPException(mock.Mock(status=400), {"code": 10014, "message": "x"})
    with pytest.raises(InvalidInputError, match="can't use the emoji 💜"):
        await gateway.publish(menu_view("reactions", message_id=42, posted_by_bot=False))


async def test_gateway_remove():
    message = gateway_message()
    channel = GatewayChannel(message)
    bot = FakeBot()
    bot.get_channel = mock.Mock(return_value=channel)
    gateway = discord_menus.RoleMenuGateway(bot)
    await gateway.remove(menu_view(message_id=5001))
    message.delete.assert_awaited_once()
    await gateway.remove(menu_view("reactions", message_id=42, posted_by_bot=False))
    assert message.remove_reaction.await_count == 2
    await gateway.remove(menu_view())  # never posted: nothing to do


class GatewayRole(SimpleNamespace):
    def __lt__(self, other):
        return self.position < other.position

    def is_default(self):
        return False


async def test_gateway_server_details():
    roles = [GatewayRole(id=501, name="she/her", position=1, managed=False),
             GatewayRole(id=503, name="Mods", position=9, managed=False),
             GatewayRole(id=600, name="SahasrahBot", position=5, managed=True)]
    me = FakeUser(user_id=999)
    me.guild_permissions = discord.Permissions(manage_roles=True)
    me.top_role = roles[2]
    postable = GatewayChannel(gateway_message())
    postable.permissions_for = lambda who: discord.Permissions(view_channel=True, send_messages=True,
                                                               embed_links=True, add_reactions=True)
    muted = GatewayChannel(gateway_message())  # FakeChannel grants nothing
    tri = mock.Mock(id=9, available=True)
    tri.name = "tri"
    tri.__str__ = lambda self: "<:tri:9>"
    guild = SimpleNamespace(me=me, channels=[postable, muted], roles=roles, emojis=[tri])
    bot = FakeBot()
    bot.get_guild = mock.Mock(side_effect=lambda gid: guild if gid == GUILD else None)
    gateway = discord_menus.RoleMenuGateway(bot)

    details = await gateway.server(GUILD)
    assert [(r.name, r.assignable) for r in details.roles] == [("@Mods", False), ("@she/her", True)]
    assert len(details.channels) == 1
    assert [e.name for e in details.emojis] == ["<:tri:9>"]
    assert await gateway.server(6) is None


# --- /api/v1 -------------------------------------------------------------------------------------


@pytest.fixture
def client(db):
    from alttprbot_api import api
    return api.sahasrahbotapi.test_client()


async def test_api_round_trip(client, login, world):  # noqa: F811
    login(ADMIN)
    assert await get_json(client, "/api/v1/role-menus/servers") == (200, {"servers": [{"id": "5", "name": "Community"}]})
    status, options = await get_json(client, f"/api/v1/role-menus/servers/{GUILD}")
    assert options['roles'][0] == {"id": "501", "name": "@she/her", "assignable": True}

    form = {"guild_id": "5", "channel_id": "300", "title": "Pronouns", "style": "buttons",
            "options": [{"role_id": "501", "label": "she/her", "emoji": "💜"}]}
    status, menu = await send_json(client, "POST", "/api/v1/role-menus", form)
    assert (status, menu['message_id'], menu['options'][0]['role_id']) == (201, "5001", "501")

    form['options'].append({"role_id": "502", "label": "he/him"})
    status, menu = await send_json(client, "PUT", f"/api/v1/role-menus/{menu['id']}",
                                   {**form, "options": [{**form['options'][0], "id": menu['options'][0]['id']},
                                                        form['options'][1]]})
    assert (status, len(menu['options'])) == (200, 2)

    status, listed = await get_json(client, "/api/v1/role-menus")
    assert [m['title'] for m in listed['menus']] == ["Pronouns"]
    assert (await get_json(client, "/api/v1/role-menus?guild_id=5"))[1]['menus'][0]['title'] == "Pronouns"
    assert (await get_json(client, "/api/v1/role-menus?guild_id=6"))[1] == {"menus": []}
    assert (await send_json(client, "POST", f"/api/v1/role-menus/{menu['id']}/repost", {}))[0] == 200
    status, body = await send_json(client, "POST", "/api/v1/role-menus", {**form, "options": []})
    assert (status, body) == (400, {"error": "Add at least one role."})
    assert (await send_json(client, "DELETE", f"/api/v1/role-menus/{menu['id']}"))[0] == 204
    assert (await get_json(client, f"/api/v1/role-menus/{menu['id']}"))[0] == 404

    login(OTHER)
    assert (await send_json(client, "POST", "/api/v1/role-menus", form))[0] == 403


# --- the migration -------------------------------------------------------------------------------


async def test_migration_copies_reaction_roles_with_their_ids():
    """The SQL is MySQL's; check what it copies and skips by reading it."""
    migration = importlib.import_module("migrations.models.101_20261126170000_role_menus")
    sql = await migration.upgrade(None)
    assert "INSERT INTO `role_menu` (`id`," in sql and "FROM `reaction_group`" in sql
    assert "'reactions'" in sql and "COALESCE(`bot_managed`, 0) <> 0" in sql
    assert "JOIN `reaction_group` g ON g.`id` = r.`reaction_group_id` AND g.`guild_id` = r.`guild_id`" in sql
    assert "WHERE r.`role_id` IS NOT NULL" in sql
    assert "DROP" not in sql and "reaction_role`" in sql
    assert "DROP TABLE IF EXISTS `role_menu`" in await migration.downgrade(None)

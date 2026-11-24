"""Small stand-ins for discord.py objects, for testing cogs without Discord.

Cog commands are called through their callbacks, so no command tree, gateway or
HTTP session is involved:

    cog = Misc(FakeBot())
    interaction = FakeInteraction()
    await call(cog.rom, cog, interaction)
    assert "checkcrc" in interaction.sent().content

``call`` works for app commands (``app_commands.Command``), prefix commands
(``commands.Command``) and plain coroutine methods such as autocompletes.
Everything that would talk to Discord is an ``AsyncMock`` you can assert on.
"""

from types import SimpleNamespace
from unittest import mock

import discord


def emoji(name, emoji_id=1):
    """A custom emoji that ``str()``s like Discord's ``<:name:id>``."""
    e = mock.Mock(spec=["name", "id", "url", "__str__"])
    e.name = name
    e.id = emoji_id
    e.url = f"https://cdn.test/emojis/{emoji_id}.png"
    e.__str__ = lambda self: f"<:{self.name}:{self.id}>"
    return e


def permissions(**flags):
    """A ``discord.Permissions`` with only the named flags set."""
    return discord.Permissions(**flags)


class FakeUser:
    def __init__(self, user_id=1001, name="runner", display_name=None, administrator=False):
        self.id = user_id
        self.name = name
        self.display_name = display_name or name
        self.discriminator = "0"
        self.mention = f"<@{user_id}>"
        self.bot = False
        self.guild_permissions = permissions(administrator=administrator)
        self.send = mock.AsyncMock()
        self.add_roles = mock.AsyncMock()
        self.remove_roles = mock.AsyncMock()

    def __str__(self):
        return self.name


class FakeRole:
    def __init__(self, role_id=500, name="Role", mentionable=True):
        self.id = role_id
        self.name = name
        self.mention = f"<@&{role_id}>"
        self.mentionable = mentionable

    def __str__(self):
        return self.name


class FakeMessage:
    def __init__(self, message_id=700, embeds=None, channel=None, guild=None, author=None):
        self.id = message_id
        self.embeds = embeds or []
        self.channel = channel
        self.guild = guild
        self.author = author
        self.mentions = []
        self.jump_url = f"https://discord.test/channels/x/y/{message_id}"
        self.attachments = []
        self.edit = mock.AsyncMock()
        self.add_reaction = mock.AsyncMock()
        self.remove_reaction = mock.AsyncMock()


class FakeChannel:
    def __init__(self, channel_id=300, name="general", guild=None, perms=None):
        self.id = channel_id
        self.name = name
        self.guild = guild
        self.mention = f"<#{channel_id}>"
        # who -> discord.Permissions; anyone not listed gets no permissions
        self.perms = perms or {}
        self.sent = []

        async def send(content=None, **kwargs):
            message = FakeMessage(message_id=800 + len(self.sent), channel=self)
            self.sent.append(SimpleNamespace(content=content, **kwargs))
            return message

        self.send = mock.AsyncMock(side_effect=send)
        self.purge = mock.AsyncMock()
        self.fetch_message = mock.AsyncMock(side_effect=lambda mid: FakeMessage(message_id=mid, channel=self))
        self.create_thread = mock.AsyncMock()

    def permissions_for(self, who):
        return self.perms.get(getattr(who, "id", who), discord.Permissions.none())


class FakeGuild:
    def __init__(self, guild_id=200, name="Test Guild", roles=(), channels=()):
        self.id = guild_id
        self.name = name
        self.roles = list(roles)
        self.channels = list(channels)
        for channel in self.channels:
            channel.guild = self
        self.me = FakeUser(user_id=999, name="SahasrahBot")
        self.default_role = FakeRole(role_id=guild_id, name="@everyone")
        self.members = {}
        self.fetch_member = mock.AsyncMock(side_effect=lambda uid: self.members[uid])

    def get_role(self, role_id):
        return discord.utils.get(self.roles, id=role_id)

    def get_channel(self, channel_id):
        return discord.utils.get(self.channels, id=channel_id)


class FakeResponse:
    def __init__(self):
        self.defer = mock.AsyncMock()
        self.send_message = mock.AsyncMock()
        self.send_modal = mock.AsyncMock()
        self.edit_message = mock.AsyncMock()


class FakeInteraction:
    """A slash-command, button or modal interaction.

    ``sent()`` returns what the command said last, whether it went through
    ``response.send_message`` or ``followup.send``, as a SimpleNamespace with
    ``content`` plus any keyword arguments (``embed``, ``ephemeral``, ``view``...).
    """

    def __init__(self, user=None, guild=None, channel=None, message=None, namespace=None):
        self.user = user or FakeUser()
        self.guild = guild
        self.channel = channel or FakeChannel(guild=guild)
        self.message = message
        self.namespace = SimpleNamespace(**(namespace or {}))
        self.response = FakeResponse()
        self.followup = SimpleNamespace(send=mock.AsyncMock())
        self.original = FakeMessage(message_id=4242, channel=self.channel, guild=guild)
        self.original_response = mock.AsyncMock(return_value=self.original)
        self.edit_original_response = mock.AsyncMock()

    def sent(self):
        call_ = self.followup.send.await_args or self.response.send_message.await_args
        assert call_ is not None, "the command sent nothing"
        content = call_.args[0] if call_.args else call_.kwargs.get("content")
        kwargs = {k: v for k, v in call_.kwargs.items() if k != "content"}
        return SimpleNamespace(content=content, **kwargs)


class FakeBot:
    def __init__(self, emojis=()):
        self.emojis = list(emojis)
        self.user = FakeUser(user_id=999, name="SahasrahBot")
        self.add_view = mock.Mock()
        self.fetch_invite = mock.AsyncMock()
        self.fetch_guild = mock.AsyncMock()
        self.is_owner = mock.AsyncMock(return_value=False)
        self.dispatch = mock.Mock()
        self.logger = mock.Mock()
        self.tree = mock.Mock()


class FakeContext:
    """A prefix-command context."""

    def __init__(self, guild=None, bot=None, attachments=()):
        self.guild = guild or FakeGuild()
        self.bot = bot or FakeBot()
        self.message = FakeMessage(guild=self.guild)
        self.message.attachments = list(attachments)
        self.reply = mock.AsyncMock()
        self.send = mock.AsyncMock()
        self.interaction = None
        self.clean_prefix = "$"
        self.command = None


async def call(command, cog, *args, **kwargs):
    """Run a cog command's body (app or prefix command, or a plain method)."""
    callback = getattr(command, "callback", None)
    if callback is not None:
        return await callback(cog, *args, **kwargs)
    return await command(*args, **kwargs)


class FakeDirectory:
    """A stand-in for ``alttprbot.services.discord_directory``: who owns the bot,
    which servers exist, who's in them with which roles, and who administers them.
    Register it with the ``directory`` fixture (tests/conftest.py)."""

    def __init__(self, owner=None):
        from alttprbot.services.discord_directory import Named
        self._named = Named
        self.owner = owner
        self.guilds = {}
        self.posted = []
        self.post_error = None

    def add_guild(self, guild_id, name="Test Server", admins=(), members=None, channels=((300, "#general"),),
                  roles=((77, "@Voters"),)):
        self.guilds[guild_id] = {
            "name": name, "admins": set(admins), "members": dict(members or {}),
            "channels": list(channels), "roles": list(roles),
        }
        for admin in admins:
            self.guilds[guild_id]["members"].setdefault(admin, [])
        return self

    async def is_owner(self, user_id):
        return user_id == self.owner

    def admin_guild_ids(self, user_id):
        """What Discord's /users/@me/guilds would say ``user_id`` administers."""
        return {gid for gid, g in self.guilds.items() if user_id in g["admins"]}

    async def bot_guilds(self, guild_ids):
        ids = set(guild_ids)
        return sorted((self._named(gid, g["name"]) for gid, g in self.guilds.items() if gid in ids),
                      key=lambda g: g.name.casefold())

    async def admin_guilds(self, user_id):
        return await self.bot_guilds(self.admin_guild_ids(user_id))

    async def is_admin(self, guild_id, user_id):
        return user_id in self.guilds.get(guild_id, {}).get("admins", set())

    async def member_role_ids(self, guild_id, user_id):
        members = self.guilds.get(guild_id, {}).get("members", {})
        return list(members[user_id]) if user_id in members else None

    async def guild_name(self, guild_id):
        return self.guilds.get(guild_id, {}).get("name")

    async def text_channels(self, guild_id):
        return [self._named(i, n) for i, n in self.guilds.get(guild_id, {}).get("channels", [])]

    async def roles(self, guild_id):
        return [self._named(i, n) for i, n in self.guilds.get(guild_id, {}).get("roles", [])]

    async def post_election(self, election_id):
        if self.post_error:
            raise self.post_error
        self.posted.append(election_id)
        return 9000 + len(self.posted)

"""An in-memory stand-in for the discord.py bot client.

The web app only touches a small part of ``discordbot``: guild, channel, role and
member lookups, ``fetch_user``, ``application_info`` and sending messages. These
classes duck-type that surface. Anything the app sends to a channel or a member
is recorded in ``OUTBOX`` so it can be inspected at ``/_dev/outbox``.

The world they describe (guilds, roles, channels, members) is built from
``devserver.fixtures`` and can be changed at runtime from the ``/_dev`` pages.
"""
import datetime
import itertools
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("devserver.discord")

OUTBOX: List[dict] = []
_message_ids = itertools.count(900000000000000001)


def _embed_to_dict(embed) -> Optional[dict]:
    if embed is None:
        return None
    to_dict = getattr(embed, "to_dict", None)
    return to_dict() if callable(to_dict) else {"repr": repr(embed)}


def record(target: str, content=None, embed=None, embeds=None, **kwargs) -> "FakeMessage":
    entry = {
        "id": next(_message_ids),
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target": target,
        "content": content,
        "embeds": [e for e in [_embed_to_dict(embed)] + [_embed_to_dict(x) for x in (embeds or [])] if e],
        "extra": sorted(k for k, v in kwargs.items() if v is not None),
    }
    OUTBOX.append(entry)
    logger.info("Discord message to %s: %s", target, content)
    return FakeMessage(entry)


class FakeMessage:
    def __init__(self, entry: dict):
        self.id = entry["id"]
        self.content = entry["content"]
        self._entry = entry

    async def edit(self, content=None, embed=None, embeds=None, **kwargs):
        record(f"{self._entry['target']} (edit of {self.id})", content=content, embed=embed, embeds=embeds, **kwargs)
        return self

    async def delete(self, **kwargs):
        return None

    async def add_reaction(self, emoji):
        return None

    @property
    def jump_url(self):
        return f"https://discord.com/channels/@dev/{self.id}"


class FakeRole:
    def __init__(self, guild: "FakeGuild", id: int, name: str, color: int = 0):
        self.guild = guild
        self.id = int(id)
        self.name = name
        self.color = color
        self.mention = f"<@&{self.id}>"

    def __eq__(self, other):
        return isinstance(other, FakeRole) and other.id == self.id

    def __hash__(self):
        return hash(("role", self.id))

    def __repr__(self):
        return f"<FakeRole {self.name} ({self.id})>"


class FakeUser:
    """A Discord user, not tied to a guild."""

    def __init__(self, id: int, name: str, global_name: Optional[str] = None, bot: bool = False):
        self.id = int(id)
        self.name = name
        self.global_name = global_name or name
        self.discriminator = "0"
        self.bot = bot
        self.mention = f"<@{self.id}>"

    @property
    def display_name(self):
        return self.global_name or self.name

    @property
    def display_avatar(self):
        return _Asset(f"/_fake/discord/avatars/{self.id}.svg")

    avatar = display_avatar

    async def send(self, content=None, **kwargs):
        return record(f"DM @{self.name}", content=content, **kwargs)

    async def create_dm(self):
        return self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return getattr(other, "id", None) == self.id

    def __hash__(self):
        return hash(("user", self.id))


class _Asset:
    def __init__(self, url):
        self.url = url

    def __str__(self):
        return self.url


class FakeMember(FakeUser):
    def __init__(self, guild: "FakeGuild", user: FakeUser, role_ids: List[int], nick: Optional[str] = None):
        super().__init__(user.id, user.name, user.global_name, user.bot)
        self.guild = guild
        self.nick = nick
        self._role_ids = [int(r) for r in role_ids]

    @property
    def display_name(self):
        return self.nick or self.global_name or self.name

    @property
    def roles(self) -> List[FakeRole]:
        roles = [self.guild.default_role]
        roles += [r for r in (self.guild.get_role(rid) for rid in self._role_ids) if r is not None]
        return roles

    async def add_roles(self, *roles, **kwargs):
        for role in roles:
            if role.id not in self._role_ids:
                self._role_ids.append(role.id)

    async def remove_roles(self, *roles, **kwargs):
        ids = {r.id for r in roles}
        self._role_ids = [r for r in self._role_ids if r not in ids]

    async def edit(self, **kwargs):
        if "nick" in kwargs:
            self.nick = kwargs["nick"]


class FakeChannel:
    def __init__(self, guild: Optional["FakeGuild"], id: int, name: str):
        self.guild = guild
        self.id = int(id)
        self.name = name
        self.mention = f"<#{self.id}>"
        self.jump_url = f"https://discord.com/channels/{guild.id if guild else '@me'}/{self.id}"

    async def send(self, content=None, **kwargs):
        return record(f"#{self.name}", content=content, **kwargs)

    async def fetch_message(self, message_id):
        return FakeMessage({"id": int(message_id), "content": None, "target": f"#{self.name}"})

    def get_partial_message(self, message_id):
        return FakeMessage({"id": int(message_id), "content": None, "target": f"#{self.name}"})

    async def create_thread(self, name=None, **kwargs):
        thread = FakeChannel(self.guild, next(_message_ids), f"{self.name}/{name}")
        if self.guild:
            self.guild._channels[thread.id] = thread
        return thread

    def __str__(self):
        return self.name


class FakeGuild:
    def __init__(self, world: "FakeWorld", id: int, name: str):
        self._world = world
        self.id = int(id)
        self.name = name
        self.default_role = FakeRole(self, self.id, "@everyone")
        self._roles: Dict[int, FakeRole] = {}
        self._channels: Dict[int, FakeChannel] = {}
        self._members: Dict[int, FakeMember] = {}
        self.emojis = []

    # roles
    @property
    def roles(self) -> List[FakeRole]:
        return [self.default_role] + list(self._roles.values())

    def get_role(self, role_id) -> Optional[FakeRole]:
        if role_id is None:
            return None
        if int(role_id) == self.id:
            return self.default_role
        return self._roles.get(int(role_id))

    # channels
    @property
    def channels(self):
        return list(self._channels.values())

    text_channels = channels

    def get_channel(self, channel_id) -> Optional[FakeChannel]:
        return self._channels.get(int(channel_id)) if channel_id is not None else None

    async def fetch_channel(self, channel_id):
        return self.get_channel(channel_id)

    # members
    @property
    def members(self):
        # Mirrors production: without the members intent the cache is never complete.
        return []

    @property
    def member_count(self):
        return len(self._members)

    def get_member(self, user_id) -> Optional[FakeMember]:
        # Like production without the members intent, the cache holds nobody, so
        # code has to go through discord_members.get_member (which falls back to fetch).
        return None

    async def fetch_member(self, user_id) -> FakeMember:
        member = self._members.get(int(user_id))
        if member is None:
            raise _not_found(f"Unknown Member {user_id}")
        return member

    def get_member_named(self, name):
        return None

    async def query_members(self, query=None, limit=5, user_ids=None, cache=True, **kwargs):
        results = []
        for member in self._members.values():
            if user_ids is not None and member.id not in user_ids:
                continue
            if query is not None and not any(
                    (n or "").lower().startswith(query.lower()) for n in (member.name, member.nick)):
                continue
            results.append(member)
        return results[:limit]

    async def chunk(self, **kwargs):
        raise RuntimeError("guild.chunk() needs the privileged members intent, which SahasrahBot does not use")

    async def create_scheduled_event(self, **kwargs):
        record(f"{self.name} scheduled event", content=kwargs.get("name"))
        return None

    def __str__(self):
        return self.name


def _not_found(message):
    import discord

    class _Resp:
        status = 404
        reason = "Not Found"

    return discord.NotFound(_Resp(), message)


class _AppInfo:
    def __init__(self, owner):
        self.owner = owner
        self.id = 1000
        self.name = "SahasrahBot (dev)"


class FakeWorld:
    """Every fake user, guild, role and channel, built from the fixtures."""

    def __init__(self):
        self.users: Dict[int, FakeUser] = {}
        self.guilds: Dict[int, FakeGuild] = {}
        self.owner_id: Optional[int] = None

    def channel(self, channel_id) -> Optional[FakeChannel]:
        for guild in self.guilds.values():
            channel = guild.get_channel(channel_id)
            if channel is not None:
                return channel
        return None

    def memberships(self, user_id) -> List[FakeMember]:
        return [g._members[int(user_id)] for g in self.guilds.values() if int(user_id) in g._members]

    def set_roles(self, guild_id: int, user_id: int, role_ids: List[int], member: bool = True):
        guild = self.guilds[int(guild_id)]
        user = self.users[int(user_id)]
        if not member:
            guild._members.pop(user.id, None)
            return
        existing = guild._members.get(user.id)
        if existing is None:
            guild._members[user.id] = FakeMember(guild, user, role_ids)
        else:
            existing._role_ids = [int(r) for r in role_ids]


class FakeDiscordBot:
    """Duck-typed replacement for ``alttprbot_discord.bot.discordbot``."""

    def __init__(self, world: FakeWorld):
        self.world = world
        self.user = FakeUser(1000, "SahasrahBot", bot=True)
        self.emojis = []
        self.logger = logger

    @property
    def guilds(self):
        return list(self.world.guilds.values())

    def is_closed(self):
        return False

    def is_ready(self):
        return True

    async def wait_until_ready(self):
        return None

    def get_guild(self, guild_id) -> Optional[FakeGuild]:
        return self.world.guilds.get(int(guild_id)) if guild_id is not None else None

    async def fetch_guild(self, guild_id) -> FakeGuild:
        guild = self.get_guild(guild_id)
        if guild is None:
            raise _not_found(f"Unknown Guild {guild_id}")
        return guild

    def get_channel(self, channel_id):
        return self.world.channel(channel_id) if channel_id is not None else None

    async def fetch_channel(self, channel_id):
        channel = self.get_channel(channel_id)
        if channel is None:
            raise _not_found(f"Unknown Channel {channel_id}")
        return channel

    def get_user(self, user_id) -> Optional[FakeUser]:
        return self.world.users.get(int(user_id)) if user_id is not None else None

    async def fetch_user(self, user_id) -> FakeUser:
        user = self.get_user(user_id)
        if user is None:
            raise _not_found(f"Unknown User {user_id}")
        return user

    async def application_info(self):
        return _AppInfo(self.get_user(self.world.owner_id) or self.user)

    def get_emoji(self, emoji_id):
        return None

    def dispatch(self, event, *args, **kwargs):
        logger.info("Discord event dispatched: %s", event)

    async def load_extension(self, name):
        logger.info("Skipping Discord extension %s in the dev server", name)

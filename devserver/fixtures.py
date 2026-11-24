"""The fake world the dev server starts with: Discord guilds, roles, channels and
users, plus the database rows seeded for them.

Ids are fixed so pages, tests and agents can link to them. Add to these lists to
cover a new page; ``python -m devserver --reset`` reseeds from scratch.
"""

from devserver.fake_discord import FakeChannel, FakeGuild, FakeRole, FakeUser, FakeWorld

GUILD_ID = 100000000000000001
OTHER_GUILD_ID = 100000000000000002

ROLE_ADMIN = 110000000000000001
ROLE_ASYNC_MOD = 110000000000000002
ROLE_VOTER = 110000000000000003
ROLE_RACER = 110000000000000004

CHANNEL_GENERAL = 120000000000000001
CHANNEL_ASYNC = 120000000000000002
CHANNEL_ASYNC_REPORTS = 120000000000000003
CHANNEL_ELECTIONS = 120000000000000004
CHANNEL_OLD_ASYNC = 120000000000000005
CHANNEL_OTHER_GENERAL = 120000000000000101

GUILDS = [
    {
        "id": GUILD_ID,
        "name": "SahasrahBot Dev Server",
        "roles": [
            (ROLE_ADMIN, "Admin"),
            (ROLE_ASYNC_MOD, "Async Mod"),
            (ROLE_VOTER, "Voter"),
            (ROLE_RACER, "Racer"),
        ],
        "channels": [
            (CHANNEL_GENERAL, "general"),
            (CHANNEL_ASYNC, "async-tournament"),
            (CHANNEL_ASYNC_REPORTS, "async-reports"),
            (CHANNEL_ELECTIONS, "elections"),
            (CHANNEL_OLD_ASYNC, "old-async"),
        ],
    },
    {
        "id": OTHER_GUILD_ID,
        "name": "Other Community",
        "roles": [],
        "channels": [(CHANNEL_OTHER_GENERAL, "general")],
    },
]

# key: the name used by /_dev/login?user=<key>.
# memberships: guild id -> role ids. A user missing from a guild is not a member.
USERS = [
    {
        "key": "admin",
        "id": 200000000000000001,
        "name": "dev-admin",
        "description": "Bot owner and server Admin. Owns the presets and elections.",
        "memberships": {GUILD_ID: [ROLE_ADMIN], OTHER_GUILD_ID: []},
        "rtgg_id": "devAdmin0000001",
    },
    {
        "key": "mod",
        "id": 200000000000000002,
        "name": "async-mod",
        "description": "Has the Async Mod role (left over from the removed async tournaments) and can vote.",
        "memberships": {GUILD_ID: [ROLE_ASYNC_MOD, ROLE_VOTER]},
        "rtgg_id": "devMod000000002",
    },
    {
        "key": "runner1",
        "id": 200000000000000003,
        "name": "runner-one",
        "description": "Racer with a racetime account.",
        "memberships": {GUILD_ID: [ROLE_RACER, ROLE_VOTER]},
        "rtgg_id": "devRunner000003",
    },
    {
        "key": "runner2",
        "id": 200000000000000004,
        "name": "runner-two",
        "description": "Racer with a forfeit, a pending review and a run in progress.",
        "memberships": {GUILD_ID: [ROLE_RACER]},
        "rtgg_id": "devRunner000004",
    },
    {
        "key": "runner3",
        "id": 200000000000000005,
        "name": "runner-three",
        "description": "Racer with no racetime account linked yet.",
        "memberships": {GUILD_ID: [ROLE_RACER]},
        "rtgg_id": None,
    },
    {
        "key": "outsider",
        "id": 200000000000000006,
        "name": "outsider",
        "description": "Not a member of the dev server and has no database user row.",
        "memberships": {},
        "rtgg_id": None,
        "db_user": False,
    },
]

OWNER_ID = USERS[0]["id"]

# The fake racetime.gg accounts shown on its login picker.
RACETIME_USERS = [
    {"id": u["rtgg_id"], "name": u["name"]} for u in USERS if u.get("rtgg_id")
] + [{"id": "devNewRacer0007", "name": "new-racer"}]

API_KEY = "dev-api-key"


def user(key: str) -> dict:
    return next(u for u in USERS if u["key"] == key)


def build_world() -> FakeWorld:
    world = FakeWorld()
    world.owner_id = OWNER_ID
    for spec in GUILDS:
        guild = FakeGuild(world, spec["id"], spec["name"])
        for role_id, name in spec["roles"]:
            guild._roles[role_id] = FakeRole(guild, role_id, name)
        for channel_id, name in spec["channels"]:
            guild._channels[channel_id] = FakeChannel(guild, channel_id, name)
        world.guilds[guild.id] = guild
    for spec in USERS:
        add_user(world, spec["id"], spec["name"], spec["memberships"])
    add_testdata_world(world)
    return world


def add_testdata_world(world: FakeWorld) -> None:
    """Add the guilds and members that the anonymized ``testdata/`` rows refer to.

    Their users are members of every testdata guild, holding the roles they held in
    the original data (the voter role of a role-gated election they voted in). Log in
    as one with ``/_dev/login?user=<discord id>``.
    """
    import testdata

    spec = testdata.world()
    for g in spec["guilds"]:
        guild = FakeGuild(world, g["id"], g["name"])
        for role_id, name in g["roles"]:
            guild._roles[role_id] = FakeRole(guild, role_id, name)
        for channel_id, name in g["channels"]:
            guild._channels[channel_id] = FakeChannel(guild, channel_id, name)
        world.guilds[guild.id] = guild
    for m in spec["members"]:
        add_user(world, m["id"], m["name"], {int(g): roles for g, roles in m["memberships"].items()})
    # The dev admin is in every testdata guild with every role, to see role-gated pages.
    for g in spec["guilds"]:
        world.set_roles(g["id"], OWNER_ID, [role_id for role_id, _ in g["roles"]])


def add_user(world: FakeWorld, user_id: int, name: str, memberships: dict) -> FakeUser:
    world.users[int(user_id)] = FakeUser(user_id, name)
    for guild_id, role_ids in memberships.items():
        world.set_roles(guild_id, user_id, role_ids)
    return world.users[int(user_id)]


async def seed_database():
    """Insert the fixture rows. Expects empty tables (see ``devserver.db.reset``).

    First the hand-made rows below, then the anonymized production-shaped slices in
    ``testdata/`` (ids from 1001 up, so they don't collide).
    """
    await _seed_handmade()
    import testdata

    await testdata.load()


async def _seed_handmade():
    from alttprbot import models

    users = {}
    for spec in USERS:
        if spec.get("db_user", True) is False:
            continue
        users[spec["key"]] = await models.Users.create(
            discord_user_id=spec["id"],
            display_name=spec["name"],
            rtgg_id=spec.get("rtgg_id"),
            test_user=True,
        )

    # --- API keys -------------------------------------------------------------
    key = await models.AuthorizationKeys.create(key=API_KEY, name="dev")
    for perm in ("racetimecmd",):
        await models.AuthorizationKeyPermissions.create(auth_key=key, type=perm)

    # --- Presets ---------------------------------------------------------------
    namespace = await models.PresetNamespaces.create(name="dev-admin", discord_user_id=user("admin")["id"])
    await models.PresetNamespaceCollaborators.create(namespace=namespace, discord_user_id=user("mod")["id"])
    await models.Presets.create(
        namespace=namespace, randomizer="alttpr", preset_name="devopen", generated_count=12,
        content="goal_name: dev open\ndescription: A dev preset\nsettings:\n  mode: open\n  goal: ganon\n",
    )
    await models.Presets.create(
        namespace=namespace, randomizer="smz3", preset_name="devsmz3",
        content="randomizer: smz3\nsettings:\n  logic: normal\n",
    )

    # --- Triforce texts ----------------------------------------------------------
    await models.TriforceTextsConfig.create(pool_name="dev", key_name="moderator", value=str(user("admin")["id"]))
    for text, approved, author in [
        ("Hello from\nthe dev server", True, "runner1"),
        ("Pending text\nawaiting review", None, "runner2"),
        ("Rejected text", False, "runner3"),
    ]:
        await models.TriforceTexts.create(
            pool_name="dev", text=text, approved=approved,
            discord_user_id=user(author)["id"], author=user(author)["name"],
        )

    # --- Ranked choice elections -----------------------------------------------
    public = await models.RankedChoiceElection.create(
        id=1, guild_id=GUILD_ID, channel_id=CHANNEL_ELECTIONS, message_id=140000000000000001, owner_id=user("admin")["id"],
        title="Pick the next community race mode", description="Rank the modes you'd like to see.", seats=1,
    )
    private = await models.RankedChoiceElection.create(
        id=2, guild_id=GUILD_ID, channel_id=CHANNEL_ELECTIONS, message_id=140000000000000002, owner_id=user("admin")["id"],
        title="Voter-role-only election", private=True, voter_role_id=ROLE_VOTER, seats=2,
    )
    for election, names in [(public, ["Open", "Keysanity", "Inverted", "Enemizer"]),
                            (private, ["Alice", "Bob", "Carol"])]:
        for name in names:
            await models.RankedChoiceCandidate.create(election=election, name=name)

    # --- Tournament games (/api/tournament/games) ---------------------------------
    for episode_id, game in [(1001, 1), (1002, 2)]:
        await models.TournamentGames.create(
            episode_id=episode_id, event="alttpr", game_number=game, preset="open", submitted=1,
        )

    return users

"""The MCP tools: thin calls into ``alttprbot/services/``, the same ones ``/api/v1`` makes,
returning the same bodies (``alttprbot_api/schemas.py``). Each tool's docstring is
what the model reads to decide when to call it.
"""

from datetime import datetime
from typing import Literal, Optional

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

from alttprbot.exceptions import InvalidInputError
from alttprbot.services import audit, elections, presets, seeds, tournament_submissions, triforce_texts, voice_roles
from alttprbot_api import schemas
from alttprbot_api.blueprints.app_api import (_int_id, audit_entry, election_detail, election_input,
                                               election_summary, voice_role_out, voice_roles_out)
from alttprbot_api.mcp.auth import current_actor
from alttprbot_api.mcp.registry import register


class WhoAmI(BaseModel):
    discord_user_id: str
    name: str
    can_make_changes: bool


def _viewer() -> presets.Viewer:
    return presets.Viewer(current_actor().discord_user_id)


# --- Orientation --------------------------------------------------------------


async def whoami() -> WhoAmI:
    """Who this connection acts as, and whether it may make changes. Call it first."""
    actor = current_actor()
    return WhoAmI(discord_user_id=str(actor.discord_user_id), name=actor.user_name,
                  can_make_changes=not actor.read_only)


# --- Presets and seeds ------------------------------------------------------------


async def list_randomizers() -> schemas.Randomizers:
    """The randomizers SahasrahBot keeps presets for."""
    return schemas.Randomizers(randomizers=presets.randomizers())


async def list_preset_namespaces() -> schemas.NamespaceList:
    """Every person's preset namespace, with how many presets each holds."""
    return schemas.NamespaceList(namespaces=await presets.list_namespaces())


async def get_preset_namespace(namespace: str) -> schemas.Namespace:
    """The presets in one namespace."""
    return schemas.Namespace(**await presets.get_namespace(namespace, _viewer()))


async def get_preset(namespace: str, randomizer: str, preset: str) -> schemas.Preset:
    """One preset in a namespace, with its YAML."""
    return schemas.Preset(**await presets.get_preset(namespace, randomizer, preset, _viewer()))


async def roll_seed(randomizer: Literal['alttpr', 'alttprmystery', 'sm', 'smz3'], preset: str, race: bool = False,
                    hints: bool = False, allow_quickswap: bool = True,
                    branch: Literal['live', 'beeta', 'tournament'] = 'live',
                    spoiler_race: bool = False) -> schemas.Seed:
    """Roll a seed from a preset, as the Discord commands do, and return its link.

    `preset` is a built-in preset name (`open`, `standard`, ...) or someone's own as
    `namespace/name`. `race` makes a race seed with no spoiler log. `hints`,
    `allow_quickswap` and `branch` are for ALTTPR; `spoiler_race` is for SMZ3.
    Takes a few seconds."""
    options = seeds.RollOptions(race=race, hints=hints, allow_quickswap=allow_quickswap, branch=branch,
                                spoiler_race=spoiler_race)
    return schemas.Seed(**await seeds.roll(randomizer, preset, options))


async def lookup_seed(hash: str) -> schemas.SeedLookup:
    """What SahasrahBot recorded about a seed it rolled, by its hash: randomizer, preset, link."""
    return schemas.SeedLookup(**await seeds.lookup(hash))


async def save_preset(namespace: str, randomizer: str, preset: str, content: str) -> schemas.Preset:
    """Create a preset in your namespace, or replace its YAML. `content` is the whole YAML file."""
    return schemas.Preset(**await presets.save_preset(namespace, randomizer, preset, content, _viewer()))


async def delete_preset(namespace: str, randomizer: str, preset: str) -> str:
    """Delete a preset from your namespace. It can't be undone."""
    await presets.delete_preset(namespace, randomizer, preset, _viewer())
    return f"Deleted {namespace}/{preset}."


# --- Elections ------------------------------------------------------------------


async def list_my_elections() -> schemas.ElectionList:
    """Elections in the Discord servers you administer, newest first. Slow: it checks each server."""
    actor = current_actor()
    admin = await elections.administered_guild_ids(actor.discord_user_id)
    return schemas.ElectionList(elections=[schemas.ElectionSummary(**election_summary(e))
                                           for e in await elections.list_elections(actor.discord_user_id, admin)])


async def get_election(election_id: int) -> schemas.ElectionDetail:
    """An election you administer, with its settings and status."""
    return election_detail(await elections.get_for_admin(election_id, current_actor().discord_user_id))


async def get_ballot(election_id: int) -> schemas.Election:
    """An open election as a voter sees it: the candidates (with their ids) and your ballot."""
    return schemas.Election(**await elections.get_ballot(election_id, current_actor().discord_user_id))


async def get_election_results(election_id: int) -> schemas.ElectionResults:
    """The count of a closed election, round by round."""
    return schemas.ElectionResults(**await elections.results(election_id))


async def cast_ballot(election_id: int, choices: list[int]) -> schemas.Election:
    """Cast or replace your ballot. `choices` are candidate ids from `get_ballot`: your ranking,
    most preferred first (stv); every candidate you approve of (approval); or the one you pick
    (plurality). Only your latest ballot counts."""
    return schemas.Election(**await elections.cast_ballot(election_id, current_actor().discord_user_id, choices))


async def create_election(guild_id: str, channel_id: str, title: str, candidates: list[str],
                          method: Literal['stv', 'approval', 'plurality'] = 'stv', seats: int = 1,
                          description: Optional[str] = None, voter_role_id: Optional[str] = None,
                          closes_at: Optional[datetime] = None,
                          show_vote_count: bool = True) -> schemas.ElectionDetail:
    """Save a new election as a draft in a server you administer. Nobody sees it until
    `publish_election`. Ids are Discord ids, as strings. `closes_at` needs a time zone."""
    data = schemas.ElectionIn(guild_id=guild_id, channel_id=channel_id, title=title, candidates=candidates,
                              method=method, seats=seats, description=description, voter_role_id=voter_role_id,
                              closes_at=closes_at, show_vote_count=show_vote_count)
    return election_detail(await elections.create_draft(current_actor().discord_user_id, election_input(data)))


async def update_election(election_id: int, guild_id: str, channel_id: str, title: str, candidates: list[str],
                          method: Literal['stv', 'approval', 'plurality'] = 'stv', seats: int = 1,
                          description: Optional[str] = None, voter_role_id: Optional[str] = None,
                          closes_at: Optional[datetime] = None,
                          show_vote_count: bool = True) -> schemas.ElectionDetail:
    """Replace an election's settings. Read it with `get_election` first and send every field back."""
    data = schemas.ElectionIn(guild_id=guild_id, channel_id=channel_id, title=title, candidates=candidates,
                              method=method, seats=seats, description=description, voter_role_id=voter_role_id,
                              closes_at=closes_at, show_vote_count=show_vote_count)
    return election_detail(await elections.update(election_id, current_actor().discord_user_id,
                                                  election_input(data)))


async def publish_election(election_id: int) -> schemas.ElectionDetail:
    """Post a draft election in its Discord channel and open voting. Everyone in the channel sees it."""
    return election_detail(await elections.publish(election_id, current_actor().discord_user_id))


async def close_election(election_id: int) -> schemas.ElectionDetail:
    """End voting now and count the ballots. It can't be reopened."""
    return election_detail(await elections.close(election_id, current_actor().discord_user_id))


async def delete_election(election_id: int) -> str:
    """Delete an election and its ballots. It can't be undone."""
    await elections.delete(election_id, current_actor().discord_user_id)
    return f"Deleted election {election_id}."


# --- Triforce texts -------------------------------------------------------------


async def get_triforce_pool(pool: str) -> schemas.TriforcePool:
    """A triforce text pool: whether you can submit, and your submissions."""
    return schemas.TriforcePool(**await triforce_texts.pool(pool, current_actor().discord_user_id))


async def list_triforce_moderation(pool: str, status: Literal['pending', 'approved', 'rejected', 'all'] = 'pending'
                                   ) -> schemas.TriforceModerationList:
    """Texts submitted to a pool you moderate."""
    texts = await triforce_texts.list_for_moderation(pool, current_actor().discord_user_id, status)
    return schemas.TriforceModerationList(pool=pool, status=status, texts=texts)


async def submit_triforce_text(pool: str, lines: list[str]) -> schemas.TriforceText:
    """Submit a triforce text to a pool: up to three lines of the in-game font."""
    actor = current_actor()
    return schemas.TriforceText(**await triforce_texts.submit(pool, actor.discord_user_id, actor.author, lines))


async def moderate_triforce_text(pool: str, text_id: int, approved: bool) -> schemas.TriforceText:
    """Approve or reject a submitted triforce text in a pool you moderate."""
    return schemas.TriforceText(**await triforce_texts.moderate(pool, text_id, current_actor().discord_user_id,
                                                                approved))


# --- Tournaments ----------------------------------------------------------------


async def get_tournament_submission_form(event: str) -> schemas.SubmissionForm:
    """The settings a tournament asks its players to choose for a race."""
    return schemas.SubmissionForm(**await tournament_submissions.get_form(event))


async def submit_tournament_settings(event: str, episode_id: int, settings: dict[str, str]) -> schemas.SubmissionDone:
    """Submit the settings for a tournament race (a SpeedGaming episode). `settings` maps each
    field key from `get_tournament_submission_form` to one of its option values."""
    done = await tournament_submissions.submit(event, episode_id, settings, current_actor().author)
    return schemas.SubmissionDone(**done)


# --- Audit log --------------------------------------------------------------------


async def list_audit_log(scope: str = 'mine', area: Optional[str] = None, search: Optional[str] = None,
                         actor_id: Optional[str] = None, before: Optional[int] = None,
                         limit: int = 50) -> schemas.AuditPage:
    """Changes made through SahasrahBot, newest first: who did what, when, in which server,
    and through what (website, API token, AI client, Discord or racetime.gg).

    `scope` is `mine` (your own actions), a Discord server id you administer, or `all`
    (the bot's owners only). `area` is one of `elections`, `presets`, `triforce_texts`,
    `server`, `tokens`, `accounts`, `tournaments`, `multiworld`. `search` matches the
    action, the person, the thing changed or the token/command. For the next page, pass
    the `next_before` you got as `before`. Slow for a server scope: it checks which
    servers you administer."""
    actor = current_actor()
    admin = await elections.administered_guild_ids(actor.discord_user_id) if scope != audit.SCOPE_MINE else frozenset()
    filters = audit.Filters(scope=scope, area=area, query=search,
                            actor_discord_id=_int_id(actor_id, 'person'), before_id=before,
                            limit=max(1, min(limit, audit.MAX_PAGE_SIZE)))
    page = await audit.list_entries(actor.discord_user_id, admin, filters)
    return schemas.AuditPage(entries=[audit_entry(e) for e in page['entries']], next_before=page['next_before'])


# --- Voice roles ----------------------------------------------------------------


def _guild_id(guild_id: str) -> int:
    value = _int_id(guild_id, 'server')
    if value is None:
        raise InvalidInputError("Give the server's Discord id.")
    return value


async def list_voice_roles(guild_id: str) -> schemas.VoiceRoles:
    """A server's voice roles: people in the voice channel get the role while they're in it.
    Also lists the server's voice channels and roles (`assignable`: SahasrahBot can give it),
    for `add_voice_role`. Server administrators only."""
    return voice_roles_out(await voice_roles.overview(_guild_id(guild_id), current_actor().discord_user_id))


async def add_voice_role(guild_id: str, voice_channel_id: str, role_id: str) -> schemas.VoiceRole:
    """Give `role_id` to everyone in the voice channel while they're in it. Ids are Discord ids,
    as strings, from `list_voice_roles`. People already in the channel get it when they next join."""
    return voice_role_out(await voice_roles.add(_guild_id(guild_id), current_actor().discord_user_id,
                                                _int_id(voice_channel_id, 'voice channel'), _int_id(role_id, 'role')))


async def remove_voice_role(guild_id: str, voice_role_id: int) -> str:
    """Stop giving a voice role (its `id` from `list_voice_roles`)."""
    await voice_roles.remove(_guild_id(guild_id), current_actor().discord_user_id, voice_role_id)
    return f"Removed voice role {voice_role_id}."


def register_all(mcp: MCPServer) -> None:
    register(mcp, whoami, title='Who am I')
    register(mcp, list_randomizers, title='List randomizers')
    register(mcp, list_preset_namespaces, title='List preset namespaces')
    register(mcp, get_preset_namespace, title='Get a preset namespace')
    register(mcp, get_preset, title='Get a preset')
    register(mcp, roll_seed, title='Roll a seed', open_world=True)
    register(mcp, lookup_seed, title='Look up a seed')
    register(mcp, save_preset, title='Save a preset', write=True)
    register(mcp, delete_preset, title='Delete a preset', write=True, destructive=True)
    register(mcp, list_my_elections, title='List my elections')
    register(mcp, get_election, title='Get an election')
    register(mcp, get_ballot, title='Get my ballot')
    register(mcp, get_election_results, title='Get election results')
    register(mcp, cast_ballot, title='Cast a ballot', write=True)
    register(mcp, create_election, title='Create an election', write=True)
    register(mcp, update_election, title='Update an election', write=True)
    register(mcp, publish_election, title='Publish an election', write=True)
    register(mcp, close_election, title='Close an election', write=True, destructive=True)
    register(mcp, delete_election, title='Delete an election', write=True, destructive=True)
    register(mcp, get_triforce_pool, title='Get a triforce text pool')
    register(mcp, list_triforce_moderation, title='List triforce texts to moderate')
    register(mcp, submit_triforce_text, title='Submit a triforce text', write=True)
    register(mcp, moderate_triforce_text, title='Moderate a triforce text', write=True)
    register(mcp, get_tournament_submission_form, title='Get a tournament settings form')
    register(mcp, submit_tournament_settings, title='Submit tournament settings', write=True)
    register(mcp, list_audit_log, title='List the audit log')
    register(mcp, list_voice_roles, title="List a server's voice roles")
    register(mcp, add_voice_role, title='Add a voice role', write=True)
    register(mcp, remove_voice_role, title='Remove a voice role', write=True, destructive=True)

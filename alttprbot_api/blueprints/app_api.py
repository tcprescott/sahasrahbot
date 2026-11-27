"""The JSON API: ``/api/v1/...``. The React app in ``web/`` uses it, and so can
anyone's scripts, with a personal access token.

Routes are thin: they find out who's calling, call a service in
``alttprbot/services/``, and return a model from ``schemas.py``. Services raise
``NotFoundError`` / ``PermissionDeniedError`` / ``InvalidInputError``, which
``api.py`` turns into 404 / 403 / 400 with ``{"error": "..."}``.

Who's calling is either the Discord OAuth session cookie (the web app) or
``Authorization: Bearer sb_pat_...`` (a token made on the API access page). A
bearer request ignores the cookie. A read-only token is refused anything that
changes data, except the POSTs in ``READ_ONLY_POSTS`` (rolling a seed changes
nothing of yours). Making tokens, deleting your data and approving an AI client
need the cookie: a token can't mint another token.

Requests that change something with the cookie must carry
``X-Requested-With: SahasrahBot``. A cross-site form can't set that header, which
keeps the session cookie from being used against the user (CSRF). A bearer token
isn't sent by a browser on its own, so it needs no such header.
"""

import asyncio
import csv
import io
import json
import time
from dataclasses import dataclass
from typing import Optional

import discord as discord_py
from quart import Blueprint, Response, abort, g, request
from quart_discord import RateLimited, Unauthorized
from quart_schema import tag, validate_querystring, validate_request, validate_response

import config
from alttprbot import models
from alttprbot.exceptions import InvalidInputError, PermissionDeniedError
from alttprbot.observability import sentry as observability
from alttprbot.services import (accounts, api_tokens, audit, discord_servers, elections, inquiries, mcp_auth, presets,
                                seeds, servers, tournament_submissions, triforce_texts, voice_roles)
from alttprbot_api import schemas
from alttprbot_api.api import SIGN_IN_SCOPES, discord

app_api_blueprint = Blueprint('app_api', __name__, url_prefix='/api/v1')

CSRF_HEADER = 'X-Requested-With'
CSRF_VALUE = 'SahasrahBot'
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
# POSTs a read-only token may make: they change nothing that's the caller's.
READ_ONLY_POSTS = frozenset({'app_api.roll_seed', 'app_api.convert_customizer', 'app_api.check_inquiry'})


@dataclass(frozen=True)
class Caller:
    """Whoever is calling: a Discord sign-in, or a personal access token acting as one."""

    id: int
    name: str
    discriminator: str = '0'
    avatar_url: Optional[str] = None
    token: Optional[models.ApiToken] = None


def _bearer() -> Optional[str]:
    header = request.headers.get('Authorization', '')
    if header[:7].lower() != 'bearer ':
        return None
    return header[7:].strip()


@app_api_blueprint.before_request
async def authenticate_request():
    raw = _bearer()
    if raw is not None:
        token = await api_tokens.authenticate(raw, api_tokens.PAT)
        if token is None:
            abort(401, description="That API token is invalid, expired or revoked.")
        g.api_token = token
        if token.read_only and request.method not in SAFE_METHODS and request.endpoint not in READ_ONLY_POSTS:
            abort(403, description="This token is read-only. Make one that can make changes on the API access page.")
        return
    if request.method not in SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        abort(403, description=f"Missing the {CSRF_HEADER} header.")


async def _granted_scopes() -> set[str]:
    scope = (await discord.get_authorization_token() or {}).get('scope') or []
    return set(scope.split() if isinstance(scope, str) else scope)


async def _session_user():
    """The Discord user of the session cookie, or None.

    A session from before the app asked for every scope in ``SIGN_IN_SCOPES`` is
    signed out, so the person signs in again once and grants the rest."""
    if not await discord.authorized:
        return None
    if not set(SIGN_IN_SCOPES) <= await _granted_scopes():
        discord.revoke()
        return None
    try:
        return await discord.fetch_user()
    except Unauthorized:
        return None


async def signed_in_user() -> Optional[Caller]:
    """Who's calling, or None. Also tells the audit log who is acting in this request."""
    token = g.get('api_token')
    if token is not None:
        caller = Caller(id=token.discord_user_id, name=token.user_name, token=token)
        audit.set_source(audit.Source(via=audit.VIA_API, detail=token.name, actor_discord_id=caller.id,
                                      actor_name=caller.name))
        return caller
    user = await _session_user()
    if user is None:
        return None
    audit.set_source(audit.Source(via=audit.VIA_WEBSITE, actor_discord_id=user.id, actor_name=user.name))
    return Caller(id=user.id, name=user.name, discriminator=str(getattr(user, 'discriminator', '0')),
                  avatar_url=getattr(user, 'avatar_url', None) or None)


async def require_user() -> Caller:
    user = await signed_in_user()
    if user is None:
        raise Unauthorized()
    return user


async def require_session_user() -> Caller:
    """The signed-in user, for things only the website may do, never a token."""
    if g.get('api_token') is not None:
        raise PermissionDeniedError("Do this on the SahasrahBot website, signed in with Discord, not with a token.")
    return await require_user()


def _session_user_schema(user: Caller) -> schemas.SessionUser:
    return schemas.SessionUser(id=str(user.id), name=user.name, avatar_url=user.avatar_url)


def _author(user: Caller) -> str:
    return f"{user.name}#{user.discriminator}"


# --- Session and profile -----------------------------------------------------


@app_api_blueprint.get('/session')
@tag(['session'])
@validate_response(schemas.SessionInfo)
async def get_session():
    """Who is signed in. Never 401: ``user`` is null when nobody is."""
    user = await signed_in_user()
    return schemas.SessionInfo(user=_session_user_schema(user) if user else None)


@app_api_blueprint.get('/telemetry')
@tag(['session'])
@validate_response(schemas.Telemetry)
async def get_telemetry():
    """Where the app reports its errors: the Sentry browser settings, or null when Sentry is off."""
    config = observability.browser_config()
    return schemas.Telemetry(sentry=schemas.BrowserSentry(**config) if config else None)


@app_api_blueprint.get('/me')
@tag(['session'])
@validate_response(schemas.Profile)
async def get_me():
    user = await require_user()
    return schemas.Profile(user=_session_user_schema(user), **await accounts.profile(user.id))


@app_api_blueprint.post('/me/purge')
@tag(['session'])
async def purge_me():
    """Delete what SahasrahBot keeps about the user, then sign them out."""
    user = await require_session_user()
    await accounts.purge(user.id)
    discord.revoke()
    return '', 204


# --- Presets -----------------------------------------------------------------


@app_api_blueprint.get('/presets/randomizers')
@tag(['presets'])
@validate_response(schemas.Randomizers)
async def get_randomizers():
    return schemas.Randomizers(randomizers=presets.randomizers())


@app_api_blueprint.get('/presets/randomizers/<randomizer>/hints')
@tag(['presets'])
@validate_response(schemas.PresetHints)
async def get_preset_hints(randomizer: str):
    """The keys and values SahasrahBot's own presets use, for the YAML editor's suggestions."""
    return schemas.PresetHints(hints=await presets.key_hints(randomizer))


@app_api_blueprint.post('/presets/customizer')
@tag(['presets'])
@validate_request(schemas.CustomizerSave)
@validate_response(schemas.PresetContent)
async def convert_customizer(data: schemas.CustomizerSave):
    """Convert an alttpr.com customizer save file to preset YAML. Saves nothing."""
    return schemas.PresetContent(content=await presets.convert_customizer(data.content))


@app_api_blueprint.get('/presets/namespaces')
@tag(['presets'])
@validate_response(schemas.NamespaceList)
async def list_namespaces():
    return schemas.NamespaceList(namespaces=await presets.list_namespaces())


@app_api_blueprint.get('/presets/mine')
@tag(['presets'])
@validate_response(schemas.MyNamespace)
async def my_namespace():
    """The signed-in user's namespace, created on first use."""
    user = await require_user()
    return schemas.MyNamespace(namespace=await presets.my_namespace(user.id, user.name))


@app_api_blueprint.get('/presets/namespaces/<namespace>')
@tag(['presets'])
@validate_response(schemas.Namespace)
async def get_namespace(namespace: str):
    user = await signed_in_user()
    return schemas.Namespace(**await presets.get_namespace(namespace, presets.Viewer(user.id if user else None)))


@app_api_blueprint.get('/presets/namespaces/<namespace>/<randomizer>/<preset>')
@tag(['presets'])
@validate_response(schemas.Preset)
async def get_preset(namespace: str, randomizer: str, preset: str):
    user = await signed_in_user()
    viewer = presets.Viewer(user.id if user else None)
    return schemas.Preset(**await presets.get_preset(namespace, randomizer, preset, viewer))


@app_api_blueprint.put('/presets/namespaces/<namespace>/<randomizer>/<preset>')
@tag(['presets'])
@validate_request(schemas.PresetContent)
@validate_response(schemas.Preset)
async def save_preset(namespace: str, randomizer: str, preset: str, data: schemas.PresetContent):
    """Create the preset, or replace its YAML."""
    user = await require_user()
    saved = await presets.save_preset(namespace, randomizer, preset, data.content, presets.Viewer(user.id))
    return schemas.Preset(**saved)


@app_api_blueprint.delete('/presets/namespaces/<namespace>/<randomizer>/<preset>')
@tag(['presets'])
async def delete_preset(namespace: str, randomizer: str, preset: str):
    user = await require_user()
    await presets.delete_preset(namespace, randomizer, preset, presets.Viewer(user.id))
    return '', 204


# --- Elections ---------------------------------------------------------------


def _id(value) -> Optional[str]:
    return None if value is None else str(value)


def _int_id(value: Optional[str], what: str) -> Optional[int]:
    if value in (None, ''):
        return None
    try:
        return int(value)
    except ValueError:
        raise InvalidInputError(f"That {what} isn't a Discord id.") from None


def election_summary(data: dict) -> dict:
    return {**data, 'guild_id': _id(data['guild_id'])}


def election_detail(data: dict) -> schemas.ElectionDetail:
    return schemas.ElectionDetail(**{
        **election_summary(data),
        'channel_id': _id(data['channel_id']),
        'message_id': _id(data['message_id']),
        'voter_role_id': _id(data['voter_role_id']),
    })


def election_input(data: schemas.ElectionIn) -> elections.ElectionInput:
    return elections.ElectionInput(
        guild_id=_int_id(data.guild_id, 'server'),
        channel_id=_int_id(data.channel_id, 'channel'),
        title=data.title,
        description=data.description,
        candidates=data.candidates,
        method=data.method,
        seats=data.seats,
        voter_role_id=_int_id(data.voter_role_id, 'role'),
        closes_at=data.closes_at,
        show_vote_count=data.show_vote_count,
    )


# The servers the signed-in user administers, from Discord's /users/@me/guilds (one
# request with their own token, which lists their permissions in each server). Cached
# briefly per user, and one request at a time per user: Discord rate-limits it hard,
# and the app asks for it from several screens at once.
ADMIN_GUILDS_TTL = 60
_admin_guilds: dict[int, tuple[float, frozenset[int]]] = {}
_admin_guild_locks: dict[int, asyncio.Lock] = {}
GUILD_PAGE = 200


async def _fetch_discord_guilds() -> list[dict]:
    """Every server the signed-in user is in, as Discord's partial guild objects."""
    guilds: list[dict] = []
    after = 0
    while True:
        for attempt in range(2):
            try:
                page = await discord.request(f"/users/@me/guilds?limit={GUILD_PAGE}&after={after}")
                break
            except RateLimited as e:
                if attempt or e.retry_after > 5:
                    raise
                await asyncio.sleep(e.retry_after)
        guilds.extend(page)
        if len(page) < GUILD_PAGE:
            return guilds
        after = page[-1]['id']


def _is_admin(guild: dict) -> bool:
    return bool(guild.get('owner')) or discord_py.Permissions(int(guild.get('permissions') or 0)).administrator


async def admin_guild_ids(user: Caller) -> frozenset[int]:
    """The servers ``user`` administers. A token has no Discord sign-in to ask with,
    so for one the bot checks each of its servers instead (slower, same answer)."""
    user_id = user.id
    cached = _admin_guilds.get(user_id)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    async with _admin_guild_locks.setdefault(user_id, asyncio.Lock()):
        cached = _admin_guilds.get(user_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        if user.token is not None:
            ids = await elections.administered_guild_ids(user_id)
        else:
            ids = frozenset(int(guild['id']) for guild in await _fetch_discord_guilds() if _is_admin(guild))
        _admin_guilds[user_id] = (time.monotonic() + ADMIN_GUILDS_TTL, ids)
        return ids


@app_api_blueprint.get('/elections/servers')
@tag(['elections'])
@validate_response(schemas.ServerList)
async def election_servers():
    """Servers the viewer can run elections in. Empty means they can't run any (the web app hides the Elections tab)."""
    user = await require_user()
    return schemas.ServerList(servers=[schemas.ServerOption(id=str(s['id']), name=s['name'])
                                       for s in await elections.servers(await admin_guild_ids(user))])


@app_api_blueprint.get('/elections/servers/<int:guild_id>')
@tag(['elections'])
@validate_response(schemas.ServerOptions)
async def election_server_options(guild_id: int):
    """The channels the bot can post in and the roles, for the create form."""
    user = await require_user()
    options = await elections.server_options(guild_id, user.id)
    return schemas.ServerOptions(
        channels=[schemas.ServerOption(id=str(c['id']), name=c['name']) for c in options['channels']],
        roles=[schemas.ServerOption(id=str(r['id']), name=r['name']) for r in options['roles']],
    )


@app_api_blueprint.get('/servers')
@tag(['servers'])
@validate_response(schemas.AdminServerList)
async def admin_servers():
    """Servers the viewer administers that SahasrahBot is in. Empty means the web app hides the Servers tab."""
    user = await require_user()
    return schemas.AdminServerList(servers=[schemas.ServerOption(id=str(s['id']), name=s['name'])
                                            for s in await servers.servers(await admin_guild_ids(user))])


@app_api_blueprint.get('/servers/<int:guild_id>')
@tag(['servers'])
@validate_response(schemas.ServerDetail)
async def server_detail(guild_id: int):
    """The server's name, channels and roles, for the Servers pages."""
    user = await require_user()
    d = await servers.detail(guild_id, user.id)
    return schemas.ServerDetail(
        id=str(d['id']), name=d['name'],
        text_channels=[schemas.ServerOption(id=str(c['id']), name=c['name']) for c in d['text_channels']],
        voice_channels=[schemas.ServerOption(id=str(c['id']), name=c['name']) for c in d['voice_channels']],
        roles=[schemas.ServerRole(id=str(r['id']), name=r['name'], position=r['position'], assignable=r['assignable'])
               for r in d['roles']],
    )


@app_api_blueprint.get('/servers/<int:guild_id>/settings')
@tag(['servers'])
@validate_response(schemas.ServerSettings)
async def get_server_settings(guild_id: int):
    user = await require_user()
    return schemas.ServerSettings(**await servers.settings(guild_id, user.id))


@app_api_blueprint.put('/servers/<int:guild_id>/settings')
@tag(['servers'])
@validate_request(schemas.ServerSettingsIn)
@validate_response(schemas.ServerSettings)
async def put_server_settings(guild_id: int, data: schemas.ServerSettingsIn):
    """Replace the server's settings."""
    user = await require_user()
    return schemas.ServerSettings(**await servers.update_settings(guild_id, user.id, data.daily_channels,
                                                                  data.holy_image_game))


def _inquiry(guild_id: int, i: dict) -> schemas.Inquiry:
    return schemas.Inquiry(
        message_id=str(i['message_id']), channel_id=str(i['channel_id']) if i['channel_id'] else None,
        channel_name=i['channel_name'], role_id=str(i['role_id']), role_name=i['role_name'], created=i['created'],
        jump_url=(f"https://discord.com/channels/{guild_id}/{i['channel_id']}/{i['message_id']}"
                  if i['channel_id'] else None),
    )


def _discord_id(value: str) -> int:
    if not value.isdigit():
        raise InvalidInputError("Pick a channel and a role from the lists.")
    return int(value)


@app_api_blueprint.get('/servers/<int:guild_id>/inquiries')
@tag(['servers'])
@validate_response(schemas.InquiryList)
async def list_inquiries(guild_id: int):
    """The server's inquiry buttons (those posted since SahasrahBot started remembering their server)."""
    user = await require_user()
    return schemas.InquiryList(inquiries=[_inquiry(guild_id, i) for i in await inquiries.list_for_guild(guild_id, user.id)])


@app_api_blueprint.post('/servers/<int:guild_id>/inquiries/check')
@tag(['servers'])
@validate_request(schemas.InquiryIn)
@validate_response(schemas.InquiryChecks)
async def check_inquiry(guild_id: int, data: schemas.InquiryIn):
    """Whether an inquiry button would work in that channel for that role. Changes nothing."""
    user = await require_user()
    checks = await inquiries.check(guild_id, user.id, _discord_id(data.channel_id), _discord_id(data.role_id))
    return schemas.InquiryChecks(checks=[schemas.InquiryCheck(ok=c.ok, text=c.text) for c in checks])


@app_api_blueprint.post('/servers/<int:guild_id>/inquiries')
@tag(['servers'])
@validate_request(schemas.InquiryIn)
@validate_response(schemas.Inquiry, 201)
async def post_inquiry(guild_id: int, data: schemas.InquiryIn):
    """Post an inquiry button in the channel. Refused unless every check passes."""
    user = await require_user()
    posted = await inquiries.post(guild_id, user.id, _discord_id(data.channel_id), _discord_id(data.role_id))
    return _inquiry(guild_id, posted), 201


@app_api_blueprint.delete('/servers/<int:guild_id>/inquiries/<int:message_id>')
@tag(['servers'])
async def delete_inquiry(guild_id: int, message_id: int):
    """Delete the inquiry button's message. Threads it opened stay."""
    user = await require_user()
    await inquiries.remove(guild_id, user.id, message_id)
    return '', 204


@app_api_blueprint.get('/elections')
@tag(['elections'])
@validate_response(schemas.ElectionList)
async def list_elections():
    user = await require_user()
    return schemas.ElectionList(elections=[schemas.ElectionSummary(**election_summary(e))
                                           for e in await elections.list_elections(user.id, await admin_guild_ids(user))])


@app_api_blueprint.post('/elections')
@tag(['elections'])
@validate_request(schemas.ElectionIn)
@validate_response(schemas.ElectionDetail, 201)
async def create_election(data: schemas.ElectionIn):
    """Save a new election as a draft. Post it with ``POST /elections/{id}/publish``."""
    user = await require_user()
    return election_detail(await elections.create_draft(user.id, election_input(data))), 201


@app_api_blueprint.get('/elections/<int:election_id>')
@tag(['elections'])
@validate_response(schemas.ElectionDetail)
async def get_election_detail(election_id: int):
    user = await require_user()
    return election_detail(await elections.get_for_admin(election_id, user.id))


@app_api_blueprint.put('/elections/<int:election_id>')
@tag(['elections'])
@validate_request(schemas.ElectionIn)
@validate_response(schemas.ElectionDetail)
async def update_election(election_id: int, data: schemas.ElectionIn):
    user = await require_user()
    return election_detail(await elections.update(election_id, user.id, election_input(data)))


@app_api_blueprint.delete('/elections/<int:election_id>')
@tag(['elections'])
async def delete_election(election_id: int):
    user = await require_user()
    await elections.delete(election_id, user.id)
    return '', 204


@app_api_blueprint.post('/elections/<int:election_id>/publish')
@tag(['elections'])
@validate_response(schemas.ElectionDetail)
async def publish_election(election_id: int):
    """Post a draft in its Discord channel and open voting."""
    user = await require_user()
    return election_detail(await elections.publish(election_id, user.id))


@app_api_blueprint.post('/elections/<int:election_id>/close')
@tag(['elections'])
@validate_response(schemas.ElectionDetail)
async def close_election(election_id: int):
    """End voting now and count the ballots."""
    user = await require_user()
    return election_detail(await elections.close(election_id, user.id))


@app_api_blueprint.get('/elections/<int:election_id>/ballot')
@tag(['elections'])
@validate_response(schemas.Election)
async def get_election_ballot(election_id: int):
    user = await require_user()
    return schemas.Election(**await elections.get_ballot(election_id, user.id))


@app_api_blueprint.put('/elections/<int:election_id>/ballot')
@tag(['elections'])
@validate_request(schemas.ElectionBallotIn)
@validate_response(schemas.Election)
async def put_election_ballot(election_id: int, data: schemas.ElectionBallotIn):
    """Cast or replace the viewer's ballot; the latest one counts."""
    user = await require_user()
    return schemas.Election(**await elections.cast_ballot(election_id, user.id, data.choices))


@app_api_blueprint.get('/elections/<int:election_id>/results')
@tag(['elections'])
@validate_response(schemas.ElectionResults)
async def election_results(election_id: int):
    """The count, public once the election has closed. No sign-in needed."""
    return schemas.ElectionResults(**await elections.results(election_id))


# The ballot routes the web app used before /elections; kept until it switches.

@app_api_blueprint.get('/ranked-choice/<int:election_id>')
@tag(['elections'])
@validate_response(schemas.Election)
async def get_election(election_id: int):
    user = await require_user()
    return schemas.Election(**await elections.get_ballot(election_id, user.id))


@app_api_blueprint.post('/ranked-choice/<int:election_id>/ballot')
@tag(['elections'])
@validate_request(schemas.BallotIn)
@validate_response(schemas.Election)
async def cast_ballot(election_id: int, data: schemas.BallotIn):
    user = await require_user()
    return schemas.Election(**await elections.cast_ballot(election_id, user.id, data.ranking))


# --- Triforce texts ----------------------------------------------------------


@app_api_blueprint.get('/triforce-texts/<string:pool>')
@tag(['triforce texts'])
@validate_response(schemas.TriforcePool)
async def get_triforce_pool(pool: str):
    user = await require_user()
    return schemas.TriforcePool(**await triforce_texts.pool(pool, user.id))


@app_api_blueprint.post('/triforce-texts/<string:pool>/submissions')
@tag(['triforce texts'])
@validate_request(schemas.TriforceTextIn)
@validate_response(schemas.TriforceText, 201)
async def submit_triforce_text(pool: str, data: schemas.TriforceTextIn):
    user = await require_user()
    return schemas.TriforceText(**await triforce_texts.submit(pool, user.id, _author(user), data.lines)), 201


@app_api_blueprint.get('/triforce-texts/<string:pool>/moderation')
@tag(['triforce texts'])
@validate_querystring(schemas.ModerationQuery)
@validate_response(schemas.TriforceModerationList)
async def list_triforce_moderation(pool: str, query_args: schemas.ModerationQuery):
    user = await require_user()
    texts = await triforce_texts.list_for_moderation(pool, user.id, query_args.status)
    return schemas.TriforceModerationList(pool=pool, status=query_args.status, texts=texts)


@app_api_blueprint.post('/triforce-texts/<string:pool>/moderation/<int:text_id>')
@tag(['triforce texts'])
@validate_request(schemas.ModerationIn)
@validate_response(schemas.TriforceText)
async def moderate_triforce_text(pool: str, text_id: int, data: schemas.ModerationIn):
    user = await require_user()
    return schemas.TriforceText(**await triforce_texts.moderate(pool, text_id, user.id, data.approved))


# --- Tournament settings submission -----------------------------------------


@app_api_blueprint.get('/tournaments/<event>/submission-form')
@tag(['tournaments'])
@validate_response(schemas.SubmissionForm)
async def get_submission_form(event: str):
    await require_user()
    return schemas.SubmissionForm(**await tournament_submissions.get_form(event))


@app_api_blueprint.post('/tournaments/<event>/submissions')
@tag(['tournaments'])
@validate_request(schemas.SubmissionIn)
@validate_response(schemas.SubmissionDone)
async def submit_settings(event: str, data: schemas.SubmissionIn):
    user = await require_user()
    done = await tournament_submissions.submit(event, data.episode_id, data.settings, _author(user))
    return schemas.SubmissionDone(**done)


# --- Seeds -------------------------------------------------------------------


@app_api_blueprint.post('/seeds')
@tag(['seeds'])
@validate_request(schemas.SeedRollIn)
@validate_response(schemas.Seed, 201)
async def roll_seed(data: schemas.SeedRollIn):
    """Roll a seed from a preset, as the Discord commands do. Takes a few seconds.

    Read-only tokens may call this: rolling a seed changes nothing of yours."""
    await require_user()
    options = seeds.RollOptions(race=data.race, hints=data.hints, allow_quickswap=data.allow_quickswap,
                                branch=data.branch, spoiler_race=data.spoiler_race)
    return schemas.Seed(**await seeds.roll(data.randomizer, data.preset, options)), 201


@app_api_blueprint.get('/seeds/<string:hash_id>')
@tag(['seeds'])
@validate_response(schemas.SeedLookup)
async def lookup_seed(hash_id: str):
    """What SahasrahBot recorded about a seed it rolled: randomizer, preset and link."""
    await require_user()
    return schemas.SeedLookup(**await seeds.lookup(hash_id))


# --- Audit log ---------------------------------------------------------------


def audit_entry(data: dict) -> schemas.AuditEntry:
    return schemas.AuditEntry(**{**data, 'actor_id': _id(data['actor_id']), 'guild_id': _id(data['guild_id'])})


def audit_filters(query: schemas.AuditQuery) -> audit.Filters:
    return audit.Filters(scope=query.scope, area=query.area or None, query=query.q,
                         actor_discord_id=_int_id(query.actor, 'person'), before_id=query.before, limit=query.limit)


@app_api_blueprint.get('/audit/options')
@tag(['audit'])
@validate_response(schemas.AuditOptions)
async def audit_options():
    """What you can filter the audit log by: your own activity, each server you
    administer, and everything if you own the bot; and the areas."""
    user = await require_user()
    return schemas.AuditOptions(
        scopes=[schemas.AuditScope(**s) for s in await audit.scopes(user.id, await admin_guild_ids(user))],
        areas=[schemas.AuditArea(**a) for a in audit.areas()],
    )


@app_api_blueprint.get('/audit')
@tag(['audit'])
@validate_querystring(schemas.AuditQuery)
@validate_response(schemas.AuditPage)
async def list_audit(query_args: schemas.AuditQuery):
    """Changes made through SahasrahBot, newest first: yours (`scope=mine`), a server you
    administer's (`scope=<server id>`), or everyone's (`scope=all`, the bot's owners)."""
    user = await require_user()
    page = await audit.list_entries(user.id, await admin_guild_ids(user), audit_filters(query_args))
    return schemas.AuditPage(entries=[audit_entry(e) for e in page['entries']], next_before=page['next_before'])


CSV_COLUMNS = ('id', 'created_at', 'label', 'action', 'actor_name', 'actor_id', 'guild_name', 'guild_id', 'target',
               'via_label', 'via_detail', 'details')


def _csv_cell(value) -> str:
    if value is None:
        text = ''
    elif isinstance(value, dict):
        text = json.dumps(value)
    else:
        text = str(value)
    # A leading =, +, - or @ would run as a formula in a spreadsheet.
    return "'" + text if text[:1] in ('=', '+', '-', '@') else text


@app_api_blueprint.get('/audit/export')
@tag(['audit'])
@validate_querystring(schemas.AuditQuery)
async def export_audit(query_args: schemas.AuditQuery):
    """The same entries as `/audit`, every page (up to 10,000), as a CSV file."""
    user = await require_user()
    rows = await audit.export_entries(user.id, await admin_guild_ids(user), audit_filters(query_args))
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([_csv_cell(row[c].isoformat() if c == 'created_at' else row[c]) for c in CSV_COLUMNS])
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="sahasrahbot-audit-log.csv"'})


# --- API tokens --------------------------------------------------------------


def _mcp_url() -> str:
    return f"{config.APP_URL}/mcp"


@app_api_blueprint.get('/tokens')
@tag(['tokens'])
@validate_response(schemas.ApiTokenList)
async def list_tokens():
    """Your personal tokens and connected AI clients. Website only."""
    user = await require_session_user()
    rows = [schemas.ApiTokenRow(**t) for t in await api_tokens.list_for_user(user.id)]
    return schemas.ApiTokenList(tokens=rows, mcp_url=_mcp_url())


@app_api_blueprint.post('/tokens')
@tag(['tokens'])
@validate_request(schemas.ApiTokenIn)
@validate_response(schemas.ApiTokenCreated, 201)
async def create_token(data: schemas.ApiTokenIn):
    """Make a personal access token. Its value is in this response and nowhere else. Website only."""
    user = await require_session_user()
    raw, row = await api_tokens.create_personal_token(user.id, user.name, data.name, data.read_only,
                                                      data.expires_in_days)
    return schemas.ApiTokenCreated(token=raw, row=schemas.ApiTokenRow(**row)), 201


@app_api_blueprint.delete('/tokens/<int:token_id>')
@tag(['tokens'])
async def revoke_token(token_id: int):
    """Revoke a token, or disconnect an AI client. Website only."""
    user = await require_session_user()
    await api_tokens.revoke(token_id, user.id)
    return '', 204


# --- AI client consent (MCP OAuth) --------------------------------------------


@app_api_blueprint.get('/oauth/requests/<string:txn>')
@tag(['tokens'])
@validate_response(schemas.OAuthRequest)
async def get_oauth_request(txn: str):
    """The AI client asking to connect, for the consent screen. Website only."""
    await require_session_user()
    return schemas.OAuthRequest(**await mcp_auth.describe_request(txn))


@app_api_blueprint.post('/oauth/requests/<string:txn>/approve')
@tag(['tokens'])
@validate_request(schemas.OAuthAnswerIn)
@validate_response(schemas.OAuthRedirect)
async def approve_oauth_request(txn: str, data: schemas.OAuthAnswerIn):
    """Let the AI client connect as you: read-only, or also making changes. Website only."""
    user = await require_session_user()
    return schemas.OAuthRedirect(redirect_url=await mcp_auth.approve(txn, user.id, user.name, data.allow_changes))


@app_api_blueprint.post('/oauth/requests/<string:txn>/deny')
@tag(['tokens'])
@validate_response(schemas.OAuthRedirect)
async def deny_oauth_request(txn: str):
    """Turn the AI client away. Website only."""
    await require_session_user()
    return schemas.OAuthRedirect(redirect_url=mcp_auth.deny(txn))


# --- Voice roles ---------------------------------------------------------------


def voice_role_out(data: dict) -> schemas.VoiceRole:
    return schemas.VoiceRole(**{**data, 'voice_channel_id': str(data['voice_channel_id']),
                                'role_id': str(data['role_id'])})


def _guild_path_id(guild_id: str) -> int:
    """A server id from the URL. Taken as a string: Discord ids don't fit in a JavaScript
    number, so the OpenAPI type must not be integer."""
    if not guild_id.isdigit():
        abort(404)
    return int(guild_id)


def voice_roles_out(data: dict) -> schemas.VoiceRoles:
    return schemas.VoiceRoles(
        voice_roles=[voice_role_out(v) for v in data['voice_roles']],
        voice_channels=[schemas.ServerOption(id=str(c['id']), name=c['name']) for c in data['voice_channels']],
        roles=[schemas.VoiceRoleRoleOption(id=str(r['id']), name=r['name'], assignable=r['assignable'])
               for r in data['roles']],
    )


@app_api_blueprint.get('/servers/<string:guild_id>/voice-roles')
@tag(['servers'])
@validate_response(schemas.VoiceRoles)
async def list_voice_roles(guild_id: str):
    """The server's voice roles (people in the voice channel get the role while they're in it),
    and the voice channels and roles a new one can use. Server administrators only."""
    user = await require_user()
    return voice_roles_out(await voice_roles.overview(_guild_path_id(guild_id), user.id))


@app_api_blueprint.post('/servers/<string:guild_id>/voice-roles')
@tag(['servers'])
@validate_request(schemas.VoiceRoleIn)
@validate_response(schemas.VoiceRole, 201)
async def add_voice_role(guild_id: str, data: schemas.VoiceRoleIn):
    user = await require_user()
    return voice_role_out(await voice_roles.add(_guild_path_id(guild_id), user.id,
                                                _int_id(data.voice_channel_id, 'voice channel'),
                                                _int_id(data.role_id, 'role'))), 201


@app_api_blueprint.delete('/servers/<string:guild_id>/voice-roles/<int:voice_role_id>')
@tag(['servers'])
async def remove_voice_role(guild_id: str, voice_role_id: int):
    user = await require_user()
    await voice_roles.remove(_guild_path_id(guild_id), user.id, voice_role_id)
    return '', 204


# --- Server directory ------------------------------------------------------------
# The partner servers a server posts to its channels. Its Administrators edit it.


async def _directory_admin(guild_id: int) -> Caller:
    user = await require_user()
    await servers.require_admin(guild_id, user.id)
    return user


async def _directory(guild_id: int) -> schemas.ServerDirectory:
    directory = await discord_servers.get_directory(guild_id)
    return schemas.ServerDirectory(
        guild_id=str(guild_id),
        categories=[schemas.DirectoryCategory(
            id=entry.category.id,
            title=entry.category.category_title,
            description=entry.category.category_description,
            channel_id=str(entry.category.channel_id),
            servers=[schemas.DirectoryServer(id=s.id, invite_code=s.invite_id, description=s.server_description)
                     for s in entry.servers],
        ) for entry in directory.categories],
        last_posted_at=directory.last_posted_at,
        unposted_changes=directory.unposted_changes,
        servers_per_message=discord_servers.SERVERS_PER_MESSAGE,
    )


def _channel_id(value: str) -> int:
    if not value.isdigit():
        raise InvalidInputError("Pick a channel.")
    return int(value)


@app_api_blueprint.get('/servers/<int:guild_id>/directory')
@tag(['servers'])
@validate_response(schemas.ServerDirectory)
async def get_server_directory(guild_id: int):
    await _directory_admin(guild_id)
    return await _directory(guild_id)


@app_api_blueprint.post('/servers/<int:guild_id>/directory/categories')
@tag(['servers'])
@validate_request(schemas.DirectoryCategoryIn)
@validate_response(schemas.ServerDirectory, 201)
async def create_directory_category(guild_id: int, data: schemas.DirectoryCategoryIn):
    """Add a category at the end."""
    await _directory_admin(guild_id)
    await discord_servers.create_category(guild_id, _channel_id(data.channel_id), data.title, data.description)
    return await _directory(guild_id), 201


@app_api_blueprint.put('/servers/<int:guild_id>/directory/categories/<int:category_id>')
@tag(['servers'])
@validate_request(schemas.DirectoryCategoryIn)
@validate_response(schemas.ServerDirectory)
async def update_directory_category(guild_id: int, category_id: int, data: schemas.DirectoryCategoryIn):
    await _directory_admin(guild_id)
    await discord_servers.edit_category(guild_id, category_id, _channel_id(data.channel_id), data.title,
                                        data.description)
    return await _directory(guild_id)


@app_api_blueprint.delete('/servers/<int:guild_id>/directory/categories/<int:category_id>')
@tag(['servers'])
@validate_response(schemas.ServerDirectory)
async def delete_directory_category(guild_id: int, category_id: int):
    """Delete a category and every server in it."""
    await _directory_admin(guild_id)
    await discord_servers.remove_category(guild_id, category_id)
    return await _directory(guild_id)


@app_api_blueprint.put('/servers/<int:guild_id>/directory/order')
@tag(['servers'])
@validate_request(schemas.DirectoryOrderIn)
@validate_response(schemas.ServerDirectory)
async def order_directory_categories(guild_id: int, data: schemas.DirectoryOrderIn):
    """Put the categories in a new order."""
    await _directory_admin(guild_id)
    await discord_servers.reorder_categories(guild_id, data.ids)
    return await _directory(guild_id)


@app_api_blueprint.put('/servers/<int:guild_id>/directory/categories/<int:category_id>/order')
@tag(['servers'])
@validate_request(schemas.DirectoryOrderIn)
@validate_response(schemas.ServerDirectory)
async def order_directory_servers(guild_id: int, category_id: int, data: schemas.DirectoryOrderIn):
    """Put a category's servers in a new order."""
    await _directory_admin(guild_id)
    await discord_servers.reorder_servers(guild_id, category_id, data.ids)
    return await _directory(guild_id)


@app_api_blueprint.post('/servers/<int:guild_id>/directory/categories/<int:category_id>/servers')
@tag(['servers'])
@validate_request(schemas.DirectoryServerIn)
@validate_response(schemas.ServerDirectory, 201)
async def add_directory_server(guild_id: int, category_id: int, data: schemas.DirectoryServerIn):
    """Check the invite with Discord and add the server at the end of the category."""
    await _directory_admin(guild_id)
    await discord_servers.add_server_from_invite(guild_id, category_id, data.invite, data.description)
    return await _directory(guild_id), 201


@app_api_blueprint.put('/servers/<int:guild_id>/directory/servers/<int:server_id>')
@tag(['servers'])
@validate_request(schemas.DirectoryServerUpdateIn)
@validate_response(schemas.ServerDirectory)
async def update_directory_server(guild_id: int, server_id: int, data: schemas.DirectoryServerUpdateIn):
    await _directory_admin(guild_id)
    await discord_servers.edit_server(guild_id, server_id, data.category_id, data.invite, data.description)
    return await _directory(guild_id)


@app_api_blueprint.delete('/servers/<int:guild_id>/directory/servers/<int:server_id>')
@tag(['servers'])
@validate_response(schemas.ServerDirectory)
async def delete_directory_server(guild_id: int, server_id: int):
    await _directory_admin(guild_id)
    await discord_servers.remove_server(guild_id, server_id)
    return await _directory(guild_id)


@app_api_blueprint.get('/servers/<int:guild_id>/directory/invite')
@tag(['servers'])
@validate_querystring(schemas.InviteQuery)
@validate_response(schemas.DirectoryInvite)
async def check_directory_invite(guild_id: int, query_args: schemas.InviteQuery):
    """What Discord says about an invite, for the add-server form."""
    await _directory_admin(guild_id)
    info = await discord_servers.lookup_invite(query_args.invite)
    return schemas.DirectoryInvite(code=info.code, server_name=info.server_name, member_count=info.member_count,
                                   expires_at=info.expires_at)


@app_api_blueprint.post('/servers/<int:guild_id>/directory/post')
@tag(['servers'])
@validate_response(schemas.DirectoryPosted)
async def post_server_directory(guild_id: int):
    """Delete SahasrahBot's messages in the directory's channels and post the list again."""
    await _directory_admin(guild_id)
    layout = await discord_servers.post(guild_id)
    return schemas.DirectoryPosted(messages=len(layout.pages), channel_ids=[str(c) for c in layout.channel_ids])

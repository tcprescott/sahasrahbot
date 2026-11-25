"""Personal access tokens for the REST API, and the OAuth tokens MCP clients hold.

Both kinds live in ``models.ApiToken``, told apart by ``origin``: ``pat`` for a token
someone made on the API access page, ``oauth`` for one an MCP client got through the
consent screen (``alttprbot/services/mcp_auth.py`` issues those). A credential made
for one surface is refused by the other, so neither can be replayed against both.

Only SHA-256 hashes are stored; the plaintext is shown once. A token acts as the
Discord user who made it, with their name as it was then. ``read_only`` refuses
anything that changes data.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services import audit

PAT = 'pat'
OAUTH = 'oauth'

PAT_PREFIX = 'sb_pat_'
OAUTH_PREFIX = 'sb_mcp_'
REFRESH_PREFIX = 'sb_mcpr_'

NAME_MAX = 100
MAX_TOKENS_PER_USER = 50
# The choices the API access page offers; None is "never".
EXPIRY_DAYS = (30, 90, 365, None)
# last_used_at is written at most this often per token, not on every request.
LAST_USED_RESOLUTION = timedelta(minutes=1)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(timezone.utc)


def _live(token: models.ApiToken, at: datetime) -> bool:
    if token.revoked_at is not None:
        return False
    if token.origin == OAUTH:
        # A connected client lasts as long as its refresh token, not one access token.
        return token.refresh_expires_at is None or token.refresh_expires_at > at
    return token.expires_at is None or token.expires_at > at


def _row(token: models.ApiToken) -> dict:
    return {
        'id': token.id,
        'name': token.name,
        'kind': 'client' if token.origin == OAUTH else 'token',
        'read_only': token.read_only,
        'prefix': token.token_prefix if token.origin == PAT else None,
        'created_at': token.created_at,
        'last_used_at': token.last_used_at,
        'expires_at': token.expires_at if token.origin == PAT else None,
    }


async def create_personal_token(discord_user_id: int, user_name: str, name: str, read_only: bool,
                                expires_in_days: Optional[int]) -> tuple[str, dict]:
    """Make a personal access token. Returns ``(plaintext, row)``; the plaintext is never stored."""
    name = (name or '').strip()
    if not name:
        raise InvalidInputError("Give the token a name, so you can tell it apart from your others.")
    if len(name) > NAME_MAX:
        raise InvalidInputError(f"Token names can be at most {NAME_MAX} characters.")
    if expires_in_days not in EXPIRY_DAYS:
        raise InvalidInputError("Tokens can expire in 30, 90 or 365 days, or never.")
    if len(await list_for_user(discord_user_id)) >= MAX_TOKENS_PER_USER:
        raise InvalidInputError(f"You can have at most {MAX_TOKENS_PER_USER} tokens. Revoke one you don't use.")
    raw = PAT_PREFIX + secrets.token_urlsafe(32)
    created = now()
    token = await models.ApiToken.create(
        discord_user_id=discord_user_id,
        user_name=user_name[:100],
        name=name,
        origin=PAT,
        token_hash=hash_token(raw),
        token_prefix=raw[:len(PAT_PREFIX) + 4],
        read_only=read_only,
        expires_at=None if expires_in_days is None else created + timedelta(days=expires_in_days),
    )
    await audit.record(audit.API_TOKEN_CREATED, target=name, actor_discord_id=discord_user_id, actor_name=user_name,
                       details={'token_id': token.id, 'read_only': read_only, 'expires_in_days': expires_in_days,
                                'prefix': token.token_prefix})
    return raw, _row(token)


async def list_for_user(discord_user_id: int) -> list[dict]:
    """The user's live tokens and connected AI clients, newest first."""
    at = now()
    tokens = await models.ApiToken.filter(discord_user_id=discord_user_id, revoked_at=None).order_by('-created_at', '-id')
    return [_row(t) for t in tokens if _live(t, at)]


async def revoke(token_id: int, discord_user_id: int) -> None:
    """Revoke one of the user's tokens, or disconnect one of their AI clients."""
    token = await models.ApiToken.get_or_none(id=token_id, discord_user_id=discord_user_id, revoked_at=None)
    if token is None:
        raise NotFoundError("That token doesn't exist, or it's already revoked.")
    await models.ApiToken.filter(id=token.id).update(revoked_at=now())
    action = audit.AI_CLIENT_DISCONNECTED if token.origin == OAUTH else audit.API_TOKEN_REVOKED
    await audit.record(action, target=token.name, actor_discord_id=discord_user_id,
                       details={'token_id': token.id})


async def revoke_all_for_user(discord_user_id: int) -> None:
    await models.ApiToken.filter(discord_user_id=discord_user_id, revoked_at=None).update(revoked_at=now())


async def authenticate(raw: str, origin: str) -> Optional[models.ApiToken]:
    """The live token of ``origin`` that ``raw`` is, or None. Marks it used."""
    if not raw:
        return None
    token = await models.ApiToken.get_or_none(token_hash=hash_token(raw))
    if token is None or token.origin != origin or token.revoked_at is not None:
        return None
    at = now()
    if token.expires_at is not None and token.expires_at <= at:
        return None
    if token.last_used_at is None or at - token.last_used_at >= LAST_USED_RESOLUTION:
        await models.ApiToken.filter(id=token.id).update(last_used_at=at)
        token.last_used_at = at
    return token

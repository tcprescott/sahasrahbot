"""The OAuth 2.1 authorization server behind the MCP endpoint (``/mcp``).

An MCP client (Claude, say) registers itself (RFC 7591), sends the person to
``/authorize``, and the SDK hands the request here. It waits, parked, while the
person signs in with Discord and answers the consent screen in the web app
(``/oauth/consent``). Approving mints a single-use code; the client exchanges it,
with its PKCE verifier, for an access token (an ``ApiToken`` with ``origin='oauth'``)
and a refresh token. Refreshing rotates both, so a stolen refresh token is good once.

What a connection may do is decided by the person on the consent screen, never by
what the client asked for: read-only, or also make changes.

Free of MCP SDK types: ``alttprbot_api/mcp/oauth.py`` translates at the boundary.
"""

import logging
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError
from alttprbot.services.api_tokens import OAUTH, OAUTH_PREFIX, REFRESH_PREFIX, hash_token, now

logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=5)
ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)
PENDING_TTL = timedelta(minutes=15)
MAX_PENDING = 1000

READ_SCOPE = 'sahasrahbot:read'
WRITE_SCOPE = 'sahasrahbot:write'
CLIENT_SCOPE = f'{READ_SCOPE} {WRITE_SCOPE}'

# The consent page sends the signed-in browser to the redirect URI from our origin,
# so a script scheme there would run as the person.
_REFUSED_REDIRECT_SCHEMES = frozenset({'javascript', 'data', 'vbscript', 'file', 'blob', 'about', 'filesystem'})
_LOOPBACK_HOSTS = frozenset({'localhost', '127.0.0.1', '::1'})


def is_allowed_redirect_uri(uri: str) -> bool:
    """https anywhere, http only to loopback, or a native app's own scheme (RFC 8252)."""
    try:
        parts = urlsplit((uri or '').strip())
        host = (parts.hostname or '').lower()
    except ValueError:
        return False
    scheme = parts.scheme.lower()
    if not scheme or scheme in _REFUSED_REDIRECT_SCHEMES or parts.fragment:
        return False
    if scheme == 'https':
        return bool(host)
    if scheme == 'http':
        return host in _LOOPBACK_HOSTS
    return True


def redirect_target(uri: str) -> str:
    """What the consent screen shows as where approving sends you: the host, or the
    whole URI for a native app's own scheme (which has no host)."""
    parts = urlsplit(uri)
    if parts.scheme in ('http', 'https'):
        return parts.netloc
    return uri


def scope_for(read_only: bool) -> str:
    return READ_SCOPE if read_only else CLIENT_SCOPE


@dataclass
class PendingAuthorization:
    """An authorization request waiting for the person to sign in and answer."""

    client_id: str
    redirect_uri: str
    redirect_uri_provided_explicitly: bool
    code_challenge: str
    state: Optional[str]
    resource: Optional[str]
    created_at: object = field(default_factory=now)


_pending: dict[str, PendingAuthorization] = {}


def _sweep_pending() -> None:
    cutoff = now() - PENDING_TTL
    for txn, pending in list(_pending.items()):
        if pending.created_at < cutoff:
            _pending.pop(txn, None)
    while len(_pending) >= MAX_PENDING:
        _pending.pop(next(iter(_pending)))


async def register_client(client_id: str, client_name: str, redirect_uris: list[str], grant_types: list[str],
                          response_types: list[str], scope: Optional[str]) -> models.McpOAuthClient:
    """Register a client. Open by design (that's what lets someone paste the server's
    address into Claude); registering grants nothing on its own."""
    if not redirect_uris:
        raise InvalidInputError('At least one redirect URI is required.')
    if not all(is_allowed_redirect_uri(uri) for uri in redirect_uris):
        raise InvalidInputError('Redirect URIs must be https, http to localhost, or an app scheme.')
    return await models.McpOAuthClient.create(
        client_id=client_id or secrets.token_urlsafe(24),
        client_name=(client_name or 'MCP client')[:255],
        redirect_uris=redirect_uris,
        grant_types=grant_types or ['authorization_code', 'refresh_token'],
        response_types=response_types or ['code'],
        scope=scope or CLIENT_SCOPE,
    )


async def get_client(client_id: str) -> Optional[models.McpOAuthClient]:
    return await models.McpOAuthClient.get_or_none(client_id=client_id)


def begin_authorization(pending: PendingAuthorization) -> str:
    """Park a request and return its transaction id, which the consent page carries."""
    _sweep_pending()
    txn = secrets.token_urlsafe(24)
    _pending[txn] = pending
    return txn


def _get_pending(txn: str) -> PendingAuthorization:
    _sweep_pending()
    pending = _pending.get(txn or '')
    if pending is None:
        raise NotFoundError('This sign-in request has expired. Start again from your AI client.')
    return pending


async def describe_request(txn: str) -> dict:
    """What the consent screen shows: who's asking and where approving sends you."""
    pending = _get_pending(txn)
    client = await get_client(pending.client_id)
    if client is None:
        raise NotFoundError('This AI client is no longer registered. Start again from your AI client.')
    return {'client_name': client.client_name, 'redirect_target': redirect_target(pending.redirect_uri)}


async def approve(txn: str, discord_user_id: int, user_name: str, allow_changes: bool) -> str:
    """Answer yes: mint a code and return the URL to send the browser to.

    Popping the request makes approval single-use."""
    pending = _get_pending(txn)
    _pending.pop(txn, None)
    if not is_allowed_redirect_uri(pending.redirect_uri):
        raise InvalidInputError("This AI client registered a redirect address SahasrahBot won't open.")
    client = await get_client(pending.client_id)
    if client is None:
        raise NotFoundError('This AI client is no longer registered. Start again from your AI client.')
    raw_code = secrets.token_urlsafe(32)
    await models.McpAuthorizationCode.create(
        code_hash=hash_token(raw_code),
        client=client,
        discord_user_id=discord_user_id,
        user_name=user_name[:100],
        redirect_uri=pending.redirect_uri,
        redirect_uri_provided_explicitly=pending.redirect_uri_provided_explicitly,
        code_challenge=pending.code_challenge,
        scope=scope_for(not allow_changes),
        resource=pending.resource,
        read_only=not allow_changes,
        expires_at=now() + CODE_TTL,
    )
    logger.info('MCP connection approved: user=%s client=%s changes=%s', discord_user_id, client.client_id, allow_changes)
    return _with_query(pending.redirect_uri, code=raw_code, state=pending.state)


def deny(txn: str) -> str:
    """Answer no: return the URL that tells the client so (RFC 6749 access_denied)."""
    pending = _get_pending(txn)
    _pending.pop(txn, None)
    return _with_query(pending.redirect_uri, error='access_denied', state=pending.state)


def _with_query(uri: str, **params) -> str:
    parts = urlsplit(uri)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query += [(k, v) for k, v in params.items() if v is not None]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


async def load_code(client_id: str, raw_code: str) -> Optional[models.McpAuthorizationCode]:
    """A live, unspent code that belongs to ``client_id``."""
    code = await models.McpAuthorizationCode.get_or_none(code_hash=hash_token(raw_code)).prefetch_related('client')
    if code is None or code.consumed_at is not None or code.client.client_id != client_id:
        return None
    return code


def _new_pair() -> tuple[str, str]:
    return OAUTH_PREFIX + secrets.token_urlsafe(32), REFRESH_PREFIX + secrets.token_urlsafe(32)


async def exchange_code(code: models.McpAuthorizationCode) -> tuple[str, str, int]:
    """Spend a code for ``(access_token, refresh_token, expires_in_seconds)``."""
    at = now()
    # One conditional UPDATE, so two concurrent exchanges can't both spend the code.
    spent = await models.McpAuthorizationCode.filter(id=code.id, consumed_at=None).update(consumed_at=at)
    if not spent:
        raise InvalidInputError('This authorization code has already been used.')
    access, refresh = _new_pair()
    client = code.client
    await models.ApiToken.create(
        discord_user_id=code.discord_user_id,
        user_name=code.user_name,
        name=client.client_name[:100],
        origin=OAUTH,
        token_hash=hash_token(access),
        token_prefix=access[:len(OAUTH_PREFIX) + 4],
        read_only=code.read_only,
        oauth_client=client,
        expires_at=at + ACCESS_TOKEN_TTL,
        refresh_token_hash=hash_token(refresh),
        refresh_expires_at=at + REFRESH_TOKEN_TTL,
    )
    return access, refresh, int(ACCESS_TOKEN_TTL.total_seconds())


async def load_refresh_token(client_id: str, raw_refresh: str) -> Optional[models.ApiToken]:
    token = await models.ApiToken.get_or_none(refresh_token_hash=hash_token(raw_refresh)).prefetch_related('oauth_client')
    if token is None or token.revoked_at is not None or token.oauth_client is None:
        return None
    if token.oauth_client.client_id != client_id:
        return None
    if token.refresh_expires_at is not None and token.refresh_expires_at <= now():
        return None
    return token


async def exchange_refresh(token: models.ApiToken) -> tuple[str, str, int]:
    """Rotate both halves of the pair on the same row, so the grant (read-only or
    not) never widens on a refresh."""
    at = now()
    access, refresh = _new_pair()
    rotated = await models.ApiToken.filter(id=token.id, refresh_token_hash=token.refresh_token_hash,
                                           revoked_at=None).update(
        token_hash=hash_token(access),
        token_prefix=access[:len(OAUTH_PREFIX) + 4],
        expires_at=at + ACCESS_TOKEN_TTL,
        refresh_token_hash=hash_token(refresh),
        refresh_expires_at=at + REFRESH_TOKEN_TTL,
    )
    if not rotated:
        raise InvalidInputError('This refresh token has already been used.')
    return access, refresh, int(ACCESS_TOKEN_TTL.total_seconds())


async def load_access_token(raw: str) -> Optional[models.ApiToken]:
    token = await models.ApiToken.get_or_none(token_hash=hash_token(raw)).prefetch_related('oauth_client')
    if token is None or token.origin != OAUTH or token.revoked_at is not None:
        return None
    if token.expires_at is not None and token.expires_at <= now():
        return None
    return token


async def revoke(token: models.ApiToken) -> None:
    await models.ApiToken.filter(id=token.id).update(revoked_at=now())

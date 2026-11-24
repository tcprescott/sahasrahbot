"""The OAuth 2.1 authorization server MCP clients sign in through.

The routes (``/authorize``, ``/token``, ``/register``, ``/revoke`` and
``/.well-known/oauth-authorization-server``) come from the MCP SDK, so PKCE and the
grant mechanics are its tested code. This provider only translates between the
SDK's types and ``alttprbot/services/mcp_auth.py``, where the rules live.

``/authorize`` doesn't mint a code: it parks the request and sends the browser to
the web app's consent screen (``/oauth/consent?txn=...``), which signs the person
in with Discord and asks them. The routes are unauthenticated, so they share a
small per-address rate limit; ``/register`` in particular writes a row per call.
"""

import json
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

from mcp.server.auth.provider import (AccessToken, AuthorizationCode, AuthorizationParams,
                                      OAuthAuthorizationServerProvider, RefreshToken, RegistrationError, TokenError)
from mcp.server.auth.routes import create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl
from starlette.routing import Route

from alttprbot.exceptions import SahasrahBotException
from alttprbot.services import mcp_auth
from alttprbot_api.mcp.wellknown import SCOPES_SUPPORTED, base_url

CONSENT_PATH = '/oauth/consent'
RATE_LIMIT = 30
RATE_WINDOW = 60.0


def _epoch(value: Optional[datetime]) -> Optional[int]:
    """The SDK compares expiries with ``time.time()`` and wants whole seconds."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


class SahasrahBotOAuthProvider(OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]):

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        client = await mcp_auth.get_client(client_id)
        if client is None:
            return None
        return OAuthClientInformationFull(
            client_id=client.client_id,
            client_name=client.client_name,
            redirect_uris=list(client.redirect_uris or []),
            grant_types=list(client.grant_types or []),
            response_types=list(client.response_types or []),
            # Always 'none': the SDK refuses a secret-based client with no stored secret,
            # and clients are public anyway. PKCE binds a code to its client.
            token_endpoint_auth_method='none',
            scope=client.scope,
        )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        try:
            await mcp_auth.register_client(
                client_id=client_info.client_id,
                client_name=client_info.client_name or 'MCP client',
                redirect_uris=[str(uri) for uri in client_info.redirect_uris or []],
                grant_types=list(client_info.grant_types or []),
                response_types=list(client_info.response_types or []),
                # Both scopes, or the SDK refuses a client asking for write; the person decides on the consent screen.
                scope=mcp_auth.CLIENT_SCOPE,
            )
        except SahasrahBotException as exc:
            raise RegistrationError(error='invalid_redirect_uri', error_description=str(exc)) from exc

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        txn = mcp_auth.begin_authorization(mcp_auth.PendingAuthorization(
            client_id=client.client_id,
            redirect_uri=str(params.redirect_uri),
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            code_challenge=params.code_challenge,
            state=params.state,
            resource=params.resource,
        ))
        return f'{base_url()}{CONSENT_PATH}?{urlencode({"txn": txn})}'

    async def load_authorization_code(self, client: OAuthClientInformationFull,
                                      authorization_code: str) -> Optional[AuthorizationCode]:
        code = await mcp_auth.load_code(client.client_id, authorization_code)
        if code is None:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=(code.scope or mcp_auth.READ_SCOPE).split(),
            expires_at=_epoch(code.expires_at),
            client_id=client.client_id,
            code_challenge=code.code_challenge,
            redirect_uri=code.redirect_uri,
            redirect_uri_provided_explicitly=code.redirect_uri_provided_explicitly,
            resource=code.resource,
        )

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: AuthorizationCode) -> OAuthToken:
        # Load it again: a concurrent exchange may have spent it since the SDK did.
        code = await mcp_auth.load_code(client.client_id, authorization_code.code)
        if code is None:
            raise TokenError(error='invalid_grant', error_description='Invalid or already-used authorization code.')
        try:
            access, refresh, expires_in = await mcp_auth.exchange_code(code)
        except SahasrahBotException as exc:
            raise TokenError(error='invalid_grant', error_description=str(exc)) from exc
        return OAuthToken(access_token=access, token_type='Bearer', expires_in=expires_in,
                          scope=code.scope or mcp_auth.READ_SCOPE, refresh_token=refresh)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str) -> Optional[RefreshToken]:
        token = await mcp_auth.load_refresh_token(client.client_id, refresh_token)
        if token is None:
            return None
        return RefreshToken(token=refresh_token, client_id=client.client_id,
                            scopes=mcp_auth.scope_for(token.read_only).split(),
                            expires_at=_epoch(token.refresh_expires_at))

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        token = await mcp_auth.load_refresh_token(client.client_id, refresh_token.token)
        if token is None:
            raise TokenError(error='invalid_grant', error_description='Invalid or expired refresh token.')
        try:
            access, refresh, expires_in = await mcp_auth.exchange_refresh(token)
        except SahasrahBotException as exc:
            raise TokenError(error='invalid_grant', error_description=str(exc)) from exc
        return OAuthToken(access_token=access, token_type='Bearer', expires_in=expires_in,
                          scope=mcp_auth.scope_for(token.read_only), refresh_token=refresh)

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        record = await mcp_auth.load_access_token(token)
        if record is None:
            return None
        return AccessToken(token=token, client_id=record.oauth_client.client_id if record.oauth_client else '',
                           scopes=mcp_auth.scope_for(record.read_only).split(), expires_at=_epoch(record.expires_at))

    async def revoke_token(self, token) -> None:
        """Revoke the whole grant, whichever half was presented (RFC 7009 allows it)."""
        raw = getattr(token, 'token', None)
        if not raw:
            return
        record = await mcp_auth.load_access_token(raw)
        if record is None:
            record = await mcp_auth.load_refresh_token(token.client_id, raw)
        if record is not None:
            await mcp_auth.revoke(record)


_hits: dict[str, deque] = defaultdict(deque)


def _client_key(scope) -> str:
    for key, value in scope.get('headers') or []:
        if key == b'x-forwarded-for':
            return value.decode('latin-1').split(',')[0].strip()
    client = scope.get('client')
    return client[0] if client else 'unknown'


def _limited(key: str) -> bool:
    now = time.monotonic()
    hits = _hits[key]
    while hits and now - hits[0] > RATE_WINDOW:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        return True
    hits.append(now)
    if len(_hits) > 10000:
        _hits.clear()
    return False


def _rate_limited(app):
    async def guarded(scope, receive, send):
        if scope.get('method') != 'OPTIONS' and _limited(_client_key(scope)):
            body = json.dumps({'error': 'rate_limited', 'error_description': 'Too many requests. Try again shortly.'})
            await send({'type': 'http.response.start', 'status': 429,
                        'headers': [(b'content-type', b'application/json'), (b'retry-after', b'60')]})
            await send({'type': 'http.response.body', 'body': body.encode()})
            return
        await app(scope, receive, send)
    return guarded


def routes() -> list[Route]:
    base = base_url()
    built = create_auth_routes(
        provider=SahasrahBotOAuthProvider(),
        issuer_url=AnyHttpUrl(base),
        service_documentation_url=AnyHttpUrl(f'{base}/api/v1/docs'),
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=SCOPES_SUPPORTED, default_scopes=SCOPES_SUPPORTED),
        revocation_options=RevocationOptions(enabled=True),
    )
    for route in built:
        route.app = _rate_limited(route.app)
    return built

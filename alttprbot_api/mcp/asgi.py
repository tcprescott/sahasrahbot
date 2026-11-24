"""The ``/mcp`` endpoint: check the bearer token, bind the caller, hand over to the
MCP transport. Raw ASGI, because the transport needs the untouched request body.

Only OAuth tokens from the consent screen are accepted. A personal access token, a
bad token or no token gets 401 with a challenge naming the protected-resource
metadata, which is how a client finds the authorization server and signs in.
"""

import json
import logging
from typing import Optional

from alttprbot.services import api_tokens
from alttprbot_api.mcp.auth import McpActor, reset_actor, set_actor
from alttprbot_api.mcp.wellknown import www_authenticate

logger = logging.getLogger(__name__)


def _bearer(scope) -> Optional[str]:
    for key, value in scope.get('headers') or []:
        if key == b'authorization':
            header = value.decode('latin-1')
            if header[:7].lower() == 'bearer ':
                return header[7:].strip() or None
    return None


async def _error(send, status: int, error: str, description: str, challenge: bool = False) -> None:
    headers = [(b'content-type', b'application/json')]
    if challenge:
        headers.append((b'www-authenticate', www_authenticate().encode()))
    await send({'type': 'http.response.start', 'status': status, 'headers': headers})
    await send({'type': 'http.response.body',
                'body': json.dumps({'error': error, 'error_description': description}).encode()})


class McpEndpoint:
    def __init__(self) -> None:
        # Set by mount() each time the app starts serving.
        self.session_manager = None

    async def __call__(self, scope, receive, send) -> None:
        if self.session_manager is None:
            await _error(send, 503, 'temporarily_unavailable', 'The MCP server is starting. Try again shortly.')
            return
        raw = _bearer(scope)
        if raw is None:
            await _error(send, 401, 'invalid_token', 'Sign in through your AI client.', challenge=True)
            return
        token = await api_tokens.authenticate(raw, api_tokens.OAUTH)
        if token is None:
            if raw.startswith(api_tokens.PAT_PREFIX):
                description = 'Personal access tokens are for the REST API. Connect through your AI client instead.'
            else:
                description = 'That token is invalid, expired or revoked.'
            await _error(send, 401, 'invalid_token', description, challenge=True)
            return
        actor = McpActor(discord_user_id=token.discord_user_id, user_name=token.user_name,
                         read_only=token.read_only, client_name=token.name)
        bound = set_actor(actor)
        try:
            await self.session_manager.handle_request(scope, receive, send)
        finally:
            reset_actor(bound)

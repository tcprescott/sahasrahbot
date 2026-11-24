"""RFC 9728 protected-resource metadata, and the Bearer challenge that points to it.

Served at the origin root (``/.well-known/oauth-protected-resource`` and its
``/mcp``-suffixed form), where clients look; the SDK's own helper would put it
under the MCP sub-app. A 401 from ``/mcp`` names this document, which is how a
client finds the authorization server and starts the OAuth flow.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

import config
from alttprbot.services.mcp_auth import READ_SCOPE, WRITE_SCOPE

MCP_PATH = '/mcp'
SCOPES_SUPPORTED = [READ_SCOPE, WRITE_SCOPE]
METADATA_PATHS = ('/.well-known/oauth-protected-resource/mcp', '/.well-known/oauth-protected-resource')


def base_url() -> str:
    return config.APP_URL.rstrip('/')


def resource_url() -> str:
    return base_url() + MCP_PATH


def protected_resource_metadata() -> dict:
    base = base_url()
    return {
        'resource': resource_url(),
        'authorization_servers': [base],
        'bearer_methods_supported': ['header'],
        'scopes_supported': SCOPES_SUPPORTED,
        'resource_name': 'SahasrahBot',
        'resource_documentation': f'{base}/api/v1/docs',
    }


def www_authenticate() -> str:
    return f'Bearer resource_metadata="{base_url()}{METADATA_PATHS[0]}"'


async def _metadata(request: Request) -> JSONResponse:
    return JSONResponse(protected_resource_metadata())


def routes() -> list[Route]:
    return [Route(path, _metadata, methods=['GET']) for path in METADATA_PATHS]

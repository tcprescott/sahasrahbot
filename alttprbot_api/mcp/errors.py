"""Service errors as MCP tool errors.

The SDK turns any exception a tool raises into a bare ``ToolError``, losing its
type, so the translation runs inside each tool (``registry.py``). Errors reach the
model as tool results it can read and recover from, prefixed with a short code.
"""

import logging
from typing import Optional

from mcp.server.mcpserver.exceptions import ToolError

from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError, SahasrahBotException

logger = logging.getLogger(__name__)


def map_service_error(exc: Exception, tool: Optional[str] = None) -> ToolError:
    if isinstance(exc, ToolError):
        return exc
    if isinstance(exc, (PermissionDeniedError, PermissionError)):
        return ToolError(f'forbidden: {exc or "Permission denied."}')
    if isinstance(exc, NotFoundError):
        return ToolError(f'not_found: {exc}')
    if isinstance(exc, (InvalidInputError, SahasrahBotException, ValueError)):
        return ToolError(f'invalid_request: {exc}')
    # Logged at ERROR so Sentry sees it; the model only gets an opaque message.
    logger.error('Unhandled exception in MCP tool %s', tool or '(unknown)', exc_info=exc)
    return ToolError('internal_error: The server hit an unexpected error.')

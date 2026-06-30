import datetime
import logging

from quart import Blueprint, abort, jsonify, request

from alttprbot.services import AuthorizationService
from alttprbot.presentation.racetime import bot as racetimebot
from alttprbot.presentation.racetime.compat import get_room_handler

logger = logging.getLogger(__name__)

racetime_blueprint = Blueprint('racetime_api', __name__)


def _extract_auth_key(req):
    """Resolve the API key from the ``Authorization`` header, falling back to the
    legacy ``?auth_key=`` query parameter.

    The query-string form leaks the key into access logs and proxies, so it is
    deprecated: callers should send ``Authorization: <key>`` (or ``Bearer <key>``).
    Both forms work for now; the query form logs a deprecation warning.
    """
    header = req.headers.get('Authorization')
    if header:
        if header.lower().startswith('bearer '):
            return header[7:].strip()
        return header.strip()

    auth_key = req.args.get('auth_key')
    if auth_key:
        logger.warning(
            "racetime_cmd_auth_key_query_deprecated",
            extra={'path': req.path},
        )
    return auth_key


@racetime_blueprint.route('/api/racetime/cmd', methods=['POST'])
async def bot_command():
    data = await request.get_json()

    category = data['category']
    room = data['room']
    cmd = data['cmd']
    auth_key = _extract_auth_key(request)
    if not auth_key:
        return abort(401)

    if not await AuthorizationService().is_racetime_cmd_authorized(auth_key, category):
        return abort(403)

    racetime_bot = racetimebot.racetime_bots.get(category)
    if not racetime_bot:
        raise Exception("Invalid game category")

    racetime_handler = get_room_handler(racetime_bot, f"{category}/{room}")
    if racetime_handler is None:
        return abort(404, "Race room not currently handled")

    fake_data = {
        'message': {
            'id': 'FAKE',
            'user': {
                'id': 'FAKE',
                'full_name': 'API-submitted command',
                'name': 'API-submitted command',
                'discriminator': None,
                'url': None,
                'avatar': None,
                'flair': None,
                'twitch_name': None,
                'twitch_display_name': None,
                'twitch_channel': None,
                'can_moderate': True,
            },
            'bot': False,
            'posted_at': datetime.datetime.utcnow().isoformat(),
            'message': cmd,
            'message_plain': cmd,
            'highlight': False,
            'is_bot': False,
            'is_monitor': True,
            'is_system': False,
            'delay': 0
        },
        'type': 'message.chat',
        'date': datetime.datetime.utcnow().isoformat(),
    }

    await racetime_handler.send_message(f"Executing command from API request: {cmd}")
    await racetime_handler.chat_message(fake_data)

    return jsonify({'success': True})

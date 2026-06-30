import datetime
import logging
import secrets
from urllib.parse import quote

import aiohttp
from quart import Blueprint, abort, jsonify, redirect, request, session
from alttprbot.presentation.api.oauth_client import requires_authorization

import config
from alttprbot.services import AuthorizationService, UserService
from alttprbot.presentation.api.api import discord
from alttprbot.presentation.racetime import bot as racetimebot
from alttprbot.presentation.racetime.compat import get_room_handler

logger = logging.getLogger(__name__)

racetime_blueprint = Blueprint('racetime', __name__)


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

RACETIME_CLIENT_ID_OAUTH = config.RACETIME_CLIENT_ID_OAUTH
RACETIME_CLIENT_SECRET_OAUTH = config.RACETIME_CLIENT_SECRET_OAUTH
RACETIME_URL = config.RACETIME_URL
APP_URL = config.APP_URL


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


@racetime_blueprint.route('/racetime/verification/initiate', methods=['GET'])
@requires_authorization
async def racetime_init_verification():
    redirect_uri = quote(f"{APP_URL}/racetime/verify/return")
    # CSRF state: bind this authorization request to the user's session so an
    # attacker can't trick a logged-in victim into linking the attacker's
    # RaceTime account via a forged callback.
    state = secrets.token_urlsafe(32)
    session['racetime_oauth_state'] = state
    return redirect(
        f"{RACETIME_URL}/o/authorize?client_id={RACETIME_CLIENT_ID_OAUTH}&response_type=code&scope=read&redirect_uri={redirect_uri}&state={quote(state)}",
    )


@racetime_blueprint.route('/racetime/verify/return', methods=['GET'])
@requires_authorization
async def return_racetime_verify():
    user = await discord.fetch_user()

    returned_state = request.args.get("state")
    stored_state = session.pop('racetime_oauth_state', None)
    if not stored_state or not returned_state or not secrets.compare_digest(returned_state, stored_state):
        return abort(400, "Invalid or missing OAuth state.")

    code = request.args.get("code")
    if code is None:
        return abort(400, "code is missing")
    data = {
        'client_id': RACETIME_CLIENT_ID_OAUTH,
        'client_secret': RACETIME_CLIENT_SECRET_OAUTH,
        'code': code,
        'grant_type': 'authorization_code',
        'scope': 'read',
        'redirect_uri': f"{APP_URL}/racetime/verify/return"
    }

    async with aiohttp.request(url=f"{RACETIME_URL}/o/token", method="post", data=data, raise_for_status=True) as resp:
        token_data = await resp.json()

    token = token_data['access_token']

    headers = {
        'Authorization': f'Bearer {token}'
    }
    async with aiohttp.request(url=f"{RACETIME_URL}/o/userinfo", method="get", headers=headers,
                               raise_for_status=True) as resp:
        userinfo_data = await resp.json()

    rtgg_id = userinfo_data['id']

    await UserService().link_racetime_account(
        discord_user_id=user.id,
        display_name=user.name,
        rtgg_id=rtgg_id,
        access_token=token,
    )

    return redirect(f"/racetime/verified?name={quote(userinfo_data['name'])}&success=true")

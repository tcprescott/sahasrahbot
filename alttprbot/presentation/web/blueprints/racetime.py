import logging
import secrets
from urllib.parse import quote

import aiohttp
from quart import Blueprint, abort, redirect, request, session

import config
from alttprbot.services import UserService
from alttprbot.presentation.web.oauth_client import requires_authorization
from alttprbot.presentation.web.web import discord

logger = logging.getLogger(__name__)

racetime_blueprint = Blueprint('racetime', __name__)

RACETIME_CLIENT_ID_OAUTH = config.RACETIME_CLIENT_ID_OAUTH
RACETIME_CLIENT_SECRET_OAUTH = config.RACETIME_CLIENT_SECRET_OAUTH
RACETIME_URL = config.RACETIME_URL
APP_URL = config.APP_URL


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

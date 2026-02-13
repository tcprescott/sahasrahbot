import datetime
from urllib.parse import quote

import aiohttp
from quart import Blueprint, abort, jsonify, redirect, render_template, request
from alttprbot_api.oauth_client import requires_authorization

import config
from alttprbot import models
from alttprbot_api.api import discord
from alttprbot_racetime import bot as racetimebot

racetime_blueprint = Blueprint('racetime', __name__)

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
    auth_key = request.args['auth_key']

    access = await models.AuthorizationKeyPermissions.get_or_none(auth_key__key=auth_key, type='racetimecmd',
                                                                  subtype=category)
    if access is None:
        return abort(403)

    racetime_bot = racetimebot.racetime_bots.get(category)
    if not racetime_bot:
        raise Exception("Invalid game category")

    racetime_handler = racetime_bot.handlers.get(f"{category}/{room}").handler

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
    return redirect(
        f"{RACETIME_URL}/o/authorize?client_id={RACETIME_CLIENT_ID_OAUTH}&response_type=code&scope=read&redirect_uri={redirect_uri}",
    )


@racetime_blueprint.route('/racetime/verify/return', methods=['GET'])
@requires_authorization
async def return_racetime_verify():
    user = await discord.fetch_user()
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

    # we need to test if the user has a rtgg_id but no discord_user_id and handle that case
    # this is really ugly and needs to be refactored
    rtgg_user = await models.Users.get_or_none(rtgg_id=rtgg_id)
    discord_user = await models.Users.get_or_none(discord_user_id=user.id)
    if not rtgg_user == discord_user and rtgg_user is not None and discord_user is not None:
        kept_user = await merge_users(rtgg_user, discord_user)
        kept_user.display_name = user.name
        await kept_user.save()
    elif rtgg_user is None:
        await models.Users.update_or_create(discord_user_id=user.id,
                                            defaults={'rtgg_id': userinfo_data['id'], 'rtgg_access_token': token,
                                                      'display_name': user.name})
    else:
        await models.Users.update_or_create(rtgg_id=rtgg_id,
                                            defaults={'discord_user_id': user.id, 'rtgg_access_token': token,
                                                      'display_name': user.name})

    return await render_template('racetime_verified.html', user=user,
                                 racetime_name=userinfo_data['name'])


async def merge_users(user_to_keep: models.Users, victim: models.Users):
    if victim.discord_user_id:
        user_to_keep.discord_user_id = victim.discord_user_id
    if victim.rtgg_id:
        user_to_keep.rtgg_id = victim.rtgg_id

    # update everything to the new user
    # we should be figuring this out dynamically by looking at the models
    await models.AsyncTournamentAuditLog.filter(user=victim).update(user=user_to_keep)
    await models.AsyncTournamentPermissions.filter(user=victim).update(user=user_to_keep)
    await models.AsyncTournamentRace.filter(user=victim).update(user=user_to_keep)
    await models.AsyncTournamentRace.filter(reviewed_by=victim).update(reviewed_by=user_to_keep)
    await models.AsyncTournamentReviewNotes.filter(author=victim).update(author=user_to_keep)

    await victim.delete()
    await user_to_keep.save()

    return user_to_keep

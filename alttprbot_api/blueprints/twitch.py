from quart import Blueprint, redirect, render_template, request, url_for, jsonify
from twitchAPI.oauth import UserAuthenticator, get_user_info
from twitchAPI.types import AuthScope

from alttprbot import models
from alttprbot_twitch.bot import twitchapi

# from ..api import discord

# from quart_discord import requires_authorization


twitch_blueprint = Blueprint('twitch', __name__)

@twitch_blueprint.route('/login', methods=['GET'])
async def login():
    target_scope = [
        AuthScope.CHANNEL_MANAGE_MODERATORS,
        AuthScope.CHANNEL_READ_STREAM_KEY,
        AuthScope.CHANNEL_MANAGE_BROADCAST,
        AuthScope.USER_EDIT_BROADCAST,
        AuthScope.USER_READ_BROADCAST,
        AuthScope.CHANNEL_MODERATE,
        AuthScope.CHANNEL_READ_EDITORS,
        AuthScope.MODERATOR_READ_CHATTERS
    ]
    auth = UserAuthenticator(twitchapi, target_scope, url="http://localhost:5001/twitch/callback", force_verify=False)
    redir = auth.return_auth_url()
    return redirect(redir)

@twitch_blueprint.route('/callback', methods=['GET'])
async def callback():
    auth = UserAuthenticator(twitchapi, [], url="http://localhost:5001/twitch/callback", force_verify=False)
    access_token, refresh_token = await auth.authenticate(user_token=request.args.get('code'))

    user_info = await get_user_info(access_token)

    user_id = user_info['sub']

    return jsonify(user_info)
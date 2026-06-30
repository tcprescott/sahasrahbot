from quart import Blueprint, jsonify, request

from alttprbot.services import UserService
from alttprbot.presentation.web.oauth_client import requires_authorization
from alttprbot.presentation.web.web import discord

profile_blueprint = Blueprint('profile', __name__)


@profile_blueprint.route('/api/me/display-name', methods=['POST'])
@requires_authorization
async def update_display_name():
    user = await discord.fetch_user()
    payload = await request.get_json(force=True) or {}
    display_name = payload.get('display_name', '')

    try:
        new_name = await UserService().set_own_display_name(int(user.id), display_name)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    return jsonify(success=True, display_name=new_name)


@profile_blueprint.route('/api/me/racetime/unlink', methods=['POST'])
@requires_authorization
async def unlink_racetime():
    user = await discord.fetch_user()

    try:
        await UserService().unlink_racetime_account(int(user.id))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    return jsonify(success=True)

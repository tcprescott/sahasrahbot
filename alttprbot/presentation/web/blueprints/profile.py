import logging

from quart import Blueprint, jsonify, request

from alttprbot.services import UserService
from alttprbot.presentation.web.oauth_client import requires_authorization
from alttprbot.presentation.web.web import discord

logger = logging.getLogger(__name__)

profile_blueprint = Blueprint('profile', __name__)


@profile_blueprint.route('/api/me/display-name', methods=['POST'])
@requires_authorization
async def update_display_name():
    user = await discord.fetch_user()
    payload = await request.get_json(force=True) or {}
    display_name = payload.get('display_name') or ''

    service = UserService()
    record = await service.get_or_create_by_discord_id(int(user.id))

    try:
        await service.update_display_name(record, display_name)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    return jsonify(success=True, display_name=record.display_name)


@profile_blueprint.route('/api/me/racetime/unlink', methods=['POST'])
@requires_authorization
async def unlink_racetime():
    user = await discord.fetch_user()

    try:
        await UserService().unlink_racetime_account(int(user.id))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    return jsonify(success=True)

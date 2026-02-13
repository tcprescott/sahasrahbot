import re

from quart import Blueprint, render_template, request, url_for, redirect, session, abort
from alttprbot_api.oauth_client import requires_authorization, Unauthorized

from alttprbot import models
from alttprbot_api.api import discord

user_blueprint = Blueprint('user', __name__)

@user_blueprint.route("/<int:id>")
async def info(id):
    return "Not implemented yet"
    # try:
    #     user = await discord.fetch_user()
    # except Unauthorized:
    #     user = None

    # user = await models.Users.get_or_none(id=id)
    # if user is None:
    #     return abort(404)

    # return await render_template('user/main.html', user=user)
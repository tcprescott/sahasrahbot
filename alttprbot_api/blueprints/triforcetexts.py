import re

from quart import Blueprint, render_template, request, url_for
from quart_discord import requires_authorization

from alttprbot import models

from ..api import discord

triforcetexts_blueprint = Blueprint('triforcetexts', __name__)

@triforcetexts_blueprint.route('/triforcetexts', methods=['GET'])
@requires_authorization
async def triforcetexts():
    user = await discord.fetch_user()
    logged_in = True

    return await render_template('triforce_text.html', logged_in=logged_in, user=user, endpoint=url_for('triforcetexts_submit'))

@triforcetexts_blueprint.route('/triforcetexts/submit', methods=['POST'])
@requires_authorization
async def triforcetexts_submit():
    user = await discord.fetch_user()
    logged_in = True

    payload = await request.form

    regex = re.compile(r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,14}$")

    if not regex.match(payload['first_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the first line.")
    if not regex.match(payload['second_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the second line.")
    if not regex.match(payload['third_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the third line.")

    text = f"{payload['first_line']}\\n{payload['second_line']}\\n{payload['third_line']}"

    await models.TriforceTexts.create(pool_name="alttpr2022", text=text, discord_user_id=user.id, author=f"{user.name}#{user.discriminator}")

    return await render_template('triforce_text_submit.html', logged_in=logged_in, user=user)


import re

from quart import Blueprint, render_template, request, url_for, redirect
from quart_discord import requires_authorization

from alttprbot import models

from ..api import discord

triforcetexts_blueprint = Blueprint('triforcetexts', __name__)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>', methods=['GET'])
@requires_authorization
async def triforcetexts(pool_name):
    user = await discord.fetch_user()
    logged_in = True

    return await render_template('triforce_text.html', logged_in=logged_in, user=user, pool_name=pool_name)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/submit', methods=['POST'])
@requires_authorization
async def submit(pool_name):
    user = await discord.fetch_user()
    logged_in = True

    payload = await request.form

    # TODO: Change 14 to 19 when we get the new font
    regex = re.compile(r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,14}$")

    if not regex.match(payload['first_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the first line.")
    if not regex.match(payload['second_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the second line.")
    if not regex.match(payload['third_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the third line.")

    text = f"{payload['first_line']}\n{payload['second_line']}\n{payload['third_line']}"

    await models.TriforceTexts.create(pool_name=pool_name, text=text, discord_user_id=user.id, author=f"{user.name}#{user.discriminator}")

    return await render_template('triforce_text_submit.html', logged_in=logged_in, user=user)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation', methods=['GET'])
@requires_authorization
async def moderation(pool_name):
    user = await discord.fetch_user()
    logged_in = True

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', logged_in=logged_in, user=user, title="Access Denied", message="You do not have permission to access this page.")

    texts = await models.TriforceTexts.filter(pool_name=pool_name, approved=False)

    return await render_template('triforce_text_moderation.html', logged_in=logged_in, user=user, pool_name=pool_name, texts=texts)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/<int:text_id>/<string:action>', methods=['GET'])
@requires_authorization
async def moderation_action(pool_name, text_id, action):
    user = await discord.fetch_user()
    logged_in = True

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', logged_in=logged_in, user=user, title="Access Denied", message="You do not have permission to access this page.")

    text = await models.TriforceTexts.get(id=text_id)

    if action == 'reject':
        await text.delete()

    if action == 'approve':
        text.approved = True
        await text.save()

    return redirect(url_for('triforcetexts.moderation', pool_name=pool_name))

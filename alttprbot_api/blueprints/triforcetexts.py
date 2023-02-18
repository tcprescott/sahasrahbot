import re

from quart import Blueprint, render_template, request, url_for, redirect
from quart_discord import requires_authorization

from alttprbot import models

from ..api import discord

triforcetexts_blueprint = Blueprint('triforcetexts', __name__)


@triforcetexts_blueprint.route('/triforcetexts/<string:event>', methods=['GET'])
@requires_authorization
async def triforcetexts(event):
    user = await discord.fetch_user()
    logged_in = True

    return await render_template('triforce_text.html', logged_in=logged_in, user=user, endpoint=url_for('triforcetexts.submit', event=event))


@triforcetexts_blueprint.route('/triforcetexts/<string:event>/submit', methods=['POST'])
@requires_authorization
async def submit(event):
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

    await models.TriforceTexts.create(pool_name=event, text=text, discord_user_id=user.id, author=f"{user.name}#{user.discriminator}")

    return await render_template('triforce_text_submit.html', logged_in=logged_in, user=user)


@triforcetexts_blueprint.route('/triforcetexts/<string:event>/moderation', methods=['GET'])
@requires_authorization
async def moderation(event):
    user = await discord.fetch_user()
    logged_in = True

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=event, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', logged_in=logged_in, user=user, title="Access Denied", message="You do not have permission to access this page.")

    texts = await models.TriforceTexts.filter(pool_name=event, approved=False)

    return await render_template('triforce_text_moderation.html', logged_in=logged_in, user=user, event=event, texts=texts)


@triforcetexts_blueprint.route('/triforcetexts/<string:event>/moderation/<int:text_id>/approve', methods=['GET'])
@requires_authorization
async def moderation_approve(event, text_id):
    user = await discord.fetch_user()
    logged_in = True

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=event, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', logged_in=logged_in, user=user, title="Access Denied", message="You do not have permission to access this page.")

    text = await models.TriforceTexts.get(id=text_id)

    text.approved = True

    await text.save()

    return redirect(url_for('triforcetexts.moderation', event=event))


@triforcetexts_blueprint.route('/triforcetexts/<string:event>/moderation/<int:text_id>/reject', methods=['GET'])
@requires_authorization
async def moderation_reject(event, text_id):
    user = await discord.fetch_user()
    logged_in = True

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=event, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', logged_in=logged_in, user=user, title="Access Denied", message="You do not have permission to access this page.")

    text = await models.TriforceTexts.get(id=text_id)

    await text.delete()

    return redirect(url_for('triforcetexts.moderation', event=event))

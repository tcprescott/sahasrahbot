import re

from quart import Blueprint, render_template, request, url_for, redirect, session
from alttprbot_api.oauth_client import requires_authorization, Unauthorized

from alttprbot import models
from alttprbot_api.api import discord

triforcetexts_blueprint = Blueprint('triforcetexts', __name__)


# TODO: generalize this so that it can be used for any pool that requires a key instead of discord login
@triforcetexts_blueprint.route('/triforcetexts/sgl23', methods=['GET'])
async def triforcetexts_sgl23():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None

    pool_name = "sgl23"

    key = request.args.get('key')
    triforce_texts_config = await models.TriforceTextsConfig.get_or_none(pool_name=pool_name, key_name='key')

    if not triforce_texts_config:
        return await render_template('error.html', user=user, title="Invalid key",
                                     message="This pool does not have a valid key set.")

    if key != triforce_texts_config.value:
        return await render_template('error.html', user=user, title="Invalid key",
                                     message="The key supplied is not valid.")

    session['sgl23_triforce_text_authorized'] = True

    return await render_template('triforce_text.html', user=user, pool_name=pool_name,
                                 author_name_field=True)


@triforcetexts_blueprint.route('/triforcetexts/sgl23/submit', methods=['POST'])
async def submit_sgl23():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None

    pool_name = "sgl23"

    if not session.get('sgl23_triforce_text_authorized', False):
        return await render_template('error.html', user=user, title="Invalid key",
                                     message="The key in your session store is not correct.  This should not have happened.")

    payload = await request.form

    regex = re.compile(
        r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$")

    if not regex.match(payload['first_line']):
        return await render_template('error.html', user=user, title="Invalid input.",
                                     message="Invalid text entered for the first line.")
    if not regex.match(payload['second_line']):
        return await render_template('error.html', user=user, title="Invalid input.",
                                     message="Invalid text entered for the second line.")
    if not regex.match(payload['third_line']):
        return await render_template('error.html', user=user, title="Invalid input.",
                                     message="Invalid text entered for the third line.")

    text = f"{payload['first_line']}\n{payload['second_line']}\n{payload['third_line']}"

    await models.TriforceTexts.create(pool_name=pool_name, text=text, discord_user_id=None,
                                      author=payload['author_name'])

    return await render_template('triforce_text_submit.html', user=user)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>', methods=['GET'])
@requires_authorization
async def triforcetexts(pool_name):
    user = await discord.fetch_user()

    return await render_template('triforce_text.html', user=user, pool_name=pool_name)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/submit', methods=['POST'])
@requires_authorization
async def submit(pool_name):
    user = await discord.fetch_user()

    payload = await request.form

    regex = re.compile(
        r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$")

    if not regex.match(payload['first_line']):
        return await render_template('error.html', user=user, title="Invalid input.",
                                     message="Invalid text entered for the first line.")
    if not regex.match(payload['second_line']):
        return await render_template('error.html', user=user, title="Invalid input.",
                                     message="Invalid text entered for the second line.")
    if not regex.match(payload['third_line']):
        return await render_template('error.html', user=user, title="Invalid input.",
                                     message="Invalid text entered for the third line.")

    text = f"{payload['first_line']}\n{payload['second_line']}\n{payload['third_line']}"

    await models.TriforceTexts.create(pool_name=pool_name, text=text, discord_user_id=user.id,
                                      author=f"{user.name}#{user.discriminator}")

    return await render_template('triforce_text_submit.html', user=user)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation', methods=['GET'])
@requires_authorization
async def moderation(pool_name):
    user = await discord.fetch_user()

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', user=user, title="Access Denied",
                                     message="You do not have permission to access this page.")

    filt = {
        'pool_name': pool_name
    }
    approved = request.args.get('approved', 'pending')

    if approved == 'true':
        filt['approved'] = True
    elif approved == 'false':
        filt['approved'] = False
    elif approved == 'pending':
        filt['approved__isnull'] = True

    texts = await models.TriforceTexts.filter(**filt)

    return await render_template('triforce_text_moderation.html', user=user, pool_name=pool_name,
                                 texts=texts)


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/<int:text_id>/<string:action>',
                               methods=['GET'])
@requires_authorization
async def moderation_action(pool_name, text_id, action):
    user = await discord.fetch_user()

    triforce_texts_config = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')

    moderators = [int(x.value) for x in triforce_texts_config]

    if user.id not in moderators:
        return await render_template('error.html', user=user, title="Access Denied",
                                     message="You do not have permission to access this page.")

    text = await models.TriforceTexts.get(id=text_id)

    if action == 'reject':
        text.approved = False
        await text.save()

    if action == 'approve':
        text.approved = True
        await text.save()

    return redirect(url_for('triforcetexts.moderation', pool_name=pool_name))

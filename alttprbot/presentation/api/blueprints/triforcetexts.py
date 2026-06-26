import re

from quart import Blueprint, request, jsonify
from alttprbot.presentation.api.oauth_client import requires_authorization

from alttprbot import models
from alttprbot.presentation.api.api import discord

triforcetexts_blueprint = Blueprint('triforcetexts', __name__)


# ---------------------------------------------------------------------------
# JSON endpoints for the SPA — session auth.
# ---------------------------------------------------------------------------

TRIFORCE_TEXT_REGEX = re.compile(
    r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,19}$")


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/api', methods=['POST'])
@requires_authorization
async def submit_json(pool_name):
    user = await discord.fetch_user()
    payload = await request.get_json(force=True) or {}

    for line_key in ('first_line', 'second_line', 'third_line'):
        val = payload.get(line_key, '')
        if not TRIFORCE_TEXT_REGEX.match(val):
            return jsonify({'error': f'Invalid characters in {line_key}. Max 19 characters from the allowed set.'}), 400

    text = f"{payload.get('first_line', '')}\n{payload.get('second_line', '')}\n{payload.get('third_line', '')}"
    await models.TriforceTexts.create(pool_name=pool_name, text=text, discord_user_id=user.id,
                                      author=f"{user.name}#{user.discriminator}")
    return jsonify({'success': True})


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/api', methods=['GET'])
@requires_authorization
async def moderation_json(pool_name):
    user = await discord.fetch_user()
    config_entries = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')
    moderators = [int(x.value) for x in config_entries]
    if user.id not in moderators:
        return jsonify({'error': 'Access denied.'}), 403

    approved_filter = request.args.get('approved', 'pending')
    filt = {'pool_name': pool_name}
    if approved_filter == 'true':
        filt['approved'] = True
    elif approved_filter == 'false':
        filt['approved'] = False
    elif approved_filter == 'pending':
        filt['approved__isnull'] = True

    texts = await models.TriforceTexts.filter(**filt)
    return jsonify({
        'pool_name': pool_name,
        'filter': approved_filter,
        'texts': [
            {'id': t.id, 'text': t.text, 'author': t.author, 'approved': t.approved}
            for t in texts
        ],
    })


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/api/<int:text_id>', methods=['POST'])
@requires_authorization
async def moderation_action_json(pool_name, text_id):
    user = await discord.fetch_user()
    config_entries = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')
    moderators = [int(x.value) for x in config_entries]
    if user.id not in moderators:
        return jsonify({'error': 'Access denied.'}), 403

    payload = await request.get_json(force=True) or {}
    action = payload.get('action')  # 'approve' or 'reject'
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Invalid action.'}), 400

    text = await models.TriforceTexts.get_or_none(id=text_id)
    if text is None:
        return jsonify({'error': 'Text not found.'}), 404

    text.approved = action == 'approve'
    await text.save()
    return jsonify({'success': True, 'approved': text.approved})

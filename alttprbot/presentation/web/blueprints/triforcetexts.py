from quart import Blueprint, request, jsonify
from alttprbot.presentation.web.oauth_client import requires_authorization

from alttprbot.services import AuthorizationService, AuthSubject, TriforceTextService
from alttprbot.presentation.web.web import discord

triforcetexts_blueprint = Blueprint('triforcetexts', __name__)


# ---------------------------------------------------------------------------
# JSON endpoints for the SPA — session auth.
# ---------------------------------------------------------------------------


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/api', methods=['POST'])
@requires_authorization
async def submit_json(pool_name):
    user = await discord.fetch_user()
    payload = await request.get_json(force=True) or {}

    lines = []
    for line_key in ('first_line', 'second_line', 'third_line'):
        val = payload.get(line_key, '')
        if not TriforceTextService.is_valid_line(val):
            return jsonify({'error': f'Invalid characters in {line_key}. Max 19 characters from the allowed set.'}), 400
        lines.append(val)

    await TriforceTextService().submit(
        pool_name=pool_name,
        lines=lines,
        discord_user_id=user.id,
        author=f"{user.name}#{user.discriminator}",
    )
    return jsonify({'success': True})


@triforcetexts_blueprint.route('/triforcetexts/<string:pool_name>/moderation/api', methods=['GET'])
@requires_authorization
async def moderation_json(pool_name):
    user = await discord.fetch_user()
    service = TriforceTextService()
    if not await AuthorizationService().is_triforce_moderator(AuthSubject(discord_user_id=user.id), pool_name):
        return jsonify({'error': 'Access denied.'}), 403

    approved_filter = request.args.get('approved', 'pending')
    texts = await service.list_texts(pool_name, approved_filter)
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
    service = TriforceTextService()
    if not await AuthorizationService().is_triforce_moderator(AuthSubject(discord_user_id=user.id), pool_name):
        return jsonify({'error': 'Access denied.'}), 403

    payload = await request.get_json(force=True) or {}
    action = payload.get('action')  # 'approve' or 'reject'
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Invalid action.'}), 400

    text = await service.moderate(text_id, approve=action == 'approve')
    if text is None:
        return jsonify({'error': 'Text not found.'}), 404

    return jsonify({'success': True, 'approved': text.approved})

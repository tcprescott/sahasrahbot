import logging

from quart import Blueprint, jsonify, request, session

from alttprbot.presentation.discord.tournament import dispatch as tournament_dispatch
from alttprbot.presentation.web.web import discord

logger = logging.getLogger(__name__)

tournament_blueprint = Blueprint('tournament', __name__)


@tournament_blueprint.route('/api/tournament/submit', methods=['POST'])
async def api_submit():
    token = session.get('discord_oauth_token')
    if not token:
        return jsonify(error="unauthenticated"), 401

    try:
        user = await discord.fetch_user()
    except Exception:
        return jsonify(error="unauthenticated"), 401

    try:
        payload = await request.get_json(force=True)
        if not payload:
            return jsonify(error="Request body must be JSON."), 400

        event = payload.get('event', '').strip()
        episode_id_raw = payload.get('episodeid')

        if not event:
            return jsonify(error="Missing required field: event"), 400
        if episode_id_raw is None:
            return jsonify(error="Missing required field: episodeid"), 400

        episode_id = int(episode_id_raw)

        from werkzeug.datastructures import ImmutableMultiDict
        flat_payload = ImmutableMultiDict(list(payload.items()))

        tournament_race = await tournament_dispatch.fetch_tournament_handler(event, episode_id)
        submitted_by = getattr(user, 'name', str(user)) or "unknown"
        await tournament_race.process_submission_form(flat_payload, submitted_by=submitted_by)
        return jsonify(success=True, versus=tournament_race.versus)
    except (ValueError, TypeError):
        # Log the detail server-side; don't reflect exception internals to the client.
        logger.warning("tournament_submit_invalid_input", exc_info=True)
        return jsonify(error="Invalid submission data provided."), 400
    except Exception:
        logger.exception("tournament_submit_failed")
        return jsonify(error="An error occurred while processing your submission."), 400

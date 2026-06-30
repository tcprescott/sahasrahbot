from quart import Blueprint, jsonify, request, session

from alttprbot.services import TournamentGamesService
from alttprbot.services.tournament import registry as tournament_registry
from alttprbot.presentation.discord.tournament import dispatch as tournament_dispatch
from alttprbot.presentation.api.api import discord

tournament_blueprint = Blueprint('tournament', __name__)


@tournament_blueprint.route('/api/tournament/games', methods=['GET'])
async def get_tournament_games():
    # Only known columns may be filtered on; unknown query params are ignored
    # (previously any param was forwarded straight into the ORM filter).
    data = await TournamentGamesService().search(dict(request.args))
    return jsonify(data)


@tournament_blueprint.route('/api/tournament/form-config/<string:event>', methods=['GET'])
async def get_form_config(event):
    if event not in tournament_registry.TOURNAMENT_DATA:
        return jsonify(error=f"Unknown event: {event}"), 404

    event_config = await tournament_dispatch.get_config(event)
    form_data = event_config.submission_form

    if form_data is None:
        return jsonify(error="There is no submission form configured for this event."), 422

    # Custom HTML template events (form_data is a string template name) are not
    # supported by the JSON API — those events still use the server-rendered path.
    if isinstance(form_data, str):
        return jsonify(error="This event uses a custom submission form. Please use the legacy form URL."), 422

    return jsonify(settings=form_data)


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
    except (ValueError, TypeError) as e:
        return jsonify(error=f"Invalid input: {e}"), 400
    except Exception as e:
        return jsonify(error=f"Error processing submission: {e}"), 400

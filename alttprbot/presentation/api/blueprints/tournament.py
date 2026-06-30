import logging

from quart import Blueprint, jsonify, request

from alttprbot.services import TournamentGamesService
from alttprbot.services.tournament import registry as tournament_registry
from alttprbot.presentation.discord.tournament import dispatch as tournament_dispatch

logger = logging.getLogger(__name__)

tournament_blueprint = Blueprint('tournament_api', __name__)


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

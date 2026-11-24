from quart import Blueprint, jsonify, request

from alttprbot import models

tournament_blueprint = Blueprint('tournament', __name__)


@tournament_blueprint.route('/api/tournament/games', methods=['GET'])
async def get_tournament_games():
    terms = request.args
    data = await models.TournamentGames.filter(**terms).values()
    return jsonify(data)

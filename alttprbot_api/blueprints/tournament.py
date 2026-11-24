from quart import Blueprint, jsonify, request

from alttprbot.services import tournament_games

tournament_blueprint = Blueprint('tournament', __name__)


# Unauthenticated, and the query string goes straight to the database filter, as it
# always has. Left as is on purpose; see the PR that moved this into a service.
@tournament_blueprint.route('/api/tournament/games', methods=['GET'])
async def get_tournament_games():
    terms = request.args
    data = await tournament_games.search(terms)
    return jsonify(data)

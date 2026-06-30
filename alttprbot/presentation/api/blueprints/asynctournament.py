from quart import (Blueprint, abort, jsonify, request, Response)

from alttprbot.services import AsyncTournamentScoringService, AsyncTournamentService
from alttprbot.presentation.api import auth

asynctournament_blueprint = Blueprint('async_api', __name__)


@asynctournament_blueprint.route('/api/tournaments', methods=['GET'])
@auth.authorized_key('asynctournament')
async def tournaments_api():
    active = None
    if request.args.get('active'):
        active = request.args.get('active') == 'true'

    res = await AsyncTournamentService().tournaments_json(active)
    return Response(res, mimetype='application/json')


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def tournament_api(tournament_id):
    res = await AsyncTournamentService().tournament_json(tournament_id)
    if res is None:
        return jsonify({'error': 'Tournament not found.'})

    return Response(res, mimetype='application/json')


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/races', methods=['GET'])
@auth.authorized_key('asynctournament')
async def races_api(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('user_id'):
        filter_args['user_id'] = request.args.get('user_id')
    if request.args.get('permalink_id'):
        filter_args['permalink_id'] = request.args.get('permalink_id')
    if request.args.get('pool_id'):
        filter_args['permalink__pool_id'] = request.args.get('pool_id')
    if request.args.get('status'):
        filter_args['status'] = request.args.get('status')

    if request.args.get('page'):
        page = int(request.args.get('page'))
        if page < 1 or page > 100000:
            return abort(400, 'page must be between 1 and 100000.')
    else:
        page = 1

    if request.args.get('page_size'):
        page_size = int(request.args.get('page_size'))
        if page_size > 100:
            return abort(400, 'page_size cannot be greater than 100.')
    else:
        page_size = 20

    res = await AsyncTournamentService().races_json(tournament_id, filter_args, page, page_size)
    return Response(res, mimetype='application/json')


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/pools', methods=['GET'])
@auth.authorized_key('asynctournament')
async def pools_api(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')

    res = await AsyncTournamentService().pools_json(tournament_id, filter_args)
    return Response(res, mimetype='application/json')


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/permalinks', methods=['GET'])
@auth.authorized_key('asynctournament')
async def permalinks_api(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('pool_id'):
        filter_args['pool_id'] = request.args.get('pool_id')

    res = await AsyncTournamentService().permalinks_json(tournament_id, filter_args)
    return Response(res, mimetype='application/json')


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/leaderboard', methods=['GET'])
@auth.authorized_key('asynctournament')
async def leaderboard_api(tournament_id):
    tournament = await AsyncTournamentService().get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'})

    leaderboard = await AsyncTournamentScoringService().get_leaderboard(tournament)

    return jsonify([
        {
            'player': {
                'id': e.player.id,
                'display_name': e.player.display_name,
                'discord_user_id': e.player.discord_user_id,
                'twitch_name': e.player.twitch_name,
                'rtgg_id': e.player.rtgg_id,
            },
            'score': e.score,
            'rank': idx + 1,
            'races': [
                {
                    'id': race.id,
                    'start_time': race.start_time,
                    'end_time': race.end_time,
                    'score': race.score,
                    'permalink_id': race.permalink_id,
                    'elapsed_time': race.elapsed_time_formatted,
                    'status': race.status,
                } if race else None
                for race in e.races
            ],
            'counts': {
                'finished': e.finished_race_count,
                'forfeited': e.forfeited_race_count,
                'unplayed': e.unattempted_race_count,
            }
        }
        for idx, e in enumerate(leaderboard)
    ])

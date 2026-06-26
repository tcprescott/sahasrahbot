from quart import (Blueprint, abort, jsonify, request, Response)
from alttprbot.presentation.api.oauth_client import Unauthorized

from alttprbot.services import AsyncTournamentService, UserService
from alttprbot.util import asynctournament
from alttprbot.presentation.api import auth
from alttprbot.presentation.api.api import discord
from alttprbot.presentation.api.util import checks

asynctournament_blueprint = Blueprint('async', __name__)


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

    leaderboard = await asynctournament.get_leaderboard(tournament)

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

# ---------------------------------------------------------------------------
# Public JSON endpoints for the SPA — session auth, same access rules as
# the Jinja template routes (public when tournament is inactive, admin/mod only
# when active).
# ---------------------------------------------------------------------------

@asynctournament_blueprint.route('/races/<int:tournament_id>/info', methods=['GET'])
async def async_tournament_info_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await UserService().get_by_discord_id(discord_user.id)

    tournament = await AsyncTournamentService().get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized and tournament.active:
        return jsonify({'error': 'Not authorized.'}), 403

    return jsonify({
        'id': tournament.id,
        'name': tournament.name,
        'active': tournament.active,
        'runs_per_pool': tournament.runs_per_pool,
    })


@asynctournament_blueprint.route('/races/<int:tournament_id>/leaderboard.json', methods=['GET'])
async def async_tournament_leaderboard_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await UserService().get_by_discord_id(discord_user.id)

    tournament = await AsyncTournamentService().get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized and tournament.active:
        return jsonify({'error': 'Not authorized.'}), 403

    leaderboard = await asynctournament.get_leaderboard(tournament)

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
            },
        }
        for idx, e in enumerate(leaderboard)
    ])



@asynctournament_blueprint.route('/races/<int:tournament_id>/dashboard.json', methods=['GET'])
async def async_tournament_dashboard_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await UserService().get_by_discord_id(discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    races = await service.list_user_races(user, tournament)

    reattempted = any(r.reattempted for r in races)

    return jsonify({
        'tournament': {
            'id': tournament.id,
            'name': tournament.name,
            'active': tournament.active,
            'allowed_reattempts': tournament.allowed_reattempts,
            'runs_per_pool': tournament.runs_per_pool,
        },
        'player': {
            'id': user.id,
            'display_name': user.display_name,
        },
        'races': [
            {
                'id': race.id,
                'status': race.status,
                'review_status': race.review_status,
                'created': race.created.isoformat() if race.created is not None else None,
                'start_time': race.start_time.isoformat() if race.start_time is not None else None,
                'end_time': race.end_time.isoformat() if race.end_time is not None else None,
                'elapsed_time': race.elapsed_time_formatted,
                'reattempted': race.reattempted,
                'reattempt_reason': race.reattempt_reason,
                'runner_notes': race.runner_notes,
                'runner_vod_url': race.runner_vod_url,
                'score': race.score,
                'score_formatted': race.score_formatted,
                'reviewer_notes': race.reviewer_notes,
                'pool_name': race.permalink.pool.name,
                'permalink_url': race.permalink.url,
                'permalink_notes': race.permalink.notes,
                'permalink_live_race': race.permalink.live_race,
            }
            for race in races
        ],
        'reattempted': reattempted,
    })



@asynctournament_blueprint.route('/races/<int:tournament_id>/reattempt.json', methods=['GET'])
async def async_tournament_reattempt_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await UserService().get_by_discord_id(discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    race_id = request.args.get('race_id', None)
    if race_id is None:
        return jsonify({'error': 'race_id is required.'}), 400

    reattempted_races = await service.list_reattempted_races(user, tournament)
    if reattempted_races:
        return jsonify({'error': 'You have already reattempted a race in this tournament.'}), 403

    race = await service.get_user_race_with_pool(int(race_id), user, tournament)
    if race is None:
        return jsonify({'error': 'Race not found or you are not the player.'}), 403

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'race': {
            'id': race.id,
            'status': race.status,
            'elapsed_time': race.elapsed_time_formatted,
            'pool_name': race.permalink.pool.name,
            'permalink_url': race.permalink.url,
        },
    })


@asynctournament_blueprint.route('/races/<int:tournament_id>/reattempt.json', methods=['POST'])
async def async_tournament_reattempt_submit_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await UserService().get_by_discord_id(discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    reattempted_races = await service.list_reattempted_races(user, tournament)
    if reattempted_races:
        return jsonify({'error': 'You have already reattempted a race in this tournament.'}), 403

    payload = await request.get_json(force=True) or {}
    race_id = payload.get('race_id')
    reason = payload.get('reason', '')

    if not race_id:
        return jsonify({'error': 'race_id is required.'}), 400

    race = await service.get_user_race(int(race_id), user, tournament)
    if race is None:
        return jsonify({'error': 'Race not found or you are not the player.'}), 403

    await service.submit_reattempt(race, reason)

    return jsonify({'success': True})


@asynctournament_blueprint.route('/races/<int:tournament_id>/queue.json', methods=['GET'])
async def async_tournament_queue_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await UserService().get_by_discord_id(discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return jsonify({'error': 'Not authorized.'}), 403

    page = int(request.args.get('page', 1))
    page_size = 20
    request_filter = {}

    status = request.args.get('status', 'finished')
    if status != 'all':
        request_filter['status'] = status

    reviewer = request.args.get('reviewed', 'all')
    if reviewer == 'unreviewed':
        request_filter['reviewed_by'] = None
    elif reviewer == 'me':
        request_filter['reviewed_by'] = user
    elif reviewer != 'all':
        try:
            request_filter['reviewed_by_id'] = int(reviewer)
        except ValueError:
            pass

    review_status = request.args.get('review_status', 'pending')
    if review_status != 'all':
        request_filter['review_status'] = review_status

    live = request.args.get('live', 'false')
    if live != 'all':
        request_filter['thread_id__isnull'] = live == 'true'

    races = await service.list_queue_races(tournament, request_filter, page, page_size)

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'races': [
            {
                'id': race.id,
                'status': race.status,
                'review_status': race.review_status,
                'elapsed_time': race.elapsed_time_formatted,
                'score_formatted': race.score_formatted,
                'created': race.created.isoformat() if race.created else None,
                'pool_name': race.permalink.pool.name,
                'permalink_url': race.permalink.url,
                'user_id': race.user.id,
                'user_display_name': race.user.display_name,
                'reviewed_by_name': race.reviewed_by.display_name if race.reviewed_by else None,
                'runner_vod_url': race.runner_vod_url,
            }
            for race in races
        ],
        'page': page,
        'page_size': page_size,
        'filters': {'status': status, 'reviewed': reviewer, 'review_status': review_status, 'live': live},
    })


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>/data.json', methods=['GET'])
async def async_tournament_review_json(tournament_id: int, race_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await UserService().get_by_discord_id(discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return jsonify({'error': 'Not authorized.'}), 403

    race = await service.get_race_for_review(race_id, tournament)
    if race is None:
        return jsonify({'error': 'Race not found.'}), 404

    reviewable = race.status == 'finished' and not race.reattempted

    # Auto-claim for review (same as the legacy Jinja route)
    if race.reviewed_by is None and reviewable:
        await service.claim_for_review(race, user)

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name},
        'race': {
            'id': race.id,
            'status': race.status,
            'review_status': race.review_status,
            'elapsed_time': race.elapsed_time_formatted,
            'score_formatted': race.score_formatted,
            'created': race.created.isoformat() if race.created else None,
            'start_time': race.start_time.isoformat() if race.start_time else None,
            'end_time': race.end_time.isoformat() if race.end_time else None,
            'runner_notes': race.runner_notes,
            'runner_vod_url': race.runner_vod_url,
            'run_collection_rate': race.run_collection_rate,
            'run_igt': race.run_igt,
            'reattempted': race.reattempted,
            'reviewer_notes': race.reviewer_notes,
            'reviewed_by_name': race.reviewed_by.display_name if race.reviewed_by else None,
            'reviewed_at': race.reviewed_at.isoformat() if race.reviewed_at else None,
            'pool_name': race.permalink.pool.name,
            'permalink_url': race.permalink.url,
            'permalink_notes': race.permalink.notes,
            'user_id': race.user.id,
            'user_display_name': race.user.display_name,
        },
        'reviewable': reviewable,
        'already_claimed': race.reviewed_by is not None and race.reviewed_by.id != user.id,
        'reviewer_is_self': race.user.id == user.id,
    })


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>/submit.json', methods=['POST'])
async def async_tournament_review_submit_json(tournament_id: int, race_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        return jsonify({'error': 'Authentication required.'}), 401

    user = await UserService().get_by_discord_id(discord_user.id)
    if user is None:
        return jsonify({'error': 'Authentication required.'}), 401

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return jsonify({'error': 'Not authorized.'}), 403

    race = await service.get_race(race_id, tournament)
    if race is None:
        return jsonify({'error': 'Race not found.'}), 404

    if race.status != 'finished':
        return jsonify({'error': 'Race is not finished.'}), 400

    if race.reattempted:
        return jsonify({'error': 'Race was reattempted.'}), 400

    await race.fetch_related('user')
    if race.user.id == user.id:
        return jsonify({'error': 'Cannot review your own run.'}), 403

    payload = await request.get_json(force=True) or {}
    await service.submit_review(
        race,
        review_status=payload.get('review_status', 'pending'),
        reviewer_notes=payload.get('reviewer_notes', None),
        reviewer=user,
    )

    return jsonify({'success': True})


@asynctournament_blueprint.route('/pools/<int:tournament_id>/data.json', methods=['GET'])
async def async_tournament_pools_json(tournament_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await UserService().get_by_discord_id(discord_user.id)

    tournament = await AsyncTournamentService().get_tournament_with_pools(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod', 'public'])
    if not authorized and tournament.active:
        return jsonify({'error': 'Not authorized.'}), 403

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'pools': [
            {
                'id': pool.id,
                'name': pool.name,
                'preset': pool.preset,
                'permalinks': [
                    {
                        'id': p.id,
                        'url': p.url,
                        'notes': p.notes,
                        'par_time': p.par_time_formatted if p.par_time else None,
                        'live_race': p.live_race,
                    }
                    for p in pool.permalinks
                ],
            }
            for pool in tournament.permalink_pools
        ],
    })


@asynctournament_blueprint.route('/permalink/<int:tournament_id>/<int:permalink_id>/data.json', methods=['GET'])
async def async_tournament_permalink_json(tournament_id: int, permalink_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await UserService().get_by_discord_id(discord_user.id)

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    permalink = await service.get_permalink(permalink_id, tournament)
    if permalink is None:
        return jsonify({'error': 'Permalink not found.'}), 404

    if not permalink.live_race:
        authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod', 'public'])
        if not authorized and tournament.active:
            return jsonify({'error': 'Not authorized.'}), 403

    races = await service.list_permalink_races(permalink)

    return jsonify({
        'tournament': {'id': tournament.id, 'name': tournament.name, 'active': tournament.active},
        'permalink': {
            'id': permalink.id,
            'url': permalink.url,
            'notes': permalink.notes,
            'par_time': permalink.par_time_formatted if permalink.par_time else None,
            'live_race': permalink.live_race,
            'pool_name': permalink.pool.name,
        },
        'races': [
            {
                'id': race.id,
                'status': race.status,
                'elapsed_time': race.elapsed_time_formatted,
                'score_formatted': race.score_formatted,
                'review_status': race.review_status,
            }
            for race in races
        ],
    })


@asynctournament_blueprint.route('/player/<int:tournament_id>/<int:user_id>/data.json', methods=['GET'])
async def async_tournament_player_json(tournament_id: int, user_id: int):
    try:
        discord_user = await discord.fetch_user()
    except Unauthorized:
        discord_user = None

    user = None
    if discord_user:
        user = await UserService().get_by_discord_id(discord_user.id)

    service = AsyncTournamentService()
    tournament = await service.get_tournament(tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'}), 404

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod', 'public'])
    if not authorized and tournament.active:
        return jsonify({'error': 'Not authorized.'}), 403

    player = await UserService().get_by_id(user_id)
    if player is None:
        return jsonify({'error': 'Player not found.'}), 404

    races = await service.list_tournament_user_races(tournament, user_id)

    return jsonify({
        'tournament': {
            'id': tournament.id,
            'name': tournament.name,
            'active': tournament.active,
            'runs_per_pool': tournament.runs_per_pool,
        },
        'player': {
            'id': player.id,
            'display_name': player.display_name,
        },
        'races': [
            {
                'id': race.id,
                'status': race.status,
                'review_status': race.review_status,
                'created': race.created.isoformat() if race.created is not None else None,
                'start_time': race.start_time.isoformat() if race.start_time is not None else None,
                'end_time': race.end_time.isoformat() if race.end_time is not None else None,
                'elapsed_time': race.elapsed_time_formatted,
                'reattempted': race.reattempted,
                'score': race.score,
                'score_formatted': race.score_formatted,
                'pool_name': race.permalink.pool.name,
                'permalink_url': race.permalink.url,
                'permalink_notes': race.permalink.notes,
                'permalink_live_race': race.permalink.live_race,
            }
            for race in races
        ],
    })

import datetime

import tortoise.exceptions
from quart import (Blueprint, abort, jsonify, redirect,
                   render_template, request, url_for)
from quart_discord import requires_authorization

from alttprbot import models
from alttprbot.util import asynctournament
from alttprbot_api import auth
from alttprbot_api.util import checks

from ..api import discord

asynctournament_blueprint = Blueprint('async', __name__)


@asynctournament_blueprint.route('/api/tournaments', methods=['GET'])
@auth.authorized_key('asynctournament')
async def tournaments_api():
    filter_args = {}
    if request.args.get('active'):
        filter_args['active'] = request.args.get('active') == 'true'

    result = await models.AsyncTournament.filter(**filter_args)
    return jsonify([asynctournament_to_dict(t) for t in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def tournament_api(tournament_id):
    result = await models.AsyncTournament.get_or_none(id=tournament_id)
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    return jsonify(asynctournament_to_dict(result))


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/races', methods=['GET'])
@auth.authorized_key('asynctournament')
async def races_api(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('discord_user_id'):
        filter_args['discord_user_id'] = request.args.get('discord_user_id')
    if request.args.get('permalink_id'):
        filter_args['permalink_id'] = request.args.get('permalink_id')
    if request.args.get('pool_id'):
        filter_args['permalink__pool_id'] = request.args.get('pool_id')
    if request.args.get('pool_name'):
        filter_args['permalink__pool__name'] = request.args.get('pool_name')
    if request.args.get('status'):
        filter_args['status'] = request.args.get('status')

    result = await models.AsyncTournamentRace.filter(tournament_id=tournament_id, **filter_args).prefetch_related('tournament', 'user', 'permalink', 'permalink__pool')
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    # figure out how to also return the permalink and tournament data
    return jsonify([asynctournamentrace_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/pools', methods=['GET'])
@auth.authorized_key('asynctournament')
async def pools_api(tournament_id):
    result = await models.AsyncTournamentPermalinkPool.filter(tournament_id=tournament_id).prefetch_related('tournament')
    if result is None:
        return jsonify({'error': 'No pools found.'})

    return jsonify([asynctournamentpermalinkpool_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/pools/<int:pool_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def pool_api(tournament_id, pool_id):
    result = await models.AsyncTournamentPermalinkPool.get_or_none(tournament_id=tournament_id, id=pool_id)
    if result is None:
        return jsonify({'error': 'Pool not found.'})

    return jsonify(asynctournamentpermalinkpool_to_dict(result))


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/permalinks', methods=['GET'])
@auth.authorized_key('asynctournament')
async def permalinks_api(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('permalink'):
        filter_args['permalink'] = request.args.get('permalink')
    if request.args.get('pool_id'):
        filter_args['pool_id'] = request.args.get('pool_id')

    result = await models.AsyncTournamentPermalink.filter(pool__tournament_id=tournament_id, **filter_args).prefetch_related('pool')
    if result is None:
        return jsonify({'error': 'No permalinks found.'})

    return jsonify([asynctournamentpermalink_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/permalinks/<int:permalink_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def permalink_api(tournament_id, permalink_id):
    result = await models.AsyncTournamentPermalink.get_or_none(pool__tournament_id=tournament_id, id=permalink_id)
    if result is None:
        return jsonify({'error': 'Permalink not found.'})

    return jsonify(asynctournamentpermalink_to_dict(result))


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/whitelist', methods=['GET'])
@auth.authorized_key('asynctournament')
async def whitelist_api(tournament_id):
    result = await models.AsyncTournamentWhitelist.filter(tournament_id=tournament_id).prefetch_related('tournament')
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    return jsonify([asynctournamentwhitelist_to_dict(r) for r in result])


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/leaderboard', methods=['GET'])
@auth.authorized_key('asynctournament')
async def leaderboard_api(tournament_id):
    tournament = await models.AsyncTournament.get_or_none(id=tournament_id)
    if tournament is None:
        return jsonify({'error': 'Tournament not found.'})

    leaderboard = await asynctournament.get_leaderboard(tournament)

    return jsonify([
        {
            'player': users_to_dict(e.player),
            'score': e.score,
            'rank': idx + 1,
            'races': [asynctournamentrace_to_dict(race) for race in e.races]
        }
        for idx, e in enumerate(leaderboard)
    ])


@asynctournament_blueprint.route('/races/<int:tournament_id>', methods=['GET'])
@requires_authorization
async def async_tournament_queue(tournament_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    page = int(request.args.get('page', 1))
    page_size = 20

    request_filter = {}

    if not (status := request.args.get('status', 'finished')) == 'all':
        request_filter['status'] = status

    if not (reviewer := request.args.get('reviewed', 'all')) == 'all':
        if reviewer == 'unreviewed':
            request_filter['reviewed_by'] = None
        elif reviewer == 'me':
            request_filter['reviewed_by'] = user
        else:
            try:
                request_filter['reviewed_by_id'] = int(reviewer)
            except ValueError:
                pass

    if not (review_status := request.args.get('review_status', 'pending')) == 'all':
        request_filter['review_status'] = review_status

    if not (live := request.args.get('live', 'false')) == 'all':
        request_filter['thread_id__isnull'] = live == 'true'

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    races = await tournament.races.filter(reattempted=False, **request_filter).offset((page-1)*page_size).limit(page_size).prefetch_related('user', 'reviewed_by', 'permalink', 'permalink__pool', 'tournament')

    return await render_template(
        'asynctournament_race_list.html',
        logged_in=True,
        user=discord_user,
        tournament=tournament,
        races=races,
        status=status,
        reviewer=reviewer,
        review_status=review_status,
        live=live,
        page=page
    )


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>', methods=['GET'])
@requires_authorization
async def async_tournament_review(tournament_id: int, race_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        abort(404, "Race not found.")

    if race.status != 'finished':
        abort(403, "This race cannot be reviewed yet.")

    if race.reattempted:
        abort(403, "This race was marked as reattempted and cannot be reviewed.")

    await race.fetch_related('user', 'reviewed_by', 'permalink', 'permalink__pool')

    # if race.user == user:
    #     abort(403, "You are not authorized to review your own tournament run.")

    if race.reviewed_by is None:
        race.reviewed_by = user
        await race.save()

    return await render_template('asynctournament_race_view.html', logged_in=True, user=discord_user, tournament=tournament, race=race, already_claimed=race.reviewed_by != user)


@asynctournament_blueprint.route('/races/<int:tournament_id>/review/<int:race_id>', methods=['POST'])
@requires_authorization
async def async_tournament_review_submit(tournament_id: int, race_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    race = await models.AsyncTournamentRace.get_or_none(id=race_id, tournament=tournament)
    if race is None:
        abort(404, "Race not found.")

    if race.status != 'finished':
        abort(403, "This race cannot be reviewed yet.")

    if race.reattempted:
        abort(403, "This race was marked as reattempted and cannot be reviewed.")

    if race.user == user:
        abort(403, "You are not authorized to review your own tournament run.")

    payload = await request.form

    race.review_status = payload.get('review_status', 'pending')
    race.reviewer_notes = payload.get('reviewer_notes', None)
    race.reviewed_at = datetime.datetime.now()
    race.reviewed_by = user

    await race.save()

    return redirect(url_for("async.async_tournament_queue", tournament_id=tournament_id))


@asynctournament_blueprint.route('/races/<int:tournament_id>/leaderboard', methods=['GET'])
@requires_authorization
async def async_tournament_leaderboard(tournament_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    leaderboard = await asynctournament.get_leaderboard(tournament)

    return await render_template('asynctournament_leaderboard.html', logged_in=True, user=discord_user, tournament=tournament, leaderboard=leaderboard)


@asynctournament_blueprint.route('/player/<int:tournament_id>/<int:user_id>', methods=['GET'])
@requires_authorization
async def async_tournament_player(tournament_id: int, user_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    player = await models.Users.get_or_none(id=user_id)
    races = await models.AsyncTournamentRace.filter(tournament=tournament, user_id=user_id).order_by('-created').prefetch_related('tournament', 'user', 'permalink', 'permalink__pool')

    return await render_template('asynctournament_user.html', logged_in=True, user=discord_user, races=races, tournament=tournament, player=player)

@asynctournament_blueprint.route('/pools/<int:tournament_id>', methods=['GET'])
@requires_authorization
async def async_tournament_pools(tournament_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    await tournament.fetch_related('permalink_pools', 'permalink_pools__permalinks')

    return await render_template('asynctournament_pools.html', logged_in=True, user=discord_user, tournament=tournament)

@asynctournament_blueprint.route('/permalink/<int:tournament_id>/<int:permalink_id>', methods=['GET'])
@requires_authorization
async def async_tournament_permalink(tournament_id: int, permalink_id: int):
    discord_user = await discord.fetch_user()
    user = await models.Users.get_or_none(discord_user_id=discord_user.id)

    tournament = await models.AsyncTournament.get(id=tournament_id)

    authorized = await checks.is_async_tournament_user(user, tournament, ['admin', 'mod'])
    if not authorized:
        return abort(403, "You are not authorized to view this tournament.")

    permalink = await models.AsyncTournamentPermalink.get(id=permalink_id, pool__tournament=tournament).prefetch_related('races', 'races__live_race')

    return await render_template('asynctournament_permalink_view.html', logged_in=True, user=discord_user, tournament=tournament, permalink=permalink)

def asynctournament_to_dict(at: models.AsyncTournament):
    try:
        return {
            'id': at.id,
            'name': at.name,
            'active': at.active,
            'created': at.created,
            'updated': at.updated,
            'guild_id': at.guild_id,
            'channel_id': at.channel_id,
            'owner_id': at.owner_id,
            'allowed_reattempts': at.allowed_reattempts,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentwhitelist_to_dict(asynctournamentwhitelist: models.AsyncTournamentWhitelist):
    try:
        return {
            'id': asynctournamentwhitelist.id,
            'tournament': asynctournament_to_dict(asynctournamentwhitelist.tournament),
            'user': users_to_dict(asynctournamentwhitelist.user),
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentpermalink_to_dict(asynctournamentpermalink: models.AsyncTournamentPermalink):
    try:
        return {
            'id': asynctournamentpermalink.id,
            'permalink': asynctournamentpermalink.url,
            'pool': asynctournamentpermalinkpool_to_dict(asynctournamentpermalink.pool),
            'live_race': asynctournamentpermalink.live_race
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentpermalinkpool_to_dict(asynctournamentpermalinkpool: models.AsyncTournamentPermalinkPool):
    try:
        return {
            'id': asynctournamentpermalinkpool.id,
            'tournament': asynctournament_to_dict(asynctournamentpermalinkpool.tournament),
            'name': asynctournamentpermalinkpool.name,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def asynctournamentrace_to_dict(asynctournamentrace: models.AsyncTournamentRace):
    try:
        return {
            'id': asynctournamentrace.id,
            'tournament': asynctournament_to_dict(asynctournamentrace.tournament),
            'permalink': asynctournamentpermalink_to_dict(asynctournamentrace.permalink),
            'user': users_to_dict(asynctournamentrace.user),
            'thread_id': asynctournamentrace.thread_id,
            'thread_open_time': asynctournamentrace.thread_open_time,
            'thread_timeout_time': asynctournamentrace.thread_timeout_time,
            'start_time': asynctournamentrace.start_time,
            'end_time': asynctournamentrace.end_time,
            'elapsed_time': asynctournamentrace.elapsed_time,  # calculated
            'status': asynctournamentrace.status,
            'live_race': asynctournamentrace.live_race,  # TODO: translate to dictionary
            'reattempted': asynctournamentrace.reattempted,
            'runner_notes': asynctournamentrace.runner_notes_html,
            'runner_vod_url': asynctournamentrace.runner_vod_url,
            'review_status': asynctournamentrace.review_status,
            'reviewed_by': users_to_dict(asynctournamentrace.reviewed_by),
            'reviewed_at': asynctournamentrace.reviewed_at,
            'reviewer_notes': asynctournamentrace.reviewer_notes,
            'score': asynctournamentrace.score,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None


def users_to_dict(user: models.Users):
    try:
        return {
            'id': user.id,
            'discord_user_id': user.discord_user_id,
            'display_name': user.display_name,
            'rtgg_id': user.rtgg_id,
        }
    except AttributeError:
        return None
    except tortoise.exceptions.NoValuesFetched:
        return None

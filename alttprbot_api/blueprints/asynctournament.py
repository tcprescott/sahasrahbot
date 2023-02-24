from quart import Blueprint, jsonify, redirect, render_template, request, send_file, url_for, Response

from alttprbot import models
from alttprbot_api import auth

from ..api import discord

asynctournament_blueprint = Blueprint('async', __name__)


@asynctournament_blueprint.route('/api/tournaments', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournaments():
    filter_args = {}
    if request.args.get('active'):
        filter_args['active'] = request.args.get('active') == 'true'

    result = await models.AsyncTournament.filter(**filter_args).values()
    return jsonify(result)


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_by_id(tournament_id):
    result = await models.AsyncTournament.get_or_none(id=tournament_id).values()
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    return jsonify(result)


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/races', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_races(tournament_id):
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

    result = await models.AsyncTournamentRace.filter(tournament_id=tournament_id, **filter_args).prefetch_related('tournament', 'permalink').values()
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    # figure out how to also return the permalink and tournament data
    return jsonify(result)


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/pools', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_pools(tournament_id):
    result = await models.AsyncTournamentPermalinkPool.filter(tournament_id=tournament_id).prefetch_related('tournament').values()
    if result is None:
        return jsonify({'error': 'No pools found.'})

    return jsonify(result)


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/permalinks', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_permalinks(tournament_id):
    filter_args = {}
    if request.args.get('id'):
        filter_args['id'] = request.args.get('id')
    if request.args.get('permalink'):
        filter_args['permalink'] = request.args.get('permalink')
    if request.args.get('pool_id'):
        filter_args['pool_id'] = request.args.get('pool_id')

    result = await models.AsyncTournamentPermalink.filter(pool__tournament_id=tournament_id, **filter_args).prefetch_related('pool').values()
    if result is None:
        return jsonify({'error': 'No permalinks found.'})

    return jsonify(result)


@asynctournament_blueprint.route('/api/tournaments/<int:tournament_id>/whitelist', methods=['GET'])
@auth.authorized_key('asynctournament')
async def async_tournament_whitelist(tournament_id):
    result = await models.AsyncTournamentWhitelist.filter(tournament_id=tournament_id).prefetch_related('tournament').values()
    if result is None:
        return jsonify({'error': 'Tournament not found.'})

    return jsonify(result)

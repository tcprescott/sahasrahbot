import os

from quart import Quart, abort, jsonify, request

from alttprbot.alttprgen.mystery import get_weights, generate
from alttprbot.tournament import league, alttpr
from alttprbot.database import league_playoffs
from alttprbot_discord.bot import discordbot
from alttprbot_srl.bot import srlbot

sahasrahbotapi = Quart(__name__)


@sahasrahbotapi.route('/api/settingsgen/mystery', methods=['POST'])
async def mysterygen():
    weights = await request.get_json()
    settings, customizer, doors = await generate(weights=weights, spoilers="mystery")
    if customizer:
        endpoint = '/api/customizer'
    elif doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'
    return jsonify(
        settings=settings,
        customizer=customizer,
        doors=doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route('/api/settingsgen/mystery/<string:weightset>', methods=['GET'])
async def mysterygenwithweights(weightset):
    weights = await get_weights(weightset)
    settings, customizer, doors = await generate(weights=weights, spoilers="mystery")
    if customizer:
        endpoint = '/api/customizer'
    elif doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'
    return jsonify(
        settings=settings,
        customizer=customizer,
        doors=doors,
        endpoint=endpoint
    )


# @sahasrahbotapi.route('/api/sgl/episodes', methods=['GET'])
# async def sgl_episodes():
#     secret = request.args.get("secret")
#     if not secret == os.environ.get('SGL_DATA_ENDPOINT_SECRET'):
#         abort(401, description="secret required")

#     result = await sgl2020_tournament.get_all_tournament_races()
#     return jsonify(results=result)


# @sahasrahbotapi.route('/api/sgl/episode/<int:episode>', methods=['GET'])
# async def sgl_episode(episode):
#     secret = request.args.get("secret")
#     if not secret == os.environ.get('SGL_DATA_ENDPOINT_SECRET'):
#         abort(401, description="secret required")

#     result = await sgl2020_tournament.get_tournament_race_by_episodeid(episode)
#     return jsonify(result=result)


@sahasrahbotapi.route('/api/league/playoff', methods=['POST'])
async def league_playoff():
    payload = await request.get_json()

    if not payload['secret'] == os.environ.get('LEAGUE_DATA_ENDPOINT_SECRET'):
        abort(401, description="secret required")

    await league.process_playoff_form(payload['form'])

    return jsonify(success=True)


@sahasrahbotapi.route('/api/alttprde/settings', methods=['POST'])
async def alttprde_settings():
    payload = await request.get_json()

    if not payload['secret'] == os.environ.get('LEAGUE_DATA_ENDPOINT_SECRET'):
        abort(401, description="secret required")

    await alttpr.alttprde_process_settings_form(payload['form'])

    return jsonify(success=True)


@sahasrahbotapi.route('/api/league/playoff/<int:episode_id>', methods=['GET'])
async def get_league_playoff(episode_id):
    results = await league_playoffs.get_playoff_by_episodeid_submitted(episode_id)
    return jsonify(results)


@sahasrahbotapi.route('/api/league/playoffs', methods=['GET'])
async def get_league_playoffs():
    results = await league_playoffs.get_all_playoffs()
    return jsonify(results)


@sahasrahbotapi.route('/healthcheck', methods=['GET'])
async def healthcheck():
    if discordbot.is_closed():
        abort(500, description='Connection to Discord is closed.')

    appinfo = await discordbot.application_info()
    await discordbot.fetch_user(appinfo.owner.id)

    if not srlbot.connected:
        abort(500, description="Connection to SRL id closed.")

    info = await srlbot.whois(os.environ['SRL_NICK'])
    if not info['identified']:
        abort(500, description="SRL bot is not identified with Nickserv.")

    return jsonify(
        success=True
    )


@sahasrahbotapi.route('/robots.txt', methods=['GET'])
async def robots():
    return 'User-agent: *\nDisallow: /\n'

# @sahasrahbotapi.errorhandler(400)
# def bad_request(e):
#     return jsonify(success=False, error=repr(e))

# @sahasrahbotapi.errorhandler(404)
# def not_found(e):
#     return jsonify(success=False, error=repr(e))

# @sahasrahbotapi.errorhandler(500)
# def something_bad_happened(e):
#     return jsonify(success=False, error=repr(e))

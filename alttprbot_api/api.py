import os

import aiohttp
from quart import Quart, abort, jsonify, request, session, redirect
from urllib.parse import quote

from alttprbot.alttprgen.mystery import get_weights, generate
from alttprbot.tournament import league, alttpr
from alttprbot.database import league_playoffs, nick_verification, srlnick
from alttprbot_discord.bot import discordbot
from alttprbot_srl.bot import srlbot

sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = os.urandom(24)

RACETIME_CLIENT_ID_OAUTH = os.environ.get('RACETIME_CLIENT_ID_OAUTH')
RACETIME_CLIENT_SECRET_OAUTH = os.environ.get('RACETIME_CLIENT_SECRET_OAUTH')
RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')
APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')

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


@sahasrahbotapi.route('/racetime/verification/initiate', methods=['GET'])
async def racetime_init_verification():
    key = request.args.get("key")
    verification = await nick_verification.get_verification(key)
    if verification is None:
        return "Invalid verification key provided.  Please re-run the command and contact Synack if this persists."

    session['verification_key'] = key
    session['discord_user_id'] = verification['discord_user_id']

    redirect_uri = quote(f"{APP_URL}/racetime/verify/return")
    return redirect(
        f"{RACETIME_URL}/o/authorize?client_id={RACETIME_CLIENT_ID_OAUTH}&response_type=code&scope=read&redirect_uri={redirect_uri}",
    )

@sahasrahbotapi.route('/racetime/verify/return', methods=['GET'])
async def return_racetime_verify():
    code = request.args.get("code")
    if code is None:
        return abort(400, "code is missing")
    data = {
        'client_id': RACETIME_CLIENT_ID_OAUTH,
        'client_secret': RACETIME_CLIENT_SECRET_OAUTH,
        'code': code,
        'grant_type': 'authorization_code',
        'scope': 'read',
        'redirect_uri': f"{APP_URL}/racetime/verify/return"
    }

    async with aiohttp.request(url=f"{RACETIME_URL}/o/token", method="post", data=data, raise_for_status=True) as resp:
        token_data = await resp.json()

    token = token_data['access_token']

    headers = {
        'Authorization': f'Bearer {token}'
    }
    async with aiohttp.request(url=f"{RACETIME_URL}/o/userinfo", method="get", headers=headers, raise_for_status=True) as resp:
        userinfo_data = await resp.json()

    await srlnick.insert_rtgg_id(session['discord_user_id'], userinfo_data['id'])
    await nick_verification.delete_verification(session['verification_key'])

    return f"Thank you {userinfo_data['name']}, we have verified you successfully."

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

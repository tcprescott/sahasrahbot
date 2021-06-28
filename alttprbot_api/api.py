import os

import aiohttp
from quart import Quart, abort, jsonify, request, session, redirect, url_for, render_template
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized, AccessDenied
from urllib.parse import quote

from alttprbot.alttprgen.mystery import get_weights, generate
from alttprbot.tournament import league, alttpr
from alttprbot.database import league_playoffs, srlnick
from alttprbot_discord.bot import discordbot

sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = bytes(os.environ.get("APP_SECRET_KEY"), "utf-8")

RACETIME_CLIENT_ID_OAUTH = os.environ.get('RACETIME_CLIENT_ID_OAUTH')
RACETIME_CLIENT_SECRET_OAUTH = os.environ.get('RACETIME_CLIENT_SECRET_OAUTH')
RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')
APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')

sahasrahbotapi.config["DISCORD_CLIENT_ID"] = int(os.environ.get("DISCORD_CLIENT_ID"))
sahasrahbotapi.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = os.environ.get("APP_URL") + "/callback/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = os.environ.get("DISCORD_TOKEN")

discord = DiscordOAuth2Session(sahasrahbotapi)

@sahasrahbotapi.route("/login/")
async def login():
    return await discord.create_session(
        scope=[
            'guilds',
            'identify',
        ],
        data=dict(redirect=session.get("login_original_path", "/me"))
    )

@sahasrahbotapi.route("/callback/")
async def callback():
    data = await discord.callback()
    redirect_to = data.get("redirect", "/me/")
    return redirect(redirect_to)

@sahasrahbotapi.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    session['login_original_path'] = request.path
    return redirect(url_for("login"))

@sahasrahbotapi.errorhandler(AccessDenied)
async def access_denied(e):
    return await render_template(
        'error.html',
        title="Access Denied",
        message="We were unable to access your Discord account."
    )

@sahasrahbotapi.errorhandler(alttpr.UnableToLookupEpisodeException)
async def unable_to_lookup(e):
    return await render_template(
        'error.html',
        title="SpeedGaming Episode Not Found",
        message="The SpeedGaming Episode ID was not found.  Please double check!"
    )

@sahasrahbotapi.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return await render_template('me.html', logged_in=True, user=user)

@sahasrahbotapi.route("/logout/")
async def logout():
    discord.revoke()
    return await render_template('logout.html', logged_in=False)

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


@sahasrahbotapi.route("/submit/alttprfr", methods=['GET'])
@sahasrahbotapi.route("/alttprfr", methods=['GET'])
@requires_authorization
async def alttprfr():
    user = await discord.fetch_user()
    episode_id = request.args.get("episode_id", "")
    return await render_template(
        'submission.html',
        logged_in=True,
        user=user,
        endpoint=url_for("alttprfr_settings"),
        settings_list=alttpr.ALTTPR_FR_SETTINGS_LIST,
        episode_id=episode_id
    )

@sahasrahbotapi.route("/submit/alttprfr", methods=['POST'])
@sahasrahbotapi.route('/alttprfr', methods=['POST'])
@requires_authorization
async def alttprfr_settings():
    user = await discord.fetch_user()
    payload = await request.form
    tournament_race = await alttpr.alttprfr_process_settings_form(payload)
    return await render_template(
        "submission_done.html",
        logged_in=True,
        user=user,
        tournament_race=tournament_race
    )

@sahasrahbotapi.route("/submit/alttpres", methods=['GET'])
@sahasrahbotapi.route("/submit/test", methods=['GET'])
@requires_authorization
async def alttpres():
    user = await discord.fetch_user()
    episode_id = request.args.get("episode_id", "")
    return await render_template(
        'submission.html',
        logged_in=True,
        user=user,
        endpoint=url_for("alttpres_settings"),
        settings_list=alttpr.ALTTPR_ES_SETTINGS_LIST,
        episode_id=episode_id
    )

@sahasrahbotapi.route("/submit/alttpres", methods=['POST'])
@sahasrahbotapi.route("/submit/test", methods=['POST'])
@requires_authorization
async def alttpres_settings():
    user = await discord.fetch_user()
    payload = await request.form
    tournament_race = await alttpr.alttpres_process_settings_form(payload)
    return await render_template(
        "submission_done.html",
        logged_in=True,
        user=user,
        tournament_race=tournament_race
    )

@sahasrahbotapi.route('/api/league/playoff/<int:episode_id>', methods=['GET'])
async def get_league_playoff(episode_id):
    results = await league_playoffs.get_playoff_by_episodeid_submitted(episode_id)
    return jsonify(results)


@sahasrahbotapi.route('/api/league/playoffs', methods=['GET'])
async def get_league_playoffs():
    results = await league_playoffs.get_all_playoffs()
    return jsonify(results)


@sahasrahbotapi.route('/racetime/verification/initiate', methods=['GET'])
@requires_authorization
async def racetime_init_verification():
    redirect_uri = quote(f"{APP_URL}/racetime/verify/return")
    return redirect(
        f"{RACETIME_URL}/o/authorize?client_id={RACETIME_CLIENT_ID_OAUTH}&response_type=code&scope=read&redirect_uri={redirect_uri}",
    )

@sahasrahbotapi.route('/racetime/verify/return', methods=['GET'])
@requires_authorization
async def return_racetime_verify():
    user = await discord.fetch_user()
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

    await srlnick.insert_rtgg_id(user.id, userinfo_data['id'])

    return await render_template('racetime_verified.html', logged_in=True, user=user, racetime_name=userinfo_data['name'])

@sahasrahbotapi.route('/healthcheck', methods=['GET'])
async def healthcheck():
    if discordbot.is_closed():
        abort(500, description='Connection to Discord is closed.')

    appinfo = await discordbot.application_info()
    await discordbot.fetch_user(appinfo.owner.id)

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

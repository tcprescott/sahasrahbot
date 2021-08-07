import os

import aiohttp
from quart import Quart, abort, jsonify, request, session, redirect, url_for, render_template
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized, AccessDenied
from urllib.parse import quote

from alttprbot.tournaments import TOURNAMENT_DATA, fetch_tournament_handler
from alttprbot.tournament.core import UnableToLookupEpisodeException
from alttprbot.alttprgen.mystery import get_weights, generate
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
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = os.environ.get("APP_URL") + "/callback/discord/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = os.environ.get("DISCORD_TOKEN")

discord = DiscordOAuth2Session(sahasrahbotapi)

@sahasrahbotapi.route("/login/")
async def login():
    return await discord.create_session(
        scope=[
            'identify',
        ],
        data=dict(redirect=session.get("login_original_path", "/me"))
    )

@sahasrahbotapi.route("/callback/discord/")
async def callback():
    data = await discord.callback()
    redirect_to = data.get("redirect", "/me/")
    return redirect(redirect_to)

@sahasrahbotapi.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    session['login_original_path'] = request.full_path
    return redirect(url_for("login"))

@sahasrahbotapi.errorhandler(AccessDenied)
async def access_denied(e):
    return await render_template(
        'error.html',
        title="Access Denied",
        message="We were unable to access your Discord account."
    )

@sahasrahbotapi.errorhandler(UnableToLookupEpisodeException)
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
    mystery = await generate(weights=weights, spoilers="mystery")
    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'
    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route("/submit/<string:event>", methods=['GET'])
@requires_authorization
async def submission_form(event):
    user = await discord.fetch_user()
    episode_id = request.args.get("episode_id", "")

    event_config = await TOURNAMENT_DATA[event].get_config()
    form_data = event_config.submission_form
    if form_data is None:
        raise Exception("There is no form submission data for this event.")

    return await render_template(
        'submission.html',
        logged_in=True,
        user=user,
        event=event,
        endpoint=url_for("submit"),
        settings_list=form_data,
        episode_id=episode_id
    )

@sahasrahbotapi.route("/submit", methods=['POST'])
@requires_authorization
async def submit():
    user = await discord.fetch_user()
    payload = await request.form
    tournament_race = await fetch_tournament_handler(payload['event'], int(payload['episodeid']))
    await tournament_race.process_submission_form(payload, submitted_by=f"{user.name}#{user.discriminator}")
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

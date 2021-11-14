from io import BytesIO
import os
import re

import aiohttp
from quart import Quart, abort, jsonify, request, session, redirect, url_for, render_template, send_file
from quart_discord import DiscordOAuth2Session, requires_authorization, Unauthorized, AccessDenied
from urllib.parse import quote

from alttprbot import models
from alttprbot.tournaments import TOURNAMENT_DATA, fetch_tournament_handler
from alttprbot.tournament.core import UnableToLookupEpisodeException
from alttprbot.alttprgen import generator
from alttprbot.database import srlnick  # TODO switch to ORM
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
    data = await generator.ALTTPRMystery.custom_from_dict(weights)
    mystery = await data.generate_test_game()

    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'

    print(mystery.custom_instructions)

    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route('/api/settingsgen/mystery', methods=['GET'])
async def mysterygenwithweightsv2():
    weightset = request.args.get('weightset')
    data = generator.ALTTPRMystery(preset=weightset)
    mystery = await data.generate_test_game()

    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'

    print(mystery.custom_instructions)

    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route('/api/settingsgen/mystery/<string:weightset>', methods=['GET'])
async def mysterygenwithweights(weightset):
    data = generator.ALTTPRMystery(preset=weightset)
    mystery = await data.generate_test_game()

    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'

    print(mystery.custom_instructions)

    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route('/api/tournament/games', methods=['GET'])
async def get_tournament_games():
    terms = request.args
    data = await models.TournamentGames.filter(**terms).values()
    return jsonify(data)


@sahasrahbotapi.route("/submit/<string:event>", methods=['GET'])
@requires_authorization
async def submission_form(event):
    user = await discord.fetch_user()
    episode_id = request.args.get("episode_id", "")

    event_config = await TOURNAMENT_DATA[event].get_config()
    form_data = event_config.submission_form
    if form_data is None:
        raise Exception("There is no form submission data for this event.")

    if isinstance(form_data, str):
        return await render_template(
            form_data,
            logged_in=True,
            user=user,
            event=event,
            endpoint=url_for("submit"),
            episode_id=episode_id
        )
    else:
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


@sahasrahbotapi.route('/presets', methods=['GET'])
# @requires_authorization
async def all_presets():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    namespaces = await models.PresetNamespaces.all()

    return await render_template('preset_namespaces_all.html', logged_in=logged_in, user=user, namespaces=namespaces)


@sahasrahbotapi.route('/purgeme', methods=['GET'])
async def purge_me():
    user = await discord.fetch_user()

    return await render_template('purge_me.html', logged_in=True, user=user)


@sahasrahbotapi.route('/purgeme', methods=['POST'])
async def purge_me_action():
    user = await discord.fetch_user()
    payload = await request.form

    if payload.get('confirmpurge', 'no') == 'yes':
        await models.PresetNamespaces.filter(discord_user_id=user.id).delete()
        await models.NickVerification.filter(discord_user_id=user.id).delete()
        await models.SRLNick.filter(discord_user_id=user.id).delete()
        await models.AuditMessages.filter(user_id=user.id).delete()

        return redirect("/logout/")

    return redirect("/me/")


@sahasrahbotapi.route('/presets/me', methods=['GET'])
@requires_authorization
async def my_presets():
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    return redirect(f"/presets/manage/{ns_current_user.name}")


@sahasrahbotapi.route('/presets/create', methods=['GET'])
@requires_authorization
async def new_preset():
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    return await render_template('preset_new.html', logged_in=True, user=user, ns_current_user=ns_current_user, randomizers=generator.PRESET_CLASS_MAPPING.keys())


@sahasrahbotapi.route('/presets/create', methods=['POST'])
@requires_authorization
async def new_preset_submit():
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    if not re.match("^[a-zA-Z0-9_]*$", payload['preset_name']):
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized", message="Invalid preset name provided.")

    preset_data, _ = await models.Presets.update_or_create(
        preset_name=payload['preset_name'],
        randomizer=payload['randomizer'],
        namespace=ns_current_user,
        defaults={
            'content': request_files['presetfile'].read().decode()
        }
    )

    return redirect(f"/presets/manage/{ns_current_user.name}/{preset_data.randomizer}/{preset_data.preset_name}")


@sahasrahbotapi.route('/presets/manage/<string:namespace>', methods=['GET'])
# @requires_authorization
async def presets_for_namespace(namespace):
    try:
        user = await discord.fetch_user()
        logged_in = True
        ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
        is_owner = ns_current_user.name == namespace
    except Unauthorized:
        user = None
        logged_in = False
        ns_current_user = None
        is_owner = False

    ns_data = await models.PresetNamespaces.get(name=namespace)
    presets = await models.Presets.filter(namespace__name=namespace)

    return await render_template('preset_namespace.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data, presets=presets)


@sahasrahbotapi.route('/presets/manage/<string:namespace>/<string:randomizer>', methods=['GET'])
# @requires_authorization
async def presets_for_namespace_randomizer(namespace, randomizer):
    try:
        user = await discord.fetch_user()
        logged_in = True
        ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
        is_owner = ns_current_user.name == namespace
    except Unauthorized:
        user = None
        logged_in = False
        ns_current_user = None
        is_owner = False

    ns_data = await models.PresetNamespaces.get(name=namespace)
    presets = await models.Presets.filter(randomizer=randomizer, namespace__name=namespace).only('id', 'preset_name', 'randomizer')

    return await render_template('preset_namespace.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data, presets=presets)


@sahasrahbotapi.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def get_preset(namespace, randomizer, preset):
    try:
        user = await discord.fetch_user()
        logged_in = True
        ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
        is_owner = ns_current_user.name == namespace
    except Unauthorized:
        user = None
        logged_in = False
        ns_current_user = None
        is_owner = False

    ns_data = await models.PresetNamespaces.get(name=namespace)
    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await render_template('preset_view.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data, preset_data=preset_data)


@sahasrahbotapi.route('/presets/download/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def download_preset(namespace, randomizer, preset):
    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await send_file(
        BytesIO(preset_data.content.encode()),
        mimetype="application/octet-stream",
        attachment_filename=f"{namespace}-{preset}.yaml",
        as_attachment=True
    )


@sahasrahbotapi.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['POST'])
@requires_authorization
async def update_preset(namespace, randomizer, preset):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
    is_owner = ns_current_user.name == namespace

    if not is_owner:
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized", message="You are not the owner of this preset.")

    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    if 'delete' in payload:
        await preset_data.delete()
        return redirect(f"/presets/manage/{namespace}")

    preset_data.content = request_files['presetfile'].read().decode()

    await preset_data.save()

    return redirect(f"/presets/manage/{namespace}/{randomizer}/{preset}")

# @sahasrahbotapi.route('/presets/<str:namespace>', methods=['POST'])
# @requires_authorization
# async def update_namespace():
#     user = await discord.fetch_user()
#     namespace = await generator.create_or_retrieve_namespace(user.id, user.name)


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

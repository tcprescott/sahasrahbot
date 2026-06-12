import logging
import os

from authlib.oauth2.rfc6749.errors import OAuth2Error
from quart import (Quart, abort, jsonify, redirect, render_template, request,
                   session, url_for, send_from_directory)

import config
from alttprbot import models
from alttprbot_discord.bot import discordbot

logger = logging.getLogger(__name__)

# Initialize Quart app
sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = bytes(config.APP_SECRET_KEY, "utf-8")

sahasrahbotapi.config["DISCORD_CLIENT_ID"] = int(config.DISCORD_CLIENT_ID)
sahasrahbotapi.config["DISCORD_CLIENT_SECRET"] = config.DISCORD_CLIENT_SECRET
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = config.APP_URL + "/callback/discord/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = config.DISCORD_TOKEN

from alttprbot_api.oauth_client import (
    AuthlibDiscordOAuth,
    Unauthorized,
    AccessDenied,
    requires_authorization
)

discord = AuthlibDiscordOAuth(
    app=sahasrahbotapi,
    client_id=config.DISCORD_CLIENT_ID,
    client_secret=config.DISCORD_CLIENT_SECRET,
    redirect_uri=config.APP_URL + "/callback/discord/"
)
logger.info("OAuth: Using Authlib implementation")

import alttprbot_api.blueprints as blueprints  # nopep8

sahasrahbotapi.register_blueprint(blueprints.presets_blueprint)
sahasrahbotapi.register_blueprint(blueprints.racetime_blueprint)
sahasrahbotapi.register_blueprint(blueprints.ranked_choice_blueprint)
sahasrahbotapi.register_blueprint(blueprints.settingsgen_blueprint)
sahasrahbotapi.register_blueprint(blueprints.sglive_blueprint, url_prefix="/sglive")
sahasrahbotapi.register_blueprint(blueprints.tournament_blueprint)
sahasrahbotapi.register_blueprint(blueprints.triforcetexts_blueprint)
sahasrahbotapi.register_blueprint(blueprints.asynctournament_blueprint, url_prefix="/async")

# not ready for prime time
if config.DEBUG:
    sahasrahbotapi.register_blueprint(blueprints.schedule_blueprint, url_prefix="/schedule")
    sahasrahbotapi.register_blueprint(blueprints.user_blueprint, url_prefix="/user")

if config.DEBUG:
    sahasrahbotapi.config['TEMPLATES_AUTO_RELOAD'] = True


@sahasrahbotapi.route("/")
async def index():
    index_html = os.path.join(_SPA_DIST, 'index.html')
    if os.path.isfile(index_html):
        return await send_from_directory(_SPA_DIST, 'index.html')
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    return await render_template('index.html', user=user)


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
        message="We were unable to access your Discord account.",
        user=None
    )


@sahasrahbotapi.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return await render_template('me.html', user=user)


@sahasrahbotapi.route("/logout/")
async def logout():
    discord.revoke()
    return redirect(url_for("index"))

if config.DEBUG:
    @sahasrahbotapi.route('/throw_error', methods=['GET'])
    async def throw_error():
        try:
            user = await discord.fetch_user()
        except Unauthorized:
            user = None

        return await render_template('error.html', user=user, title="Example Error", message="This is just a test.")

@sahasrahbotapi.route('/healthcheck', methods=['GET'])
async def healthcheck():
    if discordbot.is_closed():
        abort(500, description='Connection to Discord is closed.')

    appinfo = await discordbot.application_info()
    await discordbot.fetch_user(appinfo.owner.id)

    return jsonify(
        success=True
    )


@sahasrahbotapi.route('/purgeme', methods=['GET'])
async def purge_me():
    user = await discord.fetch_user()

    return await render_template('purge_me.html', user=user)


@sahasrahbotapi.route('/purgeme', methods=['POST'])
async def purge_me_action():
    user = await discord.fetch_user()
    payload = await request.form

    if payload.get('confirmpurge', 'no') == 'yes':
        await models.PresetNamespaces.filter(discord_user_id=user.id).delete()
        await models.NickVerification.filter(discord_user_id=user.id).delete()
        return redirect(url_for('logout'))

    return redirect(url_for('me'))


@sahasrahbotapi.route('/robots.txt', methods=['GET'])
async def robots():
    return 'User-agent: *\nDisallow: /\n'


# ---------------------------------------------------------------------------
# SPA support
# ---------------------------------------------------------------------------

_SPA_DIST = os.path.join(os.path.dirname(__file__), 'spa', 'dist')

if not os.path.isdir(_SPA_DIST):
    logger.warning(
        "SPA dist directory not found at %s — SPA routes will return 404 until the frontend is built.",
        _SPA_DIST,
    )


@sahasrahbotapi.route('/api/me', methods=['GET'])
async def api_me():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        return jsonify(error="unauthenticated"), 401

    user_id = str(user._data.get('id', ''))
    avatar_hash = user._data.get('avatar')
    if avatar_hash:
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
    else:
        discriminator = int(user._data.get('discriminator', 0) or 0)
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discriminator % 5}.png"

    name = user._data.get('global_name') or user._data.get('username', '')
    return jsonify(data=dict(id=user_id, name=name, avatar_url=avatar_url))


@sahasrahbotapi.route('/spa-assets/<path:filename>', methods=['GET'])
async def spa_assets(filename):
    assets_dir = os.path.join(_SPA_DIST, 'spa-assets')
    if not os.path.isdir(assets_dir):
        abort(404)
    return await send_from_directory(assets_dir, filename)


# Prefixes owned by existing blueprints / server routes — never hand off to SPA.
_RESERVED_PREFIXES = (
    '/api/',
    '/auth/',
    '/racetime/',
    '/triforcetexts/',
    '/presets/',
    '/sglive/',
    '/schedule/',
    '/user/',
    '/login/',
    '/logout/',
    '/callback/',
    '/me/',
    '/purgeme',
    '/healthcheck',
    '/robots.txt',
    '/assets/',
    '/theme-assets/',
    '/spa-assets/',
    '/throw_error',
)


@sahasrahbotapi.route('/<path:path>', methods=['GET'])
async def spa_catchall(path):
    full_path = '/' + path
    for prefix in _RESERVED_PREFIXES:
        if full_path.startswith(prefix):
            abort(404)
    # Serve real files from dist root first (logo, favicon, manifest, etc.)
    candidate = os.path.join(_SPA_DIST, path)
    if os.path.isfile(candidate):
        return await send_from_directory(_SPA_DIST, path)
    index_html = os.path.join(_SPA_DIST, 'index.html')
    if not os.path.isfile(index_html):
        abort(404)
    return await send_from_directory(_SPA_DIST, 'index.html')


@sahasrahbotapi.route('/assets/<path:path>', methods=['GET'])
async def assets(path):
    return await send_from_directory('alttprbot_api/static/assets', path)

@sahasrahbotapi.route('/theme-assets/<path:path>', methods=['GET'])
async def theme_assets(path):
    return await send_from_directory('alttprbot_api/static/theme-assets', path)

# @sahasrahbotapi.errorhandler(400)
# def bad_request(e):
#     return jsonify(success=False, error=repr(e))

@sahasrahbotapi.errorhandler(404)
async def not_found(e):
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None
    return await render_template(
        'error.html',
        title="Not Found",
        message="The page you are looking for does not exist.",
        user=user
    )

@sahasrahbotapi.errorhandler(OAuth2Error)
async def oauth2_error(e):
    discord.revoke()
    return await render_template(
        'error.html',
        title="OAuth Error",
        message=f"An OAuth error occurred: {e.description}",
        user=None
    )

@sahasrahbotapi.errorhandler(500)
async def something_bad_happened(e):
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None

    return await render_template(
        'error.html',
        title="Something Bad Happened",
        message="Something bad happened.  Please try again later.",
        user=user
    )

import os
import logging

from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, TokenExpiredError
from quart import (Quart, abort, jsonify, redirect, render_template, request,
                   session, url_for, send_from_directory)

import config
from alttprbot import models
from alttprbot_discord.bot import discordbot

# Initialize Quart app
sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = bytes(config.APP_SECRET_KEY, "utf-8")

sahasrahbotapi.config["DISCORD_CLIENT_ID"] = int(config.DISCORD_CLIENT_ID)
sahasrahbotapi.config["DISCORD_CLIENT_SECRET"] = config.DISCORD_CLIENT_SECRET
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = config.APP_URL + "/callback/discord/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = config.DISCORD_TOKEN
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Dual-path OAuth client initialization
# Phase 1: Authlib scaffolding behind disabled feature flag
USE_AUTHLIB = getattr(config, 'USE_AUTHLIB_OAUTH', False)

if USE_AUTHLIB:
    # New Authlib-based OAuth path (Phase 1+)
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
    logging.info("OAuth: Using Authlib implementation (USE_AUTHLIB_OAUTH=True)")
else:
    # Legacy Quart-Discord path (default)
    from quart_discord import (AccessDenied, DiscordOAuth2Session, Unauthorized,
                               requires_authorization)
    discord = DiscordOAuth2Session(sahasrahbotapi)
    logging.info("OAuth: Using Quart-Discord implementation (default)")

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

@sahasrahbotapi.errorhandler(InvalidGrantError)
async def invalid_grant(e):
    discord.revoke()
    return await render_template(
        'error.html',
        title="Discord Session Expired",
        message="Your Discord session has expired.  Please log in again.",
        user=None
    )

@sahasrahbotapi.errorhandler(TokenExpiredError)
async def token_expired(e):
    discord.revoke()
    return await render_template(
        'error.html',
        title="Discord Session Expired",
        message="Your Discord session has expired.  Please log in again.",
        user=None
    )

# Handle Authlib OAuth2Error if using Authlib path
if USE_AUTHLIB:
    from authlib.oauth2.rfc6749.errors import OAuth2Error
    
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

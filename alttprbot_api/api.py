from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, TokenExpiredError
from quart import (Quart, abort, jsonify, redirect, render_template, request,
                   session, url_for)
from quart_discord import (AccessDenied, DiscordOAuth2Session, Unauthorized,
                           requires_authorization)

import config
from alttprbot import models
from alttprbot_discord.bot import discordbot

sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = bytes(config.APP_SECRET_KEY, "utf-8")

sahasrahbotapi.config["DISCORD_CLIENT_ID"] = int(config.DISCORD_CLIENT_ID)
sahasrahbotapi.config["DISCORD_CLIENT_SECRET"] = config.DISCORD_CLIENT_SECRET
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = config.APP_URL + "/callback/discord/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = config.DISCORD_TOKEN

discord = DiscordOAuth2Session(sahasrahbotapi)

import alttprbot_api.blueprints as blueprints  # nopep8

sahasrahbotapi.register_blueprint(blueprints.presets_blueprint)
sahasrahbotapi.register_blueprint(blueprints.racetime_blueprint)
sahasrahbotapi.register_blueprint(blueprints.ranked_choice_blueprint)
sahasrahbotapi.register_blueprint(blueprints.settingsgen_blueprint)
sahasrahbotapi.register_blueprint(blueprints.sgl23_blueprint)
sahasrahbotapi.register_blueprint(blueprints.tournament_blueprint)
sahasrahbotapi.register_blueprint(blueprints.triforcetexts_blueprint)
sahasrahbotapi.register_blueprint(blueprints.asynctournament_blueprint, url_prefix="/async")


@sahasrahbotapi.route("/")
async def index():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    return await render_template('index.html', logged_in=logged_in, user=user)

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


@sahasrahbotapi.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return await render_template('me.html', logged_in=True, user=user)


@sahasrahbotapi.route("/logout/")
async def logout():
    discord.revoke()
    return await render_template('logout.html', logged_in=False)


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

    return await render_template('purge_me.html', logged_in=True, user=user)


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

# @sahasrahbotapi.errorhandler(400)
# def bad_request(e):
#     return jsonify(success=False, error=repr(e))

# @sahasrahbotapi.errorhandler(404)
# def not_found(e):
#     return jsonify(success=False, error=repr(e))

@sahasrahbotapi.errorhandler(500)
async def something_bad_happened(e):
    if isinstance(e, (InvalidGrantError, TokenExpiredError)):
        discord.revoke()
        return await render_template(
            'error.html',
            title="Discord Session Expired",
            message="Your Discord session has expired.  Please log in again."
        )

    return await render_template(
        'error.html',
        title="Something Bad Happened",
        message="Something bad happened.  Please try again later."
    )
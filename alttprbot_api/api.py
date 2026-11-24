import json
import os
from pathlib import Path
from urllib.parse import quote

import aiofiles
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError, TokenExpiredError
from quart import Quart, abort, jsonify, make_response, redirect, request, send_from_directory, session
from quart_discord import AccessDenied, DiscordOAuth2Session, Unauthorized
from quart_schema import Info, OpenAPIProvider, QuartSchema, RequestSchemaValidationError
from werkzeug.exceptions import HTTPException

import config
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError
from alttprbot.observability import sentry as observability
from alttprbot.services import bots

# The React app (web/) is built into web/dist and served from here: its files by
# name, and index.html for every other page path, so the app's router takes over.
WEB_DIST = Path(__file__).resolve().parent.parent / 'web' / 'dist'

sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = bytes(config.APP_SECRET_KEY, "utf-8")
sahasrahbotapi.config["SESSION_COOKIE_SAMESITE"] = "Lax"

sahasrahbotapi.config["DISCORD_CLIENT_ID"] = int(config.DISCORD_CLIENT_ID)
sahasrahbotapi.config["DISCORD_CLIENT_SECRET"] = config.DISCORD_CLIENT_SECRET
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = config.APP_URL + "/callback/discord/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = config.DISCORD_TOKEN
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

discord = DiscordOAuth2Session(sahasrahbotapi)

# ``guilds`` lets the app ask Discord which servers you're in, with your permissions
# there, in one request (elections use it to find the servers you administer).
SIGN_IN_SCOPES = ['identify', 'guilds']


class AppApiOpenAPIProvider(OpenAPIProvider):
    """Only the app's JSON API (/api/v1) goes in the schema the web/ client is generated from."""

    def generate_rules(self):
        for rule in super().generate_rules():
            if rule.rule.startswith('/api/v1/'):
                yield rule


QuartSchema(
    sahasrahbotapi,
    info=Info(title="SahasrahBot web API", version="1"),
    openapi_path="/api/v1/openapi.json",
    redoc_ui_path=None,
    scalar_ui_path=None,
    swagger_ui_path="/api/v1/docs",
    openapi_provider_class=AppApiOpenAPIProvider,
)

import alttprbot_api.blueprints as blueprints  # nopep8
from alttprbot_api import telemetry  # nopep8

telemetry.install(sahasrahbotapi)

sahasrahbotapi.register_blueprint(blueprints.app_api_blueprint)
sahasrahbotapi.register_blueprint(blueprints.presets_blueprint)
sahasrahbotapi.register_blueprint(blueprints.racetime_blueprint)
sahasrahbotapi.register_blueprint(blueprints.settingsgen_blueprint)
sahasrahbotapi.register_blueprint(blueprints.tournament_blueprint)

from alttprbot_api import mcp  # nopep8

mcp.mount(sahasrahbotapi)


def _wants_json() -> bool:
    return request.path.startswith('/api/') or request.path == '/healthcheck'


def _safe_next(path: str | None) -> str:
    """A same-site path to return to after signing in, never another site."""
    if not path or not path.startswith('/') or path.startswith('//') or '\\' in path:
        return '/'
    return path


def _error(status: int, message: str):
    if _wants_json():
        return jsonify(error=message), status
    # Only server-side flows (sign-in, racetime linking) land here; the app shows the message.
    return redirect(f"/error?code={status}&message={quote(message)}")


# --- Sign-in -----------------------------------------------------------------



@sahasrahbotapi.route("/login/")
async def login():
    if 'next' in request.args:
        session['login_original_path'] = _safe_next(request.args['next'])
    return await discord.create_session(
        scope=SIGN_IN_SCOPES,
        data={"redirect": _safe_next(session.pop("login_original_path", "/me"))},
    )


@sahasrahbotapi.route("/callback/discord/")
async def callback():
    data = await discord.callback()
    return redirect(_safe_next(data.get("redirect", "/me")))


@sahasrahbotapi.route("/logout/")
async def logout():
    discord.revoke()
    return redirect("/")


@sahasrahbotapi.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    if _wants_json():
        return jsonify(error="Sign in with Discord first."), 401
    session['login_original_path'] = _safe_next(request.full_path.rstrip('?'))
    return redirect("/login/")


@sahasrahbotapi.errorhandler(AccessDenied)
async def access_denied(e):
    return _error(403, "We couldn't access your Discord account.")


@sahasrahbotapi.errorhandler(InvalidGrantError)
@sahasrahbotapi.errorhandler(TokenExpiredError)
async def session_expired(e):
    discord.revoke()
    if _wants_json():
        return jsonify(error="Your Discord session expired. Sign in again."), 401
    return redirect("/login/")


# --- Errors ------------------------------------------------------------------


@sahasrahbotapi.errorhandler(NotFoundError)
async def not_found_error(e):
    return _error(404, str(e))


@sahasrahbotapi.errorhandler(PermissionDeniedError)
async def permission_denied(e):
    return _error(403, str(e))


@sahasrahbotapi.errorhandler(InvalidInputError)
async def invalid_input(e):
    return _error(400, str(e))


@sahasrahbotapi.errorhandler(RequestSchemaValidationError)
async def invalid_request_body(e):
    return jsonify(error="The request didn't match what this endpoint expects.", detail=str(e.validation_error)), 400


@sahasrahbotapi.errorhandler(HTTPException)
async def http_error(e: HTTPException):
    if e.code == 500:
        return await server_error(e)
    if e.code == 404 and not _wants_json():
        response = await app_page('')  # the app shows its own not-found page
        response.status_code = 404
        return response
    return _error(e.code, e.description or e.name)


@sahasrahbotapi.errorhandler(500)
async def server_error(e):
    # Registered for 500 rather than Exception so Sentry still sees unhandled errors.
    return _error(500, "Something went wrong on our side. Try again later.")


# --- Plain routes ------------------------------------------------------------


@sahasrahbotapi.route('/healthcheck', methods=['GET'])
async def healthcheck():
    if bots.discord().is_closed():
        abort(500, description='Connection to Discord is closed.')

    appinfo = await bots.discord().application_info()
    await bots.discord().fetch_user(appinfo.owner.id)

    return jsonify(success=True)


@sahasrahbotapi.route('/robots.txt', methods=['GET'])
async def robots():
    return 'User-agent: *\nDisallow: /\n'


# --- The React app -----------------------------------------------------------

NOT_BUILT = (
    "<!doctype html><meta charset=utf-8><title>SahasrahBot</title>"
    "<p>The web app hasn't been built. Run <code>scripts/build_web.sh</code>.</p>"
)


@sahasrahbotapi.route('/', defaults={'path': ''})
@sahasrahbotapi.route('/<path:path>')
async def app_page(path: str):
    if path.startswith('api/'):
        return jsonify(error="No such API endpoint."), 404
    if path and (WEB_DIST / path).is_file() and WEB_DIST in (WEB_DIST / path).resolve().parents:
        response = await send_from_directory(WEB_DIST, path)
        if path.startswith('assets/'):
            response.cache_control.max_age = 31536000  # Vite puts a content hash in these names
            response.cache_control.immutable = True
        return response
    if not (WEB_DIST / 'index.html').is_file():
        return await make_response(NOT_BUILT, 200)
    response = await make_response(await _index_html(), 200, {'Content-Type': 'text/html; charset=utf-8'})
    response.cache_control.no_cache = True
    return response


async def _index_html() -> str:
    """The app's index.html with the browser's Sentry settings inlined.

    ``web/src/telemetry.ts`` reads ``window.__SAHASRAHBOT_SENTRY__`` so Sentry starts
    before the first render without a round trip (``null`` means off). A native
    wrapper, whose index.html isn't served from here, asks ``/api/v1/telemetry``.
    """
    async with aiofiles.open(WEB_DIST / 'index.html', encoding='utf-8') as f:
        html = await f.read()
    settings = json.dumps(observability.browser_config()).replace('<', '\\u003c')
    script = f'<script>window.__SAHASRAHBOT_SENTRY__={settings};</script>'
    if '</head>' in html:
        return html.replace('</head>', f'{script}</head>', 1)
    return script + html

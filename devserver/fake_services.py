"""Fake external services, served by the dev app itself under ``/_fake/``.

The dev bootstrap points the app's settings at these routes, so the real code
paths run unchanged and make real HTTP requests, just to this server:

- ``/_fake/discord/api``: Discord's OAuth2 authorize/token endpoints and
  ``/users/@me``, used by quart-discord for login. The authorize page is a
  "log in as" picker.
- ``/_fake/discord/avatars``: generated avatar images.
- ``/_fake/racetime``: racetime.gg's OAuth2 endpoints (racetime account
  verification) and placeholder room/user pages.
- ``/_fake/speedgaming/api``: SpeedGaming's ``/schedule`` and ``/episode``.
"""
import datetime
import hashlib
import html
import json
from urllib.parse import urlencode

import dateutil.parser
from quart import Blueprint, Response, current_app, jsonify, redirect, render_template_string, request, session

from devserver import fixtures

fake_services = Blueprint("fake_services", __name__, url_prefix="/_fake")

PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{{ title }}</title>
<style>
 body { font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; color: #222; }
 .banner { background: #fff3cd; border: 1px solid #e0c36a; padding: .5rem .75rem; border-radius: 6px; margin-bottom: 1rem; }
 .card { border: 1px solid #ccc; border-radius: 8px; padding: .75rem 1rem; margin: .5rem 0; display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
 .muted { color: #666; font-size: .9em; }
 button, .button { padding: .4rem .9rem; border-radius: 6px; border: 1px solid #5865f2; background: #5865f2; color: #fff; cursor: pointer; text-decoration: none; font-size: .95em; }
 .secondary { background: #fff; color: #5865f2; }
</style></head>
<body><div class="banner">Fake {{ service }} (SahasrahBot dev server). Nothing here talks to the real service.</div>
{{ body|safe }}
</body></html>"""


def page(service, title, body):
    return render_template_string(PAGE, service=service, title=title, body=body)


def _world():
    return current_app.config["DEV_WORLD"]


# --- Discord OAuth2 --------------------------------------------------------------

def _with_params(url, **params):
    sep = "&" if "?" in url else "?"
    return url + sep + urlencode({k: v for k, v in params.items() if v is not None})


@fake_services.route("/discord/api/oauth2/authorize")
async def discord_authorize():
    redirect_uri = request.args.get("redirect_uri")
    state = request.args.get("state")
    chosen = request.args.get("user_id") or session.pop("_dev_login_as", None)

    if request.args.get("deny"):
        return redirect(_with_params(redirect_uri, error="access_denied", state=state))
    if chosen:
        return redirect(_with_params(redirect_uri, code=f"dev-{int(chosen)}", state=state))

    world = _world()
    cards = []
    for u in world.users.values():
        guilds = ", ".join(
            f"{m.guild.name} ({', '.join(r.name for r in m.roles[1:]) or 'no roles'})"
            for m in world.memberships(u.id)) or "no servers"
        approve = _with_params(request.url, user_id=u.id)
        cards.append(
            f'<div class="card"><div><b>{html.escape(u.name)}</b> <span class="muted">{u.id}</span>'
            f'<div class="muted">{html.escape(guilds)}</div></div>'
            f'<a class="button" href="{html.escape(approve)}">Authorize</a></div>')
    deny = _with_params(request.url, deny=1)
    body = (f"<h2>Log in to SahasrahBot as…</h2>{''.join(cards)}"
            f'<p><a class="button secondary" href="{html.escape(deny)}">Cancel (deny access)</a> '
            f'<a class="button secondary" href="/_dev/">Dev tools</a></p>')
    return await page("Discord", "Discord authorization", body)


@fake_services.route("/discord/api/oauth2/token", methods=["POST"])
async def discord_token():
    form = await request.form
    if form.get("grant_type") == "refresh_token":
        user_id = form.get("refresh_token", "").removeprefix("dev-refresh-")
    else:
        user_id = form.get("code", "").removeprefix("dev-")
    if not user_id.isdigit() or _world().users.get(int(user_id)) is None:
        return jsonify(error="invalid_grant"), 400
    return jsonify(
        access_token=f"dev-token-{user_id}",
        refresh_token=f"dev-refresh-{user_id}",
        token_type="Bearer",
        expires_in=7 * 24 * 3600,
        scope="identify",
    )


def _bearer_user_id(prefix):
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token.startswith(prefix):
        return None
    value = token.removeprefix(prefix)
    return value or None


@fake_services.route("/discord/api/users/@me")
async def discord_me():
    user_id = _bearer_user_id("dev-token-")
    user = _world().users.get(int(user_id)) if user_id and user_id.isdigit() else None
    if user is None:
        return jsonify(message="401: Unauthorized", code=0), 401
    return jsonify(
        id=str(user.id),
        username=user.name,
        global_name=user.global_name,
        discriminator="0",
        avatar="dev",
        bot=False,
        locale="en-US",
        mfa_enabled=False,
    )


@fake_services.route("/discord/avatars/<int:user_id>/<path:rest>")
@fake_services.route("/discord/avatars/<int:user_id>.svg")
async def discord_avatar(user_id, rest=None):
    user = _world().users.get(user_id)
    name = user.name if user else "?"
    hue = int(hashlib.sha1(str(user_id).encode()).hexdigest()[:4], 16) % 360
    initials = html.escape("".join(p[0] for p in name.replace("-", " ").split()[:2]).upper() or "?")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">'
           f'<rect width="128" height="128" rx="64" fill="hsl({hue},55%,45%)"/>'
           f'<text x="64" y="78" font-size="44" text-anchor="middle" fill="#fff" '
           f'font-family="sans-serif">{initials}</text></svg>')
    return Response(svg, content_type="image/svg+xml")


# --- racetime.gg -------------------------------------------------------------------

@fake_services.route("/racetime/o/authorize")
async def racetime_authorize():
    redirect_uri = request.args.get("redirect_uri")
    chosen = request.args.get("rtgg_id")
    if request.args.get("deny"):
        return redirect(_with_params(redirect_uri, error="access_denied"))
    if chosen:
        return redirect(_with_params(redirect_uri, code=f"rt-{chosen}"))
    cards = "".join(
        f'<div class="card"><div><b>{html.escape(u["name"])}</b> <span class="muted">{u["id"]}</span></div>'
        f'<a class="button" href="{html.escape(_with_params(request.url, rtgg_id=u["id"]))}">Authorize</a></div>'
        for u in fixtures.RACETIME_USERS)
    return await page("racetime.gg", "racetime.gg authorization",
                      f"<h2>Authorize SahasrahBot as which racetime.gg user?</h2>{cards}")


@fake_services.route("/racetime/o/token", methods=["POST"])
async def racetime_token():
    form = await request.form
    rtgg_id = form.get("code", "").removeprefix("rt-")
    if not any(u["id"] == rtgg_id for u in fixtures.RACETIME_USERS):
        return jsonify(error="invalid_grant"), 400
    return jsonify(access_token=f"rt-token-{rtgg_id}", token_type="Bearer", expires_in=36000, scope="read")


@fake_services.route("/racetime/o/userinfo")
async def racetime_userinfo():
    rtgg_id = _bearer_user_id("rt-token-")
    found = next((u for u in fixtures.RACETIME_USERS if u["id"] == rtgg_id), None)
    if found is None:
        return jsonify(detail="Invalid token"), 401
    return jsonify(id=found["id"], name=found["name"], discriminator="0000",
                   full_name=f'{found["name"]}#0000', url=f'/user/{found["id"]}')


@fake_services.route("/racetime/<path:path>")
async def racetime_page(path):
    return await page("racetime.gg", "racetime.gg",
                      f"<h2>racetime.gg/{html.escape(path)}</h2><p>This would be a racetime.gg page.</p>")


# --- SpeedGaming ---------------------------------------------------------------------

def _sg_player(spec):
    return {
        "id": spec["id"] % 100000,
        "displayName": spec["name"],
        "publicStream": spec["name"],
        "streamingFrom": spec["name"],
        "discordId": str(spec["id"]),
        "discordTag": spec["name"],
    }


def _sg_episode(episode_id, event, when):
    runners = [u for u in fixtures.USERS if "runner" in u["key"]]
    a = runners[episode_id % len(runners)]
    b = runners[(episode_id + 1) % len(runners)]
    return {
        "id": episode_id,
        "event": {"slug": event, "name": f"{event} (dev)", "active": True},
        "when": when.isoformat(),
        "whenCountdown": when.isoformat(),
        "length": 120,
        "title": f"{a['name']} vs {b['name']}",
        "match1": {"id": episode_id, "title": "", "players": [_sg_player(a), _sg_player(b)]},
        "match2": None,
        "channels": [{"id": 1, "name": "SpeedGaming", "slug": "speedgaming", "language": "en"}],
        "commentators": [{**_sg_player(fixtures.user("mod")), "approved": True}],
        "trackers": [],
        "broadcasters": [],
        "helpers": [],
        "approved": True,
    }


def _sg_json(data):
    # The real API answers with a text/html content type, and the client relies on it.
    return Response(json.dumps(data), content_type="text/html; charset=utf-8")


@fake_services.route("/speedgaming/api/schedule")
async def sg_schedule():
    event = request.args.get("event", "dev")
    start = dateutil.parser.isoparse(request.args["from"])
    end = dateutil.parser.isoparse(request.args["to"])
    # One match every 90 minutes, aligned to the half hour, ids stable per slot.
    slot = datetime.timedelta(minutes=90)
    epoch = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
    first = int((start - epoch) / slot) + 1
    last = int((end - epoch) / slot)
    salt = int(hashlib.sha1(event.encode()).hexdigest()[:3], 16)
    episodes = [_sg_episode(100000 + n * 7 + salt, event, epoch + n * slot) for n in range(first, last + 1)]
    return _sg_json(episodes)


@fake_services.route("/speedgaming/api/episode")
async def sg_episode():
    episode_id = int(request.args.get("id", 0))
    if episode_id <= 0:
        return _sg_json({"error": f"Failed to find episode with id {episode_id}."})
    when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    return _sg_json(_sg_episode(episode_id, request.args.get("event", "alttpr"), when))

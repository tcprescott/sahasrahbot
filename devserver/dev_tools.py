"""``/_dev``: pages for driving the dev server, for people and agents.

- ``GET /_dev/``: who you are, every fake user with a "log in as" link and their
  roles (editable), the messages the app has "sent" to Discord, useful links.
- ``GET /_dev/login?user=<key or id>&next=/path``: log in through the real OAuth
  flow as that user, then land on ``next``. ``user=new&name=x&roles=Admin,Voter``
  creates a user in the dev server first (kept until restart).
- ``GET /_dev/logout``: log out.
- ``POST /_dev/members/<user_id>``: set a user's roles in a guild (form fields
  ``guild_id``, ``member`` = on/off, ``role`` repeated). JSON body works too.
- ``GET /_dev/api/world``, ``GET /_dev/api/outbox``, ``POST /_dev/api/outbox/clear``.
"""
import html
import itertools

from quart import Blueprint, current_app, jsonify, redirect, render_template_string, request, session, url_for

from devserver import fixtures
from devserver.fake_discord import OUTBOX
from devserver.fake_services import PAGE

dev_tools = Blueprint("dev_tools", __name__, url_prefix="/_dev")

_new_user_ids = itertools.count(290000000000000001)


def _world():
    return current_app.config["DEV_WORLD"]


def _find_user(ref):
    world = _world()
    if ref is None:
        return None
    if str(ref).isdigit():
        return world.users.get(int(ref))
    spec = next((u for u in fixtures.USERS if u["key"] == ref), None)
    if spec:
        return world.users.get(spec["id"])
    return next((u for u in world.users.values() if u.name == ref), None)


@dev_tools.route("/login")
async def login_as():
    ref = request.args.get("user")
    next_path = request.args.get("next", "/me")
    world = _world()

    if ref == "new":
        name = request.args.get("name") or f"dev-user-{len(world.users) + 1}"
        guild = world.guilds[int(request.args.get("guild_id", fixtures.GUILD_ID))]
        wanted = [r.strip().lower() for r in request.args.get("roles", "").split(",") if r.strip()]
        role_ids = [r.id for r in guild.roles[1:] if r.name.lower() in wanted or str(r.id) in wanted]
        user = fixtures.add_user(world, next(_new_user_ids), name, {guild.id: role_ids})
    else:
        user = _find_user(ref)
        if user is None:
            return jsonify(error=f"No fake user {ref!r}. See /_dev/api/world."), 404

    current_app.discord.revoke()
    session["_dev_login_as"] = user.id
    session["login_original_path"] = next_path
    return redirect(url_for("login"))


@dev_tools.route("/logout")
async def logout():
    current_app.discord.revoke()
    return redirect(request.args.get("next", "/_dev/"))


@dev_tools.route("/members/<int:user_id>", methods=["POST"])
async def set_member_roles(user_id):
    world = _world()
    if request.is_json:
        data = await request.get_json()
        guild_id = int(data.get("guild_id", fixtures.GUILD_ID))
        is_member = bool(data.get("member", True))
        roles = data.get("roles", [])
    else:
        form = await request.form
        guild_id = int(form.get("guild_id", fixtures.GUILD_ID))
        is_member = form.get("member") == "on"
        roles = form.getlist("role")
    guild = world.guilds[guild_id]
    role_ids = []
    for r in roles:
        role = guild.get_role(r) if str(r).isdigit() else next(
            (x for x in guild.roles if x.name.lower() == str(r).lower()), None)
        if role is not None and role.id != guild.id:
            role_ids.append(role.id)
    world.set_roles(guild_id, user_id, role_ids, member=is_member)
    if request.is_json:
        return jsonify(_world_json()["users"][str(user_id)])
    return redirect(url_for("dev_tools.index") + f"#user-{user_id}")


def _world_json():
    world = _world()
    keys = {u["id"]: u["key"] for u in fixtures.USERS}
    return {
        "guilds": {
            str(g.id): {
                "name": g.name,
                "roles": {str(r.id): r.name for r in g.roles[1:]},
                "channels": {str(c.id): c.name for c in g.channels},
            } for g in world.guilds.values()
        },
        "users": {
            str(u.id): {
                "key": keys.get(u.id),
                "name": u.name,
                "login_url": f"/_dev/login?user={keys.get(u.id, u.id)}",
                "memberships": {str(m.guild.id): [r.name for r in m.roles[1:]] for m in world.memberships(u.id)},
            } for u in world.users.values()
        },
    }


@dev_tools.route("/api/world")
async def world_json():
    return jsonify(_world_json())


@dev_tools.route("/api/outbox")
async def outbox_json():
    return jsonify(OUTBOX)


@dev_tools.route("/api/outbox/clear", methods=["POST"])
async def outbox_clear():
    OUTBOX.clear()
    return redirect(url_for("dev_tools.index") + "#outbox") if not request.is_json else jsonify(ok=True)


LINKS = [
    ("Home", "/"),
    ("My account", "/me"),
    ("My presets", "/presets/me"),
    ("Delete my data (confirm page)", "/purgeme"),
    ("Presets: dev-admin namespace", "/presets/manage/dev-admin"),
    ("Presets: all namespaces", "/presets"),
    ("Ranked choice: public election", "/ranked_choice/1"),
    ("Ranked choice: Voter-only election", "/ranked_choice/2"),
    ("Elections: admin list (log in as admin)", "/elections"),
    ("Elections: new election form", "/elections/new"),
    ("Elections: edit a draft", "/elections/4/edit"),
    ("Elections: results of a closed election", "/elections/3/results"),
    ("Triforce texts: submit", "/triforcetexts/dev"),
    ("Triforce texts: moderation (admin)", "/triforcetexts/dev/moderation"),
    ("testdata: active role-gated election", "/ranked_choice/1004"),
    ("testdata: all preset namespaces", "/presets"),
    ("Racetime verification", "/racetime/verification/initiate"),
    ("Error page", "/error?code=500&message=Example"),
    ("API docs (OpenAPI)", "/api/v1/docs"),
    ("Healthcheck", "/healthcheck"),
]


def _membership_form(guild, user_id) -> str:
    """One guild's member checkbox and role checkboxes for a user."""
    member = guild._members.get(user_id)
    have = {r.id for r in member.roles} if member else set()
    boxes = "".join(
        f'<label><input type="checkbox" name="role" value="{r.id}" {"checked" if r.id in have else ""}> '
        f'{html.escape(r.name)}</label> ' for r in guild.roles[1:])
    return (
        f'<form method="post" action="/_dev/members/{user_id}" class="muted">'
        f'<input type="hidden" name="guild_id" value="{guild.id}">'
        f'<b>{html.escape(guild.name)}</b>: <label><input type="checkbox" name="member" '
        f'{"checked" if member else ""}> member</label> {boxes}<button class="secondary">Save</button></form>')


def _user_card(world, u, spec: dict) -> str:
    forms = [_membership_form(g, u.id) for g in world.guilds.values()]
    login = f"/_dev/login?user={spec.get('key', u.id)}&next=/_dev/"
    return (
        f'<div class="card" id="user-{u.id}" style="display:block"><div style="display:flex;justify-content:space-between">'
        f'<div><b>{html.escape(u.name)}</b> <code>{html.escape(spec.get("key", ""))}</code> '
        f'<span class="muted">{u.id}</span><div class="muted">{html.escape(spec.get("description", "Added at runtime."))}</div></div>'
        f'<a class="button" href="{html.escape(login)}">Log in as</a></div>{"".join(forms)}</div>')


@dev_tools.route("/")
async def index():
    world = _world()
    current_id = current_app.discord.user_id
    current = world.users.get(int(current_id)) if current_id else None
    keys = {u["id"]: u for u in fixtures.USERS}

    import testdata

    testdata_ids = {m["id"] for m in testdata.world()["members"]}
    rows = [_user_card(world, u, keys.get(u.id, {})) for u in world.users.values() if u.id not in testdata_ids]

    rows.append(
        f'<details class="card" style="display:block"><summary><b>{len(testdata_ids)} users from testdata/</b> '
        '<span class="muted">anonymized, production-shaped; log in with ?user=&lt;id&gt;</span></summary>'
        + " ".join(f'<a href="/_dev/login?user={uid}&amp;next=/_dev/">{html.escape(world.users[uid].name)}</a>'
                   for uid in sorted(testdata_ids) if uid in world.users)
        + '</details>')
    links = "".join(f'<li><a href="{href}">{html.escape(name)}</a></li>' for name, href in LINKS)
    outbox = "".join(
        f'<div class="card" style="display:block"><b>{html.escape(m["target"])}</b> '
        f'<span class="muted">{html.escape(m["at"])}</span><pre style="white-space:pre-wrap">'
        f'{html.escape(m["content"] or "")}</pre>'
        + "".join(f'<pre class="muted" style="white-space:pre-wrap">{html.escape(str(e))}</pre>' for e in m["embeds"])
        + "</div>" for m in reversed(OUTBOX)) or '<p class="muted">Nothing sent yet.</p>'

    who = (f'Logged in as <b>{html.escape(current.name)}</b> ({current.id}). <a href="/_dev/logout">Log out</a>'
           if current else "Not logged in.")
    body = f"""
<h1>SahasrahBot dev tools</h1>
<p>{who}</p>
<p class="muted">New user: <code>/_dev/login?user=new&amp;name=alice&amp;roles=Admin,Voter&amp;next=/me</code>.
API key for <code>Authorization</code> headers: <code>{fixtures.API_KEY}</code>.</p>
<h2>Pages</h2><ul>{links}</ul>
<h2>Users</h2>{"".join(rows)}
<h2 id="outbox">Discord outbox</h2>
<form method="post" action="/_dev/api/outbox/clear"><button class="secondary">Clear</button></form>{outbox}
"""
    return await render_template_string(PAGE, service="Discord, racetime.gg and SpeedGaming",
                                         title="SahasrahBot dev tools", body=body)

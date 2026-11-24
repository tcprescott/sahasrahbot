"""Build the anonymized fixture slices in ``testdata/`` from a production MySQL dump.

Usage (from the repo root, with the dump unzipped somewhere OUTSIDE the repo)::

    cat /path/to/Dump20261123/*.sql | poetry run python -I scripts/scrub_prod_dump.py

The dump is read as text from standard input: this script parses the ``CREATE TABLE``
and ``INSERT`` statements of a MySQL Workbench / mysqldump export (the per-table files
concatenated, or one big file) and never executes any of it. Output goes to
``testdata/`` next to this script.

What it does, per feature (see ``FEATURES``):

1. picks a small, connected slice of rows (a few tournaments, elections, namespaces),
2. replaces every personal or secret value with a consistent fake one: Discord user,
   guild, channel, role, message and thread ids, racetime ids, usernames, display
   names, Twitch names, VOD links, free-text notes, access tokens,
3. renumbers primary keys and rewrites foreign keys to match,
4. writes ``testdata/<feature>.json``, and
5. checks the output: every real id, name and token taken from the dump is searched
   for in the output, and the run fails if any of them is found.

The raw dump must never be committed. ``testdata/`` holds only this script's output.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys

# --------------------------------------------------------------------------------------
# Reading the dump
# --------------------------------------------------------------------------------------

_CREATE_RE = re.compile(r"^CREATE TABLE `(?P<name>[^`]+)` \($", re.M)
_INSERT_RE = re.compile(r"^INSERT INTO `(?P<name>[^`]+)` VALUES ", re.M)
_ESCAPES = {"0": "\0", "b": "\b", "n": "\n", "r": "\r", "t": "\t", "Z": "\x1a"}


def _parse_values(text: str, pos: int):
    """Parse ``(...),(...);`` starting at ``pos``. Returns (rows, end position)."""
    rows = []
    n = len(text)
    while pos < n:
        if text[pos] != "(":
            raise ValueError(f"expected '(' at {pos}: {text[pos:pos + 40]!r}")
        pos += 1
        row = []
        while True:
            c = text[pos]
            if c == "'":
                pos += 1
                buf = []
                while True:
                    c = text[pos]
                    if c == "\\":
                        nxt = text[pos + 1]
                        buf.append(_ESCAPES.get(nxt, nxt))
                        pos += 2
                    elif c == "'":
                        if text[pos + 1] == "'":
                            buf.append("'")
                            pos += 2
                        else:
                            pos += 1
                            break
                    else:
                        buf.append(c)
                        pos += 1
                row.append("".join(buf))
            else:
                end = pos
                while text[end] not in ",)":
                    end += 1
                token = text[pos:end].strip()
                pos = end
                if token == "NULL":
                    row.append(None)
                elif token.startswith("_binary"):
                    raise ValueError("binary column values are not supported")
                elif re.fullmatch(r"-?\d+", token):
                    row.append(int(token))
                else:
                    row.append(float(token))
            c = text[pos]
            pos += 1
            if c == ")":
                break
            if c != ",":
                raise ValueError(f"unexpected {c!r} at {pos}")
        rows.append(row)
        c = text[pos]
        pos += 1
        if c == ";":
            return rows, pos
        if c != ",":
            raise ValueError(f"unexpected {c!r} after row at {pos}")
    raise ValueError("unterminated INSERT")


def _columns(body: str):
    return [m.group(1) for m in re.finditer(r"^\s+`([^`]+)`", body, re.M)]


def load_dump(text: str) -> dict:
    """Return {table: (columns, rows)} for every table in the dump text."""
    text = text.replace("\r\n", "\n")
    tables = {}
    for m in _CREATE_RE.finditer(text):
        body = text[m.end():text.index("\n)", m.end())]
        tables[m.group("name")] = (_columns(body), [])
    for m in _INSERT_RE.finditer(text):
        rows, _ = _parse_values(text, m.end())
        tables[m.group("name")][1].extend(rows)
    return tables


def as_dicts(tables: dict, table: str) -> list:
    if table not in tables:
        return []
    cols, rows = tables[table]
    return [dict(zip(cols, r)) for r in rows]


# --------------------------------------------------------------------------------------
# Which rows to keep. Ids are the dump's own primary keys; they are not personal data.
# --------------------------------------------------------------------------------------

# Async tournaments: (tournament id, max runners kept or None for all of them).
ASYNC_TOURNAMENTS = [(10, None), (7, None), (11, 25), (4, 20)]
# Ranked choice elections: (election id, max voters kept or None, candidates are people).
ELECTIONS = [(3, None, True), (8, None, False), (9, None, False), (11, None, True),
             (12, 60, True), (14, 60, False)]
# Preset namespaces: these plus a sample of others.
PRESET_NAMESPACES = [125, 339, 340]
PRESET_NAMESPACE_SAMPLE = 9

# Primary keys in the output start here, clear of the dev server's hand-made rows.
ID_BASE = 1001

# Fake Discord snowflakes, one prefix per kind. The checks below rely on every big
# integer in the output starting with one of these.
SNOWFLAKE_BASE = {
    "user": 910_000_000_000_000_000,
    "guild": 920_000_000_000_000_000,
    "channel": 930_000_000_000_000_000,
    "role": 940_000_000_000_000_000,
    "message": 950_000_000_000_000_000,
    "thread": 960_000_000_000_000_000,
}

_ADJECTIVES = ["amber", "brisk", "cobalt", "dusky", "ember", "fable", "gilded", "hollow", "ivory",
               "jade", "keen", "lunar", "mossy", "nimble", "opal", "plucky", "quiet", "russet",
               "sable", "tidal", "umber", "vivid", "wily", "zesty"]
_NOUNS = ["lynx", "heron", "otter", "finch", "marten", "newt", "osprey", "pika", "quail", "raven",
          "stoat", "tapir", "urchin", "vole", "wren", "yak", "badger", "cricket", "dingo", "egret"]
_PEOPLE_FIRST = ["Alex", "Blair", "Casey", "Devon", "Emery", "Frankie", "Gray", "Harper", "Indy",
                 "Jordan", "Kai", "Logan", "Morgan", "Noel", "Oakley", "Parker", "Quinn", "Reese",
                 "Sage", "Taylor", "Umi", "Val", "Wren", "Xen", "Yael", "Zion"]
_RUNNER_NOTES = ["GG, fun seed.", "Rough start but recovered.", "Forgot a key in the dungeon, cost a few minutes.",
                 "Clean run, happy with it.", "Lost a heart piece route, oh well.", "VOD has a short gap near the end.",
                 "Started the timer late, video is accurate.", "Big skip worked first try.", "Got lost in the dark world.",
                 "Thanks for running this!"]
_REVIEWER_NOTES = ["Looks good.", "lgtm", "Times match the VOD.", "Requires retiming.", "VOD is incomplete.",
                   "Accepted after retime.", "No issues found."]
_REATTEMPT_REASONS = ["Game crashed early.", "Wrong seed loaded.", "Stream dropped at the start.",
                      "Emulator froze.", "Misread the settings."]
_SAFE_SHORT_TEXT = re.compile(r"[A-Za-z0-9 #._:/-]{0,24}")
_SAFE_NUMBERISH = re.compile(r"[0-9:./ ]{0,20}")


class Picker:
    """Deterministic stand-in for ``random``: the same label always gives the same picks,
    so regenerating from the same dump gives the same files."""

    def __init__(self, label: str):
        self.label = label
        self.calls = 0

    def _int(self) -> int:
        self.calls += 1
        digest = hashlib.sha256(f"{self.label}:{self.calls}".encode()).digest()
        return int.from_bytes(digest[:8], "big")

    def randint(self, low: int, high: int) -> int:
        return low + self._int() % (high - low + 1)

    def choice(self, seq):
        return seq[self._int() % len(seq)]

    def sample(self, seq, k: int) -> list:
        pool = list(seq)
        return [pool.pop(self._int() % len(pool)) for _ in range(k)]


class Faker:
    """Hands out consistent fake values. The same real value always gets the same fake."""

    def __init__(self, seed: str = "20261123"):
        self.rng = Picker(f"faker-{seed}")
        self.maps = {}
        self.counters = {}
        self.real = {"ids": set(), "names": set(), "secrets": set()}

    def _next(self, kind):
        self.counters[kind] = self.counters.get(kind, 0) + 1
        return self.counters[kind]

    def map(self, kind, real, make):
        if real is None:
            return None
        key = (kind, real)
        if key not in self.maps:
            self.maps[key] = make(self._next(kind))
        return self.maps[key]

    def snowflake(self, kind, real):
        if real is None:
            return None
        self.real["ids"].add(int(real))
        return self.map(f"sf-{kind}", int(real), lambda n: SNOWFLAKE_BASE[kind] + n)

    def pk(self, table, real):
        return self.map(f"pk-{table}", real, lambda n: ID_BASE + n - 1)

    def handle(self, n):
        adj = _ADJECTIVES[(n - 1) % len(_ADJECTIVES)]
        noun = _NOUNS[((n - 1) // len(_ADJECTIVES)) % len(_NOUNS)]
        return f"{adj.capitalize()}{noun.capitalize()}{n:03d}"

    def token(self, length=14):
        alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return "".join(self.rng.choice(alphabet) for _ in range(length))

    def pick(self, options):
        return self.rng.choice(options)


def _note(f: Faker, value, options):
    if value is None or value == "":
        return value
    return f.pick(options)


def _clean_short(value, fallback):
    if value is None:
        return None
    return value if _SAFE_SHORT_TEXT.fullmatch(value) else fallback


# --------------------------------------------------------------------------------------
# Users and Discord ids
# --------------------------------------------------------------------------------------

class World:
    """The users, guilds, channels and roles the fixtures refer to, all fake."""

    def __init__(self, faker: Faker, tables: dict):
        self.f = faker
        self.users_by_pk = {u["id"]: u for u in as_dicts(tables, "users")}
        self.users_by_discord = {u["discord_user_id"]: u for u in self.users_by_pk.values() if u["discord_user_id"]}
        self.kept_users = {}  # old users.id -> fake row
        self.discord_only = {}  # fake discord id -> fake name (people with no users row)
        self.guilds = {}  # fake guild id -> {"name", "channels": {id: name}, "roles": {id: name}}
        self.role_members = {}  # fake role id -> set of fake discord ids
        for u in self.users_by_pk.values():
            for col in ("display_name", "twitch_name"):
                if u[col]:
                    faker.real["names"].add(u[col])
            if u["rtgg_id"]:
                faker.real["secrets"].add(u["rtgg_id"])
            if u["rtgg_access_token"]:
                faker.real["secrets"].add(u["rtgg_access_token"])
            if u["discord_user_id"]:
                faker.real["ids"].add(u["discord_user_id"])

    def user_pk(self, old_pk):
        """Keep users.id ``old_pk`` and return its new primary key."""
        if old_pk is None:
            return None
        if old_pk not in self.kept_users:
            real = self.users_by_pk[old_pk]
            new_pk = self.f.pk("users", old_pk)
            discord_id = self.f.snowflake("user", real["discord_user_id"])
            name = self.f.map("name", discord_id or ("pk", old_pk), self.f.handle)
            self.kept_users[old_pk] = {
                "id": new_pk,
                "discord_user_id": discord_id,
                "display_name": name,
                "twitch_name": name.lower() if real["twitch_name"] else None,
                "rtgg_id": self.f.map("rtgg", real["rtgg_id"], lambda n: f"fk{n:04d}{self.f.token(10)}"),
                "rtgg_access_token": None,
                "test_user": False,
                "created": real["created"],
                "updated": real["updated"],
            }
        return self.kept_users[old_pk]["id"]

    def discord_user(self, real_discord_id):
        """A fake Discord user id; keeps that person's users row too, if they have one."""
        if real_discord_id is None:
            return None
        real = self.users_by_discord.get(real_discord_id)
        if real is not None:
            self.user_pk(real["id"])
            return self.kept_users[real["id"]]["discord_user_id"]
        fake = self.f.snowflake("user", real_discord_id)
        self.discord_only.setdefault(fake, self.f.map("name", fake, self.f.handle))
        return fake

    def guild(self, real_id):
        fake = self.f.snowflake("guild", real_id)
        self.guilds.setdefault(fake, {"name": f"Prod-like Community {len(self.guilds) + 1}", "channels": {}, "roles": {}})
        return fake

    def channel(self, guild_fake, real_id, name):
        if real_id is None:
            return None
        fake = self.f.snowflake("channel", real_id)
        self.guilds[guild_fake]["channels"].setdefault(fake, name)
        return fake

    def role(self, guild_fake, real_id, name):
        if real_id is None:
            return None
        fake = self.f.snowflake("role", real_id)
        self.guilds[guild_fake]["roles"].setdefault(fake, name)
        self.role_members.setdefault(fake, set())
        return fake

    def export_users(self):
        return sorted(self.kept_users.values(), key=lambda r: r["id"])

    def export_world(self):
        members = {}
        for row in self.kept_users.values():
            if row["discord_user_id"]:
                members[row["discord_user_id"]] = row["display_name"]
        members.update(self.discord_only)
        roles_of = {}
        for role_id, people in self.role_members.items():
            for person in people:
                roles_of.setdefault(person, []).append(role_id)
        guild_of_role = {r: g for g, spec in self.guilds.items() for r in spec["roles"]}
        out_members = []
        for discord_id, name in sorted(members.items()):
            memberships = {str(g): [] for g in self.guilds}
            for role_id in sorted(roles_of.get(discord_id, [])):
                memberships[str(guild_of_role[role_id])].append(role_id)
            out_members.append({"id": discord_id, "name": name, "memberships": memberships})
        return {
            "guilds": [
                {"id": g, "name": spec["name"],
                 "channels": sorted([cid, n] for cid, n in spec["channels"].items()),
                 "roles": sorted([rid, n] for rid, n in spec["roles"].items())}
                for g, spec in sorted(self.guilds.items())
            ],
            "members": out_members,
        }


# --------------------------------------------------------------------------------------
# Feature slices
# --------------------------------------------------------------------------------------

def slice_asynctournament(tables, world: World):
    f = world.f
    rng = Picker("slice-1")
    out = {k: [] for k in ("AsyncTournament", "AsyncTournamentPermissions", "AsyncTournamentPermalinkPool",
                           "AsyncTournamentPermalink", "AsyncTournamentLiveRace", "AsyncTournamentRace",
                           "AsyncTournamentReviewNotes", "AsyncTournamentWhitelist")}
    tournaments = {t["id"]: t for t in as_dicts(tables, "asynctournament")}
    pools = as_dicts(tables, "asynctournamentpermalinkpool")
    links = as_dicts(tables, "asynctournamentpermalink")
    lives = as_dicts(tables, "asynctournamentliverace")
    races = as_dicts(tables, "asynctournamentrace")
    for t_id, max_runners in ASYNC_TOURNAMENTS:
        t = tournaments[t_id]
        guild = world.guild(t["guild_id"])
        new_t = f.pk("asynctournament", t_id)
        out["AsyncTournament"].append({
            "id": new_t, "name": t["name"], "guild_id": guild,
            "channel_id": world.channel(guild, t["channel_id"], f"async-{new_t}"),
            "report_channel_id": world.channel(guild, t["report_channel_id"], f"async-{new_t}-reports"),
            "owner_id": world.discord_user(t["owner_id"]),
            "created": t["created"], "updated": t["updated"], "active": bool(t["active"]),
            "allowed_reattempts": t["allowed_reattempts"] or 0, "runs_per_pool": t["runs_per_pool"],
            "customization": _clean_short(t["customization"], "default"),
        })
        t_pools = [p for p in pools if p["tournament_id"] == t_id]
        pool_ids = {p["id"] for p in t_pools}
        for p in t_pools:
            out["AsyncTournamentPermalinkPool"].append({
                "id": f.pk("pool", p["id"]), "tournament_id": new_t,
                "name": _clean_short(p["name"], "pool"), "preset": _clean_short(p["preset"], None),
                "created": p["created"], "updated": p["updated"],
            })
        t_links = [lk for lk in links if lk["pool_id"] in pool_ids]
        link_ids = {lk["id"] for lk in t_links}
        for lk in t_links:
            n = f.pk("permalink", lk["id"])
            url = lk["url"] or ""
            if "alttpr.com" in url:
                url = f"https://alttpr.com/h/{f.token(10)}"
            elif "avianart" in url:
                url = f"https://avianart.games/perm/{f.token(12)}"
            else:
                url = f"https://example.com/seed{n}"
            out["AsyncTournamentPermalink"].append({
                "id": n, "pool_id": f.pk("pool", lk["pool_id"]), "url": url,
                "live_race": bool(lk["live_race"]), "notes": _clean_short(lk["notes"], f"Seed {n}"),
                "par_time": lk["par_time"], "par_updated_at": lk["par_updated_at"],
                "created": lk["created"], "updated": lk["updated"],
            })
        t_lives = [lr for lr in lives if lr["tournament_id"] == t_id]
        for lr in t_lives:
            n = f.pk("liverace", lr["id"])
            out["AsyncTournamentLiveRace"].append({
                "id": n, "tournament_id": new_t, "pool_id": f.pk("pool", lr["pool_id"]),
                "permalink_id": f.pk("permalink", lr["permalink_id"]) if lr["permalink_id"] in link_ids else None,
                "racetime_slug": f"alttpr/fixture-room-{n:04d}" if lr["racetime_slug"] else None,
                "episode_id": f.map("episode", lr["episode_id"], lambda k: 900000 + k),
                "match_title": f"Live race {n}" if lr["match_title"] else None,
                "status": lr["status"], "created": lr["created"], "updated": lr["updated"],
            })
        live_ids = {lr["id"] for lr in t_lives}
        t_races = [r for r in races if r["tournament_id"] == t_id]
        runners = sorted({r["user_id"] for r in t_races})
        if max_runners is not None and len(runners) > max_runners:
            runners = sorted(rng.sample(runners, max_runners))
        keep = set(runners)
        for r in t_races:
            if r["user_id"] not in keep or r["permalink_id"] not in link_ids:
                continue
            n = f.pk("race", r["id"])
            vod = r["runner_vod_url"]
            out["AsyncTournamentRace"].append({
                "id": n, "tournament_id": new_t, "permalink_id": f.pk("permalink", r["permalink_id"]),
                "user_id": world.user_pk(r["user_id"]),
                "thread_id": f.snowflake("thread", r["thread_id"]),
                "thread_open_time": r["thread_open_time"], "thread_timeout_time": r["thread_timeout_time"],
                "start_time": r["start_time"], "end_time": r["end_time"],
                "created": r["created"], "updated": r["updated"],
                "status": r["status"], "review_status": r["review_status"],
                "reviewed_by_id": world.user_pk(r["reviewed_by_id"]), "reviewed_at": r["reviewed_at"],
                "reviewer_notes": _note(f, r["reviewer_notes"], _REVIEWER_NOTES),
                "runner_notes": _note(f, r["runner_notes"], _RUNNER_NOTES),
                "runner_vod_url": None if vod is None else f"https://youtu.be/fixture{n:05d}",
                "run_igt": r["run_igt"] if r["run_igt"] and _SAFE_NUMBERISH.fullmatch(r["run_igt"]) else None,
                "run_collection_rate": r["run_collection_rate"]
                if r["run_collection_rate"] and _SAFE_NUMBERISH.fullmatch(r["run_collection_rate"]) else None,
                "reattempted": None if r["reattempted"] is None else bool(r["reattempted"]),
                "reattempt_reason": _note(f, r["reattempt_reason"], _REATTEMPT_REASONS),
                "live_race_id": f.pk("liverace", r["live_race_id"]) if r["live_race_id"] in live_ids else None,
                "score": r["score"], "score_updated_at": r["score_updated_at"],
            })
        kept_race_ids = {r["id"] for r in t_races if r["user_id"] in keep}
        for note in as_dicts(tables, "asynctournamentreviewnotes"):
            if note["race_id"] in kept_race_ids:
                out["AsyncTournamentReviewNotes"].append({
                    "id": f.pk("reviewnote", note["id"]), "race_id": f.pk("race", note["race_id"]),
                    "author_id": world.user_pk(note["author_id"]), "note": f.pick(_REVIEWER_NOTES),
                    "created": note["created"],
                })
        for w in as_dicts(tables, "asynctournamentwhitelist"):
            if w["tournament_id"] == t_id:
                out["AsyncTournamentWhitelist"].append({
                    "id": f.pk("whitelist", w["id"]), "tournament_id": new_t, "user_id": world.user_pk(w["user_id"]),
                    "discord_user_id": world.discord_user(w["discord_user_id"]),
                    "created": w["created"], "updated": w["updated"],
                })
        for perm in as_dicts(tables, "asynctournamentpermissions"):
            if perm["tournament_id"] != t_id:
                continue
            out["AsyncTournamentPermissions"].append({
                "id": f.pk("asyncperm", perm["id"]), "tournament_id": new_t, "role": perm["role"],
                "user_id": world.user_pk(perm["user_id"]),
                "discord_role_id": world.role(guild, perm["discord_role_id"], f"Async {perm['role']} {new_t}"),
                "created": perm["created"], "updated": perm["updated"],
            })
    return {
        "feature": "asynctournament",
        "description": "Async tournaments: a small active one, a two-runs-per-pool one, and runner samples "
                       "from two large qualifiers, with pools, seeds, live races, permissions and races.",
        "tables": [[k, v] for k, v in out.items() if v],
    }


def _results_text(candidates, ballots, seats):
    import pyrankvote

    objs = {c["name"]: pyrankvote.Candidate(c["name"]) for c in candidates}
    result = pyrankvote.single_transferable_vote(
        candidates=list(objs.values()),
        ballots=[pyrankvote.Ballot([objs[name] for name in ballot]) for ballot in ballots],
        number_of_seats=seats,
    )
    return str(result), {w.name for w in result.get_winners()}


def slice_ranked_choice(tables, world: World):
    f = world.f
    rng = Picker("slice-2")
    out = {"RankedChoiceElection": [], "RankedChoiceCandidate": [], "RankedChoiceAuthorizedVoters": [],
           "RankedChoiceVotes": []}
    elections = {e["id"]: e for e in as_dicts(tables, "ranked_choice_election")}
    candidates = as_dicts(tables, "ranked_choice_candidate")
    votes = as_dicts(tables, "ranked_choice_votes")
    voters_allowed = as_dicts(tables, "ranked_choice_authorized_voters")
    people_names = iter(f"{first} {last}." for last in "ABCDEFGHJKLMNPRSTW" for first in _PEOPLE_FIRST)
    for e_id, max_voters, people in ELECTIONS:
        e = elections[e_id]
        new_e = f.pk("election", e_id)
        guild = world.guild(e["guild_id"]) if e["guild_id"] else None
        role = world.role(guild, e["voter_role_id"], f"Voter {new_e}") if guild else None
        e_cands = [c for c in candidates if c["election_id"] == e_id]
        cand_rows = {}
        for c in e_cands:
            if people:
                f.real["names"].add(c["name"])
                name = next(people_names)
            else:
                name = c["name"]
            cand_rows[c["id"]] = {
                "id": f.pk("candidate", c["id"]), "election_id": new_e, "name": name, "winner": c["winner"],
                "created": c["created"], "updated": c["updated"],
            }
        e_votes = [v for v in votes if v["election_id"] == e_id and v["candidate_id"] in cand_rows]
        voters = sorted({v["user_id"] for v in e_votes})
        if max_voters is not None and len(voters) > max_voters:
            voters = sorted(rng.sample(voters, max_voters))
        keep = set(voters)
        ballots = {}
        for v in sorted(e_votes, key=lambda v: (v["user_id"], v["rank"] or 0, v["id"])):
            if v["user_id"] not in keep:
                continue
            fake_voter = world.discord_user(v["user_id"])
            if role:
                world.role_members[role].add(fake_voter)
            out["RankedChoiceVotes"].append({
                "id": f.pk("vote", v["id"]), "election_id": new_e, "user_id": fake_voter,
                "candidate_id": cand_rows[v["candidate_id"]]["id"], "rank": v["rank"],
                "created": v["created"], "updated": v["updated"],
            })
            ballots.setdefault(fake_voter, []).append(cand_rows[v["candidate_id"]]["name"])
        for a in voters_allowed:
            if a["election_id"] == e_id:
                out["RankedChoiceAuthorizedVoters"].append({
                    "id": f.pk("authvoter", a["id"]), "election_id": new_e, "user_id": world.discord_user(a["user_id"]),
                })
        results = None
        if e["results"] is not None:
            # The stored text names the real candidates and counts every real ballot:
            # recompute it from the kept ballots, the same way the bot does.
            results, winners = _results_text(list(cand_rows.values()), list(ballots.values()), e["seats"])
            for row in cand_rows.values():
                row["winner"] = row["name"] in winners or None
        out["RankedChoiceCandidate"].extend(cand_rows.values())
        noun = "candidates" if people else "options"
        description = (f"Rank the {noun} in order of preference. "
                       f"(Fixture election {new_e}; the original description was removed.)")
        out["RankedChoiceElection"].append({
            "id": new_e, "guild_id": guild,
            "channel_id": world.channel(guild, e["channel_id"], f"elections-{new_e}") if guild else None,
            "message_id": f.snowflake("message", e["message_id"]),
            "owner_id": world.discord_user(e["owner_id"]),
            "title": e["title"],
            "description": description if e["description"] else None,
            "show_vote_count": bool(e["show_vote_count"]), "active": bool(e["active"]),
            "private": bool(e["private"]), "voter_role_id": role, "seats": e["seats"],
            "results": results, "created": e["created"], "updated": e["updated"],
        })
    # Votes reference candidates: keep the tables in foreign-key order.
    return {
        "feature": "ranked_choice",
        "description": "Ranked choice elections: open and role-gated, one with an authorized-voter list, "
                       "active and finished, multi-seat, with sampled ballots and recomputed results.",
        "tables": [[k, out[k]] for k in ("RankedChoiceElection", "RankedChoiceCandidate",
                                         "RankedChoiceAuthorizedVoters", "RankedChoiceVotes") if out[k]],
    }


def slice_presets(tables, world: World, repo: pathlib.Path):
    f = world.f
    rng = Picker("slice-3")
    namespaces = as_dicts(tables, "presetnamespaces")
    for ns in namespaces:
        if ns["name"]:
            f.real["names"].add(ns["name"])
    collaborators = as_dicts(tables, "presetnamespacecollaborators")
    others = [ns["id"] for ns in namespaces if ns["id"] not in PRESET_NAMESPACES]
    chosen = set(PRESET_NAMESPACES) | set(rng.sample(others, min(PRESET_NAMESPACE_SAMPLE, len(others))))
    ns_rows, collab_rows, preset_rows = [], [], []
    # The dump has no `presets` table, so each namespace gets presets copied from the
    # public preset files in this repo.
    library = {d.name: sorted(d.glob("*.yaml")) for d in sorted((repo / "presets").iterdir()) if d.is_dir()}
    library = {k: v for k, v in library.items() if v}
    preset_id = 0
    for ns in sorted(namespaces, key=lambda n: n["id"]):
        if ns["id"] not in chosen:
            continue
        owner = world.discord_user(ns["discord_user_id"])
        new_ns = f.pk("namespace", ns["id"])
        ns_rows.append({"id": new_ns, "name": f"ns-{world.discord_only.get(owner) or _name_of(world, owner)}".lower(),
                        "discord_user_id": owner})
        for c in collaborators:
            if c["namespace_id"] == ns["id"]:
                collab_rows.append({"id": f.pk("collab", c["id"]), "namespace_id": new_ns,
                                    "discord_user_id": world.discord_user(c["discord_user_id"])})
        for randomizer in rng.sample(sorted(library), rng.randint(1, 3)):
            for path in rng.sample(library[randomizer], min(len(library[randomizer]), rng.randint(1, 3))):
                preset_id += 1
                preset_rows.append({
                    "id": ID_BASE + preset_id - 1, "namespace_id": new_ns, "randomizer": randomizer,
                    "preset_name": path.stem, "content": path.read_text(encoding="utf-8"),
                    "generated_count": rng.randint(0, 250),
                })
    return {
        "feature": "presets",
        "description": "Preset namespaces (including every namespace with collaborators) with presets copied "
                       "from this repo's presets/ files, because the dump has no presets table.",
        "tables": [["PresetNamespaces", ns_rows], ["PresetNamespaceCollaborators", collab_rows],
                   ["Presets", preset_rows]],
    }


def _name_of(world: World, discord_id):
    for row in world.kept_users.values():
        if row["discord_user_id"] == discord_id:
            return row["display_name"]
    return str(discord_id)


# --------------------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------------------

_BIG_INT = re.compile(r"(?<![\d.])\d{15,20}(?!\d)")


def find_leaks(outputs: dict, faker: Faker, tables: dict, public_texts=frozenset()) -> list:
    """Every way a real value could have survived, as a list of messages.

    ``public_texts`` are strings copied verbatim from files already in this repo
    (the preset YAML), which are exempt from the name check.
    """
    problems = []
    # Every Discord-sized number in the dump, from any column of any table.
    real_numbers = set(faker.real["ids"])
    for cols, rows in tables.values():
        for row in rows:
            for v in row:
                if isinstance(v, int) and v >= 10 ** 14:
                    real_numbers.add(v)
                elif isinstance(v, str):
                    real_numbers.update(int(m) for m in _BIG_INT.findall(v))
    fake_prefixes = tuple(str(b)[:2] for b in SNOWFLAKE_BASE.values())
    names = {n.casefold() for n in faker.real["names"] if n and len(n.strip()) >= 3}
    secrets = {s for s in faker.real["secrets"] if s and len(s) >= 6}
    name_res = [(n, re.compile(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])")) for n in names if len(n) >= 5]
    for feature, text in outputs.items():
        for m in _BIG_INT.finditer(text):
            value = int(m.group())
            if value in real_numbers:
                problems.append(f"{feature}: real id {value} is present")
            elif not m.group().startswith(fake_prefixes):
                problems.append(f"{feature}: {value} is not one of the fake id ranges")
        for s in secrets:
            if s in text:
                problems.append(f"{feature}: a real racetime id or token is present")
        data = json.loads(text)
        for value in _strings(data):
            if value in public_texts:
                continue
            folded = value.casefold()
            if folded in names:
                problems.append(f"{feature}: real name {value!r} is present")
                continue
            for name, pattern in name_res:
                if pattern.search(folded):
                    problems.append(f"{feature}: real name {name!r} appears inside {value[:60]!r}")
    return problems


def _strings(data):
    if isinstance(data, str):
        yield data
    elif isinstance(data, dict):
        for v in data.values():
            yield from _strings(v)
    elif isinstance(data, list):
        for v in data:
            yield from _strings(v)


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

# Strings that are allowed to equal a real username because they are ordinary words
# the fixtures use on purpose (pool names, preset names, candidate options).
ALLOWED_WORDS_FILE = "allowed_words.txt"


def build(dump_text: str, repo: pathlib.Path):
    tables = load_dump(dump_text)
    faker = Faker()
    world = World(faker, tables)
    features = {
        "asynctournament": slice_asynctournament(tables, world),
        "ranked_choice": slice_ranked_choice(tables, world),
        "presets": slice_presets(tables, world, repo),
    }
    users = {
        "feature": "users",
        "description": "Every fake user the feature files refer to, and the fake Discord world "
                       "(guilds, channels, roles, members) the dev server builds from them.",
        "tables": [["Users", world.export_users()]],
        "world": world.export_world(),
    }
    return tables, faker, {"users": users, **features}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check-only", action="store_true", help="build and check, but write nothing")
    args = parser.parse_args(argv)
    repo = pathlib.Path(__file__).resolve().parent.parent
    out_dir = repo / "testdata"
    if sys.stdin.isatty():
        parser.error("pipe the dump's .sql files into standard input")

    tables, faker, data = build(sys.stdin.read(), repo)
    allowed = set()
    allowed_path = out_dir / ALLOWED_WORDS_FILE
    if allowed_path.exists():
        allowed = {w.strip().casefold() for w in allowed_path.read_text().splitlines()
                   if w.strip() and not w.startswith("#")}
    faker.real["names"] = {n for n in faker.real["names"] if n.casefold() not in allowed}

    texts = {name: json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n"
             for name, payload in data.items()}
    preset_files = list((repo / "presets").glob("*/*.yaml"))
    public = {p.read_text(encoding="utf-8") for p in preset_files} | {p.stem for p in preset_files}
    problems = find_leaks(texts, faker, tables, public)
    if problems:
        print("Refusing to write: real values found in the output.", file=sys.stderr)
        for p in sorted(set(problems))[:200]:
            print("  " + p, file=sys.stderr)
        return 1
    for name, payload in data.items():
        counts = ", ".join(f"{model} {len(rows)}" for model, rows in payload["tables"])
        print(f"{name}: {counts}")
    if args.check_only:
        return 0
    out_dir.mkdir(exist_ok=True)
    for name, text in texts.items():
        (out_dir / f"{name}.json").write_text(text, encoding="utf-8")
    digest = hashlib.sha256("".join(texts[k] for k in sorted(texts)).encode()).hexdigest()[:12]
    print(f"Wrote {len(texts)} files to {out_dir} (content hash {digest}, generated {datetime.date.today()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

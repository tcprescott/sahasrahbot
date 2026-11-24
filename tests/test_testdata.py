"""The anonymized production-shaped fixtures in ``testdata/``.

Two kinds of checks: the data stays anonymous and consistent (no real-looking ids,
no tokens, every foreign key resolves), and real code runs against it (ranked choice tallies, namespaced preset lookup). A feature whose JSON
file has been deleted is skipped.
"""
import collections
import json
import re

import pytest

import testdata
from alttprbot import models

FAKE_SNOWFLAKE = re.compile(r"9[1-6]0{4}\d{12}")
BIG_INT = re.compile(r"(?<![0-9.])[0-9]{15,20}(?![0-9])")
FAKE_HANDLE = re.compile(r"[A-Z][a-z]+[A-Z][a-z]+\d{3}")

ALL_FILES = [testdata.USERS] + testdata.features()


def need(feature):
    if feature not in testdata.features():
        pytest.skip(f"testdata/{feature}.json was removed")


def _model_of_fk(model, column):
    field = model._meta.fields_map.get(column[:-3])
    if field is None or not hasattr(field, "related_model"):
        return None
    return field.related_model


@pytest.mark.parametrize("name", ALL_FILES)
def test_every_big_number_is_a_fake_snowflake(name):
    text = (testdata.HERE / f"{name}.json").read_text(encoding="utf-8")
    bad = [m.group() for m in BIG_INT.finditer(text) if not FAKE_SNOWFLAKE.fullmatch(m.group())]
    assert bad == []


def test_users_are_fake_and_tokenless():
    users = testdata.rows(testdata.USERS, "Users")
    assert users
    for u in users:
        assert FAKE_HANDLE.fullmatch(u["display_name"]), u["display_name"]
        assert u["twitch_name"] in (None, u["display_name"].lower())
        assert u["rtgg_access_token"] is None
        assert u["rtgg_id"] is None or u["rtgg_id"].startswith("fk")
    assert len({u["discord_user_id"] for u in users}) == len(users)


def test_world_covers_every_referenced_discord_id():
    world = testdata.world()
    members = {m["id"] for m in world["members"]}
    guilds = {g["id"]: g for g in world["guilds"]}
    channels = {c for g in guilds.values() for c, _ in g["channels"]}
    roles = {r for g in guilds.values() for r, _ in g["roles"]}
    for name in ALL_FILES:
        for model_name, rows in testdata.read(name)["tables"]:
            for row in rows:
                for column, value in row.items():
                    if value is None:
                        continue
                    if column in ("discord_user_id", "owner_id") or (
                            model_name in ("RankedChoiceVotes", "RankedChoiceAuthorizedVoters") and column == "user_id"):
                        assert value in members, (model_name, column, value)
                    elif column == "guild_id":
                        assert value in guilds
                    elif column in ("channel_id", "report_channel_id"):
                        assert value in channels
                    elif column in ("discord_role_id", "voter_role_id"):
                        assert value in roles


@pytest.mark.parametrize("name", ALL_FILES)
def test_foreign_keys_resolve(name):
    ids = collections.defaultdict(set)
    for file in ALL_FILES:
        for model_name, rows in testdata.read(file)["tables"]:
            ids[model_name].update(r["id"] for r in rows)
    for model_name, rows in testdata.read(name)["tables"]:
        model = getattr(models, model_name)
        for row in rows:
            for column, value in row.items():
                if not column.endswith("_id") or value is None:
                    continue
                target = _model_of_fk(model, column)
                if target is not None:
                    assert value in ids[target.__name__], (model_name, row["id"], column, value)


@pytest.mark.parametrize("name", testdata.features())
async def test_feature_loads_into_the_database(db, name):
    counts = await testdata.load(name)
    for model_name, rows in testdata.read(name)["tables"]:
        assert await getattr(models, model_name).all().count() == len(rows) == counts[model_name]


async def test_all_features_load_together(db):
    counts = await testdata.load()
    assert counts["Users"] == len(testdata.rows(testdata.USERS, "Users"))


async def test_ranked_choice_results_match_a_recount(db, directory):
    """Elections closed before counts were stored are recounted on their results
    page; the recount picks the winners production picked."""
    need("ranked_choice")
    from alttprbot.services import elections

    await testdata.load("ranked_choice")
    finished = [e for e in testdata.rows("ranked_choice", "RankedChoiceElection") if e["results"] and not e["active"]]
    assert finished
    won = collections.defaultdict(set)
    for c in testdata.rows("ranked_choice", "RankedChoiceCandidate"):
        if c["winner"]:
            won[c["election_id"]].add(c["id"])
    for row in finished:
        election = await models.RankedChoiceElection.get(id=row["id"])
        election.status = "closed"
        await election.save()
        results = await elections.results(row["id"])
        assert set(results["tally"]["winners"]) == won[row["id"]], row["title"]


async def test_namespaced_presets_resolve(db):
    need("presets")
    from alttprbot.alttprgen import generator

    await testdata.load("presets")
    namespaces = {n["id"]: n["name"] for n in testdata.rows("presets", "PresetNamespaces")}
    for preset in testdata.rows("presets", "Presets")[:10]:
        cls = generator.PRESET_CLASS_MAPPING[preset["randomizer"]]
        data = await cls(f"{namespaces[preset['namespace_id']]}/{preset['preset_name']}").fetch()
        assert data.preset_data is not None
        assert data.namespace == namespaces[preset["namespace_id"]]


def test_files_are_valid_json_with_a_description():
    for name in ALL_FILES:
        payload = json.loads((testdata.HERE / f"{name}.json").read_text(encoding="utf-8"))
        assert payload["feature"] == name
        assert payload["description"]

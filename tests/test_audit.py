"""Tests for the audit log: the service (alttprbot/services/audit.py), what each
service records, who it's attributed to on each front end, and reading it back
through /api/v1 and the MCP tool."""

import dataclasses
import datetime
from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, PermissionDeniedError
from alttprbot.services import (accounts, api_tokens, audit, elections, guild_config, presets,
                                triforce_texts)
from alttprbot_api import api
from alttprbot_api.blueprints import app_api
from alttprbot_discord import audit as discord_audit
from alttprbot_racetime import telemetry as racetime_telemetry
from tests.discord_fakes import FakeInteraction, FakeUser
from tests.test_api import CSRF, get_json, login, send_json  # noqa: F401 (fixture)

ALICE = 81000000000000001
BOB = 81000000000000002
OWNER = 81000000000000009
GUILD = 600
OTHER_GUILD = 601


def as_(user_id, name="alice", via=audit.VIA_WEBSITE, detail=None):
    return audit.acting(audit.Source(via=via, detail=detail, actor_discord_id=user_id, actor_name=name))


async def rows():
    return await models.AuditLog.all().order_by('id')


# --- The catalogue --------------------------------------------------------------


def test_every_action_has_a_label_and_an_area():
    constants = {v for k, v in vars(audit).items() if k.isupper() and isinstance(v, str) and '.' in v
                 and not k.startswith('VIA_')}
    assert constants == set(audit.ACTIONS)
    for action in audit.ACTIONS:
        assert audit.area_of(action) is not None, action
        assert audit.ACTIONS[action][0].isupper(), action


def test_changes_lists_only_what_differs():
    when = datetime.datetime(2026, 11, 24, tzinfo=datetime.timezone.utc)
    assert audit.changes({'a': 1, 'b': 'x', 'c': None}, {'a': 1, 'b': 'y', 'c': when}) == {
        'b': ['x', 'y'], 'c': [None, when.isoformat()]}


# --- Writing ----------------------------------------------------------------------


async def test_record_takes_the_actor_and_surface_from_the_source(db):
    with as_(ALICE, via=audit.VIA_API, detail="My script"):
        await audit.record(audit.PRESET_DELETED, target="ns/p", details={'k': ('a', 'b')})
    row = (await rows())[0]
    assert (row.actor_discord_id, row.actor_name, row.via, row.via_detail, row.target) == (
        ALICE, "alice", "api", "My script", "ns/p")
    assert row.details == {'k': ['a', 'b']}


async def test_record_without_a_source_is_the_bot_itself(db):
    await audit.record(audit.ELECTION_CLOSED, target="Vote")
    row = (await rows())[0]
    assert (row.via, row.actor_discord_id, row.actor_name) == ("system", None, None)


async def test_an_explicit_actor_wins_and_gets_their_stored_name(db):
    await models.Users.create(discord_user_id=BOB, display_name="bobby")
    with as_(ALICE):
        await audit.record(audit.RACER_VERIFICATION_VERIFIED, actor_discord_id=BOB)
    row = (await rows())[0]
    assert (row.actor_discord_id, row.actor_name, row.via) == (BOB, "bobby", "website")


async def test_racetime_actor_is_linked_to_their_discord_account(db):
    await models.Users.create(discord_user_id=ALICE, rtgg_id="rt-alice", display_name="alice")
    with audit.acting(audit.Source(via=audit.VIA_RACETIME, detail="!lock in alttpr/x", actor_name="Alice",
                                   racetime_id="rt-alice")):
        await audit.record(audit.SERVER_SETTING_CHANGED)
    row = (await rows())[0]
    assert (row.actor_discord_id, row.actor_name, row.via_detail) == (ALICE, "Alice", "!lock in alttpr/x")


async def test_unknown_action_is_a_bug(db):
    with pytest.raises(ValueError):
        await audit.record("made.up")


async def test_a_database_failure_is_logged_not_raised(db, monkeypatch, caplog):
    monkeypatch.setattr(models.AuditLog, "create", mock.AsyncMock(side_effect=RuntimeError("down")))
    await audit.record(audit.PRESET_DELETED)
    assert "Couldn't write the audit entry preset.deleted" in caplog.text


async def test_long_text_is_clipped(db):
    with as_(ALICE, detail="d" * 500):
        await audit.record(audit.PRESET_DELETED, target="t" * 500)
    row = (await rows())[0]
    assert len(row.target) == 300
    assert row.target.endswith('…')
    assert len(row.via_detail) == 200


# --- What services record --------------------------------------------------------


async def test_purge_unlinks_the_person_and_records_itself_anonymously(db):
    with as_(ALICE):
        await audit.record(audit.PRESET_DELETED, target="mine")
        await accounts.purge(ALICE)
    first, purge = await rows()
    assert (first.actor_discord_id, first.actor_name, first.target) == (None, None, "mine")
    assert (purge.action, purge.actor_discord_id, purge.via) == ("account.purged", None, "website")


async def test_racetime_link_is_recorded(db):
    await accounts.link_racetime(ALICE, "alice", "rt-1", "tok")
    row = (await rows())[0]
    assert (row.action, row.actor_discord_id, row.target) == ("account.racetime_linked", ALICE, "rt-1")


async def test_preset_create_update_and_delete(db):
    namespace = await presets.my_namespace(ALICE, "alice")
    viewer = presets.Viewer(ALICE)
    with as_(ALICE):
        await presets.save_preset(namespace, "alttpr", "p", "settings: {}", viewer)
        await presets.save_preset(namespace, "alttpr", "p", "settings: {}", viewer)  # unchanged: nothing
        await presets.save_preset(namespace, "alttpr", "p", "settings: {a: 1}", viewer)
        await presets.delete_preset(namespace, "alttpr", "p", viewer)
    assert [r.action for r in await rows()] == ["preset.created", "preset.updated", "preset.deleted"]


async def test_triforce_texts(db):
    await models.TriforceTextsConfig.create(pool_name="p", key_name="moderator", value=str(BOB))
    with as_(ALICE):
        text = await triforce_texts.submit("p", ALICE, "alice#0", ["HI", "", ""])
    with as_(BOB, "bob"):
        await triforce_texts.moderate("p", text['id'], BOB, True)
        await triforce_texts.moderate("p", text['id'], BOB, True)  # no change: nothing
        await triforce_texts.moderate("p", text['id'], BOB, False)
    assert [(r.action, r.actor_name) for r in await rows()] == [
        ("triforce_text.submitted", "alice"), ("triforce_text.approved", "bob"), ("triforce_text.rejected", "bob")]


async def test_api_tokens_and_ai_clients(db):
    _, row = await api_tokens.create_personal_token(ALICE, "alice", "script", True, 30)
    await api_tokens.revoke(row['id'], ALICE)
    client = await models.McpOAuthClient.create(client_id="c", client_name="Claude", redirect_uris=[],
                                                grant_types=[], response_types=[])
    token = await models.ApiToken.create(discord_user_id=ALICE, user_name="alice", name="Claude", origin="oauth",
                                         token_hash="h", token_prefix="sb_mcp_", oauth_client=client)
    await api_tokens.revoke(token.id, ALICE)
    created, revoked, disconnected = await rows()
    assert (created.action, created.target, created.details['read_only']) == ("api_token.created", "script", True)
    assert "sb_pat_" in created.details['prefix']
    assert len(created.details['prefix']) < 15
    assert revoked.action == "api_token.revoked"
    assert disconnected.action == "ai_client.disconnected"


async def test_server_settings(db):
    with as_(ALICE, via=audit.VIA_DISCORD, detail="/config"):
        await guild_config.set_value(GUILD, "DailyChannel", "1")
        await guild_config.set_value(GUILD, "DailyChannel", "1")  # unchanged: nothing
        await guild_config.set_value(GUILD, "DailyChannel", "2")
        await guild_config.delete_value(GUILD, "DailyChannel")
        await guild_config.delete_value(GUILD, "DailyChannel")  # nothing there: nothing
    log = await rows()
    assert [r.action for r in log] == ["server_setting.changed", "server_setting.changed", "server_setting.removed"]
    assert log[1].details == {'changes': {'DailyChannel': ['1', '2']}}
    assert {r.guild_id for r in log} == {GUILD}


async def test_elections_record_each_step_but_never_a_ballot(db, directory):
    directory.add_guild(GUILD, admins=[ALICE], members={BOB: []})
    data = elections.ElectionInput(guild_id=GUILD, channel_id=300, title="Vote", description=None,
                                   candidates=["A", "B"], method="stv", seats=1, voter_role_id=None,
                                   closes_at=None, show_vote_count=True)
    with as_(ALICE):
        draft = await elections.create_draft(ALICE, data)
        await elections.update(draft['id'], ALICE, dataclasses.replace(data, title="Vote 2"))
        await elections.publish(draft['id'], ALICE)
    ballot = await elections.get_ballot(draft['id'], BOB)
    with as_(BOB, "bob", via=audit.VIA_MCP, detail="Claude"):
        await elections.cast_ballot(draft['id'], BOB, [c['id'] for c in ballot['candidates']])
    with as_(ALICE):
        await elections.close(draft['id'], ALICE)
        await elections.delete(draft['id'], ALICE)
    log = await rows()
    assert [r.action for r in log] == ["election.created", "election.updated", "election.published",
                                       "election.voted", "election.closed", "election.deleted"]
    assert log[1].details['changes'] == {'title': ['Vote', 'Vote 2']}
    voted = log[3]
    assert (voted.actor_discord_id, voted.via, voted.via_detail) == (BOB, "mcp", "Claude")
    assert voted.details == {'election_id': draft['id']}
    assert {r.guild_id for r in log} == {GUILD}


# --- Front ends set the source ------------------------------------------------------


async def test_discord_button_decorator_acts_as_the_presser(db):
    class View:
        @discord_audit.audited("Join button")
        async def press(self, interaction, button):
            await audit.record(audit.MULTIWORLD_STARTED)
            return audit.current_source()

    source = await View().press(FakeInteraction(user=FakeUser(user_id=ALICE, name="alice")), None)
    assert (source.via, source.detail, source.actor_discord_id) == ("discord", "Join button", ALICE)
    assert audit.current_source() is audit.SYSTEM


def test_prefix_command_source():
    ctx = SimpleNamespace(author=SimpleNamespace(id=ALICE, name="alice"),
                          command=SimpleNamespace(qualified_name="reactionrole create"))
    source = discord_audit.context_source(ctx)
    assert (source.via, source.detail, source.actor_discord_id) == ("discord", "$reactionrole create", ALICE)


def test_racetime_command_source():
    handler = SimpleNamespace(data={'name': 'alttpr/cool-room'}, bot=SimpleNamespace(category_slug='alttpr'))
    message = {'user': {'id': 'rt1', 'name': 'Alice'}}
    source = racetime_telemetry.command_source(handler, 'lock', ([], message), {})
    assert (source.via, source.detail, source.actor_name, source.racetime_id) == (
        "racetime", "!lock in alttpr/cool-room", "Alice", "rt1")
    assert racetime_telemetry.command_source(handler, 'x', (), {}).actor_name is None


# --- Reading: who sees what -------------------------------------------------------


async def seed():
    with as_(ALICE):
        await audit.record(audit.PRESET_CREATED, target="alice/p")
        await audit.record(audit.ELECTION_CREATED, target="Vote", guild_id=GUILD)
    with as_(BOB, "bob"):
        await audit.record(audit.SERVER_SETTING_CHANGED, target="X", guild_id=OTHER_GUILD)
        await audit.record(audit.TRIFORCE_TEXT_APPROVED, target="Pool p", guild_id=GUILD)


async def test_mine_is_your_own_actions(db, directory):
    await seed()
    page = await audit.list_entries(ALICE, [], audit.Filters(scope='mine'))
    assert [e['target'] for e in page['entries']] == ["Vote", "alice/p"]


async def test_a_server_needs_its_admin_or_an_owner(db, directory):
    directory.add_guild(GUILD, name="Racing")
    directory.owner = OWNER
    await seed()
    page = await audit.list_entries(BOB, [GUILD], audit.Filters(scope=str(GUILD)))
    assert [(e['target'], e['guild_name']) for e in page['entries']] == [("Pool p", "Racing"), ("Vote", "Racing")]
    with pytest.raises(PermissionDeniedError):
        await audit.list_entries(BOB, [GUILD], audit.Filters(scope=str(OTHER_GUILD)))
    assert len((await audit.list_entries(OWNER, [], audit.Filters(scope=str(OTHER_GUILD))))['entries']) == 1
    with pytest.raises(InvalidInputError):
        await audit.list_entries(BOB, [], audit.Filters(scope='nonsense'))


async def test_everything_is_for_owners_and_listed_viewers(db, directory, monkeypatch):
    directory.owner = OWNER
    await seed()
    with pytest.raises(PermissionDeniedError):
        await audit.list_entries(ALICE, [], audit.Filters(scope='all'))
    assert len((await audit.list_entries(OWNER, [], audit.Filters(scope='all')))['entries']) == 4
    monkeypatch.setattr(audit.config, "AUDIT_LOG_VIEWER_IDS", [ALICE], raising=False)
    assert len((await audit.list_entries(ALICE, [], audit.Filters(scope='all')))['entries']) == 4


async def test_scopes_offer_what_you_can_see(db, directory):
    directory.add_guild(GUILD, name="Racing").add_guild(OTHER_GUILD, name="Other")
    directory.owner = OWNER
    assert await audit.scopes(ALICE, [GUILD, 999]) == [
        {'key': 'mine', 'label': 'My activity'}, {'key': str(GUILD), 'label': 'Racing'}]
    assert (await audit.scopes(OWNER, []))[-1] == {'key': 'all', 'label': 'Everything'}


async def test_area_search_actor_and_paging(db, directory):
    directory.owner = OWNER
    await seed()
    find = lambda **kw: audit.list_entries(OWNER, [], audit.Filters(scope='all', **kw))  # noqa: E731
    assert [e['action'] for e in (await find(area='server'))['entries']] == ["server_setting.changed"]
    assert [e['target'] for e in (await find(query='approved'))['entries']] == ["Pool p"]  # matches the label
    assert [e['target'] for e in (await find(query='BOB'))['entries']] == ["Pool p", "X"]
    assert len((await find(actor_discord_id=ALICE))['entries']) == 2
    first = await find(limit=3)
    assert len(first['entries']) == 3
    assert first['next_before'] == first['entries'][-1]['id']
    rest = await find(limit=3, before_id=first['next_before'])
    assert [e['target'] for e in rest['entries']] == ["alice/p"]
    assert rest['next_before'] is None
    with pytest.raises(InvalidInputError):
        await find(area='nope')
    assert len(await audit.export_entries(OWNER, [], audit.Filters(scope='all', limit=1))) == 4


# --- Through /api/v1 and MCP ----------------------------------------------------------


@pytest.fixture
def client(db):
    return api.sahasrahbotapi.test_client()


async def test_api_options_list_and_csv(client, login, directory):  # noqa: F811
    directory.add_guild(GUILD, name="Racing", admins=[ALICE])
    await seed()
    login(ALICE, name="alice")
    status, options = await get_json(client, "/api/v1/audit/options")
    assert status == 200
    assert [s['key'] for s in options['scopes']] == ['mine', str(GUILD)]
    assert {'key': 'elections', 'label': 'Elections'} in options['areas']
    status, page = await get_json(client, f"/api/v1/audit?scope={GUILD}")
    assert status == 200
    assert [(e['target'], e['actor_id'], e['guild_id'], e['via_label']) for e in page['entries']] == [
        ("Pool p", str(BOB), str(GUILD), "Website"), ("Vote", str(ALICE), str(GUILD), "Website")]
    status, body = await get_json(client, f"/api/v1/audit?scope={OTHER_GUILD}")
    assert status == 403
    resp = await client.get(f"/api/v1/audit/export?scope={GUILD}")
    text = (await resp.get_data()).decode()
    assert resp.headers['Content-Type'].startswith('text/csv')
    assert text.splitlines()[0].startswith('id,created_at,label,action')
    assert "Approved a triforce text" in text


def test_csv_cells_cannot_become_formulas():
    assert app_api._csv_cell("=HYPERLINK()") == "'=HYPERLINK()"
    assert app_api._csv_cell({'a': 1}) == '{"a": 1}'
    assert app_api._csv_cell(None) == ''


async def test_website_changes_are_recorded_as_the_signed_in_person(client, login):  # noqa: F811
    login(ALICE, name="alice")
    await get_json(client, "/api/v1/presets/mine")
    namespace = (await models.PresetNamespaces.get(discord_user_id=ALICE)).name
    status, _ = await send_json(client, "PUT", f"/api/v1/presets/namespaces/{namespace}/alttpr/p",
                                {"content": "settings: {}"})
    assert status == 200
    row = (await rows())[-1]
    assert (row.action, row.actor_discord_id, row.actor_name, row.via) == ("preset.created", ALICE, "alice", "website")


async def test_token_changes_name_the_token(client):
    raw, _ = await api_tokens.create_personal_token(ALICE, "alice", "CI sync", False, None)
    namespace = await presets.my_namespace(ALICE, "alice")
    resp = await client.put(f"/api/v1/presets/namespaces/{namespace}/alttpr/p", json={"content": "settings: {}"},
                            headers={"Authorization": f"Bearer {raw}"})
    assert resp.status_code == 200
    row = (await rows())[-1]
    assert (row.action, row.via, row.via_detail) == ("preset.created", "api", "CI sync")


async def test_mcp_tool_lists_your_own_log(db, monkeypatch):
    from alttprbot_api.mcp import auth as mcp_actor, tools
    await seed()
    token = mcp_actor.set_actor(mcp_actor.McpActor(discord_user_id=ALICE, user_name="alice", read_only=True,
                                                   client_name="Claude"))
    try:
        page = await tools.list_audit_log()
        assert [e.target for e in page.entries] == ["Vote", "alice/p"]
        with pytest.raises(InvalidInputError):
            await tools.list_audit_log(actor_id="not-a-number")
    finally:
        mcp_actor.reset_actor(token)

"""tournaments.yaml and its loader (alttprbot/tournament/event_settings.py).

The expected values below are the ones the tournament classes hardcoded before
the ids moved to tournaments.yaml, so these tests pin that each event still
gets the same TournamentConfig.
"""


import pytest

import config
from alttprbot.services import bots
from alttprbot.tournament import alttpr, alttprleague, dailies, event_settings as settings, test as test_tournament


class FakeGuild:
    def __init__(self, guild_id):
        self.id = guild_id

    def get_role(self, role_id):
        return ("role", role_id)


class FakeDiscord:
    def get_guild(self, guild_id):
        return FakeGuild(guild_id)

    def get_channel(self, channel_id):
        return ("channel", channel_id)


@pytest.fixture
def fake_discord(monkeypatch):
    monkeypatch.setattr(bots, "_discord_client", FakeDiscord())


def channel(channel_id):
    return ("channel", channel_id)


def roles(*ids):
    return [("role", i) for i in ids]


LEAGUE_HELPERS = roles(543596853871116288, 543597099649073162, 676530377812082706,
                       553295025190993930, 674109759179194398)

EXPECTED = {
    alttpr.ALTTPR2024Race: dict(
        guild=334795604918272012, racetime_category='alttpr',
        racetime_goal='Beat the game - Tournament (Solo)', event_slug='alttpr',
        audit_channel=channel(647966639266201620), commentary_channel=channel(947095820673638400),
        scheduling_needs_channel=channel(434560353461075969), scheduling_needs_tracker=True,
        create_scheduled_events=True, stream_delay=10,
        gsheet_id='1epZRDXfe-O4BBerzOEZbFMOVCFrVXU6TCDNjp66P7ZI',
        helper_roles=roles(334797023054397450, 435200206552694794, 482353483853332481,
                           426487540829388805, 613394561594687499, 334796844750209024),
    ),
    alttprleague.ALTTPRLeague: dict(
        guild=543577975032119296, racetime_category='alttpr',
        racetime_goal='Beat the game - Tournament (Solo)', event_slug='invleague',
        audit_channel=channel(546728638272241674), commentary_channel=channel(1157407211094556703),
        helper_roles=LEAGUE_HELPERS, stream_delay=10, create_scheduled_events=True,
        scheduling_needs_channel=None, scheduling_needs_tracker=False,
        gsheet_id=config.TOURNAMENT_RESULTS_SHEET,
    ),
    alttprleague.ALTTPROpenLeague: dict(
        guild=543577975032119296, racetime_category='alttpr',
        racetime_goal='Beat the game - Tournament (Solo)', event_slug='alttprleague',
        audit_channel=channel(546728638272241674), commentary_channel=channel(1157407211094556703),
        helper_roles=LEAGUE_HELPERS, stream_delay=10, create_scheduled_events=True,
    ),
    dailies.AlttprSGDailyRace: dict(
        guild=307860211333595146, racetime_category='alttpr',
        racetime_goal='Beat the game - Casual', event_slug='alttprdaily', room_open_time=60,
        audit_channel=None, helper_roles=None, stream_delay=0,
    ),
    dailies.SMZ3DailyRace: dict(
        guild=445948207638511616, racetime_category='smz3', racetime_goal='Beat the games',
        event_slug='smz3', room_open_time=60, audit_channel=None,
    ),
    test_tournament.TestTournament: dict(
        guild=508335685044928540, racetime_category='test', racetime_goal='Beat the game',
        event_slug='test', audit_channel=channel(537469084527230976), commentary_channel=None,
        stream_delay=0, create_scheduled_events=False,
    ),
}


@pytest.mark.parametrize("cls", list(EXPECTED), ids=lambda c: c.__name__)
async def test_event_config_matches_the_old_hardcoded_values(fake_discord, cls):
    race = cls(episodeid="1")
    cfg = await race.configuration()

    for field, expected in EXPECTED[cls].items():
        actual = getattr(cfg, field)
        if field == 'guild':
            actual = actual.id
        assert actual == expected, field


def test_every_registered_event_has_settings():
    for slug in ('alttpr', 'invleague', 'alttprleague', 'alttprdaily', 'smz3', 'test'):
        assert slug in settings.SETTINGS


def test_unknown_event_is_an_error():
    with pytest.raises(settings.TournamentSettingsError):
        settings.tournament_config("no-such-event")


def write(tmp_path, text):
    path = tmp_path / "tournaments.yaml"
    path.write_text(text)
    return path


def test_load_rejects_a_missing_guild(tmp_path):
    path = write(tmp_path, "ev:\n  racetime_category: c\n  racetime_goal: g\n")
    with pytest.raises(settings.TournamentSettingsError, match="no guild"):
        settings.load(path)


@pytest.mark.parametrize("extra, match", [
    ("  stream_dealy: 10\n", "unknown keys"),
    ("  event_slug: other\n", "unknown keys"),
    ("  channels:\n    audti: 1\n", "unknown channel"),
    ("  roles:\n    helpers: [1]\n", "unknown role list"),
])
def test_load_rejects_typos(tmp_path, extra, match):
    path = write(tmp_path, "ev:\n  guild: 1\n  racetime_category: c\n  racetime_goal: g\n" + extra)
    with pytest.raises(settings.TournamentSettingsError, match=match):
        settings.load(path)


def test_announcements_are_only_on_the_dailies():
    assert settings.announcement('alttprdaily')['channel'] == 307861467838021633
    assert settings.announcement('smz3')['mention'] == 449260882501959700
    assert settings.announcement('alttpr') is None
    assert settings.announcement('missing') is None


def test_daily_announcement_settings_match_the_old_table():
    from alttprbot_discord import notifications

    assert notifications.DAILY_ANNOUNCEMENTS == {
        'alttprdaily': {
            'channel_id': 307861467838021633,
            'heading': "SpeedGaming Daily Race Series",
            'mention': None,
            'webhook_mention': "<@&399038388964950016>",
            'show_seed_time': True,
        },
        'smz3': {
            'channel_id': 451977523123978260,
            'heading': "SMZ3 Weekly Race",
            'mention': "<@&449260882501959700>",
            'webhook_mention': None,
            'show_seed_time': False,
        },
    }


def test_settings_file_is_plain_data():
    """Discord ids must load as ints (YAML would read a quoted one as a string)."""
    for slug, entry in settings.SETTINGS.items():
        assert isinstance(entry['guild'], int), slug
        for channel_id in (entry.get('channels') or {}).values():
            assert isinstance(channel_id, int), slug
        for role_ids in (entry.get('roles') or {}).values():
            assert all(isinstance(r, int) for r in role_ids), slug

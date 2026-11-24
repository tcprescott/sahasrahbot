"""Chat commands of the smaller racetime.gg category handlers (SMR, Z1R, Z2R, FF1R,
SMB3R, the test category) and the ALTTPR spoiler commands.

Built on the helpers in ``tests/test_racetime_handlers.py``: a handler with its
outgoing actions mocked, fed chat messages the way racetime.gg sends them.
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot_racetime.handlers import alttpr, ff1r, smb3r, smr, smz3, z1r, z2r
from alttprbot_racetime.handlers import test as test_category
from alttprbot_racetime.handlers.core import MSG_GENERATING, MSG_NO_PRESET, MSG_ROLL_COMPLETE
from tests.test_racetime_handlers import chat, fake_seed, make_handler, said

TEAMS = [
    {"user": {"name": "a"}, "team": {"name": "red"}},
    {"user": {"name": "b"}, "team": {"name": "blue"}},
]


# ---------------------------------------------------------------------------
# Super Metroid (smr)
# ---------------------------------------------------------------------------


async def test_smr_choozorace(monkeypatch):
    make = mock.AsyncMock(return_value=SimpleNamespace(url="https://varia.test/c"))
    monkeypatch.setattr(smr.smvaria, "generate_choozo", make)
    h = make_handler(smr.GameHandler)

    await chat(h, "!choozorace Major Full RandomBoss Hard RandomEscape Random Ship")

    assert make.await_args.args[1:] == (True, "Major", "Full", "RandomBoss", "Hard", "RandomEscape", "Random", "Ship")
    h.set_bot_raceinfo.assert_awaited_once_with(
        "Super Metroid Choozo Randomizer - https://varia.test/c - Major Full RandomBoss Hard RandomEscape Random Ship")
    assert said(h) == ["https://varia.test/c", MSG_ROLL_COMPLETE, "Don't forget to disable screen shake during escape."]
    assert h.seed_rolled is True


async def test_smr_choozorace_argument_count_and_errors(monkeypatch):
    h = make_handler(smr.GameHandler)
    await chat(h, "!choozorace Major")
    assert said(h) == ["1 argument provided, 7 required (item split, area, boss, difficulty, escape, morph, start)"]

    monkeypatch.setattr(smr.smvaria, "generate_choozo", mock.AsyncMock(side_effect=ValueError("bad area")))
    await chat(h, "!choozorace a b c d VanillaEscape f g")
    assert said(h)[-1] == "bad area"
    assert h.seed_rolled is False


async def test_smr_multiworld(monkeypatch):
    make = mock.AsyncMock(side_effect=lambda preset, players, **kw: SimpleNamespace(url=f"https://samus.test/{players[0]}"))
    monkeypatch.setattr(smr.smz3multi, "generate_multiworld", make)
    monkeypatch.setattr(smr.random, "choice", lambda options: options[1])
    h = make_handler(smr.GameHandler)
    h.data.update(team_race=True, entrants=TEAMS)

    await chat(h, "!multiworld tournament 42")

    assert {c.kwargs["seed_number"] for c in make.await_args_list} == {42}
    assert make.await_args.args[0] == "tournament_full"
    assert make.await_args.kwargs["randomizer"] == "sm"
    assert said(h)[0] == MSG_GENERATING
    assert "Team red: https://samus.test/a" in said(h)
    h.set_bot_raceinfo.assert_awaited_once_with("SM Multiworld - tournament_full")
    assert h.seed_rolled is True


async def test_smr_multiworld_refusals(monkeypatch):
    h = make_handler(smr.GameHandler)
    await chat(h, "!multiworld")
    assert said(h) == [MSG_NO_PRESET]
    await chat(h, "!multiworld casual_full")
    assert said(h)[-1] == "This must be a team race."
    h.data.update(team_race=True, entrants=TEAMS + [{"user": {"name": "c"}, "team": {"name": "red"}}])
    await chat(h, "!multiworld casual_full")
    assert said(h)[-1] == "Teams are unequal in size."
    await chat(h, "!multiworld casual_full 99999999999")
    assert "Seed number must be between" in said(h)[-1]

    h.data["entrants"] = TEAMS
    monkeypatch.setattr(smr.smz3multi, "generate_multiworld", mock.AsyncMock(side_effect=RuntimeError("samus down")))
    await chat(h, "!multiworld casual_full")
    assert said(h)[-1] == "samus down"


async def test_smr_league_playoff(monkeypatch):
    make = mock.AsyncMock(return_value=SimpleNamespace(url="https://varia.test/p"))
    monkeypatch.setattr(smr.smvaria, "generate_league_playoff", make)
    h = make_handler(smr.GameHandler)

    await chat(h, "!smleagueplayoff full split random")
    make.assert_awaited_once_with("full", "split", "random")
    h.set_bot_raceinfo.assert_awaited_once_with(
        "Super Metroid League Playoffs - full - https://varia.test/p - full, split, random")

    h2 = make_handler(smr.GameHandler)
    await chat(h2, "!smleagueplayoff")
    assert said(h2) == [MSG_NO_PRESET]
    make.side_effect = IndexError("list index out of range")
    await chat(h2, "!smleagueplayoff full")
    assert said(h2)[-1] == "list index out of range"


async def test_smr_totalrace(monkeypatch):
    async def fake_generate(self, tournament=True, spoilers=False):
        self.seed = SimpleNamespace(url="https://sm.test/1", code="Kraid Ridley")

    monkeypatch.setattr(generator.SMPreset, "generate", fake_generate)
    h = make_handler(smr.GameHandler)
    await chat(h, "!totalrace casual_full")
    h.set_bot_raceinfo.assert_awaited_once_with("SM Total Randomizer - casual_full - https://sm.test/1 - (Kraid Ridley)")

    h2 = make_handler(smr.GameHandler)
    await chat(h2, "!totalrace")
    assert said(h2) == [MSG_NO_PRESET]


async def test_known_issue_smr_total_alias_never_runs():
    """KNOWN ISSUE, pinned not endorsed: ``!total`` calls ``ex_totalrace`` without
    ``await``, so the coroutine is dropped and nothing is rolled or said."""
    h = make_handler(smr.GameHandler)
    with pytest.warns(RuntimeWarning, match="never awaited"):
        await chat(h, "!total casual_full")
        import gc
        gc.collect()
    assert said(h) == []


@pytest.mark.parametrize("command", ["!varia", "!smvaria", "!variarace"])
async def test_smr_varia(monkeypatch, command):
    make = mock.AsyncMock(return_value=SimpleNamespace(url="https://varia.test/v"))
    monkeypatch.setattr(smr.smvaria, "generate_preset", make)
    h = make_handler(smr.GameHandler)

    await chat(h, f"{command} default regular")

    make.assert_awaited_once_with(settings="default", skills="regular", race=True)
    h.set_bot_raceinfo.assert_awaited_once_with("default / regular - https://varia.test/v")


async def test_smr_varia_errors(monkeypatch):
    from pyz3r.exceptions import UnableToGenerate

    h = make_handler(smr.GameHandler)
    await chat(h, "!varia default")
    assert said(h) == ["You must specify setting and skill presets!"]
    monkeypatch.setattr(smr.smvaria, "generate_preset", mock.AsyncMock(side_effect=UnableToGenerate("varia down")))
    await chat(h, "!varia default regular")
    assert said(h)[-1] == "varia down"


@pytest.mark.parametrize(
    "text, mode, spoiler",
    [("!dash classic_mm", "classic_mm", False), ("!smdash --spoiler sgl23", "sgl23", True),
     ("!dashrace classic_full", "classic_full", False)],
)
async def test_smr_dash(monkeypatch, text, mode, spoiler):
    make = mock.AsyncMock(return_value="https://dash.test/seed")
    monkeypatch.setattr(smr.smdash, "create_smdash", make)
    h = make_handler(smr.GameHandler)

    await chat(h, text)

    make.assert_awaited_once_with(mode=mode, spoiler=spoiler)
    h.set_bot_raceinfo.assert_awaited_once_with("SM Dash Randomizer - https://dash.test/seed")


async def test_smr_dash_usage_and_errors(monkeypatch):
    monkeypatch.setattr(smr.smdash, "get_smdash_presets", mock.AsyncMock(return_value=["classic_mm", "sgl23"]))
    h = make_handler(smr.GameHandler)
    await chat(h, "!dash")
    assert said(h) == ["Usage: !dash [--spoiler] <preset>", "Available presets: classic_mm, sgl23"]

    await chat(h, "!dash --nope classic_mm")
    assert said(h)[-1].startswith("Invalid option: --nope")

    monkeypatch.setattr(smr.smdash, "create_smdash", mock.AsyncMock(side_effect=RuntimeError("dash down")))
    await chat(h, "!dash classic_mm")
    assert said(h)[-1] == "dash down"


# ---------------------------------------------------------------------------
# Zelda 1 (z1r), Zelda 2 (z2r), FF1R, SMB3R
# ---------------------------------------------------------------------------


@pytest.fixture
def fixed_seed(monkeypatch):
    for module in (z1r, smb3r):
        name = "roll_z1r" if module is z1r else "roll_smb3r"
        monkeypatch.setattr(module, name, lambda flags: (123, flags))


async def test_z1r_flags_and_presets(fixed_seed):
    h = make_handler(z1r.GameHandler)
    await chat(h, "!flags ABCDEF")
    h.set_bot_raceinfo.assert_awaited_once_with("Seed: 123 - Flags: ABCDEF")

    h = make_handler(z1r.GameHandler)
    await chat(h, "!race rr2024")
    assert said(h)[0] == f"rr2024 - Flags: {z1r.PRESETS['rr2024']} Seed: 123"

    h = make_handler(z1r.GameHandler)
    await chat(h, "!flags")
    await chat(h, "!race")
    await chat(h, "!race nope")
    assert said(h) == ["You must specify a set of flags!", "No preset specified.", "Invalid preset specified."]


@pytest.mark.parametrize(
    "command, preset",
    [("!power", "power"), ("!courage", "courage"), ("!wisdom", "wisdom"), ("!sglonline", "sgl25online"),
     ("!sglirl", "sglirl")],
)
async def test_z1r_shortcuts(fixed_seed, command, preset):
    h = make_handler(z1r.GameHandler)
    await chat(h, command)
    assert said(h)[0].startswith(f"{preset} - Flags: {z1r.PRESETS[preset]}")


@pytest.mark.parametrize("roll, preset", [(1, "power"), (2, "courage"), (3, "wisdom")])
async def test_z1r_ttp3_picks_a_flagset(monkeypatch, fixed_seed, roll, preset):
    monkeypatch.setattr(z1r.random, "randint", lambda a, b: roll)
    h = make_handler(z1r.GameHandler)
    await chat(h, "!ttp3")
    assert said(h)[0].startswith(f"{preset} - ")


def test_z1r_random_seed_range():
    from alttprbot.alttprgen.randomizer.z1r import roll_z1r

    seed, flags = roll_z1r("X")
    assert 0 <= seed <= 8999999999999999999 and flags == "X"


async def test_z2r_commands(monkeypatch):
    monkeypatch.setattr(z2r.random, "randint", lambda a, b: 77)
    monkeypatch.setattr(z2r.z2r, "mrb", lambda: (88, "MRB", "desc"))
    monkeypatch.setattr(z2r.z2r, "preset", lambda name: (99, f"F-{name}"))

    h = make_handler(z2r.GameHandler)
    await chat(h, "!flags XYZ")
    h.set_bot_raceinfo.assert_awaited_once_with("Seed: 77 - Flags: XYZ")

    h = make_handler(z2r.GameHandler)
    await chat(h, "!mrb")
    h.set_bot_raceinfo.assert_awaited_once_with("Seed: 88 - Flags: MRB - desc")

    h = make_handler(z2r.GameHandler)
    await chat(h, "!flags")
    assert said(h) == ["You must specify a set of flags!"]


@pytest.mark.parametrize("preset", ["maxrando", "groups1", "groups2", "groups3", "groups4", "brackets", "nit",
                                    "sgl4", "sgl"])
async def test_z2r_presets(monkeypatch, preset):
    monkeypatch.setattr(z2r.z2r, "preset", lambda name: (99, f"F-{name}"))
    h = make_handler(z2r.GameHandler)
    await chat(h, f"!{preset}")
    h.set_bot_raceinfo.assert_awaited_once_with(f"Seed: 99 - Flags: F-{preset}")
    assert h.seed_rolled is True


async def test_ff1r_url(monkeypatch):
    monkeypatch.setattr(ff1r, "roll_ffr", lambda url: ("ABCD1234", url + "&s=ABCD1234"))
    h = make_handler(ff1r.GameHandler)
    await chat(h, "!ff1url https://4-8-0.finalfantasyrandomizer.com/?f=FLAGS")
    h.set_bot_raceinfo.assert_awaited_once_with("https://4-8-0.finalfantasyrandomizer.com/?f=FLAGS&s=ABCD1234")

    h = make_handler(ff1r.GameHandler)
    await chat(h, "!ff1url")
    assert said(h) == ["You must specify a FF1R URL with the flags!"]


def test_roll_ffr_replaces_the_seed(monkeypatch):
    from alttprbot.alttprgen.randomizer import ffr

    monkeypatch.setattr(ffr.random, "randrange", lambda n: 0xBEEF)
    seed, url = ffr.roll_ffr("https://ff1r.test/?f=FLAGS&s=OLD")
    assert seed == "0000BEEF"
    assert url == "https://ff1r.test/?f=FLAGS&s=0000BEEF"


async def test_smb3r_flags(fixed_seed):
    h = make_handler(smb3r.GameHandler)
    await chat(h, "!flags 17BCA")
    h.set_bot_raceinfo.assert_awaited_once_with("Seed: 123 - Flags: 17BCA")
    h = make_handler(smb3r.GameHandler)
    await chat(h, "!flags")
    assert said(h) == ["You must specify a set of flags!"]


async def test_locked_rooms_refuse_to_roll(fixed_seed):
    for cls, text in [(z1r.GameHandler, "!flags X"), (z1r.GameHandler, "!race power"), (z2r.GameHandler, "!mrb"),
                      (z2r.GameHandler, "!flags X"), (z2r.GameHandler, "!nit"), (smb3r.GameHandler, "!flags X"),
                      (ff1r.GameHandler, "!ff1url https://x.test/"), (smr.GameHandler, "!varia a b"),
                      (smr.GameHandler, "!dash a"), (smr.GameHandler, "!choozorace a b c d e f g"),
                      (smr.GameHandler, "!multiworld a"), (smr.GameHandler, "!smleagueplayoff a"),
                      (smr.GameHandler, "!totalrace a")]:
        h = make_handler(cls)
        h.state["locked"] = True
        await chat(h, text)
        assert said(h) and "locked" in said(h)[0], (cls.__module__, text)
        h.set_bot_raceinfo.assert_not_awaited()


# ---------------------------------------------------------------------------
# The test category
# ---------------------------------------------------------------------------


async def test_test_category_countdown(monkeypatch):
    countdown = mock.AsyncMock()
    h = make_handler(test_category.GameHandler)
    h.countdown_timer = countdown

    await chat(h, "!test 5")
    await chat(h, "!test")
    await chat(h, "!test soon")

    assert [c.args for c in countdown.await_args_list] == [(5,), (30,)]
    assert said(h) == ["initated test command, waiting 5 seconds", "test command complete",
                       "initated test command, waiting 30 seconds", "test command complete",
                       "Invalid number of seconds"]


# ---------------------------------------------------------------------------
# SMZ3 multiworld success
# ---------------------------------------------------------------------------


async def test_smz3_multiworld_rolls_each_team(monkeypatch):
    make = mock.AsyncMock(side_effect=lambda preset, players, **kw: SimpleNamespace(url=f"https://samus.test/{players[0]}"))
    monkeypatch.setattr(smz3.smz3multi, "generate_multiworld", make)
    h = make_handler(smz3.GameHandler)
    h.data.update(team_race=True, entrants=TEAMS)

    await chat(h, "!multiworld normal 7")

    assert sorted(c.args[1] for c in make.await_args_list) == [["a"], ["b"]]
    assert make.await_args.kwargs == {"tournament": True, "randomizer": "smz3", "seed_number": 7}
    h.set_bot_raceinfo.assert_awaited_once_with("SMZ3 Multiworld - normal")

    h2 = make_handler(smz3.GameHandler)
    h2.data.update(team_race=True, entrants=TEAMS)
    make.side_effect = RuntimeError("samus down")
    await chat(h2, "!multiworld normal")
    assert said(h2)[-1] == "samus down"


async def test_smz3_without_preset():
    h = make_handler(smz3.GameHandler)
    await chat(h, "!race")
    await chat(h, "!multiworld")
    assert said(h) == [MSG_NO_PRESET, MSG_NO_PRESET]


# ---------------------------------------------------------------------------
# ALTTPR spoiler commands and jokes
# ---------------------------------------------------------------------------


@pytest.fixture
def spoiler_game(monkeypatch):
    spoiler = SimpleNamespace(seed=fake_seed(), spoiler_log_url="https://spoilers.test/x",
                              preset=SimpleNamespace(preset_data={"studytime": 600}))
    make = mock.AsyncMock(return_value=spoiler)
    monkeypatch.setattr(alttpr.spoilers, "generate_spoiler_game", make)
    return make


@pytest.mark.parametrize(
    "text, call_kwargs, studytime",
    [("!spoiler open", {}, 600), ("!spoiler open 1200", {}, 1200),
     ("!tournamentspoiler open", {"branch": "tournament"}, 600), ("!progression open", {"spoiler_type": "progression"}, 0)],
)
async def test_alttpr_spoiler_commands(db, spoiler_game, text, call_kwargs, studytime):
    h = make_handler(alttpr.GameHandler)

    await chat(h, text)

    assert spoiler_game.await_args.args == ("open",)
    assert spoiler_game.await_args.kwargs == call_kwargs
    h.set_bot_raceinfo.assert_awaited_once_with("spoiler open - https://alttpr.test/h/abc - (Bow/Bombs/Hookshot/Lamp/Map)")
    race = await models.SpoilerRaces.get()
    assert (race.spoiler_url, race.studytime) == ("https://spoilers.test/x", studytime)
    assert h.seed_rolled is True


@pytest.mark.parametrize("command", ["!spoiler", "!tournamentspoiler", "!progression"])
async def test_alttpr_spoiler_commands_need_a_preset(command):
    h = make_handler(alttpr.GameHandler)
    await chat(h, command)
    assert said(h) == [MSG_NO_PRESET]


async def test_alttpr_newrace_without_preset_and_mystery_errors(monkeypatch):
    h = make_handler(alttpr.GameHandler)
    await chat(h, "!newrace")
    assert said(h) == [MSG_NO_PRESET]

    monkeypatch.setattr(generator.ALTTPRMystery, "generate",
                        mock.AsyncMock(side_effect=generator.WeightsetNotFoundException("No such weightset")))
    await chat(h, "!mystery nope")
    assert said(h)[-1] == "No such weightset"

    monkeypatch.setattr(generator.ALTTPRMystery, "generate",
                        mock.AsyncMock(return_value=SimpleNamespace(seed=fake_seed(), custom_instructions=None)))
    await chat(h, "!mystery")
    h.set_bot_raceinfo.assert_awaited_with("mystery weighted - https://alttpr.test/h/abc - (Bow/Bombs/Hookshot/Lamp/Map)")


@pytest.mark.parametrize(
    "command, reply",
    [("!register", "Lazy Kid ain't got nothing compared to me."), ("!vt", "You summon Veetorp"),
     ("!synack", "You need to be more creative.")],
)
async def test_alttpr_jokes(command, reply):
    h = make_handler(alttpr.GameHandler)
    await chat(h, command)
    assert said(h)[0].startswith(reply)


async def test_alttpr_pending_hides_comments(db):
    h = make_handler(alttpr.GameHandler)
    await h.status_pending()
    h.edit.assert_awaited_with(hide_comments=True)

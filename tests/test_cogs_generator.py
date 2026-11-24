"""Seed-rolling slash commands (alttprbot_discord/cogs/generator.py and daily.py).

The cogs are thin: they parse the options, call the generator and show the seed.
The generators and ``seed_embed`` are replaced, so these tests pin the options
each command passes and what it sends back.
"""

from types import SimpleNamespace
from unittest import mock

import discord
import pytest
import yaml

from alttprbot import models
from alttprbot.alttprgen import generator as gen
from alttprbot.exceptions import SahasrahBotException
from alttprbot_discord.cogs import daily as daily_cog
from alttprbot_discord.cogs import generator as cog_module
from tests.discord_fakes import FakeBot, FakeInteraction, FakeUser, call


@pytest.fixture
def embeds(monkeypatch):
    """Replace seed_embed / smvaria_embed with fakes that record the seed they were given."""
    seen = []

    async def fake_seed_embed(seed, emojis=None, name=None, notes=None):
        seen.append(SimpleNamespace(seed=seed, emojis=emojis, name=name, notes=notes))
        return discord.Embed(title=name or "seed")

    monkeypatch.setattr(cog_module, "seed_embed", fake_seed_embed)
    monkeypatch.setattr(daily_cog, "seed_embed", fake_seed_embed)
    monkeypatch.setattr(cog_module, "smvaria_embed", lambda seed: discord.Embed(title=f"varia {seed}"))
    return seen


def field(embed, name):
    return next(f.value for f in embed.fields if f.name == name)


def attachment(content: bytes):
    return SimpleNamespace(read=mock.AsyncMock(return_value=content), url="https://cdn.test/file")


@pytest.fixture
def bot():
    return FakeBot()


# ---------------------------------------------------------------------------
# /alttpr
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "options, expected",
    [
        ({}, dict(hints=False, spoilers="on", tournament=False, allow_quickswap=True, branch="live")),
        (
            dict(race="yes", hints="yes", allow_quickswap="no", branch="tournament"),
            dict(hints=True, spoilers="off", tournament=True, allow_quickswap=False, branch="tournament"),
        ),
    ],
)
async def test_alttpr_preset_options(monkeypatch, embeds, bot, options, expected):
    generate = mock.AsyncMock(return_value="SEED")
    monkeypatch.setattr(gen.ALTTPRPreset, "generate", generate)
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction()

    await call(cog.preset, cog, interaction, "open", **options)

    interaction.response.defer.assert_awaited_once()
    generate.assert_awaited_once_with(**expected)
    embed = interaction.sent().embed
    assert embeds[0].seed == "SEED"
    assert (embed.fields[0].name, embed.fields[0].value) == ("Preset", "open")


async def test_alttpr_preset_without_seed_raises(monkeypatch, embeds, bot):
    monkeypatch.setattr(gen.ALTTPRPreset, "generate", mock.AsyncMock(return_value=None))
    cog = cog_module.AlttprGenerator(bot)
    with pytest.raises(SahasrahBotException, match="Could not generate game"):
        await call(cog.preset, cog, FakeInteraction(), "nope")


async def test_alttpr_custompreset_saves_as_latest(db, monkeypatch, embeds, bot):
    monkeypatch.setattr(gen.ALTTPRPreset, "generate", mock.AsyncMock(return_value="SEED"))
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction(user=FakeUser(user_id=42, name="Alice"))
    content = yaml.safe_dump({"randomizer": "alttpr", "settings": {"mode": "open"}}).encode()

    await call(cog.custompreset, cog, interaction, attachment(content))

    preset = await models.Presets.get(preset_name="latest").prefetch_related("namespace")
    assert preset.namespace.name == "alice"
    assert "alice/latest" in field(interaction.sent().embed, "Saved as preset!")


async def test_alttpr_spoiler(monkeypatch, embeds, bot):
    spoiler = SimpleNamespace(seed="SEED", spoiler_log_url="https://spoilers.test/log.txt")
    make = mock.AsyncMock(return_value=spoiler)
    monkeypatch.setattr(cog_module, "generate_spoiler_game", make)
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction()

    await call(cog.spoiler, cog, interaction, "open", progression_spoiler=True)

    make.assert_awaited_once_with("open", spoiler_type="progression", branch="live")
    embed = interaction.sent().embed
    assert [f.name for f in embed.fields[:2]] == ["Spoiler Log URL", "Preset"]
    assert field(embed, "Spoiler Log URL") == spoiler.spoiler_log_url


async def test_alttpr_customspoiler(monkeypatch, embeds, bot):
    spoiler = SimpleNamespace(seed="SEED", spoiler_log_url="https://spoilers.test/log.txt")
    make = mock.AsyncMock(return_value=spoiler)
    monkeypatch.setattr(cog_module, "generate_spoiler_game_custom", make)
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction()

    await call(cog.customspoiler, cog, interaction, attachment(b"yaml"), branch="beeta")

    make.assert_awaited_once_with(b"yaml", branch="beeta")
    assert field(interaction.sent().embed, "Spoiler Log URL") == spoiler.spoiler_log_url


async def test_alttpr_mystery(monkeypatch, embeds, bot):
    mystery = SimpleNamespace(seed="SEED", custom_instructions="Do a barrel roll")
    generate = mock.AsyncMock(return_value=mystery)
    monkeypatch.setattr(gen.ALTTPRMystery, "generate", generate)
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction()

    await call(cog.mystery, cog, interaction, "weighted")

    generate.assert_awaited_once_with(spoilers="mystery", tournament=True)
    embed = interaction.sent().embed
    assert embeds[0].name == "Mystery Game"
    assert [f.name for f in embed.fields[:2]] == ["Weightset", "Custom Instructions"]


async def test_known_issue_mystery_mask_settings_no_still_masks(monkeypatch, embeds, bot):
    """KNOWN ISSUE, pinned not endorsed: ``mask_settings`` is the string "yes"/"no",
    but the command tests it for truth, so choosing "no" still masks the settings."""
    generate = mock.AsyncMock(return_value=SimpleNamespace(seed="SEED", custom_instructions=None))
    monkeypatch.setattr(gen.ALTTPRMystery, "generate", generate)
    cog = cog_module.AlttprGenerator(bot)

    await call(cog.mystery, cog, FakeInteraction(), "weighted", race="no", mask_settings="no")

    generate.assert_awaited_once_with(spoilers="mystery", tournament=False)


async def test_alttpr_custommystery_saves_weightset(db, monkeypatch, embeds, bot):
    generate = mock.AsyncMock(return_value=SimpleNamespace(seed="SEED", custom_instructions=None))
    monkeypatch.setattr(gen.ALTTPRMystery, "generate", generate)
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction(user=FakeUser(user_id=43, name="Bob"))
    content = yaml.safe_dump({"weights": {"mode": {"open": 1}}}).encode()

    await call(cog.custommystery, cog, interaction, attachment(content))

    assert await models.Presets.filter(preset_name="latest", randomizer="alttprmystery").exists()
    embed = interaction.sent().embed
    assert "bob/latest" in field(embed, "Saved as custom weightset!")
    assert "Custom Instructions" not in [f.name for f in embed.fields]


async def test_preset_and_weightset_autocomplete(monkeypatch, bot):
    monkeypatch.setattr(gen.ALTTPRPreset, "search", mock.AsyncMock(return_value=["open", "openboots"]))
    monkeypatch.setattr(gen.ALTTPRMystery, "search", mock.AsyncMock(return_value=["weighted"]))
    cog = cog_module.AlttprGenerator(bot)

    presets = await cog.preset_autocomplete(FakeInteraction(), "op")
    weightsets = await cog.mystery_weightset_autocomplete(FakeInteraction(), "w")

    assert [(c.name, c.value) for c in presets] == [("open", "open"), ("openboots", "openboots")]
    assert [c.value for c in weightsets] == ["weighted"]


async def test_kisspriest(monkeypatch, bot):
    seeds = [
        SimpleNamespace(data={"spoiler": {"meta": {"name": "Priest A"}}}, url="https://alttpr.test/h/a", code=["Bow"]),
        SimpleNamespace(data={"spoiler": {"meta": {}}}, url="https://alttpr.test/h/b", code=["Bow"]),
    ]
    create = mock.AsyncMock(return_value=seeds)
    monkeypatch.setattr(cog_module, "create_priestmode", create)
    cog = cog_module.AlttprGenerator(bot)
    interaction = FakeInteraction()

    await call(cog.kisspriest, cog, interaction, count=2)

    assert create.await_args.kwargs["count"] == 2
    embed = interaction.sent().embed
    assert [f.name for f in embed.fields] == ["Priest A", "Game 1"]
    assert embed.fields[0].value == "https://alttpr.test/h/a\nBow"


# ---------------------------------------------------------------------------
# /alttprutils
# ---------------------------------------------------------------------------


async def test_convertcustomizer(monkeypatch, bot):
    monkeypatch.setattr(cog_module.pyz3r.customizer, "convert2settings", lambda save: {"mode": "open"})
    cog = cog_module.AlttprUtils(bot)
    interaction = FakeInteraction()

    await call(cog.convertcustomizer, cog, interaction, attachment(b'{"some": "save"}'))

    sent = interaction.sent()
    assert sent.ephemeral is True
    assert sent.file.filename == "output.yaml"
    assert yaml.safe_load(sent.file.fp.read()) == {
        "customizer": True,
        "randomizer": "alttpr",
        "settings": {"mode": "open"},
    }


async def test_savepreset(db, bot):
    cog = cog_module.AlttprUtils(bot)
    interaction = FakeInteraction(user=FakeUser(user_id=44, name="Carol"))
    content = yaml.safe_dump({"randomizer": "alttpr", "settings": {"mode": "standard"}}).encode()

    await call(cog.savepreset, cog, interaction, "mine", attachment(content))

    assert interaction.sent().content == "Preset saved as carol/mine"
    assert await models.Presets.filter(preset_name="mine", namespace__name="carol").exists()


async def test_verifygame(db, bot):
    await models.AuditGeneratedGames.create(
        randomizer="alttpr", hash_id="abc123", permalink="https://alttpr.test/h/abc123",
        settings={}, gentype="preset", genoption="open",
    )
    cog = cog_module.AlttprUtils(bot)

    found = FakeInteraction()
    await call(cog.verifygame, cog, found, "abc123")
    missing = FakeInteraction()
    await call(cog.verifygame, cog, missing, "zzz")

    assert "**Game Option:** open" in found.sent().content
    assert "<https://alttpr.test/h/abc123>" in found.sent().content
    assert missing.sent().content == "That game was not generated by SahasrahBot."


# ---------------------------------------------------------------------------
# /sm, /smz3, /smvaria, /smdash, /ctjets, /z2r
# ---------------------------------------------------------------------------


async def test_sm(monkeypatch, embeds, bot):
    async def fake_generate(self, tournament=True, spoilers=False):
        self.seed = ("sm", tournament, spoilers)

    monkeypatch.setattr(gen.SMPreset, "generate", fake_generate)
    cog = cog_module.Generator(bot)
    interaction = FakeInteraction()

    await call(cog.sm, cog, interaction, "tournament_full", race="yes")

    assert embeds[0].seed == ("sm", True, False)
    interaction.followup.send.assert_awaited_once()


@pytest.mark.parametrize("spoiler_url, expected_fields", [(None, []), ("https://samus.test/spoiler", ["Race Spoiler Log"])])
async def test_smz3(monkeypatch, embeds, bot, spoiler_url, expected_fields):
    async def fake_generate(self, tournament=True, spoilers=False):
        self.seed = ("smz3", tournament, spoilers)

    monkeypatch.setattr(gen.SMZ3Preset, "generate", fake_generate)
    monkeypatch.setattr(gen.SMZ3Preset, "spoiler_url", lambda self: spoiler_url)
    cog = cog_module.Generator(bot)
    interaction = FakeInteraction()

    await call(cog.smz3, cog, interaction, "normal", spoiler_race="yes")

    assert embeds[0].seed == ("smz3", False, True)
    assert [f.name for f in interaction.sent().embed.fields] == expected_fields


async def test_smvaria(monkeypatch, embeds, bot):
    make = mock.AsyncMock(return_value="SEED")
    monkeypatch.setattr(cog_module.smvaria, "generate_preset", make)
    cog = cog_module.Generator(bot)
    interaction = FakeInteraction()

    await call(cog.smvaria, cog, interaction, "default", "regular", race="yes")

    make.assert_awaited_once_with(settings="default", skills="regular", race=True)
    assert interaction.sent().embed.title == "varia SEED"


async def test_smvaria_autocompletes_filter_by_prefix(bot):
    cog = cog_module.Generator(bot)
    assert await cog.autocomplete_smvaria_skills(FakeInteraction(), "S") == ["SMRAT2021", "Season_Races"]
    settings = await cog.autocomplete_smvaria_settings(FakeInteraction(), "scav")
    assert settings == sorted(settings) and len(settings) == 4
    assert await cog.autocomplete_smvaria_settings(FakeInteraction(), "zzz") == []


async def test_smdash(monkeypatch, bot):
    make = mock.AsyncMock(return_value="https://dashrando.test/seed/1")
    monkeypatch.setattr(cog_module.smdash, "create_smdash", make)
    monkeypatch.setattr(cog_module.smdash, "get_smdash_presets", mock.AsyncMock(return_value=["sgl23", "classic_mm", "classic_full"]))
    cog = cog_module.Generator(bot)
    interaction = FakeInteraction()

    await call(cog.smdash, cog, interaction, "classic_mm", spoiler="yes")
    choices = await cog.smdash_preset_autocomplete(FakeInteraction(), "CLASSIC")

    make.assert_awaited_once_with(mode="classic_mm", spoiler=True)
    assert interaction.sent().content == "https://dashrando.test/seed/1"
    assert [c.value for c in choices] == ["classic_full", "classic_mm"]


async def test_ctjets(monkeypatch, bot):
    monkeypatch.setattr(gen.CTJetsPreset, "generate", mock.AsyncMock(return_value="https://ctjot.test/seed/x"))
    monkeypatch.setattr(gen.CTJetsPreset, "search", mock.AsyncMock(return_value=["standard"]))
    cog = cog_module.Generator(bot)
    interaction = FakeInteraction()

    await call(cog.ctjets, cog, interaction, "standard")

    assert interaction.sent().content == "https://ctjot.test/seed/x"
    assert [c.value for c in await cog.ctjets_autocomplete(FakeInteraction(), "")] == ["standard"]


async def test_sm_and_smz3_autocomplete(monkeypatch, bot):
    monkeypatch.setattr(gen.SMPreset, "search", mock.AsyncMock(return_value=["casual_full"]))
    cog = cog_module.Generator(bot)
    assert [c.value for c in await cog.sm_autocomplete(FakeInteraction(), "c")] == ["casual_full"]
    assert [c.value for c in await cog.smz3_autocomplete(FakeInteraction(), "c")] == ["casual_full"]


async def test_z2r_preset_and_mrb(monkeypatch, bot):
    monkeypatch.setattr(cog_module.z2r, "preset", lambda name: (1234, f"FLAGS-{name}"))
    monkeypatch.setattr(cog_module.z2r, "mrb", lambda: (5678, "MRBFLAGS", "Spicy"))
    cog = cog_module.Z2RGenerator(bot)

    preset = FakeInteraction()
    await call(cog.preset, cog, preset, "maxrando")
    mrb = FakeInteraction()
    await call(cog.mrb, cog, mrb)

    assert preset.sent().content == "**Seed**: 1234\n**Flags:** FLAGS-maxrando"
    assert mrb.sent().content == "**Seed**: 5678\n**Flags:** MRBFLAGS\n**Description**: Spicy"


def test_get_embed_field():
    embed = discord.Embed().add_field(name="A", value="1")
    assert cog_module.get_embed_field("A", embed) == "1"
    assert cog_module.get_embed_field("B", embed) is None


async def test_setup_adds_every_cog():
    bot = mock.Mock(add_cog=mock.AsyncMock())
    await cog_module.setup(bot)
    assert [type(c.args[0]).__name__ for c in bot.add_cog.await_args_list] == [
        "AlttprGenerator", "AlttprUtils", "Generator", "Z2RGenerator",
    ]


# ---------------------------------------------------------------------------
# /dailygame
# ---------------------------------------------------------------------------


async def test_dailygame(monkeypatch, embeds):
    monkeypatch.setattr(daily_cog, "find_daily_hash", mock.AsyncMock(return_value={"hash": "dailyhash"}))
    retrieve = mock.AsyncMock(return_value="DAILY SEED")
    monkeypatch.setattr(daily_cog.ALTTPRClient, "retrieve", retrieve)
    await daily_cog.get_daily_seed.cache.clear()
    cog = daily_cog.Daily(FakeBot())
    interaction = FakeInteraction()

    await call(cog.dailygame, cog, interaction)
    await call(cog.dailygame, cog, FakeInteraction())

    retrieve.assert_awaited_once_with(hash_id="dailyhash")  # cached for a day
    assert embeds[0].seed == "DAILY SEED"
    assert "daily challenge" in embeds[0].notes
    interaction.response.send_message.assert_awaited_once()
    await daily_cog.get_daily_seed.cache.clear()

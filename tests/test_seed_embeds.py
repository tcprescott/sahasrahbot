"""Discord embeds for generated seeds (alttprbot_discord/util/seed_embeds.py).

Seeds are instances of the real randomizer classes built without calling their
constructors, so ``seed_embed`` dispatches on them as it does in production, but
no randomizer site is called.
"""

import datetime

import discord
import pytest
from pyz3r import ALTTPR
from pyz3r.smvaria import SuperMetroidVaria

from alttprbot.alttprgen.randomizer.alttprdoor import AlttprDoor
from alttprbot.alttprgen.randomizer.avianart import AVIANART
from alttprbot_discord.util import seed_embeds
from tests.discord_fakes import emoji

CODE = ["Bow", "Hookshot", "Big Key", "Heart", "Map"]

SETTINGS_MAP = {
    "item_placement": {"advanced": "Advanced"},
    "dungeon_items": {"standard": "Standard", "full": "Keysanity"},
    "accessibility": {"items": "100% Inventory"},
    "goals": {"ganon": "Defeat Ganon"},
    "world_state": {"open": "Open", "inverted": "Inverted"},
    "entrance_shuffle": {"crossed": "Crossed"},
    "boss_shuffle": {"none": "None", "full": "Full"},
    "enemy_shuffle": {"none": "None"},
    "weapons": {"randomized": "Randomized"},
    "item_pool": {"normal": "Normal"},
    "item_functionality": {"normal": "Normal"},
    "enemy_damage": {"default": "Default"},
    "enemy_health": {"default": "Default"},
}

META = {
    "name": "Open Boots", "notes": "<p>Have <b>fun</b></p>", "logic": "NoGlitches",
    "item_placement": "advanced", "dungeon_items": "standard", "accessibility": "items", "goal": "ganon",
    "entry_crystals_tower": "7", "entry_crystals_ganon": "7", "mode": "open", "hints": "off",
    "enemizer.boss_shuffle": "none", "enemizer.enemy_shuffle": "none", "weapons": "randomized",
    "item_pool": "normal", "item_functionality": "normal", "enemizer.enemy_damage": "default",
    "enemizer.enemy_health": "default",
}

EMOJIS = [emoji(name, i) for i, name in enumerate(["SahasrahBot", *seed_embeds.EMOJI_CODE_MAP.values()])]


class FakeALTTPR(ALTTPR):
    code = CODE
    url = "https://alttpr.test/h/abc"

    async def randomizer_settings(self):
        return SETTINGS_MAP


def alttpr_seed(**meta):
    seed = FakeALTTPR.__new__(FakeALTTPR)
    seed.data = {"spoiler": {"meta": {**META, **meta}}, "generated": "2024-06-01T18:00:00+00:00"}
    return seed


def values(embed):
    return {f.name: f.value for f in embed.fields}


def test_file_select_code_with_and_without_emojis():
    seed = alttpr_seed()
    assert seed_embeds.build_file_select_code(seed) == "Bow/Hookshot/Big Key/Heart/Map"
    with_emojis = seed_embeds.build_file_select_code(seed, EMOJIS)
    assert with_emojis.startswith("<:Bow:")
    assert with_emojis.endswith(" (Bow/Hookshot/Big Key/Heart/Map)")
    assert "<:BigKey:" in with_emojis and "<:ALotOfLove:" in with_emojis


async def test_alttpr_embed_settings():
    embed = await seed_embeds.seed_embed(alttpr_seed(shuffle="crossed", **{"enemizer.pot_shuffle": "on"}),
                                         emojis=EMOJIS)
    assert embed.title == "Open Boots"
    assert embed.description.strip() == "Have __fun__"
    assert embed.colour == discord.Colour.dark_red()
    assert embed.timestamp == datetime.datetime(2024, 6, 1, 18, tzinfo=datetime.timezone.utc)
    v = values(embed)
    assert list(v) == ["Item Placement", "Goal", "Gameplay", "Difficulty", "File Select Code", "Permalink"]
    assert v["Item Placement"] == ("**Glitches Required:** NoGlitches\n**Item Placement:** Advanced\n"
                                   "**Dungeon Items:** Standard\n**Accessibility:** 100% Inventory")
    assert v["Goal"] == "**Goal:** Defeat Ganon\n**Open Tower:** 7\n**Ganon Vulnerable:** 7"
    assert "**Entrance Shuffle:** Crossed" in v["Gameplay"] and "**Pot Shuffle:** on" in v["Gameplay"]
    assert v["Permalink"] == "https://alttpr.test/h/abc"
    assert embed.footer.text == "Generated"
    assert embed.footer.icon_url == EMOJIS[0].url


async def test_alttpr_embed_defaults_when_meta_is_sparse():
    seed = alttpr_seed()
    for key in ("entry_crystals_tower", "entry_crystals_ganon"):
        del seed.data["spoiler"]["meta"][key]
    embed = await seed_embeds.alttpr_embed(seed, emojis=EMOJIS, name="Custom", notes="Notes")
    v = values(embed)
    assert (embed.title, embed.description) == ("Custom", "Notes")
    assert "**Open Tower:** unknown" in v["Goal"]
    assert "**Entrance Shuffle:** None" in v["Gameplay"] and "**Pot Shuffle:** off" in v["Gameplay"]


async def test_alttpr_embed_without_meta_uses_requested_seed():
    seed = alttpr_seed()
    seed.data["spoiler"] = {}
    embed = await seed_embeds.alttpr_embed(seed, emojis=EMOJIS, include_settings=False)
    assert embed.title == "Requested Seed"
    assert list(values(embed)) == ["File Select Code", "Permalink"]


async def test_alttpr_mystery_and_festive_embeds():
    mystery = await seed_embeds.alttpr_embed(alttpr_seed(spoilers="mystery"), emojis=EMOJIS)
    assert list(values(mystery))[:2] == ["Mystery Game", "Item Placement"]
    assert values(mystery)["Item Placement"] == "**Glitches Required:** NoGlitches"

    festive = await seed_embeds.alttpr_embed(alttpr_seed(special=True), emojis=EMOJIS)
    v = values(festive)
    assert list(v)[:2] == ["Festive Randomizer", "Settings"]
    assert "**World State:** Open\n**Hints:** off\n**Swords:** Randomized" in v["Settings"]


async def test_alttpr_tournament_embed_hides_permalink():
    embed = await seed_embeds.seed_tournament_embed(alttpr_seed(), emojis=EMOJIS)
    assert embed.colour == discord.Colour.dark_gold()
    assert "Permalink" not in values(embed)


def door_seed(spoilers=True, attempts=3):
    seed = AlttprDoor.__new__(AlttprDoor)
    seed.__dict__.update(spoilers=spoilers, attempts=attempts, spoiler_name="door.txt")
    return seed


@pytest.fixture
def door_props(monkeypatch):
    monkeypatch.setattr(AlttprDoor, "code", property(lambda self: CODE))
    monkeypatch.setattr(AlttprDoor, "url", property(lambda self: "https://door.test/seed"))
    monkeypatch.setattr(AlttprDoor, "version", property(lambda self: "1.4.1"))


async def test_door_embeds(door_props):
    public = await seed_embeds.seed_embed(door_seed(), emojis=EMOJIS)
    assert (public.title, public.description) == ("Requested Seed", "Requested Door Randomizer Game.")
    assert list(values(public)) == ["Door Randomizer", "File Select Code", "Permalink", "Spoiler Log",
                                    "Generation Attempts", "Version"]
    assert values(public)["Generation Attempts"] == "3"
    assert values(public)["Spoiler Log"].endswith(".s3.amazonaws.com/spoiler/door.txt")

    quiet = await seed_embeds.seed_embed(door_seed(spoilers=False), emojis=EMOJIS, name="N", notes="D")
    assert (quiet.title, quiet.description) == ("N", "D")
    assert "Spoiler Log" not in values(quiet)

    first_try = await seed_embeds.seed_tournament_embed(door_seed(attempts=1), emojis=EMOJIS, name="Race")
    assert list(values(first_try)) == ["Door Randomizer", "File Select Code", "Spoiler Log", "Version"]
    no_spoiler = seed_embeds.door_tournament_embed(door_seed(spoilers=False), emojis=EMOJIS)
    assert list(values(no_spoiler)) == ["Door Randomizer", "File Select Code", "Version"]
    big = seed_embeds.door_tournament_embed(door_seed(), emojis=EMOJIS)
    assert "Generation Attempts" in values(big)


async def test_avianart_embeds(monkeypatch):
    monkeypatch.setattr(AVIANART, "code", property(lambda self: CODE))
    monkeypatch.setattr(AVIANART, "url", property(lambda self: "https://avianart.test/perm/x"))
    monkeypatch.setattr(AVIANART, "version", property(lambda self: "0.9"), raising=False)
    seed = AVIANART.__new__(AVIANART)
    seed.__dict__["preset"] = "open"

    public = await seed_embeds.seed_embed(seed, emojis=EMOJIS)
    assert list(values(public)) == ["AVIANART", "Preset", "File Select Code", "Permalink", "Version"]
    assert values(public)["Preset"] == "open"

    tournament = await seed_embeds.seed_tournament_embed(seed, emojis=EMOJIS, name="Race", notes="n")
    assert list(values(tournament)) == ["Door Randomizer", "File Select Code", "Version"]


def test_smvaria_embed(monkeypatch):
    seed = SuperMetroidVaria.__new__(SuperMetroidVaria)
    seed.__dict__.update(skills_preset="regular", settings_preset="default", data={"errorMsg": "Watch out"})
    monkeypatch.setattr(SuperMetroidVaria, "url", property(lambda self: "https://varia.test/seed"), raising=False)

    embed = seed_embeds.smvaria_embed(seed)
    assert embed.description == "**Skills preset: **regular\n**Settings preset: **default"
    assert values(embed) == {"Link": "https://varia.test/seed", "Warnings": "Watch out"}

    seed.data = {"errorMsg": ""}
    assert list(values(seed_embeds.smvaria_embed(seed))) == ["Link"]

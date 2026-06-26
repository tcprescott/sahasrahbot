"""Tests for the seed-embed presenter dispatcher (presentation).

Verifies that `seed_embed` / `seed_tournament_embed` route to the correct
per-randomizer builder based on the seed's type — the behavior that replaced the
old per-class `seed.embed()` method dispatch. The real builders read pyz3r
computed properties (`code`/`url`), so routing is tested by swapping the dispatch
table for tagged stubs; one real builder (`smvaria_embed`, which uses plain
attributes) is exercised end-to-end.
"""

import discord
import pytest

import alttprbot.presentation.discord.util.seed_embeds as seed_embeds
from alttprbot.presentation.discord.util.seed_embeds import (
    seed_embed,
    seed_tournament_embed,
    smvaria_embed,
)
from alttprbot.services.seedgen.seedclasses import (
    ALTTPRSeed,
    AlttprDoorSeed,
    AVIANARTSeed,
    SMSeed,
    SMZ3Seed,
)


def _tagged_table():
    def builder(tag):
        async def fn(seed, **kwargs):
            return {"tag": tag, "kwargs": kwargs}
        return fn

    return (
        (ALTTPRSeed, builder("alttpr")),
        (AlttprDoorSeed, builder("door")),
        (AVIANARTSeed, builder("avianart")),
        (SMSeed, builder("sm")),
    )


@pytest.mark.parametrize("cls, expected", [
    (ALTTPRSeed, "alttpr"),
    (AlttprDoorSeed, "door"),
    (AVIANARTSeed, "avianart"),
    (SMSeed, "sm"),
    (SMZ3Seed, "sm"),  # SMZ3 is an SMSeed -> shares the SM builder
])
async def test_seed_embed_routes_by_type(monkeypatch, cls, expected):
    monkeypatch.setattr(seed_embeds, "_EMBED_DISPATCH", _tagged_table())
    result = await seed_embed(cls.__new__(cls))
    assert result["tag"] == expected


async def test_seed_embed_forwards_kwargs(monkeypatch):
    monkeypatch.setattr(seed_embeds, "_EMBED_DISPATCH", _tagged_table())
    result = await seed_embed(ALTTPRSeed.__new__(ALTTPRSeed), name="X", include_settings=False)
    assert result["kwargs"] == {"name": "X", "include_settings": False}


async def test_tournament_embed_routes_by_type(monkeypatch):
    monkeypatch.setattr(seed_embeds, "_TOURNAMENT_EMBED_DISPATCH", _tagged_table())
    result = await seed_tournament_embed(AlttprDoorSeed.__new__(AlttprDoorSeed))
    assert result["tag"] == "door"


async def test_alttpr_is_exclusive_to_alttpr_builder():
    # ALTTPRSeed must not be an instance of any other builder's type,
    # so the dispatcher can only route it to the alttpr builder.
    alttpr = ALTTPRSeed.__new__(ALTTPRSeed)
    assert not isinstance(alttpr, (AlttprDoorSeed, AVIANARTSeed, SMSeed))


async def test_smvaria_embed_builds_embed():
    seed = object.__new__(type("V", (), {}))
    seed.skills_preset = "expert"
    seed.settings_preset = "tournament"
    seed.url = "http://varia/seed"
    seed.data = {}
    embed = smvaria_embed(seed)
    assert isinstance(embed, discord.Embed)
    assert dict((f.name, f.value) for f in embed.fields)["Link"] == "http://varia/seed"


async def test_unknown_seed_type_raises():
    with pytest.raises(TypeError):
        await seed_embed(object())
    with pytest.raises(TypeError):
        await seed_tournament_embed(object())

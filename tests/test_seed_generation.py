"""Seed generation is a service layer: no Discord, racetime or web imports.

The randomizer clients in ``alttprbot/alttprgen/`` generate and describe seeds;
``alttprbot_discord/util/seed_embeds.py`` turns them into Discord embeds.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SEED_GENERATION_MODULES = [
    "alttprbot.alttprgen.generator",
    "alttprbot.alttprgen.spoilers",
    "alttprbot.alttprgen.smz3multi",
    "alttprbot.alttprgen.smvaria",
    "alttprbot.alttprgen.randomizer.alttpr",
    "alttprbot.alttprgen.randomizer.alttprdoor",
    "alttprbot.alttprgen.randomizer.avianart",
    "alttprbot.alttprgen.randomizer.mysterydoors",
    "alttprbot.alttprgen.randomizer.sm",
]

_BOUNDARY_CHECK = """
import sys
sys.path.insert(0, {root!r})
sys.path.insert(0, {tests!r})
import conftest
import importlib
importlib.import_module({module!r})
bad = sorted(m for m in sys.modules
             if m.split('.')[0] in ('alttprbot_discord', 'alttprbot_racetime', 'alttprbot_api'))
assert not bad, bad
"""


@pytest.mark.parametrize("module", SEED_GENERATION_MODULES)
def test_seed_generation_imports_no_presentation_layer(module):
    code = _BOUNDARY_CHECK.format(root=str(ROOT), tests=str(ROOT / "tests"), module=module)
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, f"{module} pulled in a presentation-layer module:\n{result.stderr[-4000:]}"


FORBIDDEN_LIBRARIES = {"discord", "racetime_bot", "quart", "quart_discord"}


def test_seed_generation_code_has_no_presentation_imports():
    """No module under alttprbot/alttprgen/ imports a chat or web library itself.

    (The import check above can't assert this for ``discord``, because
    ``alttprbot.models`` still imports ``discord.utils``.)
    """
    import ast

    offenders = []
    for path in sorted((ROOT / "alttprbot" / "alttprgen").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(), str(path))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                if name.split(".")[0] in FORBIDDEN_LIBRARIES:
                    offenders.append(f"{path.relative_to(ROOT)}:{node.lineno} imports {name}")
    assert not offenders, "\n".join(offenders)


def _alttpr_data(**meta):
    return {"spoiler": {"meta": meta}}


@pytest.mark.parametrize("meta, expected", [
    ({}, "casual open"),
    ({"spoilers": "mystery"}, "mystery"),
    ({"mode": "standard"}, "standard"),
    ({"mode": "inverted", "dungeon_items": "mcs"}, "inverted mcs"),
    ({"weapons": "swordless", "enemizer.boss_shuffle": "full"}, "enemizer swordless open"),
    ({"goal": "fast_ganon", "entry_crystals_tower": "0", "entry_crystals_ganon": "0"}, "casual open 0/0 fast ganon"),
    ({"dungeon_items": "full", "goal": "dungeons"}, "all dungeons keysanity"),
    ({"item_pool": "hard", "shuffle": "crossed"}, "hard open defeat ganon + entrance shuffle"),
    ({"difficulty": "custom"}, "casual open (customizer)"),
])
def test_alttpr_generated_goal(meta, expected):
    from alttprbot.alttprgen.randomizer.alttpr import generated_goal

    assert generated_goal(_alttpr_data(**meta)) == expected


_SM_ARGS = dict(settings=None, slug_id=None, guid_id=None, baseurl=None, randomizer=None, username=None,
                password=None)


def test_sm_clients_report_their_randomizer():
    from alttprbot.alttprgen.randomizer.sm import SMClient, SMZ3Client

    assert SMClient(**_SM_ARGS).generated_goal == "sm"
    assert SMZ3Client(**_SM_ARGS).generated_goal == "smz3"


def test_seed_embed_dispatches_on_seed_type():
    from alttprbot.alttprgen.randomizer.sm import SMZ3Client
    from alttprbot_discord.util.seed_embeds import seed_embed, seed_tournament_embed

    class FakeSeed(SMZ3Client):
        code = "Kraid Ridley Phantoon Draygon"
        url = "https://samus.link/seed/abc"

    seed = FakeSeed(**_SM_ARGS)

    embed = asyncio.run(seed_embed(seed))
    assert embed.description == "Requested SMZ3 Randomizer Game."
    assert [f.name for f in embed.fields] == ["File Select Code", "Permalink"]

    tournament = asyncio.run(seed_tournament_embed(seed, name="Race"))
    assert tournament.title == "Race"
    assert [f.name for f in tournament.fields] == ["File Select Code"]


def test_seed_embed_rejects_unknown_seed_type():
    from alttprbot_discord.util.seed_embeds import seed_embed

    with pytest.raises(TypeError):
        asyncio.run(seed_embed(object()))


def test_seed_presenter_requires_registration_then_delegates():
    """Core reaches the Discord embed builders only through the hook sahasrahbot.py registers."""
    from alttprbot.util import seed_presenter

    saved = (seed_presenter._embed_builder, seed_presenter._tournament_embed_builder)
    try:
        seed_presenter.register(None, None)
        with pytest.raises(RuntimeError):
            asyncio.run(seed_presenter.seed_embed(object()))

        async def public(seed, **kwargs):
            return ("public", seed, kwargs)

        async def tournament(seed, **kwargs):
            return ("tournament", seed, kwargs)

        seed_presenter.register(public, tournament)
        assert asyncio.run(seed_presenter.seed_embed("s", name="n")) == ("public", "s", {"name": "n"})
        assert asyncio.run(seed_presenter.seed_tournament_embed("s")) == ("tournament", "s", {})
    finally:
        seed_presenter.register(*saved)


def test_discord_gateways_register_seed_embeds(monkeypatch):
    """sahasrahbot.py calls alttprbot_discord.gateways.register() at startup, which installs the builders."""
    from alttprbot.util import seed_presenter
    from alttprbot_discord import gateways
    from alttprbot_discord.util import seed_embeds

    # Leave the async tournament service's hooks alone; only the seed hook is under test.
    monkeypatch.setattr(gateways.asynctournament_service, "set_member_role_lookup", lambda fn: None)
    monkeypatch.setattr(gateways.asynctournament_jobs, "set_timeout_notifier", lambda fn: None)

    saved = (seed_presenter._embed_builder, seed_presenter._tournament_embed_builder)
    try:
        gateways.register()
        assert seed_presenter._embed_builder is seed_embeds.seed_embed
        assert seed_presenter._tournament_embed_builder is seed_embeds.seed_tournament_embed
    finally:
        seed_presenter.register(*saved)

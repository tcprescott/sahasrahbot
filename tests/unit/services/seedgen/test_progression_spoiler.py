"""Characterization tests for progression-spoiler filtering.

Targets ``create_progression_spoiler`` from
alttprbot/services/seedgen/ext/progression_spoiler.py. ``mw_filter`` (multiworld
filter from pyz3r) is patched to the identity function so the test controls the
exact location -> item mapping per region.
"""

from collections import OrderedDict
from types import SimpleNamespace

import pytest

from alttprbot.services.seedgen.ext import progression_spoiler
from alttprbot.services.seedgen.ext.progression_spoiler import REGIONLIST, create_progression_spoiler


@pytest.fixture(autouse=True)
def identity_mw_filter(monkeypatch):
    monkeypatch.setattr(progression_spoiler, "mw_filter", lambda region: region)


def make_seed(spoiler_meta, regions=None, seed_hash="ABCDE", url="https://alttpr.com/h/ABCDE"):
    """Build a fake seed. Every region in REGIONLIST is present (empty by default)."""
    spoiler = {region: {} for region in REGIONLIST}
    if regions:
        spoiler.update(regions)
    spoiler["meta"] = spoiler_meta
    return SimpleNamespace(data={"spoiler": spoiler}, hash=seed_hash, url=url)


@pytest.mark.parametrize("spoilers_value", ["off", None, "races"])
def test_returns_none_when_spoilers_not_enabled(spoilers_value):
    meta = {"spoilers": spoilers_value} if spoilers_value is not None else {}
    seed = make_seed(meta)
    assert create_progression_spoiler(seed) is None


@pytest.mark.parametrize("spoilers_value", ["on", "generate"])
def test_enabled_spoiler_values_proceed(spoilers_value):
    seed = make_seed({"spoilers": spoilers_value, "shuffle": "none"})
    result = create_progression_spoiler(seed)
    assert result is not None


def test_entrance_shuffle_raises():
    seed = make_seed({"spoilers": "on", "shuffle": "full"})
    with pytest.raises(Exception, match="Entrance randomizer"):
        create_progression_spoiler(seed)


def test_filters_to_progression_items_only():
    seed = make_seed(
        {"spoilers": "on", "shuffle": "none"},
        regions={
            "Light World": {"Loc A": "Lamp", "Loc B": "RupeeGreen", "Loc C": "Hookshot"},
            "Ganons Tower": {"Loc D": "MoonPearl"},
            "Eastern Palace": {"Loc E": "TenArrows"},  # no progression -> omitted
        },
    )
    result = create_progression_spoiler(seed)

    assert isinstance(result, OrderedDict)
    assert result["Light World"] == ["Loc A", "Loc C"]  # Lamp + Hookshot, not RupeeGreen
    assert result["Ganons Tower"] == ["Loc D"]
    assert "Eastern Palace" not in result  # filtered out: no progression items
    # Regions are emitted in REGIONLIST order (Ganons Tower #12 precedes Light World #13),
    # not in the input dict's insertion order.
    assert [k for k in result if k != "meta"] == ["Ganons Tower", "Light World"]


def test_meta_carries_hash_and_permalink():
    seed = make_seed({"spoilers": "generate", "shuffle": "none"}, seed_hash="HASH1", url="https://x/y")
    result = create_progression_spoiler(seed)
    assert result["meta"]["hash"] == "HASH1"
    assert result["meta"]["permalink"] == "https://x/y"


def test_meta_is_aliased_not_copied():
    # Characterizes a side effect: hash/permalink are stamped onto the SAME meta
    # dict held by the seed (an alias, not a copy). A refactor to deepcopy would
    # change this behavior.
    seed = make_seed({"spoilers": "on", "shuffle": "none"})
    result = create_progression_spoiler(seed)
    assert result["meta"] is seed.data["spoiler"]["meta"]

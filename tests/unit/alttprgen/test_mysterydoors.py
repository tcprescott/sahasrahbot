"""Characterization tests for the mystery weight -> settings transform.

Targets ``generate_doors_settings`` from
alttprbot/alttprgen/randomizer/mysterydoors.py.

``get_random_option`` is patched to the identity function so every weighted
choice resolves to the literal value we provide -- this makes the mapping
deterministic and lets us assert how options translate into the settings
payload. The ``options`` dict is pre-populated with the keys the real caller
(``generate_doors_mystery``) sets before delegating, since
``generate_doors_settings`` reads but does not set them.
"""

import pytest

from alttprbot.alttprgen.randomizer import mysterydoors
from alttprbot.alttprgen.randomizer.mysterydoors import generate_doors_settings

# Keys accessed on weights without a default -> must always be present.
REQUIRED_WEIGHTS = {
    "glitches_required": "none",
    "dungeon_items": "standard",
    "accessibility": "items",
    "goals": "ganon",
    "ganon_open": "7",
    "tower_open": "7",
    "world_state": "open",
    "hints": "off",
    "weapons": "randomized",
    "item_pool": "normal",
    "item_functionality": "normal",
    "boss_shuffle": "none",
    "enemy_shuffle": "none",
    "enemy_damage": "default",
    "enemy_health": "default",
    "entrance_shuffle": "none",
}

# Keys read from options but populated by the caller, not by the function.
CALLER_OPTIONS = {
    "door_shuffle": "vanilla",
    "keydropshuffle": "off",
    "dropshuffle": "off",
    "pottery": "none",
    "shopsanity": "off",
    "collection_rate": "off",
    "bombbag": "off",
}


@pytest.fixture(autouse=True)
def identity_random(monkeypatch):
    """Resolve every weighted choice to its literal value."""
    monkeypatch.setattr(mysterydoors, "get_random_option", lambda value: value)


def make_weights(**overrides):
    weights = dict(REQUIRED_WEIGHTS)
    weights.update(overrides)
    return weights


def make_options(**overrides):
    options = dict(CALLER_OPTIONS)
    options.update(overrides)
    return options


def test_baseline_open_world_mapping():
    settings = generate_doors_settings(make_weights(), make_options())
    assert settings["retro"] is False
    assert settings["mode"] == "open"
    assert settings["goal"] == "ganon"
    assert settings["swords"] == "random"
    assert settings["difficulty"] == "normal"
    assert settings["shuffleganon"] is True
    assert settings["shuffle"] == "vanilla"
    assert settings["usestartinventory"] is False


def test_crystals_cross_mapping_is_directional():
    # crystals_gt <- tower_open and crystals_ganon <- ganon_open (a cross-mapping).
    # Distinct values pin the direction; equal values would hide a swap.
    settings = generate_doors_settings(
        make_weights(tower_open="4", ganon_open="6"), make_options()
    )
    assert settings["crystals_gt"] == "4"
    assert settings["crystals_ganon"] == "6"


def test_retro_world_state_sets_retro_and_open_mode():
    settings = generate_doors_settings(make_weights(world_state="retro"), make_options())
    assert settings["retro"] is True
    assert settings["mode"] == "open"


@pytest.mark.parametrize(
    "goals, expected_goal",
    [("fast_ganon", "crystals"), ("triforce-hunt", "triforcehunt"), ("ganon", "ganon"), ("dungeons", "dungeons")],
)
def test_goal_mapping(goals, expected_goal):
    settings = generate_doors_settings(make_weights(goals=goals), make_options())
    assert settings["goal"] == expected_goal


@pytest.mark.parametrize(
    "weapons, expected_swords",
    [("randomized", "random"), ("assured", "assured"), ("vanilla", "vanilla"), ("swordless", "swordless")],
)
def test_swords_mapping(weapons, expected_swords):
    # world_state stays 'open' so the standard-mode "assured" override does not fire.
    settings = generate_doors_settings(make_weights(weapons=weapons), make_options())
    assert settings["swords"] == expected_swords


def test_standard_mode_forces_assured_weapons_with_enemizer():
    # The "survivors of SRL #264658" rule: non-vanilla/assured weapons in
    # standard with any enemizer setting are bumped to assured.
    settings = generate_doors_settings(
        make_weights(world_state="standard", weapons="randomized", enemy_shuffle="shuffled"),
        make_options(),
    )
    assert settings["swords"] == "assured"


def test_standard_mode_without_enemizer_keeps_weapons():
    # Negative case: same standard/randomized but enemizer all-default -> the
    # override must NOT fire, so swords stays 'random'.
    settings = generate_doors_settings(
        make_weights(
            world_state="standard",
            weapons="randomized",
            enemy_shuffle="none",
            enemy_damage="default",
            enemy_health="default",
        ),
        make_options(),
    )
    assert settings["swords"] == "random"


@pytest.mark.parametrize(
    "dungeon_items, mapshuffle, keyshuffle, bigkeyshuffle, keysanity",
    [
        ("standard", False, False, False, False),
        ("mcs", True, True, False, False),
        ("full", True, True, True, True),
    ],
)
def test_dungeon_items_drive_shuffle_flags(dungeon_items, mapshuffle, keyshuffle, bigkeyshuffle, keysanity):
    # With these keys absent from weights, the dungeon shuffle flags derive from
    # options['dungeon_items'] membership (mc/mcs/full).
    settings = generate_doors_settings(make_weights(dungeon_items=dungeon_items), make_options())
    assert settings["mapshuffle"] is mapshuffle
    assert settings["keyshuffle"] is keyshuffle
    assert settings["bigkeyshuffle"] is bigkeyshuffle
    assert settings["keysanity"] is keysanity


def test_matching_rule_overrides_option():
    weights = make_weights(
        rules=[{"conditions": [{"Key": "world_state", "Value": "open"}], "actions": {"item_pool": "hard"}}]
    )
    settings = generate_doors_settings(weights, make_options())
    assert settings["difficulty"] == "hard"


def test_non_matching_rule_leaves_option_untouched():
    weights = make_weights(
        rules=[{"conditions": [{"Key": "world_state", "Value": "inverted"}], "actions": {"item_pool": "hard"}}]
    )
    settings = generate_doors_settings(weights, make_options())
    assert settings["difficulty"] == "normal"

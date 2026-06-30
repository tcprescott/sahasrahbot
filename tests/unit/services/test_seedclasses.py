"""Characterization tests for the extracted seed classes' `generated_goal`."""

from alttprbot.services.seedgen.seedclasses import (
    ALTTPRSeed,
    AlttprDoorSeed,
    AVIANARTSeed,
    SMSeed,
    SMZ3Seed,
)


def _alttpr_with_meta(meta):
    # bypass pyz3r __init__; generated_goal only reads self.data
    seed = ALTTPRSeed.__new__(ALTTPRSeed)
    seed.data = {"spoiler": {"meta": meta}}
    return seed


def test_alttpr_generated_goal_defaults():
    # an all-defaults open/ganon seed summarizes as "casual open"
    assert _alttpr_with_meta({}).generated_goal == "casual open"


def test_alttpr_generated_goal_mystery():
    assert _alttpr_with_meta({"spoilers": "mystery"}).generated_goal == "mystery"


def test_alttpr_generated_goal_keysanity_inverted():
    meta = {"mode": "inverted", "dungeon_items": "full", "goal": "ganon"}
    goal = _alttpr_with_meta(meta).generated_goal
    assert "inverted" in goal and "keysanity" in goal


def test_trivial_generated_goals():
    assert AlttprDoorSeed.__new__(AlttprDoorSeed).generated_goal == "door randomizer"

    avianart = AVIANARTSeed.__new__(AVIANARTSeed)
    avianart.preset = "mypreset"
    assert avianart.generated_goal == "mypreset"

    sm = SMSeed.__new__(SMSeed)
    sm.randomizer = "sm"
    assert sm.generated_goal == "sm"

    smz3 = SMZ3Seed.__new__(SMZ3Seed)
    smz3.randomizer = "smz3"
    assert smz3.generated_goal == "smz3"


def test_seed_class_hierarchy():
    # SMZ3 is an SM seed (shares the SM embed builder); the alttpr-family are distinct
    assert issubclass(SMZ3Seed, SMSeed)
    assert not issubclass(AlttprDoorSeed, ALTTPRSeed)
    assert not issubclass(AVIANARTSeed, ALTTPRSeed)

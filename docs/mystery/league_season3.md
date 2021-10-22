---
layout: default
title:  League Season 3 Weightset
---
* Table of contents
{: toc}
# League Season 3 Weight Explaination

The [ALTTPR League Season 3 Mystery Weights](https://github.com/tcprescott/sahasrahbot/blob/master/weights/league.yaml) (click the link to view them directly)
are more complex than the weights for the previous season.  This document outlines
the meaning of this weightset and how it'll impact you during mystery week.

The goal of this weightset is to create a more balanced experience that, hopefully
will result in objectively more fun™.

This weightset has several "global" weights that are the same regardless of the
subweight chosen, plus three subweights (entrance, normal, and triforce).
One subweight will be chosen and those weights will be used to determine the
rest of the weights used to roll your game.

## Global/Default Weights

This enables Quickswap.  Quickswap will be available for all League Season 3 races.
```yaml
allow_quickswap: true
```

This tells the mystery generator to fill the rest of the item pool with "Green 20s"
if necessary to get the item pool up to 216 items.
```yaml
options:
  FillItemPoolWith: TwentyRupees2
```

Sorry glitched folks, this is a non-glitched league.  OWG League when?
```yaml
glitches_required: "none"
```

All mystery games will have "normal" item functionality.  No modification of
item behavior will occur this season (at least for mystery week).
```yaml
item_functionality: "normal"
```

Item placement will always be set to "advanced".
```yaml
item_placement: "advanced"
```

Hints will never be enabled.
```yaml
hints: "off"
```

This is also pretty balanced.  We've skewed it a bit away from Swordless.
```yaml
weapons:
  randomized: 45
  assured: 25
  vanilla: 20
  swordless: 10
```

Boss shuffle will always have a 10% chance of simple, 10% of full, and 10% of
random (known as Chaos on the website).
```yaml
boss_shuffle:
  none: 70
  simple: 10
  full: 10
  random: 10
```

Enemy shuffle has a 20% chance of being enabled.
No random/chaos enemy shuffle, because unkillable theives are terrible.
```yaml
enemy_shuffle:
  none: 80
  shuffled: 20
```

Enemy damage and health will always be default.
```yaml
enemy_damage: "default"
enemy_health: "default"
```

## Subweights

There are three subweights this season: entrance, normal, and triforce.

1. Entrance has a 30% chance of being selected.
2. Normal has a 60% chance of being selected.
3. Triforce Hunt has a 10% chance of being selected.

### entrance subweight

You're more likely than not going to have full keysanity when entrance is rolled.
```yaml
dungeon_items:
  standard: 30
  full: 70 # Keysanity
```

This is pretty normal as well.
```yaml
accessibility:
  items: 65
  locations: 10
  none: 25
```

The entrance subweight skews more towards Fast Ganon instead of Defeat Ganon.
We're also excluding Triforce Hunt from ER.
```yaml
goals:
  ganon: 30
  fast_ganon: 60
  dungeons: 10
  pedestal: 10
  triforce-hunt: 0 # never have ER triforce hunt
```

We're going to have an equal chance of the tower being open with 0 crystals, or all 7.
```yaml
tower_open:
  "0": 1
  "1": 1
  "2": 1
  "3": 1
  "4": 1
  "5": 1
  "6": 1
  "7": 1
```

Compared to the normal subweight, entrance will be a bit more skewed towards
games that require fewer crystals to defeat ganon.
```yaml
ganon_open:
  "0": 2
  "1": 2
  "2": 2
  "3": 10
  "4": 20
  "5": 24
  "6": 20
  "7": 20
```

We're keeping a relatively balanced set of choices for world state, skewing slightly towards standard and open.
Retro is included here because when coupled with Entrance Randomizer it can be more fun.
```yaml
world_state:
  standard: 30
  open: 35
  inverted: 25
  retro: 10
```

Nice.
```yaml
entrance_shuffle:
  simple: 31
  crossed: 69
```

No expert item pool here.  Entrance Randomizer will already give you plenty to do.
```yaml
item_pool:
  normal: 90
  hard: 10
  expert: 0
```

### normal subweight

When the normal subweight is rolled, the customizer comes into play.
This will create an experience you're likely not experienced before.

Maps, Compasses, Small Keys, and Big Keys are shuffled independantly, so we
leave this set to "standard" and let the customizer section handle this.
```yaml
dungeon_items: "standard"
```

```yaml
accessibility:
  items: 55
  locations: 10
  none: 35
```

A balance of goals.  Instead of heavily shifting the focus to Fast Ganon, we're
making it a bit more balanced.  Notice that Triforce Hunt is missing here, that
will be covered by the "triforce" subweight.
```yaml
goals:
  ganon: 45
  fast_ganon: 35
  dungeons: 10
  pedestal: 10
  triforce-hunt: 0
```

We want Ganon's Tower to be available later, as opposed to Entrance Randomizer.
Nobody likes pendant dungeons, right?
```yaml
tower_open:
  "0": 0
  "1": 0
  "2": 0
  "3": 15
  "4": 15
  "5": 20
  "6": 25
  "7": 25
```

For item randomizer, we want to skew the game more towards requiring all
7 crystals to defeat Ganon.  We also want to avoid games that could end quickly
due to low Ganon requirements.
```yaml
ganon_open:
  "0": 0
  "1": 0
  "2": 0
  "3": 10
  "4": 10
  "5": 20
  "6": 20
  "7": 40
```

We're excluding retro for item randomizer in general.
```yaml
world_state:
  standard: 45
  open: 45
  inverted: 10
  retro: 0
```

Well, it is the item randomizer subweight right?
```yaml
entrance_shuffle: "none"
```

We're adding a small chance of expert for the normal and triforce subweights.
```yaml
item_pool:
  normal: 70
  hard: 25
  expert: 5
```

This is the meat of the customizer settings you'll need to deal with.  These also apply to the triforce subweight.
The "eq" section provides a chance to start with Pegasus Boots or a pre-activated Flute.

If the world state is `standard`, the Flute will instead be deactivated and must
be reactivated after finishing escape.  This is to prevent rainstate-related
softlocks from occuring.
```yaml
customizer:
  eq:
    "PegasusBoots":
      True: 50
      False: 50
    "OcarinaActive":
      True: 50
      False: 50
```

This forces v31 prize pack rules.  Otherwise, we'd have completely random prize
packs which isn't really in line with what we'd want.
```yaml
  custom:
    customPrizePacks: False
```

This independantly activates "wild" Maps, Compasses, Small Keys, and Big Keys.
The keysanity menu, when you press start, is automatically updated to reflect what is shuffled.
```yaml
    region.wildMaps:
      True: 40
      False: 60
    region.wildCompasses:
      True: 40
      False: 60
    region.wildKeys:
      True: 40
      False: 60
    region.wildBigKeys:
      True: 40
      False: 60
```

This enables a bow that costs rupees, instead of arrows, to fire.
This is the bow behavior from retro world state.

You'll need to purchase wooden arrows from a shop, just like retro.
```yaml
    rom.rupeeBow:
      True: 10
      False: 90
```

This makes all small keys universal and puts small keys in the shops.
This is the small key behavior from retro world state.
```yaml
    rom.genericKeys:
      True: 10
      False: 90
```

This causes uncle to give up the deets on the Pegasus Boots location.   This
is only applicable in standard world state.  If you miss the hint from Uncle,
the signpost east of Link's House also has this info.
```yaml
    spoil.BootsLocation:
      True: 70
      False: 30
```

### triforce subweight

This subweight is similar to the normal subweight, so we're going going to
commentate on the differences.

For Triforce Hunt, we're going to ensure beatable-only cannot be chosen.
Beatable-only accessibility causes a very front-loaded game when playing
Triforce Hunt.
```yaml
accessibility:
  items: 90
  locations: 10
  none: 0
```

This forces Triforce Hunt, which is the gimmic of this subweight.
```yaml
goals: triforce-hunt
```

This is just for clarity.  The vulnerability of Ganon is irrelevent.
```yaml
ganon_open: "7"
```

We're also not going to be using entrance randomizer for any Triforce Hunts.
```yaml
entrance_shuffle: "none"
```

The `triforce-hunt` section lets us specify the number of Triforce Pieces required
to complete the game, and also specify how many are in the pool.

We can have from 20 to 50 triforce pieces required to beat the game,
30 to 60 pieces availabe in the item pool, and at least a difference of 10 pieces
between what is required, and the number of pieces available in the item pool.
```yaml
customizer:
  triforce-hunt:
    goal: [20, 50]
    pool: [30, 60]
    min_difference: 10
```

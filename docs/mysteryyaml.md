---
layout: default title:  Mystery YAML file documentation
---

* Table of contents {: toc}

# Mystery YAML file documentation

The mystery weightset yaml file (aka. "weightset"), can be a bit confusing to understand, especially with some of the
more advanced features. This document is intended to help you craft your own mystery weights for use with SahasrahBot.

# Basics

At the start of each weightset, a `description` should be provided of the weightset.

```yaml
description: Example description.
```

For a basic weightset, a value, and its weight, needs to be specified for the following settings: glitches_required,
item_placement, dungeon_items, accessibility, goals, tower_open, ganon_open, world_state, entrance_shuffle,
boss_shuffle, enemy_shuffle, hints, weapons, item_pool, item_functionality, enemy_damage, enemy_health, pot_shuffle

For each setting that is being rolled, a dictionary consisting of a value for the setting, and its weight, should be
specified. From this point on, I will refer to this as a "weight" within the weightset file.

```yaml
dungeon_items:
  standard: 60
  mc: 10 # Maps/Compasses
  mcs: 10 # Maps/Compasses/Small Keys
  full: 20 # Keysanity
```

In the example above, `standard` has a 60% chance, `mc` has a 10% chance, `mcs` has a 20% chance, and `full` has a 20%
chance. The weight values don't need to add up to 100, but generally its considered good practice to do so to help
others understand the chances.

If you want an setting to always be a specific value, you can just specify it as a string.

```yaml
glitches_required: "none"
```

The example above will always set `glitches_required` to `none`.

To allow quickswap:

```yaml
allow_quickswap: true
```

You can check out the [weighted](https://github.com/tcprescott/sahasrahbot/blob/master/weights/weighted.yaml) for a
basic example.

# Customizer

Use of the customizer makes things a bit more complex. The customizer is very powerful, but it can be overwhelming,
especially if you're not familar with the syntax of the customizer. This section only is used when entrance shuffle is
rolled as `none`.

Customizer is specified as a key on the root of the weightset file called `customizer`. The customizer section has five
sections:

```yaml
customizer:
  eq: ...
  custom: ...
  timed-ohko: ...
  triforce-hunt: ...
  pool: ...
```

The [chaos](https://github.com/tcprescott/sahasrahbot/blob/master/weights/chaos.yaml) weightset has a good example of
these in action.

## "eq" - Equipped gear

This section lets you customize the changes that Link will be pre-equipped with specific items. This is most commonly
used to randomize a boots start, however it can be used to randomize whatever starting equipment you want.

### Example

```yaml
customizer:
  eq:
    "ProgressiveSword":
      0: 80
      1: 10
      2: 5
      3: 3
      4: 2
    "PegasusBoots":
      0: 50
      1: 50
```

## "custom" custom configuration settings

This is probably the most complex section. For a full list of available custom options, you may need to search ALTTPR's
source code. This is all undocumented and may work in unexpected ways. Below are some settings that can be set, but it
is not exhaustive.

### Example

```yaml
customizer:
  custom:
    customPrizePacks:
      True: 50
      False: 50
    # item.require.Lamp is actually backwards (True enables dark room navigation)
    # if this is True, enemy_shuffle and enemy_damage are set to defaults
    item.require.Lamp: False
    prize.shufflePendants:
      True: 95
      False: 5
    prize.shuffleCrystals:
      True: 95
      False: 5
    region.wildMaps:
      True: 50
      False: 50
    region.wildCompasses:
      True: 50
      False: 50
    region.wildKeys:
      True: 50
      False: 50
    region.wildBigKeys:
      True: 50
      False: 50
    rom.dungeonCount:
      "pickup": 40
      "on": 10
      "off": 50
    rom.mapOnPickup:
      True: 90
      False: 10
    rom.timerMode:
      "countdown-ohko": 10
      "off": 90
    rom.rupeeBow:
      True: 5
      False: 95
    rom.genericKeys:
      True: 5
      False: 95
    item.overflow.replacement.Sword:
      TwentyRupees2: 25
      Heart: 10
      SmallMagic: 15
      Rupoor: 50
    item.overflow.replacement.Shield:
      TwentyRupees2: 25
      Heart: 10
      SmallMagic: 15
      Rupoor: 50
    item.overflow.replacement.Armor:
      TwentyRupees2: 25
      Heart: 10
      SmallMagic: 15
      Rupoor: 50
    item.overflow.replacement.Bow:
      TwentyRupees2: 25
      Heart: 10
      SmallMagic: 15
      Rupoor: 50
    item.overflow.replacement.Bottle:
      TwentyRupees2: 25
      Heart: 10
      SmallMagic: 15
      Rupoor: 50
    item.overflow.count.Sword:
      2: 5 # expert
      3: 10 # hard
      4: 85 # normal
    item.overflow.count.Armor:
      0: 5 # hard/expert
      1: 10
      2: 85 # normal
    item.overflow.count.Bow:
      1: 10 # hard/expert
      2: 90 # normal
    item.overflow.count.Shield:
      0: 5
      1: 5 # expert
      2: 10 # hard
      3: 80 # normal
    item.overflow.count.BossHeartContainer:
      2: 5 # expert
      6: 10 # hard
      10: 85 # normal
    item.overflow.count.PieceOfHeart:
      8: 5 # expert
      16: 10 # hard
      24: 85 # normal
    item.overflow.count.Bottle: 4
    item.value.Rupoor:
      5: 50
      10: 30
      20: 20
    spoil.BootsLocation:
      True: 70
      False: 30
```

## "timed-ohko" settings

In the `custom` section of `customizer`, there is a `rom.timerMode` setting.

```yaml
rom.timerMode:
  "countdown-ohko": 10
  "off": 90
```

If `countdown-ohko` is rolled, the `timed-ohko` section activates. This allows you to specify the starting time on the
OHKO (One Hit Knockout) clock, the amount of time the clocks grant, and the number of them added to th e pool. A random
value is chosen between the two numbers specified. If this section is absent, the game will be traditional OHKO mode
without any clocks.

### Example

```yaml
customizer:
  timed-ohko:
    timerStart: [ 900, 1500 ]
    clock:
      GreenClock:
        value: [ 180, 300 ]
        pool: [ 12, 16 ]
      BlueClock:
        value: [ 300, 600 ]
        pool: [ 0, 2 ]
      RedClock:
        value: [ -600, 300 ]
        pool: [ 0, 3 ]
```

## "triforce-hunt" - Triforce Hunt Options

These settings allow you to customize the behavior of the Triforce Hunt goal. If chosen, it lets you specify the random
range of the number of pieces required to meet the goal, the number of pieces in the pool, and the minimum difference
between the number of goal pieces and the number of pool pieces.

### Example

```yaml
customizer:
  triforce-hunt:
    goal: [ 30, 60 ]
    pool: [ 40, 70 ]
    min_difference: 10
```

## "pool" - Item Pool Customization

This allows you to customize the contents of the item pool. You can add or remove whatever items you see fit.

### Example

```yaml
customizer:
  pool:
    "BossHeartContainer":
      "1": 5
      "2": 10
      "4": 20
      "6": 30
      "10": 30
      "12": 5
```

# Subweights

If you didn't have enough already to take in, there is also a feature called "subweights". Subweights allow you to allow
you to roll a specific set of weights first, then merge those weights into the "parent" weights.

These only merge one key deep, so if `customizer` is specifed in a subweight, the entire `customizer` key from the
parent weightset is replaced.

```yaml
subweights:
  # states the chance of not doing anything, leaving out the "weights" will have
  # the mystery generator use the global weights
  default:
    chance: 30

  # a simple example of a subweight
  test1:
    chance: 50
    weights:
      pot_shuffle: "off"
      item_functionality:
        normal: 5
        hard: 15
        expert: 80
      customizer: null # this cancels any customizer options that might have been specified in the parent weights

  # a timed ohko example
  ohko:
    chance: 20
    weights:
      item_placement: basic
      item_functionality: normal
      enemy_damage: default
      enemy_health: default
      boss_shuffle: none
      enemy_shuffle: none
      pot_shuffle: none
      entrances: none
      # merge only happens 1 key deep, so you must specify EVERYTHING, we don't
      # try to merge the parent customizer key with the subweight's customizer key
      # instead, it'll just overwrite everything
      customizer:
        eq:
          "PegasusBoots":
            False: 70
            True: 30
        timed-ohko:
          timerStart: [ 900, 1500 ]
          clock:
            GreenClock:
              value: [ 180, 300 ]
              pool: [ 12, 16 ]
            BlueClock:
              value: [ 300, 600 ]
              pool: [ 0, 2 ]
            RedClock:
              value: [ -600, 300 ]
              pool: [ 0, 3 ]
        custom:
          customPrizePacks:
            True: 50
            False: 50
```

The [pogchampion_season5](https://github.com/tcprescott/sahasrahbot/blob/master/weights/pogchampion_season5.yaml)
weightset has a good example of these in action.

# Preset rolling

You can have it choose a SahasrahBot preset. This is rolled first before anything else. If something other than `none`
is selected, it'll create a game using that preset instead.

```yaml
# this lets you have the mystery generator just use another SahasrahBot preset
preset:
  none: 95
  openmajoritems: 2.5
  lightsped: 2
  trueicerodhunt: .5 # why?????
```

# Misc options

This section contians some miscellaneous options. Currently the only option is `FillItemPoolWith`, which will have the
customizer fill the reminding item pool with a specific item if it was less than 216 items.

```yaml
options:
  FillItemPoolWith: TwentyRupees2
```

# Mystery generation workflow

This is a basic overview of how a mystery game is currently generated. There are several steps that occur.

1. A preset is chosen from the `preset` key. If anything other than `none`, it retrieves that preset and returns,
   otherwise continue.
2. Pick a subweight, if the `subweights` section exists. Merge that subweight into the parent's weights.
3. Roll `entrance_shuffle`.
4. If `entrance_shuffle` is "none", and there is a `customizer` section:
    1. Roll starting equipment in the `eq` section.
    2. Roll custom options in the `custom` section.
    3. Roll starting item pool in `pool` section.
5. If anything required customizer, then get a copy of the default customizer payload, else get the default randomizer
   payload.
6. Roll `glitches_required`, `item_placement`, `dungeon_items`, `accessibility`, `goals`, `tower_open`, `ganon_open`
   , `world_state`, `entrance_shuffle`, `boss_shuffle`, `enemy_shuffle`, `hints`, `weapons`, `item_pool`
   , `item_functionality`, `enemy_damage`, `enemy_health`, `pot_shuffle`.
7. Set `allow_quickswap`. Default is `false`.
8. If customizer is required (as determined in step 4).
    1. Remove any pre-equipped items from the pool.
    2. If `item.require.Lamp` is True (dark rooms are required by logic). Set `enemy_shuffle`, `enemy_damage`,
       and `pot_shuffle` to defaults.
    3. If `region.wildKeys`, `region.wildBigKeys`, `region.wildCompasses`, `region.wildMaps` exists in the `custom`
       section. Set `dungeon_items` to `standard`.
    4. If the goal is `triforce-hunt`, then use the `triforce-hunt` section in `customizer` to add triforce pieces to
       the pool, and set the number of goal pieces.
    5. If `rom.timerMode` is `countdown-ohko`, then add clocks and set the timed OHKO settings specified in
       the `timed-ohko` section.
    6. Determine if there is less than 216 items in the pool, and fill the remainder of the pool with
       the `FillItemPoolWith` option to get it to 216 (a `Nothing` item by default).
    7. If the goal is `pedestal` or `dungeons`, `prize.crossWorld` is forced to True.
9. Since entrance randomizer on the website doesn't support Map/Compass (MC) and Map/Compass/Small Key (MCS) dungeon
   item shuffles, those are set to "Standard" and "Keysanity" respectively for Entrance Randomizer.
10. If weapons is `swordless` or `randomized`, the world state is `standard`, and `enemy_shuffle`, `enemy_damage`
    and `enemy_health` are something other than default, then force weapons to `assured`. This makes an enemized escape
    possible most of the time.

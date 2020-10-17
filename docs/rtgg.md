---
layout: default
title:  SahasrahBot
---
* Table of contents
{:toc}

# RT.gg Commands

## ALTTPR Commands
### !race / !quickswaprace
Use this command in the RaceTime.gg race room.

This allows you to generate a game using a pre-defined combination of settings.

Example: `!race open`

If `!quickswaprace` is the command, the item quickswap feature is enabled for the race.  Quickswap is always available for entrance randomizer races.

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

### !mystery
Use this command in an RaceTime.gg race room.

Here is a [list of currently supported weights](mystery.md).  The weightset name will be the name of the file without the .yaml extension.

Example: `!mystery weighted`

### !spoiler
Use this command in the RaceTime.gg race room.

This allows you to generate a spoiler race game using a pre-defined combination of settings.

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

Example: `!spoiler open`

SahasrahBot, after the start of the race in RaceTime.gg, will post the spoiler log in chat and will automatically begin counting down 900s minutes.

This bot will inform you when you're ready to begin racing.

## SMZ3 Commands

### !race
Use this command in the RaceTime.gg race room.

This allows you to generate a game using a pre-defined combination of settings.

Example: `!race normal`

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

## Super Mario Bros 3 Randomizer (SMB3R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags 17BAS2LNJ4`

Please be aware that the flag string is not validated.

### !sglpractice
Provides a seed and flags for the SpeedGamingLive 2020 tournament.

## The Legend of Zelda Randomizer (Z1R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags VlWlIEwJ1MsKkaOCWhlit2veXNSffs`

Please be aware that the flag string is not validated.

### !sglpractice
Provides a seed and flags for the SpeedGamingLive 2020 tournament.

## Final Fantasy Randomizer (FF1R)

### !flags
Use this command to roll a seed number and post a link to the seed in the race info and chat.

Example `!flags yGcifaseK8fJxIkkAzUzYAzx32UoP5toiyJrTE864J9FEyMsXe5XhM5T94nANOh1T6wJN7BZU4p3r3WORe9o7vyXSpZD`

Please be aware that the flag string is not validated.

### !sglpods
Provides a URL to a seed using the SpeedGamingLive 2020 pod stage flags.

### !sglbrackets
Provides a URL to a seed using the SpeedGamingLive 2020 bracket stage flags.

## Super Metroid Randomizer (SMR)

### !totalrace
Generate a seed using Total's Super Metroid Randomizer at https://sm.samus.link

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

Example `!totalrace casual_full`

### !variarace
Generate a seed using the Super Metroid VARIA Randomizer at https://randommetroidsolver.pythonanywhere.com/

First argument is the settings preset, and the second argument is the skills preset.  Lists of both presets can be found on the randomizer's website.

Example `!totalrace default regular`

**This is currently broken and will not function.**  There's no ETA on a fix.

### !dashrace
Generate a seed using the Super Metroid DASH Randomizer, found at https://dashrando.github.io/

Example `!dashrace`

## Global Commands
### !lock

This command prevents any seed rolling from occuring, except by a race monitor or a category moderator.

*This command is only available to race monitors.*

### !unlock

This command allows anyone to roll again.

*This command is only available to race monitors.*

### !help

Provides a link to this document.

### !cancel

Cancels the current race and clears the race info.  This allows you to roll a different game, in case there was a mistake.

*This command is only available to race monitors.*
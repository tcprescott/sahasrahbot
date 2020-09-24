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
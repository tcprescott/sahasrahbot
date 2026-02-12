---
layout: default
title:  SahasrahBot
---
* Table of contents
{:toc}

# RT.gg Commands

This page documents RaceTime.gg command usage for supported game categories.

## ALTTPR Commands
### !race / !quickswaprace
Use this command in the RaceTime.gg race room.

Generates a game using a predefined preset.

Example: `!race open`

If you use `!quickswaprace`, item quickswap is enabled for the race. Quickswap is always enabled for entrance randomizer races.

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

### !mystery
Use this command in a RaceTime.gg race room.

Here is a [list of currently supported weights](mystery.md).  The weightset name will be the name of the file without the .yaml extension.

Example: `!mystery weighted`

### !spoiler
Use this command in the RaceTime.gg race room.

Generates a spoiler-race game using a predefined preset.

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

Example: `!spoiler open`

After the race starts, SahasrahBot posts the spoiler log in chat and starts the configured spoiler countdown.

The bot announces when spoiler study time is complete.

## SMZ3 Commands

### !race
Use this command in the RaceTime.gg race room.

This allows you to generate a game using a pre-defined combination of settings.

Example: `!race normal`

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

### !multiworld
Use this command in the RaceTime.gg race room.

This allows you to generate a multiworld game in a team race room, creating a multiworld for each team.  The race must be a team race.

Example: `!multiworld normal`

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

## Super Mario Bros 3 Randomizer (SMB3R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags 17BAS2LNJ4`

The flag string is not validated.

## The Legend of Zelda Randomizer (Z1R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags VlWlIEwJ1MsKkaOCWhlit2veXNSffs`

The flag string is not validated.

### !race
Use this command in the RaceTime.gg race room.

This allows you to generate a game using a pre-defined combination of settings.

Example: `!race consternation`

Here is a [list of currently supported presets](presets.md).

## Zelda 2 Randomizer (Z2R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags jhEhMROm7DZ$MHRBTNBhBAh0PSm`

The flag string is not validated.

## Final Fantasy Randomizer (FF1R)

### !ff1url
Use this command to roll a seed number and post a link to the seed in the race info and chat.

Example `!ff1url https://4-2-0.finalfantasyrandomizer.com/?s=00000000&f=AgJO1tSXqnnX-JaaScPxkw0C.ecQDS8vc3iN9TWsbcTxxkB.we6qcINzOn754c0ATcdYK..B.PZ01XbeTw-tY99fnt-lVvSvLjUusyHE85QbhZxXm2IF.YqCsdaqmyHiUAQsp90Ct.9-B

The URL is not validated.

## Super Metroid Randomizer (SMR)

### !total
Generate a seed using Total's Super Metroid Randomizer at https://sm.samus.link

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

Example `!totalrace casual_full`

### !varia
Generate a seed using the Super Metroid VARIA Randomizer at https://randommetroidsolver.pythonanywhere.com/

First argument is the settings preset, and the second argument is the skills preset.  Lists of both presets can be found on the randomizer's website.

Example `!variarace default regular`

**This command is currently non-functional.** No ETA is available.

### !dash
Generate a seed using the Super Metroid DASH Randomizer, found at https://dashrando.net

DASH supports many popular features such as boss and area randomization along with unique modes which rebalance existing items and introduce new progression items.

#### Commands
`!dash` - List available presets  
`!dash [--spoiler] <preset>` - Generate a seed using the specified preset (e.g., _classic_, _recall_, _chozo_bozo_, etc.)

### !multiworld
Use this command in the RaceTime.gg race room.

This allows you to generate a multiworld game in a team race room, creating a multiworld for each team.  The race must be a team race.

Example: `!multiworld normal`

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

## Super Metroid (SM)

### !bingo
Use this command in RaceTime.gg race room.

This allows you to have a bingo card generated via the SRL bingo tool at the time the race starts.

Example: `!bingo`

## Global Commands
### !lock

This command prevents seed rolling except for race monitors or category moderators.

*This command is only available to race monitors.*

### !unlock

This command re-enables seed rolling for all users.

*This command is only available to race monitors.*

### !help

Provides a link to this document.

### !cancel

Cancels the current race and clears race info so a new game can be rolled.

*This command is only available to race monitors.*

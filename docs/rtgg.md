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

### !multiworld
Use this command in the RaceTime.gg race room.

This allows you to generate a multiworld game in a team race room, creating a multiworld for each team.  The race must be a team race.

Example: `!multiworld normal`

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

## Super Mario Bros 3 Randomizer (SMB3R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags 17BAS2LNJ4`

Please be aware that the flag string is not validated.

## The Legend of Zelda Randomizer (Z1R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags VlWlIEwJ1MsKkaOCWhlit2veXNSffs`

Please be aware that the flag string is not validated.

## Zelda 2 Randomizer (Z2R)

### !flags
Use this command to roll a seed number and put the seed and flags in the race info and chat.

Example `!flags jhEhMROm7DZ$MHRBTNBhBAh0PSm`

Please be aware that the flag string is not validated.

## Final Fantasy Randomizer (FF1R)

### !ff1url
Use this command to roll a seed number and post a link to the seed in the race info and chat.

Example `!ff1url https://4-2-0.finalfantasyrandomizer.com/?s=00000000&f=AgJO1tSXqnnX-JaaScPxkw0C.ecQDS8vc3iN9TWsbcTxxkB.we6qcINzOn754c0ATcdYK..B.PZ01XbeTw-tY99fnt-lVvSvLjUusyHE85QbhZxXm2IF.YqCsdaqmyHiUAQsp90Ct.9-B

Please be aware that the URL is not validated.

## Super Metroid Randomizer (SMR)

### !total
Generate a seed using Total's Super Metroid Randomizer at https://sm.samus.link

Here is a [list of currently supported presets](presets.md).  The preset name will be the name of the file without the .yaml extension.

Example `!totalrace casual_full`

### !varia
Generate a seed using the Super Metroid VARIA Randomizer at https://randommetroidsolver.pythonanywhere.com/

First argument is the settings preset, and the second argument is the skills preset.  Lists of both presets can be found on the randomizer's website.

Example `!variarace default regular`

**This is currently broken and will not function.**  There's no ETA on a fix.

### !dash
Generate a seed using the Super Metroid DASH Randomizer, found at https://dashrando.github.io/

Valid modes are: mm, full

Example `!dashrace <mode>`

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

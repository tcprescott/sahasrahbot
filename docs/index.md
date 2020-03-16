---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults
---
# SahasrahBot SRL Commands
## $preset
Use this command in the SRL race room.

This allows you to generate a game using a pre-defined combination of settings.

Example: `$preset open`

Currently supported presets can be found <https://l.synack.live/presets>.  The preset name will be the name of the file without the .yaml extension.

You can append `--hints` to the command to enable hints.  All presets have hints disabled by default, with a few exceptions (see preset for details).

The option `--accessible` may be appended to mark the race as using an accessible ruleset.  See <https://link.alttpr.com/accessible> for details on this ruleset.

Supported for both alttphacks and smz3 games.  For smz3, only the normal and hard presets are supported.


## $mystery

Use this command in an SRL race room.

Currently supported weights can be found at <https://l.synack.live/weights>.  The preset name will be the name of the file without the .yaml extension.

Example: `$mystery weighted`

The option `--accessible` may be appended to mark the race as using an accessible ruleset.  See <https://link.alttpr.com/accessible> for details on this ruleset.

Only supported for alttphacks

## $spoiler

Use this command in the SRL race room.

This allows you to generate a spoiler race game using a pre-defined combination of settings.

Currently supported presets can be found <https://l.synack.live/presets>.  The preset name will be the name of the file without the .yaml extension.

Example: `$spoiler open`

The option `--accessible` may be appended to mark the race as using an accessible ruleset.  See <https://link.alttpr.com/accessible> for details on this ruleset.

SahasrahBot, after the start of the race in SRL, will post the spoiler log in chat and will automatically begin counting down 900s minutes (1500s for alttpsm games) by default.  This can be overwritten with the argument `--studytime [seconds]`.

This bot will inform you when you're ready to begin racing.

Only supported for alttphacks and alttpsm.

## $cancel

Use this command in the SRL race room.

This command cancels an existing race.

Use this command in the SRL race room. Must be done before rerolling.

## $joinroom

Use this in #speedrunslive channel to force SahasrahBot to join the race room.

Example: `$joinroom #srl-abc12`

## $rules

Will post a link to the ALTTPR Racing Rules page.  This isn't context specific.

## $help

Gives you a link to this help page.
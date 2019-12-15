from . import util

async def preset(target):
    srl_id = util.srl_race_id(target)
    srl = await get_race(srl_id)
    await self.message(target, "Generating game, please wait.  If nothing happens after a minute, contact Synack.")
    race = await srl_races.get_srl_race_by_id(srl_id)

    if race:
        await self.message(target, "There is already a game generated for this room.  To cancel it, use the $cancel command.")
        return

    if srl['game']['abbrev'] == 'alttphacks':
        try:
            seed, preset_dict = await preset.get_preset(args.preset, hints=args.hints, spoilers="off")
        except preset.PresetNotFoundException:
            await self.message(target, "That preset does not exist.  For documentation on using this bot, visit https://sahasrahbot.synack.live")

        goal_name = preset_dict['goal_name']
        goal = f"vt8 randomizer - {goal_name}"
        code = await seed.code()
        if args.silent:
            await self.message(target, f"{goal} - {seed.url} - ({'/'.join(code)})")
        else:
            await self.message(target, f".setgoal {goal} - {seed.url} - ({'/'.join(code)})")
    elif srl['game']['abbrev'] == 'alttpsm':
        seed = await smz3_preset.get_preset(args.preset)
        goal = 'beat the games'
        if args.silent:
            await self.message(target, f"{goal} - {args.preset} - {seed.url}")
        else:
            await self.message(target, f".setgoal {goal} - {args.preset} - {seed.url}")
    else:
        await self.message(target, "This game is not yet supported.")
        return

    await srl_races.insert_srl_race(srl_id, goal)
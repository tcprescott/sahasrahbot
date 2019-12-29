import discord

from alttprbot.database import config, srlnick
from alttprbot.util import srl
from alttprbot_discord.bot import discordbot


async def discord_race_start(srl_id):
    race = await srl.get_race(srl_id)
    configguilds = await config.get_all_parameters_by_name('CurrentlyRacingRoleId')
    for configguild in configguilds:
        guild = discord.utils.get(discordbot.guilds, id=configguild['guild_id'])
        role = discord.utils.get(guild.roles, name=configguild['value'])
        for entrant in race['entrants']:
            nickmappings = await srlnick.get_discord_id(entrant)
            if nickmappings:
                for nickmapping in nickmappings:
                    user = discord.utils.get(guild.members, id=nickmapping['discord_user_id'])
                    try:
                        await user.add_roles(role, reason=f'Started SRL race {srl_id}')
                    except:
                        pass


async def discord_race_finish(nick, srl_id):
    nickmappings = await srlnick.get_discord_id(nick)
    configguilds = await config.get_all_parameters_by_name('CurrentlyRacingRoleId')
    for configguild in configguilds:
        guild = discord.utils.get(discordbot.guilds, id=configguild['guild_id'])
        role = discord.utils.get(guild.roles, name=configguild['value'])
        if nickmappings:
            for nickmapping in nickmappings:
                user = discord.utils.get(guild.members, id=nickmapping['discord_user_id'])
                try:
                    await user.remove_roles(role, reason=f'Finished SRL race {srl_id}')
                except:
                    pass

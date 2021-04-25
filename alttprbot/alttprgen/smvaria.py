from alttprbot_discord.util.smvaria_discord import SuperMetroidVariaDiscord


async def generate_preset(settings, skills, race=False):
    seed = await SuperMetroidVariaDiscord.create(
        skills_preset=skills,
        settings_preset=settings,
        race=race
    )
    return seed

async def generate_league_playoff(majors, area, bosses):
    if majors not in ['Full', 'Major', 'Chozo']:
        raise Exception("Invalid major setting. Must be Full, Major, or Chozo.")

    if area not in ['Off', 'Light', 'Full']:
        raise Exception("Invalid area setting.  Must be Off, Light, or Full.")

    if bosses not in ['Off', 'On']:
        raise Exception("Invalid bosses setting.  Must be Off, or On.")

    seed = await SuperMetroidVariaDiscord.create(
        settings_preset="Season_Races",
        skills_preset="Season_Races",
        settings_dict={
            "majorsSplit": majors,

            # these are both set at same time
            "areaRandomization": "off" if area == "Off" else "on",
            "areaLayout": "off" if area == "Off" else "on",

            # requires area rando on
            "lightAreaRandomization": "on" if area == "Light" else "off",

            # boss rando
            "bossRandomization": "off" if bosses == "Off" else "on",
        },
        race=True
    )
    return seed
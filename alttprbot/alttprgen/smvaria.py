from alttprbot_discord.util.smvaria_discord import SuperMetroidVariaDiscord

async def generate_preset(settings, skills, race=False):
    seed = await SuperMetroidVariaDiscord.create(
        skills_preset=skills,
        settings_preset=settings,
        race=race
    )
    return seed
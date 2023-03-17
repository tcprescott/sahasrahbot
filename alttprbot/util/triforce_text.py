import random
from alttprbot import models
from alttprbot.alttprgen import generator


async def get_triforce_text_balanced(pool_name: str):
    """
    Get a triforce text that is balanced across all users.
    """

    # get a list of all discord_user_ids that have submitted triforce texts
    discord_user_ids = await models.TriforceTexts.filter(pool_name=pool_name, approved=True).distinct().values_list("discord_user_id", flat=True)
    if not discord_user_ids:
        return None

    discord_user_id = random.choice(discord_user_ids)
    triforce_texts = await models.TriforceTexts.filter(approved=True, pool_name=pool_name, discord_user_id=discord_user_id)
    triforce_text = random.choice(triforce_texts)
    return triforce_text.text


async def generate_with_triforce_text(pool_name: str, preset: str, settings: dict = None):
    data = generator.ALTTPRPreset(preset)
    await data.fetch()
    text = await get_triforce_text_balanced(pool_name=pool_name)
    if text:
        data.preset_data['settings']['texts'] = {}
        data.preset_data['settings']['texts']['end_triforce'] = "{NOBORDER}\n" + text

    if settings is not None and isinstance(settings, dict):
        data.preset_data['settings'] = {**data.preset_data['settings'], **settings}

    return await data.generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off")

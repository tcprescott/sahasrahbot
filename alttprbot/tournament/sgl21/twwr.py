# import random

# from alttprbot import models
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLCoreTournamentRace


class TWWR(SGLCoreTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='twwr',
            racetime_goal="The Wind Waker Randomizer",
            event_slug="sgl21twwr",
            audit_channel=discordbot.get_channel(774336581808291863),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    @property
    def hours_before_room_open(self):
        return 1.5

    # async def roll(self):
    #     settings_key = random.choice(twwr.SPOILER_LOG_DEFAULT)

    #     settings_text = f"Settings: {settings_key}"
    #     settings_description = twwr.SETTINGS_DESCRIPTIONS[settings_key]
    #     if settings_description:
    #         settings_text += f" ({settings_description})"

    #     await self.rtgg_handler.send_message(settings_text)

    #     self.seed = await twwr.generate_seed(
    #         permalink=twwr.SPOILER_LOG_PERMALINKS.get(settings_key),
    #         generate_spoiler_log=True
    #     )
    #     await models.SpoilerRaces.update_or_create(
    #         srl_id=self.rtgg_handler.data.get('name'),
    #         defaults={'spoiler_url': self.seed.spoiler_log_url, 'studytime': 3600}
    #     )

    # @property
    # def seed_info(self):
    #     return f"Seed: {self.seed.seed}, Permalink: {self.seed.permalink}"

    # async def choose_permalink(self, default_settings, presets, args):
    #     if len(args) > 0:
    #         settings_list = args
    #     else:
    #         settings_list = default_settings

    #     banned_presets = self.state.get("bans").values()
    #     settings_without_bans = [
    #         preset
    #         for preset in settings_list
    #         if preset not in banned_presets
    #     ]

    #     if len(settings_list) > 1 and len(settings_without_bans) > 0:
    #         settings_key = random.choice(settings_without_bans)
    #         settings_text = f"Settings: {settings_key}"
    #         settings_description = twwr.SETTINGS_DESCRIPTIONS[settings_key]
    #         if settings_description:
    #             settings_text += f" ({settings_description})"

    #         await self.send_message(settings_text)
    #         await self.set_raceinfo(settings_text, False, False)
    #     else:
    #         settings_key = settings_list[0]

    #     return presets.get(settings_key, settings_key)

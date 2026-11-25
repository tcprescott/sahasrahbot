from dataclasses import dataclass

import config
from alttprbot_racetime import handlers
from alttprbot_racetime.core import SahasrahBotRaceTimeBot
from alttprbot_racetime.handlers.core import SahasrahBotCoreHandler


@dataclass
class RacetimeBotConfig:
    category_slug: str
    handler_class: type[SahasrahBotCoreHandler]
    bot_class: type[SahasrahBotRaceTimeBot] = SahasrahBotRaceTimeBot

    @property
    def client_id(self):
        return getattr(config, f"RACETIME_CLIENT_ID_{self.category_slug.upper().replace('-', '')}")

    @property
    def client_secret(self):
        return getattr(config, f"RACETIME_CLIENT_SECRET_{self.category_slug.upper().replace('-', '')}")


if config.DEBUG:
    RACETIME_CATEGORIES = {
        'test': RacetimeBotConfig(
            category_slug='test',
            handler_class=handlers.test.GameHandler
        )
    }
else:
    RACETIME_CATEGORIES = {
        'alttpr': RacetimeBotConfig(
            category_slug='alttpr',
            handler_class=handlers.alttpr.GameHandler,
        ),
        'ct-jets': RacetimeBotConfig(
            category_slug='ct-jets',
            handler_class=handlers.ctjets.GameHandler,
        ),
        'ff1r': RacetimeBotConfig(
            category_slug='ff1r',
            handler_class=handlers.ff1r.GameHandler,
        ),
        'smr': RacetimeBotConfig(
            category_slug='smr',
            handler_class=handlers.smr.GameHandler,
        ),
        'smz3': RacetimeBotConfig(
            category_slug='smz3',
            handler_class=handlers.smz3.GameHandler,
        ),
        'twwr': RacetimeBotConfig(
            category_slug='twwr',
            handler_class=handlers.twwr.GameHandler,
        ),
        'z1r': RacetimeBotConfig(
            category_slug='z1r',
            handler_class=handlers.z1r.GameHandler,
        ),
        'z2r': RacetimeBotConfig(
            category_slug='z2r',
            handler_class=handlers.z2r.GameHandler,
        )
    }

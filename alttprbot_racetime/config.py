from dataclasses import dataclass

from alttprbot_racetime import handlers
from alttprbot_racetime.core import SahasrahBotRaceTimeBot
from alttprbot_racetime.handlers.core import SahasrahBotCoreHandler
import config


@dataclass
class RacetimeBotConfig:
    category_slug: str
    handler_class: SahasrahBotCoreHandler
    bot_class: SahasrahBotRaceTimeBot = SahasrahBotRaceTimeBot

    @property
    def client_id(self):
        return getattr(config, f"RACETIME_CLIENT_ID_{self.category_slug.upper().replace('-', ''))}")

    @property
    def client_secret(self):
        return getattr(config, f"RACETIME_CLIENT_SECRET_{self.category_slug.upper()}")

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
        'contra': RacetimeBotConfig(
            category_slug='contra',
            handler_class=handlers.contra.GameHandler,
        ),
        'ct-jets': RacetimeBotConfig(
            category_slug='ct-jets',
            handler_class=handlers.ctjets.GameHandler,
        ),
        'ff1r': RacetimeBotConfig(
            category_slug='ff1r',
            handler_class=handlers.ff1r.GameHandler,
        ),
       'sgl': RacetimeBotConfig(
           category_slug='sgl',
           handler_class=handlers.sgl.GameHandler,
       ),
        'sm': RacetimeBotConfig(
            category_slug='sm',
            handler_class=handlers.sm.GameHandler,
        ),
        'smb3r': RacetimeBotConfig(
            category_slug='smb3r',
            handler_class=handlers.smb3r.GameHandler,
        ),
        'smr': RacetimeBotConfig(
            category_slug='smr',
            handler_class=handlers.smr.GameHandler,
        ),
        'smw-hacks': RacetimeBotConfig(
            category_slug='smw-hacks',
            handler_class=handlers.smwhacks.GameHandler,
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

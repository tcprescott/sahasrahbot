import os
from dataclasses import dataclass

from alttprbot_racetime import handlers
from alttprbot_racetime.core import SahasrahBotRaceTimeBot
from alttprbot_racetime.handlers.core import SahasrahBotCoreHandler
from config import Config as c


@dataclass
class RacetimeBotConfig:
    client_id: str
    client_secret: str
    handler_class: SahasrahBotCoreHandler
    bot_class: SahasrahBotRaceTimeBot = SahasrahBotRaceTimeBot


if c.DEBUG:
    RACETIME_CATEGORIES = {
        'test': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_TEST"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_TEST'),
            handler_class=handlers.test.GameHandler
        )
    }
else:
    RACETIME_CATEGORIES = {
        'alttpr': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_ALTTPR"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_ALTTPR'),
            handler_class=handlers.alttpr.GameHandler,
        ),
        'contra': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_CONTRA"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_CONTRA'),
            handler_class=handlers.contra.GameHandler,
        ),
        'ct-jets': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_CTJETS"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_CTJETS'),
            handler_class=handlers.ctjets.GameHandler,
        ),
        'ff1r': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_FF1R"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_FF1R'),
            handler_class=handlers.ff1r.GameHandler,
        ),
        'sgl': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_SGL"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_SGL'),
            handler_class=handlers.sgl.GameHandler,
        ),
        'sm': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_SM"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_SM'),
            handler_class=handlers.sm.GameHandler,
        ),
        'smb3r': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_SMB3R"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_SMB3R'),
            handler_class=handlers.smb3r.GameHandler,
        ),
        'smr': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_SMR"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_SMR'),
            handler_class=handlers.smr.GameHandler,
        ),
        # 'smw-hacks': RacetimeBotConfig(
        #     category='smw-hacks',
        #     client_id=os.environ.get(f"RACETIME_CLIENT_ID_SMWHACKS"),
        #     client_secret=os.environ.get(f'RACETIME_CLIENT_SECRET_SMWHACKS'),
        #     handler_class=handlers.smwhacks.GameHandler,
        # ),
        'smz3': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_SMZ3"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_SMZ3'),
            handler_class=handlers.smz3.GameHandler,
        ),
        'twwr': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_TWWR"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_TWWR'),
            handler_class=handlers.twwr.GameHandler,
        ),
        'z1r': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_Z1R"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_Z1R'),
            handler_class=handlers.z1r.GameHandler,
        ),
        'z2r': RacetimeBotConfig(
            client_id=os.environ.get("RACETIME_CLIENT_ID_Z2R"),
            client_secret=os.environ.get('RACETIME_CLIENT_SECRET_Z2R'),
            handler_class=handlers.z2r.GameHandler,
        )
    }

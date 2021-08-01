from dataclasses import dataclass

import discord

from alttprbot.tournament import core
from alttprbot_discord.bot import discordbot

@dataclass
class TournamentConfig:
    guild: discord.Guild

    racetime_category: str
    racetime_goal: str

    schedule_type: str = "sg"

    audit_channel: discord.TextChannel = None
    commentary_channel: discord.TextChannel = None
    mod_channel: discord.TextChannel = None
    scheduling_needs_channel: discord.TextChannel = None

    scheduling_needs_tracker = False

    admin_roles: list = None
    helper_roles: list = None
    commentator_roles: list = None
    mod_roles: list = None

    lang: str = 'en'
    submission: bool = False
    coop: bool = False

    tournament_class: core.TournamentRace = core.TournamentRace

TOURNAMENT_DATA = {}

alttpr_de_guild = discordbot.get_guild(469300113290821632)
TOURNAMENT_DATA['alttprde'] = TournamentConfig(
    guild=alttpr_de_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game',
    audit_channel=discordbot.get_channel(473668481011679234),
    commentary_channel=discordbot.get_channel(469317757331308555),
    helper_roles=[
        alttpr_de_guild.get_role(534030648713674765),
        alttpr_de_guild.get_role(469300493542490112),
        alttpr_de_guild.get_role(623071415129866240),
    ],
    lang='de',
)

TOURNAMENT_DATA['alttprmini'] = TournamentConfig(
    guild=alttpr_de_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game',
    audit_channel=discordbot.get_channel(473668481011679234),
    commentary_channel=discordbot.get_channel(469317757331308555),
    helper_roles=[
        alttpr_de_guild.get_role(534030648713674765),
        alttpr_de_guild.get_role(469300493542490112),
        alttpr_de_guild.get_role(623071415129866240),
    ],
    lang='de',
)

TOURNAMENT_DATA['alttprcd'] = TournamentConfig(
    guild=alttpr_de_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game',
    audit_channel=discordbot.get_channel(473668481011679234),
    commentary_channel=discordbot.get_channel(469317757331308555),
    helper_roles=[
        alttpr_de_guild.get_role(534030648713674765),
        alttpr_de_guild.get_role(469300493542490112),
        alttpr_de_guild.get_role(623071415129866240),
    ],
    lang='de',
)

alttpr_tournament_guild = discordbot.get_guild(334795604918272012)
TOURNAMENT_DATA['alttpr'] = TournamentConfig(
    guild=alttpr_tournament_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game',
    audit_channel=discordbot.get_channel(647966639266201620),
    commentary_channel=discordbot.get_channel(408347983709470741),
    scheduling_needs_channel=discordbot.get_channel(434560353461075969),
    scheduling_needs_tracker=True,
    helper_roles=[
        alttpr_tournament_guild.get_role(334797023054397450),
        alttpr_tournament_guild.get_role(435200206552694794),
        alttpr_tournament_guild.get_role(482353483853332481),
        alttpr_tournament_guild.get_role(426487540829388805),
        alttpr_tournament_guild.get_role(613394561594687499),
        alttpr_tournament_guild.get_role(334796844750209024)
    ],
)

smwde_guild = discordbot.get_guild(753727862229565612)
TOURNAMENT_DATA['smwde'] = TournamentConfig(
    guild=smwde_guild,
    racetime_category='smw-hacks',
    racetime_goal='Any%',
    audit_channel=discordbot.get_channel(826775494329499648),
    scheduling_needs_channel=discordbot.get_channel(835946387065012275),
    helper_roles=[
        smwde_guild.get_role(754845429773893782),
        smwde_guild.get_role(753742980820631562),
    ],
    lang='de',
)

alttprfr_guild = discordbot.get_guild(470200169841950741)
TOURNAMENT_DATA['alttprfr'] = TournamentConfig(
    guild=alttprfr_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game',
    audit_channel=discordbot.get_channel(856581631241486346),
    commentary_channel=discordbot.get_channel(470202208261111818),
    helper_roles=[
        alttprfr_guild.get_role(482266765137805333),
        alttprfr_guild.get_role(507932829527703554),
    ],
    lang='fr',
    submission=True,
)

alttprhmg_guild = discordbot.get_guild(535946014037901333)
TOURNAMENT_DATA['alttprhmg'] = TournamentConfig(
    guild=alttprhmg_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game (glitched)',
    audit_channel=discordbot.get_channel(647966639266201620),
    commentary_channel=discordbot.get_channel(408347983709470741),
    scheduling_needs_channel=discordbot.get_channel(434560353461075969),
    scheduling_needs_tracker=True,
    helper_roles=[
        alttprhmg_guild.get_role(549708578731327489),
        alttprhmg_guild.get_role(535962854004883467),
        alttprhmg_guild.get_role(535962802230132737),
    ],
)

alttpres_guild = discordbot.get_guild(477850508368019486)
TOURNAMENT_DATA['alttpres'] = TournamentConfig(
    guild=alttpres_guild,
    racetime_category='alttpr',
    racetime_goal='Beat the game',
    audit_channel=discordbot.get_channel(859058002426462211),
    commentary_channel=discordbot.get_channel(838011943000080395),
    scheduling_needs_channel=discordbot.get_channel(863771537903714324),
    scheduling_needs_tracker=True,
    helper_roles=[
        alttpres_guild.get_role(479423657584754698),
        alttpres_guild.get_role(477968190606016528),
    ],
    lang="es",
)

smz3_tournament = discordbot.get_guild(460905692857892865)
TOURNAMENT_DATA['smz3coop'] = TournamentConfig(
    guild=smz3_tournament,
    racetime_category='smz3',
    racetime_goal='Beat the games',
    audit_channel=discordbot.get_channel(516808047935619073),
    commentary_channel=discordbot.get_channel(687471466714890296),
    scheduling_needs_channel=discordbot.get_channel(864249492370489404),
    scheduling_needs_tracker=True,
    helper_roles=[
        smz3_tournament.get_role(464497534631542795),
    ],
)

async def fetch_tournament_handler(event, **kwargs):
    tournament_class = TOURNAMENT_DATA[event].tournament_class
    return await tournament_class.construct(**kwargs)
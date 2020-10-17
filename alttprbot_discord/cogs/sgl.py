import random
import string

from alttprbot.alttprgen import randomizer
from alttprbot.database import config
from alttprbot_racetime.bot import racetime_sgl
from alttprbot_racetime.tools import create_race
from discord.ext import commands


class SpeedGamingLive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):  # pylint: disable=invalid-overridden-method
        if ctx.guild is None:
            return False

        if await config.get(ctx.guild.id, 'SpeedGamingLiveEnabled') == 'true':
            return True

        return False

    @commands.command(
        help="Generate a SGL race room on racetime."
    )
    @commands.is_owner()
    async def sgltest(self, ctx):
        room_name = await create_race(
            game='sgl',
            config={
                'goal': 1450,
                'custom_goal': '',
                'invitational': 'on',
                'unlisted': 'on',
                'info': 'bot testing',
                'start_delay': 15,
                'time_limit': 24,
                'streaming_required': 'on',
                'allow_comments': 'on',
                'allow_midrace_chat': 'on',
                'allow_non_entrant_chat': 'off',
                'chat_message_delay': 0})

        await racetime_sgl.create_handler_by_room_name(room_name)
        await ctx.send(f'https://racetime.gg{room_name}')

    @commands.command()
    @commands.is_owner()
    async def sglsmobingotest(self, ctx):
        room_url = await randomizer.create_bingo_card(
            config={
                'room_name': f'synacktest-{get_random_string(8)}',
                'passphrase': 'test',
                'nickname': 'Synack',
                'game_type': 45,
                'variant_type': 45,
                'custom_json': '',
                'lockout_mode': 1,
                'seed': '',
                'is_spectator': 'on',
                'hide_card': 'on'
            }
        )

        await ctx.send(room_url)

    @commands.command()
    @commands.is_owner()
    async def sglsmdabbingotest(self, ctx):
        room_url = await randomizer.create_bingo_card(
            config={
                'room_name': f'synacktest-{get_random_string(8)}',
                'passphrase': 'test',
                'nickname': 'Synack',
                'game_type': 4,
                'variant_type': 164,
                'custom_json': '',
                'lockout_mode': 1,
                'seed': '',
                'is_spectator': 'on',
                'hide_card': 'on'
            }
        )

        await ctx.send(room_url)

    @commands.command()
    @commands.is_owner()
    async def sglootrtest(self, ctx):
        seed_url = await randomizer.roll_ootr(
            encrypt=True,
            settings={
                "world_count": 1,
                "create_spoiler": True,
                "randomize_settings": False,
                "open_forest": "open",
                "open_door_of_time": True,
                "zora_fountain": "closed",
                "gerudo_fortress": "fast",
                "bridge": "stones",
                "triforce_hunt": False,
                "logic_rules": "glitchless",
                "all_reachable": True,
                "bombchus_in_logic": False,
                "one_item_per_dungeon": False,
                "trials_random": False,
                "trials": 0,
                "no_escape_sequence": True,
                "no_guard_stealth": True,
                "no_epona_race": True,
                "no_first_dampe_race": True,
                "useful_cutscenes": False,
                "fast_chests": True,
                "logic_no_night_tokens_without_suns_song": False,
                "free_scarecrow": False,
                "start_with_rupees": False,
                "start_with_consumables": False,
                "starting_hearts": 3,
                "chicken_count_random": False,
                "chicken_count": 7,
                "big_poe_count_random": False,
                "big_poe_count": 1,
                "shuffle_kokiri_sword": True,
                "shuffle_ocarinas": False,
                "shuffle_weird_egg": False,
                "shuffle_gerudo_card": False,
                "shuffle_song_items": False,
                "shuffle_cows": False,
                "shuffle_beans": False,
                "entrance_shuffle": "off",
                "shuffle_scrubs": "off",
                "shopsanity": "off",
                "tokensanity": "off",
                "shuffle_mapcompass": "startwith",
                "shuffle_smallkeys": "dungeon",
                "shuffle_bosskeys": "dungeon",
                "shuffle_ganon_bosskey": "lacs_vanilla",
                "enhance_map_compass": False,
                "mq_dungeons_random": False,
                "mq_dungeons": 0,
                "disabled_locations": [
                    "Deku Theater Mask of Truth"
                ],
                "allowed_tricks": [
                    "logic_fewer_tunic_requirements",
                    "logic_grottos_without_agony",
                    "logic_child_deadhand",
                    "logic_man_on_roof",
                    "logic_dc_jump",
                    "logic_rusted_switches",
                    "logic_windmill_poh",
                    "logic_crater_bean_poh_with_hovers",
                    "logic_forest_vines",
                    "logic_goron_city_pot_with_strength"
                ],
                "logic_earliest_adult_trade": "prescription",
                "logic_latest_adult_trade": "claim_check",
                "logic_lens": "chest-wasteland",
                "starting_equipment": [],
                "starting_items": [],
                "starting_songs": [],
                "ocarina_songs": False,
                "correct_chest_sizes": False,
                "clearer_hints": True,
                "hints": "always",
                "hint_dist": "tournament",
                "text_shuffle": "none",
                "ice_trap_appearance": "junk_only",
                "junk_ice_traps": "normal",
                "item_pool_value": "balanced",
                "damage_multiplier": "normal",
                "starting_tod": "default",
                "starting_age": "child"
            }
        )

        await ctx.send(seed_url)


def get_random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))


def setup(bot):
    bot.add_cog(SpeedGamingLive(bot))

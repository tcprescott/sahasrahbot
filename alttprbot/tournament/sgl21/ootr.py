from alttprbot.alttprgen.randomizer import roll_ootr
from alttprbot.tournament.core import TournamentConfig
from alttprbot_discord.bot import discordbot
from .sglcore import SGLRandomizerTournamentRace

class OOTR(SGLRandomizerTournamentRace):
    async def configuration(self):
        guild = discordbot.get_guild(590331405624410116)
        return TournamentConfig(
            guild=guild,
            racetime_category='sgl',
            racetime_goal="Ocarina of Time Randomizer",
            event_slug="sgl21ootr",
            audit_channel=discordbot.get_channel(774336581808291863),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False
        )

    @property
    def seed_info(self):
        return f"https://ootrandomizer.com/seed/get?id={self.seed['id']}"

    async def roll(self): ## TODO confirm flags with admins
        self.seed = await roll_ootr(
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

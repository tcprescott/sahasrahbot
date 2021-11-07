import os

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
            audit_channel=discordbot.get_channel(772351829022474260),
            commentary_channel=discordbot.get_channel(631564559018098698),
            coop=False,
            stream_delay=15,
            gsheet_id=os.environ.get("SGL_RESULTS_SHEET")
        )

    @property
    def seed_info(self):
        return f"https://ootrandomizer.com/seed/get?id={self.seed['id']}"

    async def roll(self):
        self.seed = await roll_ootr(
            encrypt=True,
            version='dev_6.0.131',
            settings={
                "world_count": 1,
                "create_spoiler": True,
                "randomize_settings": False,
                "open_forest": "open",
                "open_kakariko": "open",
                "open_door_of_time": True,
                "zora_fountain": "closed",
                "gerudo_fortress": "fast",
                "bridge": "stones",
                "bridge_stones": 3,
                "triforce_hunt": False,
                "logic_rules": "glitchless",
                "reachable_locations": "all",
                "bombchus_in_logic": False,
                "one_item_per_dungeon": False,
                "trials_random": False,
                "trials": 0,
                "skip_child_zelda": True,
                "no_escape_sequence": True,
                "no_guard_stealth": True,
                "no_epona_race": True,
                "skip_some_minigame_phases": True,
                "useful_cutscenes": False,
                "complete_mask_quest": False,
                "fast_chests": True,
                "logic_no_night_tokens_without_suns_song": False,
                "free_scarecrow": False,
                "fast_bunny_hood": True,
                "start_with_rupees": False,
                "start_with_consumables": True,
                "starting_hearts": 3,
                "chicken_count_random": False,
                "chicken_count": 7,
                "big_poe_count_random": False,
                "big_poe_count": 1,
                "shuffle_kokiri_sword": True,
                "shuffle_ocarinas": False,
                "shuffle_gerudo_card": False,
                "shuffle_song_items": "song",
                "shuffle_cows": False,
                "shuffle_beans": False,
                "shuffle_medigoron_carpet_salesman": False,
                "shuffle_interior_entrances": "off",
                "shuffle_grotto_entrances": False,
                "shuffle_dungeon_entrances": False,
                "shuffle_overworld_entrances": False,
                "owl_drops": False,
                "warp_songs": False,
                "spawn_positions": True,
                "shuffle_scrubs": "off",
                "shopsanity": "off",
                "tokensanity": "off",
                "shuffle_mapcompass": "startwith",
                "shuffle_smallkeys": "dungeon",
                "shuffle_hideoutkeys": "vanilla",
                "shuffle_bosskeys": "dungeon",
                "shuffle_ganon_bosskey": "on_lacs",
                "lacs_condition": "vanilla",
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
                    "logic_lens_botw",
                    "logic_lens_castle",
                    "logic_lens_gtg",
                    "logic_lens_shadow",
                    "logic_lens_shadow_back",
                    "logic_lens_spirit"
                ],
                "logic_earliest_adult_trade": "prescription",
                "logic_latest_adult_trade": "claim_check",
                "starting_equipment": [
                    "deku_shield"
                ],
                "starting_items": [
                    "ocarina"
                ],
                "starting_songs": [],
                "ocarina_songs": False,
                "correct_chest_sizes": True,
                "clearer_hints": True,
                "no_collectible_hearts": False,
                "hints": "always",
                "hint_dist": "league",
                "item_hints": [],
                "hint_dist_user": {},
                "text_shuffle": "none",
                "misc_hints": True,
                "ice_trap_appearance": "junk_only",
                "junk_ice_traps": "off",
                "item_pool_value": "balanced",
                "damage_multiplier": "normal",
                "starting_tod": "default",
                "starting_age": "random"
            }
        )

import asyncio
import logging

from quart import Blueprint, redirect, render_template, request
from quart_discord import Unauthorized

from alttprbot import models
from alttprbot.util import triforce_text
from alttprbot.alttprgen import generator
from alttprbot.alttprgen.randomizer import roll_ffr, roll_ootr
from alttprbot.alttprgen.randomizer.smdash import create_smdash

from alttprbot_api.api import discord

sgl23_blueprint = Blueprint('sgl23', __name__)

@sgl23_blueprint.route('/sgl23', methods=["GET"])
async def sgl23_dashboard():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    return await render_template("sgl23_dashboard.html", logged_in=logged_in, user=user)

@sgl23_blueprint.route('/sgl23/generate/alttpr', methods=["GET"]) # updated
async def sgl23_generate_alttpr():
    preset = "sglive2023"
    # seed = await generator.ALTTPRPreset(preset).generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off", branch="tournament")
    seed = await triforce_text.generate_with_triforce_text(pool_name="sgl23", preset=preset, branch="tournament", balanced=False)
    logging.info("SGL23 - Generated ALTTPR seed %s", seed.url)
    await asyncio.sleep(2) # workaround for tournament branch seeds not being available immediately
    await models.SGL2023OnsiteHistory.create(
        tournament="alttpr",
        url=seed.url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed.url)

@sgl23_blueprint.route('/sgl23/generate/ootr') # updated
async def sgl23_generate_ootr():
    settings = {
        "enable_distribution_file": False,
        "enable_cosmetic_file": False,
        "create_spoiler": False, # disable spoilers
        "web_output_type": "z64",
        "web_common_key_string": "",
        "web_wad_channel_id": "NICE",
        "web_wad_channel_title": "OoTRandomizer",
        "web_wad_legacy_mode": False,
        "show_seed_info": True,
        "user_message": "SGL 2023",
        "world_count": 1,
        "player_num": 1,
        "randomize_settings": False,
        "logic_rules": "glitchless",
        "open_forest": "closed_deku",
        "open_kakariko": "open",
        "open_door_of_time": True,
        "zora_fountain": "closed",
        "gerudo_fortress": "fast",
        "dungeon_shortcuts_choice": "off",
        "dungeon_shortcuts": [],
        "bridge": "stones",
        "bridge_medallions": 6,
        "bridge_stones": 3,
        "bridge_rewards": 9,
        "bridge_tokens": 100,
        "bridge_hearts": 20,
        "trials_random": False,
        "trials": 0,
        "starting_age": "adult",
        "mq_dungeons_mode": "vanilla",
        "mq_dungeons_specific": [],
        "mq_dungeons_count": 0,
        "empty_dungeons_mode": "rewards",
        "empty_dungeons_specific": [],
        "empty_dungeons_rewards": ["Light Medallion"],
        "empty_dungeons_count": 2,
        "shuffle_interior_entrances": "off",
        "shuffle_hideout_entrances": False,
        "shuffle_grotto_entrances": False,
        "shuffle_dungeon_entrances": "off",
        "shuffle_bosses": "off",
        "shuffle_overworld_entrances": False,
        "shuffle_gerudo_valley_river_exit": False,
        "owl_drops": False,
        "warp_songs": False,
        "spawn_positions": ["child"],
        "triforce_hunt": False,
        "triforce_count_per_world": 30,
        "triforce_goal_per_world": 20,
        "free_bombchu_drops": False,
        "one_item_per_dungeon": False,
        "shuffle_song_items": "song",
        "shopsanity": "off",
        "shopsanity_prices": "random",
        "tokensanity": "off",
        "shuffle_scrubs": "off",
        "shuffle_child_trade": [],
        "adult_trade_shuffle": False,
        "adult_trade_start":
            ["Prescription", "Eyeball Frog", "Eyedrops", "Claim Check"],
        "shuffle_freestanding_items": "off",
        "shuffle_pots": "off",
        "shuffle_crates": "off",
        "shuffle_cows": False,
        "shuffle_beehives": False,
        "shuffle_kokiri_sword": True,
        "shuffle_ocarinas": False,
        "shuffle_gerudo_card": False,
        "shuffle_beans": False,
        "shuffle_expensive_merchants": False,
        "shuffle_frog_song_rupees": False,
        "shuffle_loach_reward": "off",
        "shuffle_individual_ocarina_notes": False,
        "shuffle_mapcompass": "startwith",
        "shuffle_smallkeys": "dungeon",
        "shuffle_hideoutkeys": "vanilla",
        "shuffle_tcgkeys": "vanilla",
        "key_rings_choice": "off",
        "key_rings": [],
        "keyring_give_bk": False,
        "shuffle_bosskeys": "dungeon",
        "shuffle_ganon_bosskey": "on_lacs",
        "ganon_bosskey_medallions": 6,
        "ganon_bosskey_stones": 3,
        "ganon_bosskey_rewards": 9,
        "ganon_bosskey_tokens": 100,
        "ganon_bosskey_hearts": 20,
        "shuffle_silver_rupees": "vanilla",
        "silver_rupee_pouches_choice": "off",
        "silver_rupee_pouches": [],
        "enhance_map_compass": True,
        "reachable_locations": "all",
        "logic_no_night_tokens_without_suns_song": False,
        "disabled_locations":
            [
            "Deku Theater Mask of Truth",
            "Kak 40 Gold Skulltula Reward",
            "Kak 50 Gold Skulltula Reward",
            ],
        "allowed_tricks":
            [
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
            "logic_lens_shadow_platform",
            "logic_lens_bongo",
            "logic_lens_spirit",
            ],
        "tricks_list_msg": None,
        "starting_equipment": ["deku_shield"],
        "starting_inventory": ["ocarina", "zeldas_letter", "farores_wind"],
        "starting_songs": ["prelude"],
        "start_with_consumables": True,
        "start_with_rupees": False,
        "starting_hearts": 3,
        "no_escape_sequence": True,
        "no_guard_stealth": True,
        "no_epona_race": True,
        "skip_some_minigame_phases": True,
        "complete_mask_quest": False,
        "useful_cutscenes": False,
        "fast_chests": True,
        "free_scarecrow": True,
        "fast_bunny_hood": True,
        "auto_equip_masks": False,
        "plant_beans": False,
        "chicken_count_random": False,
        "chicken_count": 3,
        "big_poe_count_random": False,
        "big_poe_count": 1,
        "easier_fire_arrow_entry": False,
        "fae_torch_count": 3,
        "ruto_already_f1_jabu": False,
        "ocarina_songs": "off",
        "correct_chest_appearances": "both",
        "minor_items_as_major_chest": "bombchus",
        "invisible_chests": False,
        "correct_potcrate_appearances": "textures_content",
        "key_appearance_match_dungeon": False,
        "clearer_hints": True,
        "hints": "always",
        "hint_dist": "sgl2023",
        "bingosync_url": "",
        "misc_hints":
            ["altar", "ganondorf", "warp_songs", "20_skulltulas", "30_skulltulas"],
        "text_shuffle": "none",
        "damage_multiplier": "normal",
        "deadly_bonks": "none",
        "no_collectible_hearts": False,
        "starting_tod": "default",
        "blue_fire_arrows": False,
        "fix_broken_drops": False,
        "item_pool_value": "balanced",
        "junk_ice_traps": "off",
        "ice_trap_appearance": "junk_only",
        "default_targeting": "hold",
        "display_dpad": True,
        "dpad_dungeon_menu": True,
        "correct_model_colors": True,
        "randomize_all_cosmetics": False,
        "model_adult": "Default",
        "model_child": "Default",
        "model_unavailable_msg": None,
        "kokiri_color": "Kokiri Green",
        "goron_color": "Goron Red",
        "zora_color": "Zora Blue",
        "silver_gauntlets_color": "Silver",
        "golden_gauntlets_color": "Gold",
        "mirror_shield_frame_color": "Red",
        "heart_color": "Red",
        "magic_color": "Green",
        "a_button_color": "N64 Blue",
        "b_button_color": "N64 Green",
        "c_button_color": "Yellow",
        "start_button_color": "N64 Red",
        "navi_color_default_inner": "White",
        "navi_color_default_outer": "[Same as Inner]",
        "navi_color_enemy_inner": "Yellow",
        "navi_color_enemy_outer": "[Same as Inner]",
        "navi_color_npc_inner": "Light Blue",
        "navi_color_npc_outer": "[Same as Inner]",
        "navi_color_prop_inner": "Green",
        "navi_color_prop_outer": "[Same as Inner]",
        "bombchu_trail_color_inner": "Red",
        "bombchu_trail_color_outer": "[Same as Inner]",
        "boomerang_trail_color_inner": "Yellow",
        "boomerang_trail_color_outer": "[Same as Inner]",
        "sword_trail_color_inner": "White",
        "sword_trail_color_outer": "[Same as Inner]",
        "sword_trail_duration": 4,
        "randomize_all_sfx": False,
        "disable_battle_music": False,
        "speedup_music_for_last_triforce_piece": False,
        "slowdown_music_when_lowhp": False,
        "background_music": "normal",
        "fanfares": "normal",
        "ocarina_fanfares": False,
        "sfx_ocarina": "ocarina",
        "sfx_bombchu_move": "default",
        "sfx_hover_boots": "default",
        "sfx_iron_boots": "default",
        "sfx_boomerang_throw": "default",
        "sfx_hookshot_chain": "default",
        "sfx_arrow_shot": "default",
        "sfx_slingshot_shot": "default",
        "sfx_magic_arrow_shot": "default",
        "sfx_explosion": "default",
        "sfx_link_adult": "Default",
        "sfx_link_child": "Default",
        "sfx_link_unavailable_msg": None,
        "sfx_navi_overworld": "default",
        "sfx_navi_enemy": "default",
        "sfx_horse_neigh": "default",
        "sfx_cucco": "default",
        "sfx_daybreak": "default",
        "sfx_nightfall": "default",
        "sfx_menu_cursor": "default",
        "sfx_menu_select": "default",
        "sfx_low_hp": "default",
        "sfx_silver_rupee": "default",
        "sfx_get_small_item": "default",
        "settings_string": "",
        "theme": "",
        "distribution_file": "",
        "cosmetic_file": "",
    }
    seed = await roll_ootr(settings=settings, version='devSGLive22_7.1.143', encrypt=True)
    logging.info("sgl23 - Generated OOTR seed %s", seed['id'])
    url = f"https://ootrandomizer.com/seed/get?id={seed['id']}"
    await models.SGL2023OnsiteHistory.create(
        tournament="ootr",
        url=url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(url)

@sgl23_blueprint.route("/sgl23/generate/smr") #updated
async def sgl23_generate_smr():
    seed_url = await create_smdash(mode="sgl23")
    await models.SGL2023OnsiteHistory.create(
        tournament="smr",
        url=seed_url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed_url)

@sgl23_blueprint.route("/sgl23/generate/ffr") # updated
async def sgl23_generate_ffr():
    _, seed_url = roll_ffr("https://4-7-2.finalfantasyrandomizer.com/?s=00000000&f=m1-dPYu5-7ZlHqdPgC9BsTva4786C4mX5d0uZn85JzpVARtsVYb4TkKKyi4owT82MQwSww28yiLaHtMBNNzxMGjISw8IWcAfUS7AEkSp52Degtu4wErH3htXn4zENBWaNXWqXL6O-k8R3wZ8h55Gye21Spp4emwbbNwehPD")
    await models.SGL2023OnsiteHistory.create(
        tournament="ffr",
        url=seed_url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed_url)

@sgl23_blueprint.route("/sgl23/generate/smz3/main")
async def sgl23_generate_smz3_main():
    seed = await generator.SMZ3Preset("hardfast").generate(tournament=True)
    await models.SGL2023OnsiteHistory.create(
        tournament="smz3_main",
        url=seed.url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed.url)

@sgl23_blueprint.route("/sgl23/generate/smz3/alt")
async def sgl23_generate_smz3_alt():
    seed = await generator.SMZ3Preset("normal").generate(tournament=True)
    await models.SGL2023OnsiteHistory.create(
        tournament="smz3_alt",
        url=seed.url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed.url)
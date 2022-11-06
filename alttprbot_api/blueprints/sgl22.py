import logging

from quart import Blueprint, redirect, render_template
from quart_discord import Unauthorized

from alttprbot.alttprgen import generator, smvaria
from alttprbot.alttprgen.randomizer import roll_ffr, roll_ootr

from ..api import discord

sgl22_blueprint = Blueprint('sgl22', __name__)

@sgl22_blueprint.route('/sgl22', methods=["GET"])
async def sgl22_dashboard():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    return await render_template("sgl22_dashboard.html", logged_in=logged_in, user=user)

@sgl22_blueprint.route('/sgl22/generate/alttpr', methods=["GET"])
async def sgl22_generate_alttpr():
    preset = "sgl2022"
    seed = await generator.ALTTPRPreset(preset).generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off")
    logging.info("SGL22 - Generated ALTTPR seed %s", seed.url)
    return redirect(seed.url)

@sgl22_blueprint.route('/sgl22/generate/ootr')
async def sgl22_generate_ootr():
    settings = {
        "enable_distribution_file": False,
        "enable_cosmetic_file": False,
        "create_spoiler": False,
        "web_output_type": "z64",
        "web_common_key_string": "",
        "web_wad_channel_id": "NICE",
        "web_wad_channel_title": "OoTRandomizer",
        "web_wad_legacy_mode": False,
        "show_seed_info": True,
        "user_message": "SGL 2022",
        "world_count": 1,
        "player_num": 1,
        "randomize_settings": False,
        "logic_rules": "glitchless",
        "open_forest": "open",
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
        "starting_age": "random",
        "mq_dungeons_mode": "vanilla",
        "mq_dungeons_specific": [],
        "mq_dungeons_count": 0,
        "empty_dungeons_mode": "none",
        "empty_dungeons_specific": [],
        "empty_dungeons_count": 2,
        "shuffle_interior_entrances": "off",
        "shuffle_grotto_entrances": False,
        "shuffle_dungeon_entrances": "off",
        "shuffle_bosses": "off",
        "shuffle_overworld_entrances": False,
        "owl_drops": False,
        "warp_songs": False,
        "spawn_positions": True,
        "triforce_hunt": False,
        "triforce_count_per_world": 30,
        "triforce_goal_per_world": 20,
        "bombchus_in_logic": False,
        "one_item_per_dungeon": False,
        "shuffle_song_items": "song",
        "shopsanity": "off",
        "shopsanity_prices": "random",
        "tokensanity": "off",
        "shuffle_scrubs": "off",
        "shuffle_child_trade": "skip_child_zelda",
        "shuffle_cows": False,
        "shuffle_kokiri_sword": True,
        "shuffle_ocarinas": False,
        "shuffle_gerudo_card": False,
        "shuffle_beans": False,
        "shuffle_medigoron_carpet_salesman": False,
        "shuffle_frog_song_rupees": False,
        "shuffle_mapcompass": "startwith",
        "shuffle_smallkeys": "dungeon",
        "shuffle_hideoutkeys": "vanilla",
        "key_rings_choice": "off",
        "key_rings": [],
        "shuffle_bosskeys": "dungeon",
        "shuffle_ganon_bosskey": "on_lacs",
        "ganon_bosskey_medallions": 6,
        "ganon_bosskey_stones": 3,
        "ganon_bosskey_rewards": 9,
        "ganon_bosskey_tokens": 100,
        "ganon_bosskey_hearts": 20,
        "enhance_map_compass": False,
        "reachable_locations": "all",
        "logic_no_night_tokens_without_suns_song": False,
        "disabled_locations": ["Deku Theater Mask of Truth", "Kak 40 Gold Skulltula Reward", "Kak 50 Gold Skulltula Reward"],
        "allowed_tricks": ["logic_fewer_tunic_requirements", "logic_grottos_without_agony", "logic_child_deadhand", "logic_man_on_roof", "logic_dc_jump", "logic_rusted_switches", "logic_windmill_poh", "logic_crater_bean_poh_with_hovers", "logic_forest_vines", "logic_lens_botw", "logic_lens_castle", "logic_lens_gtg", "logic_lens_shadow", "logic_lens_shadow_platform", "logic_lens_bongo", "logic_lens_spirit"],
        "tricks_list_msg": "",
        "starting_equipment": ["deku_shield"],
        "starting_items": ["ocarina"],
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
        "plant_beans": False,
        "chicken_count_random": False,
        "chicken_count": 3,
        "big_poe_count_random": False,
        "big_poe_count": 1,
        "easier_fire_arrow_entry": False,
        "fae_torch_count": 3,
        "ocarina_songs": "off",
        "correct_chest_appearances": "both",
        "invisible_chests": False,
        "bombchus_gilded_chest_appearance": True,
        "clearer_hints": True,
        "hints": "always",
        "hint_dist": "sgl2022",
        "bingosync_url": "",
        "misc_hints": ["altar", "ganondorf", "warp_songs"],
        "text_shuffle": "none",
        "damage_multiplier": "normal",
        "deadly_bonks": "none",
        "no_collectible_hearts": False,
        "starting_tod": "default",
        "blue_fire_arrows": False,
        "item_pool_value": "balanced",
        "junk_ice_traps": "off",
        "ice_trap_appearance": "junk_only",
        "adult_trade_start": ["Prescription", "Eyeball Frog", "Eyedrops", "Claim Check"],
        "default_targeting": "hold",
        "display_dpad": True,
        "correct_model_colors": False,
        "randomize_all_cosmetics": False,
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
        "background_music": "normal",
        "fanfares": "normal",
        "ocarina_fanfares": False,
        "sfx_low_hp": "default",
        "sfx_horse_neigh": "default",
        "sfx_nightfall": "default",
        "sfx_hover_boots": "default",
        "sfx_ocarina": "ocarina",
        "sfx_menu_cursor": "default",
        "sfx_menu_select": "default",
        "sfx_navi_overworld": "default",
        "sfx_navi_enemy": "default",
        "settings_string": "",
        "distribution_file": "",
        "cosmetic_file": ""
    }
    seed = await roll_ootr(settings=settings, version='devSGLive22_6.2.197', encrypt=True)
    logging.info("SGL22 - Generated OOTR seed %s", seed['id'])
    return redirect(f"https://ootrandomizer.com/seed/get?id={seed['id']}")

@sgl22_blueprint.route("/sgl22/generate/smr/<string:game_num>")
async def sgl22_generate_smr(game_num):
    if game_num not in ["1", "2", "3"]:
        return "bad input"

    seed = await smvaria.generate_preset(
        settings=f"SGLive2022_Game_{game_num}",
        skills="Season_Races",
        race=True
    )
    return redirect(seed.url)

@sgl22_blueprint.route("/sgl22/generate/ffr")
async def sgl22_generate_ffr():
    _, seed_url = roll_ffr("https://4-6-2.finalfantasyrandomizer.com/?s=00000000&f=ePMaDqw0oGJc7M6XlzT4jyfeIq4bh2fqDnPVafb.RXEaa.l2e55h.Ffv07WTbtutjWOIrV3MTKoR.ISYQQTjPtSB42oxxHtWscLxyc0l7Ea7ptfKITpWDViEPsYTX12UsLdnxl0JI5IAKJFK6Xxr2bnOMv9-wLYskNjvq")
    return redirect(seed_url)

@sgl22_blueprint.route("/sgl22/generate/smz3")
async def sgl22_generate_smz3():
    seed = await generator.SMZ3Preset("fast").generate(tournament=True)
    return redirect(seed.url)
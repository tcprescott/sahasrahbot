import asyncio
import dateutil.parser
from dateutil.tz import tzutc
from datetime import datetime, timedelta
import logging

import aiocache
from pytz import timezone
from quart import Blueprint, redirect, render_template, request
from quart_discord import Unauthorized

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.alttprgen.randomizer import roll_ffr, roll_ootr
from alttprbot.alttprgen.randomizer.smdash import create_smdash
from alttprbot.util import triforce_text, speedgaming
from alttprbot_api.api import discord

import config

sglive_blueprint = Blueprint('sglive', __name__)


# TODO requires updating
@sglive_blueprint.route('/', methods=["GET"])
async def sglive_dashboard():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None

    games = [
        {
            "name": "ALTTP NMG",
            "notes": "This is a speedrun, no seeds are generated.",
            # "schedule_url": "https://schedule.speedgaming.org/alttpnmg",
            # "challonge_url": "https://challonge.com/alttpnmg",
        },
        {
            "name": "TWWR",
            # "schedule_url": "https://schedule.speedgaming.org/twwr",
            # "challonge_url": "https://challonge.com/twwr",
            "download_url": "https://github.com/tanjo3/wwrando/releases/tag/s7-v1",
            "model_pack_url": "https://github.com/Sage-of-Mirrors/Custom-Wind-Waker-Player-Models/archive/master.zip",
        },
        {
            "name": "OOTR",
            "generator_url": "/sglive/generate/ootr",
            # "schedule_url": "https://schedule.speedgaming.org/ootr",
            # "challonge_url": "https://challonge.com/ootr",
        },
        {
            "name": "ALTTPR",
            "generator_url": "/sglive/generate/alttpr",
            # "schedule_url": "https://schedule.speedgaming.org/alttpr",
            # "challonge_url": "https://challonge.com/alttpr",
        },
        {
            "name": "Z1R",
            "generator_url": "/sglive/generate/z1r",
            # "schedule_url": "https://schedule.speedgaming.org/z1r",
            # "challonge_url": "https://challonge.com/z1r",
        },
        {
            "name": "FFR",
            "generator_url": "/sglive/generate/ffr",
            # "schedule_url": "https://schedule.speedgaming.org/ffr",
            # "challonge_url": "https://challonge.com/ffr",
        },
        {
            "name": "MMR",
            "generator_url": "/sglive/generate/mmr",
            "download_url": "https://github.com/ZoeyZolotova/mm-rando/releases/tag/v1.16.0.12"
            # "schedule_url": "https://schedule.speedgaming.org/mmr",
            # "challonge_url": "https://challonge.com/mmr",
        },
        {
            "name": "SMR",
            "generator_url": "/sglive/generate/smr",
            # "schedule_url": "https://schedule.speedgaming.org/smdash",
            # "challonge_url": "https://challonge.com/smr",
        },
        {
            "name": "MMX",
            "notes": "This is a speedrun, no seeds are generated.",
            # "schedule_url": "https://schedule.speedgaming.org/mmx",
            # "challonge_url": "https://challonge.com/mmx",
        },
        {
            "name": "SMB3R",
            # "download_url": "/sglive/generate/smb3r",
            # "schedule_url": "https://schedule.speedgaming.org/smb3r",
            # "challonge_url": "https://challonge.com/smb3r",
        }
    ]

    return await render_template("sglive_dashboard.html", user=user, games=games)


# updated for SGL24
@sglive_blueprint.route('/generate/alttpr', methods=["GET"])  # updated
async def sglive_generate_alttpr():
    preset = "sglive2024"
    # seed = await generator.ALTTPRPreset(preset).generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off", branch="tournament")
    seed = await triforce_text.generate_with_triforce_text(pool_name="sgl24", preset=preset, balanced=False)
    logging.info("sglive - Generated ALTTPR seed %s", seed.url)
    await asyncio.sleep(2)  # workaround for tournament branch seeds not being available immediately
    await models.SGL2023OnsiteHistory.create(
        tournament="alttpr",
        url=seed.url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed.url)

# updated for sgl24
@sglive_blueprint.route('/generate/ootr')  # updated
async def sglive_generate_ootr():
    settings = {
        "create_spoiler": True,
        "show_seed_info": True,
        "user_message": "SGL 2024 (Experimental)",
        "world_count": 1,
        "randomize_settings": False,
        "logic_rules": "glitchless",
        "open_forest": "closed_deku",
        "open_kakariko": "open",
        "open_door_of_time": True,
        "zora_fountain": "closed",
        "gerudo_fortress": "fast",
        "dungeon_shortcuts_choice": "off",
        "bridge": "stones",
        "bridge_stones": 3,
        "trials_random": False,
        "trials": 0,
        "starting_age": "adult",
        "mq_dungeons_mode": "vanilla",
        "empty_dungeons_mode": "rewards",
        "empty_dungeons_rewards": ["Light Medallion"],
        "shuffle_interior_entrances": "off",
        "shuffle_grotto_entrances": False,
        "shuffle_dungeon_entrances": "off",
        "shuffle_bosses": "off",
        "shuffle_overworld_entrances": False,
        "owl_drops": False,
        "warp_songs": False,
        "spawn_positions": ["child"],
        "triforce_hunt": False,
        "free_bombchu_drops": False,
        "one_item_per_dungeon": False,
        "shuffle_song_items": "song",
        "shopsanity": "off",
        "tokensanity": "off",
        "shuffle_scrubs": "off",
        "shuffle_child_trade": [],
        "shuffle_freestanding_items": "off",
        "shuffle_pots": "off",
        "shuffle_crates": "off",
        "shuffle_cows": False,
        "shuffle_beehives": False,
        "shuffle_kokiri_sword": true,
        "shuffle_ocarinas": False,
        "shuffle_gerudo_card": False,
        "shuffle_beans": False,
        "shuffle_expensive_merchants": False,
        "shuffle_frog_song_rupees": False,
        "shuffle_mapcompass": "startwith",
        "shuffle_smallkeys": "dungeon",
        "shuffle_hideoutkeys": "vanilla",
        "key_rings_choice": "off",
        "shuffle_bosskeys": "dungeon",
        "shuffle_ganon_bosskey": "on_lacs",
        "enhance_map_compass": True,
        "reachable_locations": "all",
        "logic_no_night_tokens_without_suns_song": False,
        "disabled_locations": ["Deku Theater Mask of Truth", "Kak 40 Gold Skulltula Reward", "Kak 50 Gold Skulltula Reward"],
        "allowed_tricks": ["logic_fewer_tunic_requirements", "logic_grottos_without_agony", "logic_child_deadhand", "logic_man_on_roof", "logic_dc_jump", "logic_rusted_switches", "logic_windmill_poh", "logic_crater_bean_poh_with_hovers", "logic_forest_vines", "logic_lens_botw", "logic_lens_castle", "logic_lens_gtg", "logic_lens_shadow", "logic_lens_shadow_platform", "logic_lens_bongo", "logic_lens_spirit", "logic_deku_b1_skip"],
        "starting_equipment": ["deku_shield"],
        "starting_inventory": ["ocarina", "zeldas_letter", "lens", "farores_wind"],
        "starting_songs": ["prelude"],
        "start_with_consumables": True,
        "start_with_rupees": False,
        "starting_hearts": 3,
        "skip_reward_from_rauru": True,
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
        "ruto_already_f1_jabu": True,
        "ocarina_songs": "off",
        "correct_chest_appearances": "both",
        "chest_textures_specific": ["major", "bosskeys", "keys", "tokens", "hearts"],
        "soa_unlocks_chest_texture": False,
        "minor_items_as_major_chest": ["bombchus"],
        "invisible_chests": False,
        "correct_potcrate_appearances": "textures_unchecked",
        "potcrate_textures_specific": ["major", "bosskeys", "keys", "tokens", "hearts"],
        "soa_unlocks_potcrate_texture": False,
        "clearer_hints": True,
        "hints": "always",
        "hint_dist": "sgl2024",
        "misc_hints": ["altar", "ganondorf", "warp_songs", "20_skulltulas", "30_skulltulas"],
        "text_shuffle": "none",
        "damage_multiplier": "normal",
        "deadly_bonks": "none",
        "no_collectible_hearts": False,
        "starting_tod": "default",
        "blue_fire_arrows": True,
        "fix_broken_drops": False,
        "item_pool_value": "balanced",
        "junk_ice_traps": "off",
        "ice_trap_appearance": "junk_only",
        "adult_trade_shuffle": False,
        "adult_trade_start": ["Claim Check"]
    }
    seed = await roll_ootr(settings=settings, version='devSGLive22_8.1.49-40', encrypt=True)
    logging.info("sglive - Generated OOTR seed %s", seed['id'])
    url = f"https://ootrandomizer.com/seed/get?id={seed['id']}"
    await models.SGL2023OnsiteHistory.create(
        tournament="ootr",
        url=url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(url)

# updated for SGL24
@sglive_blueprint.route("/generate/smr")  # updated
async def sglive_generate_smr():
    seed_url = await create_smdash(mode="sgl24")
    await models.SGL2023OnsiteHistory.create(
        tournament="smr",
        url=seed_url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed_url)

# updated for SGL24
@sglive_blueprint.route("/generate/ffr")  # updated
async def sglive_generate_ffr():
    _, seed_url = roll_ffr(
        "https://4-8-4.finalfantasyrandomizer.com/?s=925170C9&f=Oi8sqe8EtEbVp1APHwr9olO0ycGtljkk7F-0SmIM09GoRLzaTydcWAUjAqLlDs3DD8stDlLfhhwd1GwaUi98jg6dZwxFR8I2ylQBWQJWJxQEndIzpq2PUreYxBGv7AFwelXB-OhDufRdb6JnRk3B1Dzw-4o4iYWhY6.6LRNpJ0rUjxD")
    await models.SGL2023OnsiteHistory.create(
        tournament="ffr",
        url=seed_url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed_url)

#updated for sgl24
@sglive_blueprint.route("/generate/smz3/main")
async def sglive_generate_smz3_main():
    seed = await generator.SMZ3Preset("mm2nescartridge/sgl2024").generate(tournament=True)
    await models.SGL2023OnsiteHistory.create(
        tournament="smz3_main",
        url=seed.url,
        ip_address=request.headers.get('X-Real-IP', request.remote_addr),
    )
    return redirect(seed.url)

@sglive_blueprint.route("/reports/capacity")
async def sglive_reports_capacity():
    try:
        user = await discord.fetch_user()
    except Unauthorized:
        user = None

    events = {
        'sgl24smb3rx': timedelta(hours=3), # updated
        'sgl24mmxx': timedelta(hours=1, minutes=0),
        'sgl24smz3': timedelta(hours=3, minutes=30), # updated
        'sgl24smrx': timedelta(hours=1, minutes=45),
        'sgl24mm64r': timedelta(hours=2, minutes=30), # updated
        'sgl24ffrx': timedelta(hours=1, minutes=30), # updated
        'sgl24z1rx': timedelta(hours=2), # updated
        'sgl24ootr': timedelta(hours=3), # updated
        'sgl24alttprx': timedelta(hours=2), # updated
        'sgl24wwr': timedelta(hours=2, minutes=30),
        'sgl24alttpnmg': timedelta(hours=2), # updated
    }
    report = await create_capacity_report(events)
    threshold = 10 if config.DEBUG else 25
    return await render_template("sglive_reports_capacity.html", events=events.keys(), report=report, alert_threshold=threshold, user=user)

# TODO: update for SGL24
@aiocache.cached(ttl=60, cache=aiocache.SimpleMemoryCache)
async def create_capacity_report(events):
    results = {}
    hours = 48
    tz = timezone('US/Eastern')

    if config.DEBUG:
        current_time = datetime(2023, 11, 9, 9, 0, 0, tzinfo=tz)
    else:
        current_time = datetime.now(tz)

    nearest_15 = round_dt_to_delta(current_time)

    for event, run_time in events.items():
        episodes = await speedgaming.get_upcoming_episodes_by_event(event, hours_past=4, hours_future=hours, static_time=nearest_15)
        start_times = []
        for episode in episodes:
            start_time = dateutil.parser.parse(episode['whenCountdown'])
            start_time = start_time.astimezone(tz)
            start_times.append(start_time)

        # result[event] = {}

        intervals_to_check = [nearest_15 + timedelta(minutes=x) for x in range(0, 60*hours, 15)]
        for time_interval in intervals_to_check: # 48 hours in 15 minute intervals
            # format time_interval as a string for human readability
            # skip overnight hours (midnight to 8am)
            if time_interval.hour < 8 or time_interval.hour >= 24:
                continue
            time_interval_formatted = time_interval.strftime('%A %I:%M %p')
            results.setdefault(time_interval_formatted, {}).setdefault("runtime", {}).setdefault(event, sum(1 for x in start_times if x <= time_interval < x + run_time))
            results.setdefault(time_interval_formatted, {}).setdefault("starting", {}).setdefault(event, sum(1 for x in start_times if x <= time_interval < x + timedelta(minutes=15)))


    # sum the number of matches running in each category at each 15 minute interval
    for time_interval, data in results.items():
        results[time_interval]['runtime_total'] = sum(data['runtime'].values())
    for time_interval, data in results.items():
        results[time_interval]['starting_total'] = sum(data['starting'].values())

    return results

def round_dt_to_delta(dt, delta=timedelta(minutes=15)):
    ref = datetime.min.replace(tzinfo=dt.tzinfo)
    return ref + round((dt - ref) / delta) * delta

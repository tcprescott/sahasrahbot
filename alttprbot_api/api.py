import os
import re
from io import BytesIO
from urllib.parse import quote
import datetime

import aiohttp
from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot.alttprgen.randomizer.ootr import roll_ootr
from alttprbot.tournaments import TOURNAMENT_DATA, fetch_tournament_handler
from alttprbot_discord.bot import discordbot
from alttprbot_racetime.bot import racetime_bots
from quart import (Quart, abort, jsonify, redirect, render_template, request,
                   send_file, session, url_for)
from quart_discord import (AccessDenied, DiscordOAuth2Session, Unauthorized,
                           requires_authorization)

sahasrahbotapi = Quart(__name__)
sahasrahbotapi.secret_key = bytes(os.environ.get("APP_SECRET_KEY"), "utf-8")

RACETIME_CLIENT_ID_OAUTH = os.environ.get('RACETIME_CLIENT_ID_OAUTH')
RACETIME_CLIENT_SECRET_OAUTH = os.environ.get('RACETIME_CLIENT_SECRET_OAUTH')
RACETIME_URL = os.environ.get('RACETIME_URL', 'https://racetime.gg')
APP_URL = os.environ.get('APP_URL', 'https://sahasrahbotapi.synack.live')

sahasrahbotapi.config["DISCORD_CLIENT_ID"] = int(os.environ.get("DISCORD_CLIENT_ID"))
sahasrahbotapi.config["DISCORD_CLIENT_SECRET"] = os.environ.get("DISCORD_CLIENT_SECRET")
sahasrahbotapi.config["DISCORD_REDIRECT_URI"] = os.environ.get("APP_URL") + "/callback/discord/"
sahasrahbotapi.config["DISCORD_BOT_TOKEN"] = os.environ.get("DISCORD_TOKEN")

discord = DiscordOAuth2Session(sahasrahbotapi)


@sahasrahbotapi.route("/login/")
async def login():
    return await discord.create_session(
        scope=[
            'identify',
        ],
        data=dict(redirect=session.get("login_original_path", "/me"))
    )


@sahasrahbotapi.route("/callback/discord/")
async def callback():
    data = await discord.callback()
    redirect_to = data.get("redirect", "/me/")
    return redirect(redirect_to)


@sahasrahbotapi.errorhandler(Unauthorized)
async def redirect_unauthorized(e):
    session['login_original_path'] = request.full_path
    return redirect(url_for("login"))


@sahasrahbotapi.errorhandler(AccessDenied)
async def access_denied(e):
    return await render_template(
        'error.html',
        title="Access Denied",
        message="We were unable to access your Discord account."
    )


@sahasrahbotapi.route("/me/")
@requires_authorization
async def me():
    user = await discord.fetch_user()
    return await render_template('me.html', logged_in=True, user=user)


@sahasrahbotapi.route("/logout/")
async def logout():
    discord.revoke()
    return await render_template('logout.html', logged_in=False)


@sahasrahbotapi.route('/api/settingsgen/mystery', methods=['POST'])
async def mysterygen():
    weights = await request.get_json()
    data = await generator.ALTTPRMystery.custom_from_dict(weights)
    mystery = await data.generate_test_game()

    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'

    print(mystery.custom_instructions)

    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route('/api/settingsgen/mystery', methods=['GET'])
async def mysterygenwithweightsv2():
    weightset = request.args.get('weightset')
    data = generator.ALTTPRMystery(preset=weightset)
    mystery = await data.generate_test_game()

    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'

    print(mystery.custom_instructions)

    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )


@sahasrahbotapi.route('/api/settingsgen/mystery/<string:weightset>', methods=['GET'])
async def mysterygenwithweights(weightset):
    data = generator.ALTTPRMystery(preset=weightset)
    mystery = await data.generate_test_game()

    if mystery.customizer:
        endpoint = '/api/customizer'
    elif mystery.doors:
        endpoint = None
    else:
        endpoint = '/api/randomizer'

    print(mystery.custom_instructions)

    return jsonify(
        settings=mystery.settings,
        customizer=mystery.customizer,
        doors=mystery.doors,
        endpoint=endpoint
    )

@sahasrahbotapi.route('/api/tournament/games', methods=['GET'])
async def get_tournament_games():
    terms = request.args
    data = await models.TournamentGames.filter(**terms).values()
    return jsonify(data)

@sahasrahbotapi.route('/api/racetime/cmd', methods=['POST'])
async def bot_command():
    data = await request.get_json()

    category = data['category']
    room = data['room']
    cmd = data['cmd']
    auth_key = request.args['auth_key']

    access = await models.AuthorizationKeyPermissions.get_or_none(auth_key__key=auth_key, type='racetimecmd', subtype=category)
    if access is None:
        return abort(403)

    racetime_bot = racetime_bots.get(category)
    if not racetime_bot:
        raise Exception("Invalid game category")

    racetime_handler = racetime_bot.handlers.get(f"{category}/{room}").handler

    fake_data = {
        'message': {
            'id': 'FAKE',
            'user': {
                'id': 'FAKE',
                'full_name': 'API-submitted command',
                'name': 'API-submitted command',
                'discriminator': None,
                'url': None,
                'avatar': None,
                'flair': None,
                'twitch_name': None,
                'twitch_display_name': None,
                'twitch_channel': None,
                'can_moderate': True,
            },
            'bot': False,
            'posted_at': datetime.datetime.utcnow().isoformat(),
            'message': cmd,
            'message_plain': cmd,
            'highlight': False,
            'is_bot': False,
            'is_monitor': True,
            'is_system': False,
            'delay': 0
        },
        'type': 'message.chat',
        'date': datetime.datetime.utcnow().isoformat(),
    }

    await racetime_handler.send_message(f"Executing command from API request: {cmd}")
    await racetime_handler.chat_message(fake_data)

    return jsonify({'success': True})

@sahasrahbotapi.route("/submit/<string:event>", methods=['GET'])
@requires_authorization
async def submission_form(event):
    user = await discord.fetch_user()
    episode_id = request.args.get("episode_id", "")

    event_config = await TOURNAMENT_DATA[event].get_config()
    form_data = event_config.submission_form
    if form_data is None:
        raise Exception("There is no form submission data for this event.")

    if isinstance(form_data, str):
        return await render_template(
            form_data,
            logged_in=True,
            user=user,
            event=event,
            endpoint=url_for("submit"),
            episode_id=episode_id
        )
    else:
        return await render_template(
            'submission.html',
            logged_in=True,
            user=user,
            event=event,
            endpoint=url_for("submit"),
            settings_list=form_data,
            episode_id=episode_id
        )


@sahasrahbotapi.route("/submit", methods=['POST'])
@requires_authorization
async def submit():
    user = await discord.fetch_user()
    payload = await request.form
    tournament_race = await fetch_tournament_handler(payload['event'], int(payload['episodeid']))
    await tournament_race.process_submission_form(payload, submitted_by=f"{user.name}#{user.discriminator}")
    return await render_template(
        "submission_done.html",
        logged_in=True,
        user=user,
        tournament_race=tournament_race
    )


@sahasrahbotapi.route('/racetime/verification/initiate', methods=['GET'])
@requires_authorization
async def racetime_init_verification():
    redirect_uri = quote(f"{APP_URL}/racetime/verify/return")
    return redirect(
        f"{RACETIME_URL}/o/authorize?client_id={RACETIME_CLIENT_ID_OAUTH}&response_type=code&scope=read&redirect_uri={redirect_uri}",
    )


@sahasrahbotapi.route('/racetime/verify/return', methods=['GET'])
@requires_authorization
async def return_racetime_verify():
    user = await discord.fetch_user()
    code = request.args.get("code")
    if code is None:
        return abort(400, "code is missing")
    data = {
        'client_id': RACETIME_CLIENT_ID_OAUTH,
        'client_secret': RACETIME_CLIENT_SECRET_OAUTH,
        'code': code,
        'grant_type': 'authorization_code',
        'scope': 'read',
        'redirect_uri': f"{APP_URL}/racetime/verify/return"
    }

    async with aiohttp.request(url=f"{RACETIME_URL}/o/token", method="post", data=data, raise_for_status=True) as resp:
        token_data = await resp.json()

    token = token_data['access_token']

    headers = {
        'Authorization': f'Bearer {token}'
    }
    async with aiohttp.request(url=f"{RACETIME_URL}/o/userinfo", method="get", headers=headers, raise_for_status=True) as resp:
        userinfo_data = await resp.json()

    await models.SRLNick.update_or_create(discord_user_id=user.id, defaults={'rtgg_id': userinfo_data['id']})

    return await render_template('racetime_verified.html', logged_in=True, user=user, racetime_name=userinfo_data['name'])


@sahasrahbotapi.route('/healthcheck', methods=['GET'])
async def healthcheck():
    if discordbot.is_closed():
        abort(500, description='Connection to Discord is closed.')

    appinfo = await discordbot.application_info()
    await discordbot.fetch_user(appinfo.owner.id)

    return jsonify(
        success=True
    )


@sahasrahbotapi.route('/presets', methods=['GET'])
# @requires_authorization
async def all_presets():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    namespaces = await models.PresetNamespaces.all()

    return await render_template('preset_namespaces_all.html', logged_in=logged_in, user=user, namespaces=namespaces)


@sahasrahbotapi.route('/purgeme', methods=['GET'])
async def purge_me():
    user = await discord.fetch_user()

    return await render_template('purge_me.html', logged_in=True, user=user)


@sahasrahbotapi.route('/purgeme', methods=['POST'])
async def purge_me_action():
    user = await discord.fetch_user()
    payload = await request.form

    if payload.get('confirmpurge', 'no') == 'yes':
        await models.PresetNamespaces.filter(discord_user_id=user.id).delete()
        await models.NickVerification.filter(discord_user_id=user.id).delete()
        await models.SRLNick.filter(discord_user_id=user.id).delete()
        await models.AuditMessages.filter(user_id=user.id).delete()

        return redirect("/logout/")

    return redirect("/me/")

@sahasrahbotapi.route('/triforcetexts', methods=['GET'])
@requires_authorization
async def triforcetexts():
    user = await discord.fetch_user()
    logged_in = True

    return await render_template('triforce_text.html', logged_in=logged_in, user=user, endpoint=url_for('triforcetexts_submit'))

@sahasrahbotapi.route('/triforcetexts/submit', methods=['POST'])
@requires_authorization
async def triforcetexts_submit():
    user = await discord.fetch_user()
    logged_in = True

    payload = await request.form

    regex = re.compile(r"^[A-Za-z0-9 ?!,-….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ]{0,14}$")

    if not regex.match(payload['first_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the first line.")
    if not regex.match(payload['second_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the second line.")
    if not regex.match(payload['third_line']):
        return await render_template('error.html', logged_in=logged_in, user=user, title="Invalid input.", message="Invalid text entered for the third line.")

    text = f"{payload['first_line']}\\n{payload['second_line']}\\n{payload['third_line']}"

    await models.TriforceTexts.create(pool_name="alttpr2022", text=text, discord_user_id=user.id, author=f"{user.name}#{user.discriminator}")

    return await render_template('triforce_text_submit.html', logged_in=logged_in, user=user)


@sahasrahbotapi.route('/presets/me', methods=['GET'])
@requires_authorization
async def my_presets():
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    return redirect(f"/presets/manage/{ns_current_user.name}")


@sahasrahbotapi.route('/presets/create', methods=['GET'])
@requires_authorization
async def new_preset():
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    return await render_template('preset_new.html', logged_in=True, user=user, ns_current_user=ns_current_user, randomizers=generator.PRESET_CLASS_MAPPING.keys())


@sahasrahbotapi.route('/presets/create', methods=['POST'])
@requires_authorization
async def new_preset_submit():
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    if not re.match("^[a-zA-Z0-9_]*$", payload['preset_name']):
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized", message="Invalid preset name provided.")

    preset_data, _ = await models.Presets.update_or_create(
        preset_name=payload['preset_name'],
        randomizer=payload['randomizer'],
        namespace=ns_current_user,
        defaults={
            'content': request_files['presetfile'].read().decode()
        }
    )

    return redirect(f"/presets/manage/{ns_current_user.name}/{preset_data.randomizer}/{preset_data.preset_name}")


@sahasrahbotapi.route('/presets/manage/<string:namespace>', methods=['GET'])
# @requires_authorization
async def presets_for_namespace(namespace):
    try:
        user = await discord.fetch_user()
        logged_in = True
        ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
        is_owner = ns_current_user.name == namespace
    except Unauthorized:
        user = None
        logged_in = False
        ns_current_user = None
        is_owner = False

    ns_data = await models.PresetNamespaces.get(name=namespace)
    presets = await models.Presets.filter(namespace__name=namespace)

    return await render_template('preset_namespace.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data, presets=presets)


@sahasrahbotapi.route('/presets/manage/<string:namespace>/<string:randomizer>', methods=['GET'])
# @requires_authorization
async def presets_for_namespace_randomizer(namespace, randomizer):
    try:
        user = await discord.fetch_user()
        logged_in = True
        ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
        is_owner = ns_current_user.name == namespace
    except Unauthorized:
        user = None
        logged_in = False
        ns_current_user = None
        is_owner = False

    ns_data = await models.PresetNamespaces.get(name=namespace)
    presets = await models.Presets.filter(randomizer=randomizer, namespace__name=namespace).only('id', 'preset_name', 'randomizer')

    return await render_template('preset_namespace.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data, presets=presets)


@sahasrahbotapi.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def get_preset(namespace, randomizer, preset):
    try:
        user = await discord.fetch_user()
        logged_in = True
        ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
        is_owner = ns_current_user.name == namespace
    except Unauthorized:
        user = None
        logged_in = False
        ns_current_user = None
        is_owner = False

    ns_data = await models.PresetNamespaces.get(name=namespace)
    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await render_template('preset_view.html', logged_in=logged_in, user=user, is_owner=is_owner, ns_data=ns_data, preset_data=preset_data)


@sahasrahbotapi.route('/presets/download/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def download_preset(namespace, randomizer, preset):
    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await send_file(
        BytesIO(preset_data.content.encode()),
        mimetype="application/octet-stream",
        attachment_filename=f"{namespace}-{preset}.yaml",
        as_attachment=True
    )


@sahasrahbotapi.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['POST'])
@requires_authorization
async def update_preset(namespace, randomizer, preset):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)
    is_owner = ns_current_user.name == namespace

    if not is_owner:
        return await render_template('error.html', logged_in=True, user=user, title="Unauthorized", message="You are not the owner of this preset.")

    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    if 'delete' in payload:
        await preset_data.delete()
        return redirect(f"/presets/manage/{namespace}")

    preset_data.content = request_files['presetfile'].read().decode()

    await preset_data.save()

    return redirect(f"/presets/manage/{namespace}/{randomizer}/{preset}")


@sahasrahbotapi.route('/sgl22', methods=["GET"])
async def sgl22_dashboard():
    try:
        user = await discord.fetch_user()
        logged_in = True
    except Unauthorized:
        user = None
        logged_in = False

    return await render_template("sgl22_dashboard.html", logged_in=logged_in, user=user)

@sahasrahbotapi.route('/sgl22/generate/alttpr', methods=["GET"])
async def sgl22_generate_alttpr():
    preset = "sgl2022"
    seed = await generator.ALTTPRPreset(preset).generate(allow_quickswap=True, tournament=True, hints=False, spoilers="off")
    return redirect(seed.url)

@sahasrahbotapi.route('/sgl22/generate/ootr')
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
    return redirect(f"https://ootrandomizer.com/seed/get?id={seed['id']}")

# @sahasrahbotapi.route('/presets/<str:namespace>', methods=['POST'])
# @requires_authorization
# async def update_namespace():
#     user = await discord.fetch_user()
#     namespace = await generator.create_or_retrieve_namespace(user.id, user.name)


@sahasrahbotapi.route('/robots.txt', methods=['GET'])
async def robots():
    return 'User-agent: *\nDisallow: /\n'

# @sahasrahbotapi.errorhandler(400)
# def bad_request(e):
#     return jsonify(success=False, error=repr(e))

# @sahasrahbotapi.errorhandler(404)
# def not_found(e):
#     return jsonify(success=False, error=repr(e))

# @sahasrahbotapi.errorhandler(500)
# def something_bad_happened(e):
#     return jsonify(success=False, error=repr(e))

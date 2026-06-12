import re
from io import BytesIO

from quart import Blueprint, redirect, request, send_file, jsonify
from alttprbot_api.oauth_client import Unauthorized, requires_authorization
from tortoise.query_utils import Prefetch

from alttprbot import models
from alttprbot.alttprgen import generator
from alttprbot_api.api import discord

presets_blueprint = Blueprint('presets', __name__)


@presets_blueprint.route('/presets/me', methods=['GET'])
@requires_authorization
async def my_presets():
    user = await discord.fetch_user()
    ns_current_user = await generator.create_or_retrieve_namespace(user.id, user.name)

    return redirect(f"/presets/manage/{ns_current_user.name}")


@presets_blueprint.route('/presets/<string:namespace>/create', methods=['POST'])
@requires_authorization
async def new_preset_submit(namespace):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    if not generator.is_namespace_owner(user, ns_data):
        return jsonify({'error': 'You are not authorized to create presets in this namespace.'}), 403

    preset_name = payload.get('preset_name', '')
    if not re.match("^[a-zA-Z0-9_]*$", preset_name):
        return jsonify({'error': 'Invalid preset name provided.'}), 400

    if 'presetfile' not in request_files:
        return jsonify({'error': 'A preset file is required.'}), 400

    preset_data, _ = await models.Presets.update_or_create(
        preset_name=preset_name,
        randomizer=payload['randomizer'],
        namespace=ns_data,
        defaults={
            'content': request_files['presetfile'].read().decode()
        }
    )

    return jsonify({
        'success': True,
        'redirect': f"/presets/manage/{ns_data.name}/{preset_data.randomizer}/{preset_data.preset_name}",
    })


@presets_blueprint.route('/presets/manage/<string:namespace>/data.json', methods=['GET'])
async def presets_for_namespace_json(namespace):
    ns_data = await models.PresetNamespaces.get_or_none(name=namespace)
    if ns_data is None:
        return jsonify({'error': 'Namespace not found.'}), 404
    await ns_data.fetch_related('collaborators')

    try:
        user = await discord.fetch_user()
        is_owner = generator.is_namespace_owner(user, ns_data)
    except Unauthorized:
        is_owner = False

    randomizer = request.args.get('randomizer')
    query = models.Presets.filter(namespace__name=namespace)
    if randomizer:
        query = query.filter(randomizer=randomizer)
    presets = await query.only('id', 'preset_name', 'randomizer')

    return jsonify({
        'namespace': ns_data.name,
        'is_owner': is_owner,
        'randomizers': list(generator.PRESET_CLASS_MAPPING.keys()),
        'randomizer': randomizer,
        'presets': [
            {'id': p.id, 'preset_name': p.preset_name, 'randomizer': p.randomizer}
            for p in presets
        ],
    })


@presets_blueprint.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>/data.json',
                         methods=['GET'])
async def get_preset_json(namespace, randomizer, preset):
    ns_data = await models.PresetNamespaces.get_or_none(name=namespace)
    if ns_data is None:
        return jsonify({'error': 'Namespace not found.'}), 404
    await ns_data.fetch_related('collaborators')

    try:
        user = await discord.fetch_user()
        is_owner = generator.is_namespace_owner(user, ns_data)
    except Unauthorized:
        is_owner = False

    preset_data = await models.Presets.get_or_none(
        preset_name=preset, randomizer=randomizer, namespace__name=namespace)
    if preset_data is None:
        return jsonify({'error': 'Preset not found.'}), 404

    return jsonify({
        'namespace': ns_data.name,
        'is_owner': is_owner,
        'preset': {
            'preset_name': preset_data.preset_name,
            'randomizer': preset_data.randomizer,
            'content': preset_data.content,
        },
        'download_url': f"/presets/download/{namespace}/{randomizer}/{preset}",
    })


@presets_blueprint.route('/presets/download/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def download_preset(namespace, randomizer, preset):
    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    return await send_file(
        BytesIO(preset_data.content.encode()),
        mimetype="application/octet-stream",
        attachment_filename=f"{namespace}-{preset}.yaml",
        as_attachment=True
    )


@presets_blueprint.route('/presets/manage/<string:namespace>/<string:randomizer>/<string:preset>', methods=['POST'])
@requires_authorization
async def update_preset(namespace, randomizer, preset):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files
    ns_data = await models.PresetNamespaces.get(name=namespace)
    await ns_data.fetch_related('collaborators')

    if not generator.is_namespace_owner(user, ns_data):
        return jsonify({'error': 'You are not the owner of this preset.'}), 403

    preset_data = await models.Presets.get(preset_name=preset, randomizer=randomizer, namespace__name=namespace)

    if 'delete' in payload:
        await preset_data.delete()
        return jsonify({'success': True, 'redirect': f"/presets/manage/{namespace}"})

    if 'presetfile' not in request_files:
        return jsonify({'error': 'A preset file is required.'}), 400

    content = request_files['presetfile'].read().decode()
    if content == '':
        return jsonify({'error': 'Empty or missing preset file provided.'}), 400

    preset_data.content = content
    await preset_data.save()

    return jsonify({
        'success': True,
        'redirect': f"/presets/manage/{namespace}/{randomizer}/{preset}",
    })


@presets_blueprint.route('/presets/api/<string:randomizer>/list', methods=['GET'])
async def api_get_presets(randomizer):
    # this is terrible
    generators = {
        'alttpr': generator.ALTTPRPreset,
        'smz3': generator.SMZ3Preset,
        'sm': generator.SMPreset,
        'alttprmystery': generator.ALTTPRMystery,
        'ctjets': generator.CTJetsPreset
    }
    global_presets = await generators[randomizer]().get_presets(namespace=None)
    namespaces = await models.PresetNamespaces.all().prefetch_related(
        Prefetch('presets', queryset=models.Presets.filter(randomizer=randomizer)))

    output = {
        'global': global_presets,
        'namespaces': [
            {
                'name': namespace.name,
                'presets': [
                    n.preset_name for n in namespace.presets
                ]
            } for namespace in namespaces
            if namespace.presets
        ]
    }

    return jsonify(output)


@presets_blueprint.route('/presets/api/<string:randomizer>', methods=['GET'])
async def api_get_preset(randomizer):
    # this is terrible
    preset = request.args.get('preset')
    generators = {
        'alttpr': generator.ALTTPRPreset,
        'smz3': generator.SMZ3Preset,
        'sm': generator.SMPreset,
        'alttprmystery': generator.ALTTPRMystery,
        'ctjets': generator.CTJetsPreset
    }
    try:
        resp = generators[randomizer](preset=preset)
        await resp.fetch()
        return jsonify(
            {
                'preset': preset,
                'randomizer': randomizer,
                'data': resp.preset_data
            }
        )
    except generator.PresetNotFoundException:
        return jsonify(
            {}
        )

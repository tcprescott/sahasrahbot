from io import BytesIO

from quart import Blueprint, redirect, request, send_file, jsonify
from alttprbot.presentation.api.oauth_client import Unauthorized, requires_authorization

from alttprbot.services import PresetService
from alttprbot.services.seedgen import generator
from alttprbot.presentation.api.api import discord

presets_blueprint = Blueprint('presets', __name__)


@presets_blueprint.route('/presets/me', methods=['GET'])
@requires_authorization
async def my_presets():
    user = await discord.fetch_user()
    ns_current_user = await PresetService().create_or_retrieve_namespace(user.id, user.name)

    return redirect(f"/presets/manage/{ns_current_user.name}")


@presets_blueprint.route('/presets/<string:namespace>/create', methods=['POST'])
@requires_authorization
async def new_preset_submit(namespace):
    user = await discord.fetch_user()
    payload = await request.form
    request_files = await request.files

    service = PresetService()
    ns_data = await service.get_namespace(namespace)
    if ns_data is None:
        return jsonify({'error': 'Namespace not found.'}), 404

    if not PresetService.is_namespace_owner(user.id, ns_data):
        return jsonify({'error': 'You are not authorized to create presets in this namespace.'}), 403

    preset_name = payload.get('preset_name', '')
    if not PresetService.is_valid_preset_name(preset_name):
        return jsonify({'error': 'Invalid preset name provided.'}), 400

    if 'presetfile' not in request_files:
        return jsonify({'error': 'A preset file is required.'}), 400

    preset_data = await service.save_preset(
        namespace=ns_data,
        randomizer=payload['randomizer'],
        preset_name=preset_name,
        content=request_files['presetfile'].read().decode(),
    )

    return jsonify({
        'success': True,
        'redirect': f"/presets/manage/{ns_data.name}/{preset_data.randomizer}/{preset_data.preset_name}",
    })


@presets_blueprint.route('/presets/manage/<string:namespace>/data.json', methods=['GET'])
async def presets_for_namespace_json(namespace):
    service = PresetService()
    ns_data = await service.get_namespace(namespace)
    if ns_data is None:
        return jsonify({'error': 'Namespace not found.'}), 404

    try:
        user = await discord.fetch_user()
        is_owner = PresetService.is_namespace_owner(user.id, ns_data)
    except Unauthorized:
        is_owner = False

    randomizer = request.args.get('randomizer')
    presets = await service.list_presets(namespace, randomizer=randomizer)

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
    service = PresetService()
    ns_data = await service.get_namespace(namespace)
    if ns_data is None:
        return jsonify({'error': 'Namespace not found.'}), 404

    try:
        user = await discord.fetch_user()
        is_owner = PresetService.is_namespace_owner(user.id, ns_data)
    except Unauthorized:
        is_owner = False

    preset_data = await service.get_preset(namespace, randomizer, preset)
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
    preset_data = await PresetService().get_preset(namespace, randomizer, preset)
    if preset_data is None:
        return jsonify({'error': 'Preset not found.'}), 404

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

    service = PresetService()
    ns_data = await service.get_namespace(namespace)
    if ns_data is None:
        return jsonify({'error': 'Namespace not found.'}), 404

    if not PresetService.is_namespace_owner(user.id, ns_data):
        return jsonify({'error': 'You are not the owner of this preset.'}), 403

    preset_data = await service.get_preset(namespace, randomizer, preset)
    if preset_data is None:
        return jsonify({'error': 'Preset not found.'}), 404

    if 'delete' in payload:
        await service.delete_preset(preset_data)
        return jsonify({'success': True, 'redirect': f"/presets/manage/{namespace}"})

    if 'presetfile' not in request_files:
        return jsonify({'error': 'A preset file is required.'}), 400

    content = request_files['presetfile'].read().decode()
    if content == '':
        return jsonify({'error': 'Empty or missing preset file provided.'}), 400

    await service.save_preset(
        namespace=ns_data,
        randomizer=randomizer,
        preset_name=preset,
        content=content,
    )

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
    namespaces = await PresetService().list_namespaces_with_presets(randomizer)

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

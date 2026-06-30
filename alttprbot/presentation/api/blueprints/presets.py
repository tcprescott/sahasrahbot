from io import BytesIO

from quart import Blueprint, request, send_file, jsonify

from alttprbot.services import PresetService
from alttprbot.services.seedgen import generator

presets_blueprint = Blueprint('presets_api', __name__)


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

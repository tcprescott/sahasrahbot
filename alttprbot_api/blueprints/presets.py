"""Preset downloads and the public preset JSON endpoints other tools read.

The preset pages themselves are the React app's (web/src/presets/), over /api/v1.
"""
from io import BytesIO

from quart import Blueprint, abort, request, send_file, jsonify
from alttprbot.alttprgen import generator
from alttprbot.services import presets

presets_blueprint = Blueprint('presets', __name__)


@presets_blueprint.route('/presets/download/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def download_preset(namespace, randomizer, preset):
    content = await presets.preset_content(namespace, randomizer, preset)
    if content is None:
        abort(404, description="That preset doesn't exist.")

    return await send_file(
        BytesIO(content.encode()),
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
    output = {
        'global': global_presets,
        'namespaces': await presets.namespace_preset_names(randomizer),
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
                'data': resp.raw
            }
        )
    except generator.PresetNotFoundException:
        return jsonify(
            {}
        )
    except generator.InvalidPresetError as err:
        return jsonify({'error': str(err)}), 422

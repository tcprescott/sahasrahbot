"""Preset downloads and the public preset JSON endpoints other tools read.

The preset pages themselves are the React app's (web/src/presets/), over /api/v1.
"""
from io import BytesIO

from quart import Blueprint, abort, request, send_file, jsonify
from tortoise.query_utils import Prefetch

from alttprbot import models
from alttprbot.alttprgen import generator

presets_blueprint = Blueprint('presets', __name__)


@presets_blueprint.route('/presets/download/<string:namespace>/<string:randomizer>/<string:preset>', methods=['GET'])
async def download_preset(namespace, randomizer, preset):
    preset_data = await models.Presets.get_or_none(preset_name=preset, randomizer=randomizer,
                                                   namespace__name=namespace)
    if preset_data is None:
        abort(404, description="That preset doesn't exist.")

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
                'data': resp.raw
            }
        )
    except generator.PresetNotFoundException:
        return jsonify(
            {}
        )

from quart import Blueprint, jsonify, request

from alttprbot.alttprgen import generator

from alttprbot import models

settingsgen_blueprint = Blueprint('settingsgen', __name__)

@settingsgen_blueprint.route('/api/settingsgen/mystery', methods=['POST'])
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


@settingsgen_blueprint.route('/api/settingsgen/mystery', methods=['GET'])
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


@settingsgen_blueprint.route('/api/settingsgen/mystery/<string:weightset>', methods=['GET'])
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

@settingsgen_blueprint.route('/api/settingsgen/namespaces', methods=['GET'])
async def get_namespaces():
    namespaces = await models.PresetNamespaces.all().values('name')
    return jsonify([n['name'] for n in namespaces])

@settingsgen_blueprint.route('/api/settingsgen/presets/<string:randomizer>', methods=['GET'])
async def get_presets(randomizer):
    namespace = request.args.get('namespace', None)

    generators = {
        'alttpr': generator.ALTTPRPreset,
        'smz3': generator.SMZ3Preset,
        'sm': generator.SMPreset,
        'alttprmystery': generator.ALTTPRMystery,
        'ctjets': generator.CTJetsPreset
    }
    presets = await generators[randomizer]().get_presets(namespace=namespace)

    return jsonify(presets)
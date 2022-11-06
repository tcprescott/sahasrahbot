from quart import Blueprint, jsonify, request

from alttprbot.alttprgen import generator

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
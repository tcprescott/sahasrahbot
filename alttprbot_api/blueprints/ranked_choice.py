from quart import Blueprint

ranked_choice_blueprint = Blueprint('ranked_choice', __name__)

@ranked_choice_blueprint.route('/ranked_choice', methods=['GET'])
async def get_ranked_choice():
    return 'Hello, World!'
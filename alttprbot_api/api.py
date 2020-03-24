from quart import Quart, abort, jsonify, request

from pyz3r.mystery import generate_random_settings
from alttprbot.alttprgen.mystery import get_weights
from alttprbot.util import http
from alttprbot_discord.bot import discordbot
from alttprbot_srl import nick_verifier

sahasrahbotapi = Quart(__name__)

@sahasrahbotapi.route('/srl/verification/<string:nick>/<int:key>', methods=['GET'])
async def verify_srl_user(nick, key):
    result = await nick_verifier.verify_nick(nick, key)
    if result:
        user = discordbot.get_user(result['discord_user_id'])
        await user.send("We have successfully verified your SRL nick!")
        return "We have successfully verified your SRL nick!"
    else:
        return "Unable to verify your SRL nick.  Please request another key and try again.  Contact Synack if this persists."

@sahasrahbotapi.route('/api/settingsgen/mystery', methods=['POST'])
async def mysterygen():
    weights = await request.get_json()
    settings, customizer = generate_random_settings(weights=weights, spoilers="mystery")
    return jsonify(
        settings=settings,
        customizer=customizer,
        endpoint='/api/customizer' if customizer else '/api/randomizer'
    )

@sahasrahbotapi.route('/api/settingsgen/mystery/<string:weightset>', methods=['GET'])
async def mysterygenwithweights(weightset):
    weights = await get_weights(weightset)
    settings, customizer = generate_random_settings(weights=weights, spoilers="mystery")
    return jsonify(
        settings=settings,
        customizer=customizer,
        endpoint='/api/customizer' if customizer else '/api/randomizer'
    )

@sahasrahbotapi.errorhandler(400)
def bad_request(e):
    return jsonify(success=False, error=repr(e))

@sahasrahbotapi.errorhandler(404)
def not_found(e):
    return jsonify(success=False, error=repr(e))

@sahasrahbotapi.errorhandler(500)
def something_bad_happened(e):
    return jsonify(success=False, error=repr(e))

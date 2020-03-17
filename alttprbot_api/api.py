from quart import Quart, abort, jsonify, request
from alttprbot_srl import nick_verifier
from alttprbot_discord.bot import discordbot

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

@sahasrahbotapi.errorhandler(400)
def bad_request(e):
    return jsonify(success=False, name=e.name, description=e.description, status_code=e.status_code)

@sahasrahbotapi.errorhandler(404)
def not_found(e):
    return jsonify(success=False, name=e.name, description=e.description, status_code=e.status_code)

@sahasrahbotapi.errorhandler(500)
def something_bad_happened(e):
    return jsonify(success=False, name=e.name, description=e.description, status_code=e.status_code)
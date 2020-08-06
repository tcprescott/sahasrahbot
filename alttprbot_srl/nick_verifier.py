import random

from alttprbot.database import srl_nick_verification, srlnick
from alttprbot_srl.bot import srlbot


async def send_key(discord_user_id, srl_nick):
    nickinfo = await get_irc_user(srl_nick)

    if nickinfo is None:
        return False

    key = random.randint(0, 999999999999999999)
    await srl_nick_verification.insert_verification(srl_nick, key, discord_user_id)
    await srlbot.message(
        target=srl_nick,
        message=f"Hi!  To verify yourself as the owner of this SRL account, please visit: https://sahasrahbotapi.synack.live/srl/verification/{srl_nick}/{key}"
    )
    return True


async def get_irc_user(srl_nick):
    info = await srlbot.whois(srl_nick)
    return info if info['identified'] else None


async def verify_nick(srl_nick, key):
    verif = await srl_nick_verification.get_verification(srl_nick, key)
    await srl_nick_verification.delete_verification(srl_nick)

    if verif:
        await srlnick.insert_srl_nick(
            discord_user_id=verif['discord_user_id'],
            srl_nick=srl_nick,
            srl_verified=1
        )
        return verif
    else:
        return False

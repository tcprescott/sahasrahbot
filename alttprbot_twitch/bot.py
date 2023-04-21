from twitchAPI.twitch import Twitch
import settings

twitchapi = Twitch(settings.TWITCH_CLIENT_ID, settings.TWITCH_CLIENT_SECRET)
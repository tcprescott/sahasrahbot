import math

import aiocache
from twitchio.ext import commands

from alttprbot.database import gtbk
from alttprbot.util import speedgaming


async def whitelisted(ctx):
    if ctx.author.name == 'the_synack':
        return True

    if ctx.author.name == ctx.channel.name:
        return True
    if ctx.author.is_mod:
        return True

    if ctx.channel.name in [
            'alttprandomizer',
            'alttprandomizer2',
            'alttprandomizer3',
            'alttprandomizer4',
            'alttprandomizer5',
            'alttprandomizer6',
            'thealttprleague',
            'thealttprleague2',
            'thealttprleague3',
            'thealttprleague4',
            'speedgaming',
            'speedgaming2',
            'speedgaming3',
            'speedgaming4',
            'speedgaming5',
            'speedgaming6',
            "speedgamingfrancais",
            "speedgamingfrancais2",
            "speedgamingdeutsch",
            "speedgamingespanol",
            'the_synack']:
        whitelist = await get_whitelist_users(['alttpr', 'owg', 'alttprleague', 'alttprfr'])
        if ctx.author.name.lower() in whitelist:
            return True

    channel_whitelist = await gtbk.get_channel_whitelist(ctx.channel.name)
    for user in channel_whitelist:
        if user['twitch_user'].lower() == ctx.author.name.lower():
            return True

    return False

async def is_synack(ctx):
    return ctx.author.name == 'the_synack'

async def is_broadcastor(ctx):
    return ctx.author.name == ctx.channel.name

async def is_mod(ctx):
    return ctx.author.is_mod or ctx.author.name == ctx.channel.name

@commands.core.cog()
class Gtbk():
    def __init__(self, bot):
        self.bot = bot

    async def event_message(self, message):
        # capture GTBK game guesses
        game = await gtbk.get_current_active_game(message.channel.name)
        if game and game['status'] == 'STARTED' and message.content.isdigit():
            await gtbk.insert_guess(channel=message.channel.name, twitch_user=message.author.name, guess=int(message.content))

    @commands.command()
    @commands.check(whitelisted)
    async def start(self, ctx):
        await gtbk.start_game(ctx.channel.name)
        await ctx.send(
            'Get your GTBK guesses in!  The first viewer who guesses closest ' \
            'to the actual key location gets a place on the leaderboard!  ' \
            'Points are scored based on the number of participants in the game.  ' \
            'Only your last guess counts.'
        )

    @commands.command()
    @commands.check(whitelisted)
    async def stop(self, ctx):
        await gtbk.update_game_status(ctx.channel.name, "STOPPED")
        guesses = await gtbk.get_active_game_guesses(ctx.channel.name)
        if guesses:
            points = await calculate_score(ctx.channel.name)
            await ctx.send(f'Guesses have now closed. {points} points will be awarded to the winner. Good luck!')
        else:
            await ctx.send("Game had no guesses.  This game is now completed.")
            await gtbk.update_game_status(ctx.channel.name, "COMPLETED")


    @commands.command(aliases=['key'])
    @commands.check(whitelisted)
    async def bigkey(self, ctx, key: int):
        game = await gtbk.get_current_active_game(ctx.channel.name)
        if not game:
            raise gtbk.GtbkGuessingGameException("This channel does not have an active GTBK game!")

        points = await calculate_score(ctx.channel.name)

        winner = await get_winner(key, ctx.channel.name)
        runnerups = await get_runnerups(key, ctx.channel.name, winner)

        await gtbk.update_score(guess_id=winner['guess_id'], score=points)
        for runnerup in runnerups:
            await gtbk.update_score(guess_id=runnerup['guess_id'], score=5)

        await gtbk.update_game_status(ctx.channel.name, "COMPLETED")

        msg = f"{winner['twitch_user']} was the winner of the Ganon\'s Tower Big Key guessing game. {winner['twitch_user']} guessed {winner['guess']} and the big key was {key} and has thus scored {points} point(s) on the {ctx.channel.name} GTBK leaderboard!"

        if runnerups:
            msg += f"  The player(s) {', '.join([ sub['twitch_user'] for sub in runnerups])} also guessed exactly correct and score 5 bonus points each."

        msg += '  Congratulations! (use $leaderboard to see current leaderboard)'

        await ctx.send(msg)

    @commands.command()
    @commands.check(whitelisted)
    async def status(self, ctx):
        game = await gtbk.get_current_active_game(ctx.channel.name)
        if game:
            await ctx.send(f"GTBK guessing game is in the state of {game['status']}")
        else:
            await ctx.send("GTBK guessing game is inactive.")

    @commands.command()
    async def leaderboard(self, ctx):
        group_mapping = await gtbk.get_channel_group(ctx.channel.name)

        if group_mapping:
            leaderboard = await gtbk.get_group_leaderboard(group_mapping['group'])
        else:
            leaderboard = await gtbk.get_channel_leaderboard(ctx.channel.name)
        msg = f'Current GTBK game leaderboard for {ctx.channel.name}: '
        for row in leaderboard:
            if row['points'] > 0:
                msg += f"{row['twitch_user']} has {row['points']} point(s), "
        await ctx.send(msg)

    @commands.command()
    @commands.check(whitelisted)
    async def whitelist(self, ctx, twitch_user):
        await gtbk.add_channel_whitelist(ctx.channel.name, twitch_user)
        await ctx.send(f"{twitch_user} whitelisted successfully!")

    @commands.command()
    @commands.check(is_synack)
    async def testguesses(self, ctx):
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='randomguy1', guess=1)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='someotherperson', guess=1)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='testuser3', guess=8)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='fakeguy4', guess=1)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='lulimfake5', guess=6)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='somethingelse6', guess=20)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='abddf8', guess=12)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='nmbnmb9', guess=7)
        await gtbk.insert_guess(channel=ctx.channel.name, twitch_user='yuiyuiy10', guess=22)

    @commands.command()
    @commands.check(is_synack)
    async def clearcache(self, ctx):
        await aiocache.SimpleMemoryCache().clear(namespace="gtbk_status")
        await aiocache.SimpleMemoryCache().clear(namespace="gtbk_whitelist")
        await ctx.send('cleared gtbk status cache')

async def calculate_score(channel):
    guessdict = await gtbk.get_active_game_guesses(channel)
    cnt = len(guessdict)
    if cnt <= 25:
        score = math.ceil((cnt - 1)/2) + 5
    else:
        score = math.ceil(17 + ((cnt-26) / 25) * 10)

    return score

async def get_winner(key: int, channel):
    guessdict = await gtbk.get_active_game_guesses(channel)
    value = min(guessdict, key=lambda kv: abs(kv['guess'] - key))
    return value

async def get_runnerups(key: int, channel, winner):
    guessdict = await gtbk.get_active_game_guesses(channel)
    runners_up = []
    for guess in guessdict:
        if guess['guess'] == key and not guess['twitch_user'] == winner['twitch_user']:
            runners_up.append(guess)
    return runners_up

@aiocache.cached(ttl=900, cache=aiocache.SimpleMemoryCache, namespace="gtbk_whitelist")
async def get_whitelist_users(sluglist):
    whitelist = []
    for slug in sluglist:
        schedule = await speedgaming.get_upcoming_episodes_by_event(slug)
        if schedule:
            for episode in schedule:
                whitelist.extend(get_approved_crew(episode['broadcasters']))
                whitelist.extend(get_approved_crew(episode['commentators']))
                whitelist.extend(get_approved_crew(episode['trackers']))

    return(list(set(whitelist)))

def get_approved_crew(crewlist):
    approved_crew = []
    for crew in crewlist:
        if crew['approved']:
            if crew['publicStream'] == "" or crew['publicStream'] is None:
                approved_crew.append(crew['displayName'].lower())
            else:
                approved_crew.append(crew['publicStream'].lower())
    return(approved_crew)

def setup(bot):
    bot.add_cog(Gtbk(bot))

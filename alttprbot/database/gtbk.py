import aiocache

from alttprbot.exceptions import SahasrahBotException
from ..util import orm

CACHE = aiocache.Cache(aiocache.SimpleMemoryCache)

class GtbkGuessingGameException(SahasrahBotException):
    pass

async def get_current_active_game(channel):
    if await CACHE.exists(f'{channel}_gtbk_active_game'):
        results = await CACHE.get(f'{channel}_gtbk_active_game')
        return results[0] if len(results) > 0 else None

    results = await orm.select(
        'SELECT * from gtbk_games where channel=%s and status<>"COMPLETED";',
        [channel]
    )
    await CACHE.set(f'{channel}_gtbk_active_game', results)
    return results[0] if len(results) > 0 else None

async def start_game(channel):
    result = await get_current_active_game(channel)
    if not result:
        await orm.execute(
            'INSERT INTO gtbk_games(channel, status) VALUES (%s, %s)',
            [channel, "STARTED"]
        )
        await CACHE.delete(f'{channel}_gtbk_active_game')
    else:
        raise GtbkGuessingGameException("This channel already has an active GTBK game!")

async def insert_guess(channel, twitch_user, guess):
    result = await get_current_active_game(channel)
    if result:
        await orm.execute(
            'INSERT INTO gtbk_guesses(game_id, twitch_user, guess) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE guess = %s, `timestamp` = CURRENT_TIMESTAMP;',
            [result['game_id'], twitch_user, guess, guess]
        )
    else:
        raise GtbkGuessingGameException("This channel does not have an active GTBK game!")

async def update_game_status(channel, status):
    result = await get_current_active_game(channel)
    if result:
        await orm.execute(
            'UPDATE gtbk_games SET status=%s where game_id=%s',
            [status, result['game_id']]
        )
        await CACHE.delete(f'{channel}_gtbk_active_game')
    else:
        raise GtbkGuessingGameException("This channel does not have an active GTBK game!")

async def get_active_game_guesses(channel):
    result = await get_current_active_game(channel)
    if result:
        results = await orm.select(
            'SELECT * from gtbk_guesses where game_id=%s order by timestamp asc, guess_id asc;',
            [result['game_id']]
        )
        return results
    else:
        raise GtbkGuessingGameException("This channel does not have an active GTBK game!")

async def update_score(guess_id, score):
    await orm.execute(
        'UPDATE gtbk_guesses SET score=%s where guess_id=%s',
        [score, guess_id]
    )

async def get_channel_group(channel):
    results = await orm.select(
        'SELECT * from twitch_channels where channel=%s;',
        [channel]
    )
    return results[0] if len(results) > 0 else None

async def get_group_leaderboard(group):
    sql = 'SELECT guess.twitch_user,tc.group,SUM(score) as "points" ' \
            'FROM gtbk_guesses guess ' \
            'LEFT JOIN gtbk_games games ON games.game_id = guess.game_id ' \
            'LEFT JOIN twitch_channels tc ON games.channel = tc.channel ' \
            'WHERE tc.group=%s ' \
            'GROUP BY guess.twitch_user, tc.group ' \
            'ORDER BY points desc ' \
            'LIMIT 10;'
    return await orm.select(sql, [group])

async def get_channel_leaderboard(channel):
    sql = 'SELECT guess.twitch_user,games.channel,SUM(score) as "points" ' \
            'FROM gtbk_guesses guess ' \
            'LEFT JOIN gtbk_games games ON games.game_id = guess.game_id ' \
            'WHERE games.channel=%s ' \
            'GROUP BY guess.twitch_user, games.channel ' \
            'ORDER BY points desc ' \
            'LIMIT 10;'
    return await orm.select(sql, [channel])

async def get_channel_whitelist(channel):
    sql = 'SELECT * FROM gtbk_whitelist where channel=%s;'
    return await orm.select(sql, [channel])

async def add_channel_whitelist(channel, twitch_user):
    sql = 'INSERT INTO gtbk_whitelist(channel, twitch_user) VALUES (%s,%s);'
    await orm.execute(sql, [channel, twitch_user])

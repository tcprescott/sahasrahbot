"""Triforce texts: three short lines players submit to a pool, shown in-game once a
pool moderator approves them (``alttprbot/util/triforce_text.py`` picks them).

A pool is just a name. Its moderators are the ``TriforceTextsConfig`` rows with
``key_name='moderator'`` (one Discord user id per row).
"""

import re

from alttprbot import models
from alttprbot.exceptions import InvalidInputError, NotFoundError, PermissionDeniedError

MAX_LINE = 19
# The hyphen is last on purpose: the old form had it between "," and "…", which made a
# range that let through almost every character (é, ß, emoji are all in it).
LINE = re.compile(r"^[A-Za-z0-9 ?!,….~～''↑↓→←あいうえおやゆよかきくけこわをんさしすせそがぎぐたちつてとげござなにぬねのじずぜはひふへほぞだぢまみむめもづでどらりるれろばびぶべぼぱぴぷぺぽゃゅょっぁぃぅぇぉアイウエオヤユヨカキクケコワヲンサシスセソガギグタチツテトゲゴザナニヌネノジズゼハヒフヘホゾダマミムメモヅデドラリルレロバビブベボパピプペポャュョッァィゥェォ\-]{0,19}$")
LINE_NAMES = ('first', 'second', 'third')
STATUSES = ('pending', 'approved', 'rejected', 'all')


async def moderators(pool_name: str) -> list[int]:
    rows = await models.TriforceTextsConfig.filter(pool_name=pool_name, key_name='moderator')
    return [int(row.value) for row in rows]


async def is_moderator(pool_name: str, user_id: int) -> bool:
    return user_id in await moderators(pool_name)


async def moderated_pools(user_id: int) -> list[str]:
    rows = await models.TriforceTextsConfig.filter(key_name='moderator', value=str(user_id)).order_by('pool_name')
    return list(dict.fromkeys(row.pool_name for row in rows))


def _status(approved) -> str:
    return 'pending' if approved is None else 'approved' if approved else 'rejected'


def _text(row: models.TriforceTexts, with_author: bool) -> dict:
    out = {
        'id': row.id,
        'lines': row.text.split('\n'),
        'status': _status(row.approved),
        'submitted': row.timestamp,
    }
    if with_author:
        out['author'] = row.author
    return out


async def pool(pool_name: str, user_id: int) -> dict:
    """What a player sees: the rules, their own submissions, and whether they moderate."""
    mine = await models.TriforceTexts.filter(pool_name=pool_name, discord_user_id=user_id).order_by('-id')
    return {
        'pool': pool_name,
        'max_line_length': MAX_LINE,
        'is_moderator': await is_moderator(pool_name, user_id),
        'mine': [_text(row, with_author=False) for row in mine],
    }


async def submit(pool_name: str, user_id: int, author: str, lines: list[str]) -> dict:
    if len(lines) != 3:
        raise InvalidInputError("A triforce text is exactly three lines (they can be blank).")
    for name, line in zip(LINE_NAMES, lines):
        if not LINE.match(line):
            raise InvalidInputError(
                f"The {name} line has a character the game can't show, or is longer than {MAX_LINE}.")
    if not any(line.strip() for line in lines):
        raise InvalidInputError("Write something on at least one line.")

    row = await models.TriforceTexts.create(
        pool_name=pool_name, text='\n'.join(lines), discord_user_id=user_id, author=author)
    return _text(row, with_author=False)


async def list_for_moderation(pool_name: str, user_id: int, status: str = 'pending') -> list[dict]:
    if not await is_moderator(pool_name, user_id):
        raise PermissionDeniedError("Only this pool's moderators can review its texts.")
    if status not in STATUSES:
        raise InvalidInputError(f"Status must be one of {', '.join(STATUSES)}.")
    query = models.TriforceTexts.filter(pool_name=pool_name)
    if status == 'pending':
        query = query.filter(approved__isnull=True)
    elif status != 'all':
        query = query.filter(approved=status == 'approved')
    return [_text(row, with_author=True) for row in await query.order_by('id')]


async def moderate(pool_name: str, text_id: int, user_id: int, approved: bool) -> dict:
    if not await is_moderator(pool_name, user_id):
        raise PermissionDeniedError("Only this pool's moderators can review its texts.")
    row = await models.TriforceTexts.get_or_none(id=text_id, pool_name=pool_name)
    if row is None:
        raise NotFoundError("That text isn't in this pool.")
    row.approved = approved
    await row.save()
    return _text(row, with_author=True)

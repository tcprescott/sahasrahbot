from ..util import orm


async def get_tournament(slug: str, schedule_type: str = 'sg'):
    results = await orm.select(
        'SELECT * from tournaments where schedule_type=%s and slug = %s;',
        [schedule_type, slug]
    )
    return results[0] if results else None

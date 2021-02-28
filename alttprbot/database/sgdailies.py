from ..util import orm


async def get_daily(slug: str):
    results = await orm.select(
        'SELECT * from sgdailies where slug = %s;',
        [slug]
    )
    return results[0] if results else None


async def get_active_dailies():
    results = await orm.select(
        'SELECT * from sgdailies where active=1;',
    )
    return results

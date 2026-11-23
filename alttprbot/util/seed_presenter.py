"""Where the tournament engine gets seed embeds from.

Core code (``alttprbot/``) must not import a front end, but the tournament
engine posts seed embeds. The Discord layer registers its builders here at
startup (``sahasrahbot.py``), and core calls ``seed_embed`` /
``seed_tournament_embed`` without knowing about Discord.
"""

_embed_builder = None
_tournament_embed_builder = None


def register(embed_builder, tournament_embed_builder):
    """Set the async callables ``(seed, **kwargs) -> embed`` that build seed embeds."""
    global _embed_builder, _tournament_embed_builder
    _embed_builder = embed_builder
    _tournament_embed_builder = tournament_embed_builder


def _require(builder):
    if builder is None:
        raise RuntimeError("No seed embed builder registered; call alttprbot.util.seed_presenter.register() at startup.")
    return builder


async def seed_embed(seed, **kwargs):
    return await _require(_embed_builder)(seed, **kwargs)


async def seed_tournament_embed(seed, **kwargs):
    return await _require(_tournament_embed_builder)(seed, **kwargs)

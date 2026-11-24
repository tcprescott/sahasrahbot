"""/racerverification create_or_update and /rankedchoice create are for server
admins and the bot's owner only. They used to compare the un-awaited
``bot.is_owner()`` coroutine with False, which never matched, so anyone could
run them (and, through racer verification, have the bot hand out any role).
"""

from types import SimpleNamespace
from unittest import mock

import pytest

from alttprbot.services import racer_verification as verification
from alttprbot.services import ranked_choice
from alttprbot_discord.cogs import racer_verification as rv_cog
from alttprbot_discord.cogs import rankedchoice as rc_cog


def interaction(administrator):
    return SimpleNamespace(
        user=SimpleNamespace(id=7, guild_permissions=SimpleNamespace(administrator=administrator)),
        guild=SimpleNamespace(id=1),
        channel=SimpleNamespace(id=300),
        response=SimpleNamespace(send_message=mock.AsyncMock(), defer=mock.AsyncMock()),
    )


def bot(owner):
    return SimpleNamespace(is_owner=mock.AsyncMock(return_value=owner))


COMMANDS = [
    (rv_cog.RacerVerification, "create_or_update", verification, "create_or_update",
     lambda: (SimpleNamespace(id=501),)),
    (rc_cog.RankedChoice, "create", ranked_choice, "create_election", lambda: ("Title", "A,B")),
]


@pytest.mark.parametrize("cog_class, command, service, function, args", COMMANDS)
async def test_refuses_a_member_who_is_neither_admin_nor_owner(monkeypatch, cog_class, command, service, function, args):
    called = mock.AsyncMock()
    monkeypatch.setattr(service, function, called)
    cog = cog_class(bot(owner=False))
    it = interaction(administrator=False)

    await getattr(cog, command).callback(cog, it, *args())

    it.response.send_message.assert_awaited_once_with("You are not authorized to use this command.", ephemeral=True)
    called.assert_not_awaited()
    cog.bot.is_owner.assert_awaited_once_with(it.user)


@pytest.mark.parametrize("administrator, owner", [(True, False), (False, True)])
@pytest.mark.parametrize("cog_class, command, service, function, args", COMMANDS)
async def test_lets_an_admin_or_the_owner_through(monkeypatch, cog_class, command, service, function, args,
                                                  administrator, owner):
    # Stop right after the check: the service call raising proves the command got past it.
    monkeypatch.setattr(service, function, mock.AsyncMock(side_effect=RuntimeError("past the check")))
    cog = cog_class(bot(owner=owner))
    it = interaction(administrator=administrator)
    run = getattr(cog, command).callback(cog, it, *args())

    with pytest.raises(RuntimeError, match="past the check"):
        await run

    assert all("not authorized" not in str(c) for c in it.response.send_message.await_args_list)

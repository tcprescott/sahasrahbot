class SahasrahBotException(Exception):
    pass


class NotFoundError(SahasrahBotException):
    """The thing asked for doesn't exist (or isn't open). The web API answers 404."""


class PermissionDeniedError(SahasrahBotException):
    """The user may not do this. The web API answers 403."""


class InvalidInputError(SahasrahBotException):
    """The user sent something we can't accept. The web API answers 400."""


class SeedGenerationError(Exception):
    """An external randomizer or generator failed to produce a seed.

    Deliberately not a SahasrahBotException, so Sentry still reports it.
    """

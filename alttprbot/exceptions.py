class SahasrahBotException(Exception):
    pass


class UnableToLookupUserException(SahasrahBotException):
    """Raised when a tournament player can't be resolved to a Discord/RaceTime user."""
    pass


class HolyImageNotFound(SahasrahBotException):
    """Raised when a requested holy image can't be found in the catalog."""
    pass

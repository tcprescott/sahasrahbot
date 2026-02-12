"""
Normalized exception taxonomy for seed provider reliability contract.

All seed providers must surface failures through these exception types
to ensure consistent error handling across Discord, RaceTime, and API surfaces.
"""

from typing import Optional
from alttprbot.exceptions import SahasrahBotException


class SeedProviderError(SahasrahBotException):
    """Base exception for all seed provider errors."""
    
    def __init__(
        self,
        message: str,
        provider: str,
        operation: str,
        attempts: int = 1,
        status_code: Optional[int] = None,
        provider_message: Optional[str] = None
    ):
        super().__init__(message)
        self.provider = provider
        self.operation = operation
        self.attempts = attempts
        self.status_code = status_code
        self.provider_message = provider_message or message
    
    def __str__(self):
        return f"{self.provider}: {self.provider_message}"


class SeedProviderTimeoutError(SeedProviderError):
    """Provider request exceeded timeout threshold (60s per attempt)."""
    pass


class SeedProviderUnavailableError(SeedProviderError):
    """Provider is temporarily unavailable (network errors, 5xx responses)."""
    pass


class SeedProviderRateLimitError(SeedProviderError):
    """Provider returned rate limit response (HTTP 429)."""
    pass


class SeedProviderInvalidRequestError(SeedProviderError):
    """Provider rejected request due to invalid input (4xx excluding 429)."""
    pass


class SeedProviderResponseFormatError(SeedProviderError):
    """Provider response could not be parsed or had unexpected structure."""
    pass

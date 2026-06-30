"""Centralized authorization package (the Policy Decision Point).

``AuthorizationService`` owns the domain authorization decisions; ``AuthSubject``
is the normalized, surface-agnostic principal that presentation builds and passes
in. See :mod:`alttprbot.services.authorization.service`.
"""

from alttprbot.services.authorization.service import AuthorizationService
from alttprbot.services.authorization.subject import AuthSubject

__all__ = ["AuthorizationService", "AuthSubject"]

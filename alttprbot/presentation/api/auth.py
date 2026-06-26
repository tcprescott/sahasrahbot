####################
# Authorization
####################
from functools import wraps

from quart import request
from quart.wrappers import Response

from alttprbot.services import AuthorizationService


def authorized_key(auth_key_type):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth_key = request.headers.get('Authorization')
            if auth_key is None:
                return Response(status=401)

            if not await AuthorizationService().is_api_authorized(auth_key, auth_key_type):
                return Response(status=401)

            return await func(*args, **kwargs)

        return wrapper

    return decorator

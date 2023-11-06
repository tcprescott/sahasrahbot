####################
# Authorization
####################
from functools import wraps

from quart import request
from quart.wrappers import Response

from alttprbot import models


def authorized_key(auth_key_type):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            auth_key = request.headers.get('Authorization')
            if auth_key is None:
                return Response(status=401)

            access = await models.AuthorizationKeyPermissions.get_or_none(auth_key__key=auth_key, type=auth_key_type)
            if access is None:
                return Response(status=401)

            return await func(*args, **kwargs)
        return wrapper
    return decorator

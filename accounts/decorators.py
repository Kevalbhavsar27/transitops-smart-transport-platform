from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """
    Allow access only to users whose role is included in allowed_roles.

    Superusers are always allowed.
    """

    def decorator(view_function):
        @login_required
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if user.is_superuser or user.role in allowed_roles:
                return view_function(request, *args, **kwargs)

            raise PermissionDenied(
                "You do not have permission to access this page."
            )

        return wrapper

    return decorator
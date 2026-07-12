from functools import wraps

from rest_framework.exceptions import NotAuthenticated, PermissionDenied


def api_role_required(*allowed_roles):
    """
    Role decorator for DRF function-based API views.

    ViewSets should normally use permission classes instead.
    """

    def decorator(view_function):
        @wraps(view_function)
        def wrapper(request, *args, **kwargs):
            user = request.user

            if not user or not user.is_authenticated:
                raise NotAuthenticated(
                    "Authentication credentials were not provided."
                )

            if user.is_superuser or user.role in allowed_roles:
                return view_function(request, *args, **kwargs)

            raise PermissionDenied(
                "You do not have permission to perform this action."
            )

        return wrapper

    return decorator
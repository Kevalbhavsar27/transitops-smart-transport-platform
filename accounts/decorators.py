from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*allowed_roles):
    def decorator(view_function):

        @login_required
        @wraps(view_function)
        def wrapped_view(request, *args, **kwargs):

            if request.user.is_superuser:
                return view_function(
                    request,
                    *args,
                    **kwargs,
                )

            if request.user.role not in allowed_roles:
                messages.error(
                    request,
                    "You do not have permission to access this page.",
                )

                return redirect(
                    "dashboard:home"
                )

            return view_function(
                request,
                *args,
                **kwargs,
            )

        return wrapped_view

    return decorator
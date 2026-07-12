from rest_framework.permissions import BasePermission


class HasAnyRole(BasePermission):
    """
    Base API permission for role-based access.
    Superusers are always allowed.
    """

    allowed_roles = set()
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.role in self.allowed_roles


def roles_required(*allowed_roles):
    """
    Creates a DRF permission class for the supplied roles.

    Example:
        permission_classes = [
            roles_required("ADMIN", "DISPATCHER")
        ]
    """

    class DynamicRolePermission(HasAnyRole):
        pass

    DynamicRolePermission.allowed_roles = set(allowed_roles)
    return DynamicRolePermission
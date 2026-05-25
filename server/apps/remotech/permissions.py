from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsMentorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.groups.filter(name='Mentor').exists() or request.user.is_staff)
        )


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_staff

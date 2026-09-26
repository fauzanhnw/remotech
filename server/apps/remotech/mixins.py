class AssignUserMixin:
    """Automatically assign `request.user` to a serializer field on create.

    Usage:
        class CourseViewSet(AssignUserMixin, viewsets.ModelViewSet):
            ...

    Set `user_field` on the viewset if the model uses a different field name.
    """

    user_field = "user"

    def perform_create(self, serializer):
        serializer.save(**{self.user_field: self.request.user})

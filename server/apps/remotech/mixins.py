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


class CourseOwnerMixin:
    """Restrict write actions to the owner of the related course.

    Subclasses implement `get_course()` returning the course for the
    operation, based on the instance being written or the validated data.
    """

    def get_course(self, instance=None, validated_data=None):
        raise NotImplementedError

    def deny_if_not_owner(self, course):
        if course is None or course.user_id != self.request.user.pk:
            self.permission_denied(self.request, message="You do not own this course.")

    def perform_create(self, serializer):
        self.deny_if_not_owner(
            self.get_course(validated_data=serializer.validated_data)
        )
        serializer.save()

    def perform_update(self, serializer):
        self.deny_if_not_owner(
            self.get_course(
                instance=serializer.instance, validated_data=serializer.validated_data
            )
        )
        serializer.save()

    def perform_destroy(self, instance):
        self.deny_if_not_owner(self.get_course(instance=instance))
        instance.delete()

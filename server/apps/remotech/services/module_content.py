from django.core.exceptions import ValidationError

from server.apps.remotech.models import CourseModule
from server.apps.remotech.services.richtext import sanitize_richtext


def validate_module_content(attrs, instance=None):
    module = attrs.get("module")
    if module is None and instance is not None:
        module = instance.module
    if module is None:
        raise ValidationError({"module": "This field is required."})

    category = module.module_category
    if category == CourseModule.Category.TEXT:
        content_text = attrs.get("content_text")
        if content_text is None and instance is not None:
            content_text = instance.content_text
        if not content_text or not content_text.strip():
            raise ValidationError(
                {"content_text": "This field is required for text modules."}
            )
        attrs["content_text"] = sanitize_richtext(content_text)
    elif category in (CourseModule.Category.VIDEO, CourseModule.Category.UPLOAD):
        content_url = attrs.get("content_url")
        if content_url is None and instance is not None:
            content_url = instance.content_url
        if not content_url:
            raise ValidationError(
                {"content_url": "This field is required for this module category."}
            )

    return attrs

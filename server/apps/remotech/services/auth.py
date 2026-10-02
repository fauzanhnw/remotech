import secrets

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from rest_framework.exceptions import ValidationError

from server.apps.remotech.models import SetPasswordToken

PARTICIPANT_GROUP = "participant"


def register_user(email, full_name):
    names = full_name.split(maxsplit=1)
    first_name = names[0]
    last_name = names[1] if len(names) > 1 else ""

    user = User.objects.create_user(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    user.set_unusable_password()
    user.save()

    participant_group, _ = Group.objects.get_or_create(name=PARTICIPANT_GROUP)
    user.groups.add(participant_group)

    token = secrets.token_urlsafe(64)
    SetPasswordToken.objects.create(user=user, token=token)

    send_set_password_email(user, token)

    return user


def set_password(token, password):
    try:
        token_obj = SetPasswordToken.objects.get(token=token)
    except SetPasswordToken.DoesNotExist:
        raise ValidationError({"token": "Invalid token."})

    if token_obj.is_used:
        raise ValidationError({"token": "Token already used."})

    if token_obj.is_expired():
        raise ValidationError({"token": "Token has expired."})

    user = token_obj.user
    user.set_password(password)
    user.is_active = True
    user.save()

    token_obj.is_used = True
    token_obj.save()

    return user


def send_set_password_email(user, token):
    set_password_url = f"{settings.BASE_URL}/set-password/?token={token}"

    subject = "Set Your Password - Remotech"
    message = render_to_string(
        "set_password_email.txt",
        {"user": user, "set_password_url": set_password_url},
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def forgot_password(email):
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return None

    token = secrets.token_urlsafe(64)
    SetPasswordToken.objects.create(user=user, token=token)

    send_forgot_password_email(user, token)

    return user


def reset_password(token, password):
    try:
        token_obj = SetPasswordToken.objects.get(token=token)
    except SetPasswordToken.DoesNotExist:
        raise ValidationError({"token": "Invalid token."})

    if token_obj.is_used:
        raise ValidationError({"token": "Token already used."})

    if token_obj.is_expired():
        raise ValidationError({"token": "Token has expired."})

    user = token_obj.user
    user.set_password(password)
    user.save()

    token_obj.is_used = True
    token_obj.save()

    return user


def send_forgot_password_email(user, token):
    reset_password_url = f"{settings.BASE_URL}/reset-password/?token={token}"

    subject = "Reset Your Password - Remotech"
    message = render_to_string(
        "forgot_password_email.txt",
        {"user": user, "reset_password_url": reset_password_url},
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

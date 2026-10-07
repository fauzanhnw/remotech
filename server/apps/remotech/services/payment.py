import hashlib
import hmac
import uuid
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from server.apps.remotech.models import CourseEnrollment, CourseOrder

REQUEST_TIMEOUT = 10


class PaymentGatewayError(APIException):
    status_code = 502
    default_detail = "Payment gateway is unavailable."
    default_code = "payment_gateway_error"


def generate_order_no():
    return f"RC-{uuid.uuid4().hex[:20].upper()}"


def enroll_course(user, course):
    """Enroll user into a course. Every course can only be bought once.

    Returns (order, enrolled). `enrolled` is True when no payment is
    required (free course) and the enrollment is already active.
    """
    if not course.is_publish:
        raise ValidationError({"course": "Course is not published."})

    if not course.is_open:
        raise ValidationError({"course": "Course is closed for enrollment."})

    if CourseEnrollment.objects.filter(user=user, course=course).exists():
        raise ValidationError({"course": "You have already enrolled in this course."})

    already_paid_order = None

    with transaction.atomic():
        order = (
            CourseOrder.objects.select_for_update()
            .filter(user=user, course=course)
            .order_by("-id")
            .first()
        )

        if order is not None:
            if order.transaction_status == CourseOrder.StatusChoices.SETTLEMENT:
                already_paid_order = order
                order = None
            elif order.transaction_status != CourseOrder.StatusChoices.PENDING:
                # Previous payment failed (deny/cancel/expire/failure):
                # the user may buy again.
                order = None

        if already_paid_order is None:
            if order is None:
                order = CourseOrder.objects.create(
                    user=user,
                    course=course,
                    order_no=generate_order_no(),
                    gross_amount=Decimal(max(course.price, 0)).quantize(
                        Decimal("0.01")
                    ),
                )

            if course.price <= 0:
                order.transaction_status = CourseOrder.StatusChoices.SETTLEMENT
                order.gross_amount = Decimal("0.00")
                order.payment_type = "free"
                order.paid_at = timezone.now()
                order.save(
                    update_fields=[
                        "transaction_status",
                        "gross_amount",
                        "payment_type",
                        "paid_at",
                    ]
                )
                CourseEnrollment.objects.get_or_create(user=user, course=course)
                return order, True

    if already_paid_order is not None:
        # Heal a paid order that is missing its enrollment, then reject.
        CourseEnrollment.objects.get_or_create(user=user, course=course)
        raise ValidationError({"course": "You have already bought this course."})

    # Payment required: ensure the order has a Snap transaction.
    if not order.snap_token:
        create_snap_transaction(order)
    return order, False


def create_snap_transaction(order):
    server_key = settings.MIDTRANS_SERVER_KEY
    if not server_key:
        raise PaymentGatewayError("Payment service is not configured.")

    course = order.course
    payload = {
        "transaction_details": {
            "order_id": order.order_no,
            "gross_amount": int(order.gross_amount),
        },
        "item_details": [
            {
                "id": f"course-{course.pk}",
                "price": int(order.gross_amount),
                "quantity": 1,
                "name": course.title[:50],
            }
        ],
        "customer_details": _customer_details(order.user),
    }

    try:
        response = requests.post(
            f"{settings.MIDTRANS_API_BASE}/snap/v1/transactions",
            json=payload,
            auth=(server_key, ""),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise PaymentGatewayError("Failed to contact payment gateway.") from exc

    if response.status_code not in (200, 201):
        raise PaymentGatewayError(
            f"Payment gateway rejected the transaction ({response.status_code})."
        )

    data = response.json()
    order.snap_token = data.get("token", "")
    order.save(update_fields=["snap_token"])
    return order


def _customer_details(user):
    details = {
        "first_name": (user.first_name or user.username)[:50],
        "last_name": user.last_name[:50],
    }
    if user.email:
        details["email"] = user.email
    return details


def handle_notification(payload):
    """Validate a Midtrans webhook and apply it to the matching order."""
    order_no = str(payload.get("order_id") or "")
    if not order_no:
        raise ValidationError({"order_id": "Missing order_id."})

    try:
        order = CourseOrder.objects.select_related("course").get(order_no=order_no)
    except CourseOrder.DoesNotExist:
        raise ValidationError({"order_id": "Unknown order."})

    if not verify_notification_signature(payload):
        raise PermissionDenied("Invalid notification signature.")

    _assert_gross_amount(order, payload)
    return apply_payment_result(order, payload)


def verify_notification_signature(payload):
    server_key = settings.MIDTRANS_SERVER_KEY
    if not server_key:
        return False

    raw = (
        f"{payload.get('order_id', '')}"
        f"{payload.get('status_code', '')}"
        f"{payload.get('gross_amount', '')}"
        f"{server_key}"
    )
    expected = hashlib.sha512(raw.encode()).hexdigest()
    provided = str(payload.get("signature_key", ""))
    return hmac.compare_digest(expected, provided)


def _assert_gross_amount(order, payload):
    try:
        amount = Decimal(str(payload.get("gross_amount", "")))
    except Exception:
        raise ValidationError({"gross_amount": "Invalid gross_amount."})
    if amount != order.gross_amount:
        raise ValidationError(
            {"gross_amount": "Gross amount does not match the order."}
        )


def apply_payment_result(order, data):
    """Update the order from a verified payment payload (idempotent)."""
    new_status = str(data.get("transaction_status") or "")
    if new_status not in CourseOrder.StatusChoices.values:
        raise ValidationError({"transaction_status": "Unknown transaction status."})

    with transaction.atomic():
        order = CourseOrder.objects.select_for_update().get(pk=order.pk)

        # Settlement is final: never downgrade, never re-process.
        if order.transaction_status == CourseOrder.StatusChoices.SETTLEMENT:
            return order

        order.transaction_status = new_status
        order.payment_type = data.get("payment_type") or order.payment_type
        order.midtrans_transaction_id = (
            data.get("transaction_id") or order.midtrans_transaction_id
        )

        if new_status == CourseOrder.StatusChoices.SETTLEMENT:
            order.paid_at = timezone.now()
            CourseEnrollment.objects.get_or_create(user=order.user, course=order.course)

        order.save(
            update_fields=[
                "transaction_status",
                "payment_type",
                "midtrans_transaction_id",
                "paid_at",
            ]
        )
        return order


def check_payment_status(order):
    """Query Midtrans for the latest status of an order and apply it."""
    if order.transaction_status == CourseOrder.StatusChoices.SETTLEMENT:
        return order
    if order.gross_amount == 0:
        return order

    server_key = settings.MIDTRANS_SERVER_KEY
    if not server_key:
        raise PaymentGatewayError("Payment service is not configured.")

    try:
        response = requests.get(
            f"{settings.MIDTRANS_API_BASE}/v2/{order.order_no}/status",
            auth=(server_key, ""),
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise PaymentGatewayError("Failed to contact payment gateway.") from exc

    if response.status_code == 404:
        # No transaction exists at Midtrans yet (e.g. Snap never opened).
        return order
    if response.status_code != 200:
        raise PaymentGatewayError(
            f"Payment gateway status check failed ({response.status_code})."
        )

    return apply_payment_result(order, response.json())

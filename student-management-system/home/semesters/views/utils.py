# semesters/views/utils.py
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
import logging
import re

User = get_user_model()
logger = logging.getLogger(__name__)


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and getattr(user, "is_admin", False)


def create_notification(user, message):
    """Create a notification for a user"""
    try:
        # Example: If you later add a Notification model, you can enable this
        # from notifications.models import Notification
        # Notification.objects.create(user=user, message=message)

        # For now, just log the notification
        logger.info("Notification for %s: %s", user.username if user else "Unknown", message)
    except Exception as e:
        logger.exception("Error creating notification: %s", str(e))


def get_user_permissions(user):
    """Get user permissions for semester management"""
    permissions = {
        "can_view": user.is_authenticated,
        "can_add": is_admin(user),
        "can_edit": is_admin(user),
        "can_delete": is_admin(user),
        "can_manage_students": is_admin(user),
        "can_manage_teachers": is_admin(user),
        "can_export": is_admin(user),
    }
    return permissions


def validate_email_list(email_string):
    """Validate and parse email list from string"""

    if not email_string:
        return [], []

    # Split by comma, semicolon, or newline
    emails = re.split(r"[,;\n\r]+", email_string.strip())

    valid_emails = []
    invalid_emails = []

    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    for email in emails:
        email = email.strip()
        if email:  # Skip empty strings
            if email_pattern.match(email):
                valid_emails.append(email.lower())
            else:
                invalid_emails.append(email)

    return valid_emails, invalid_emails


def paginate_queryset(request, queryset, per_page=20):
    """Helper function for pagination"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page", 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return page_obj

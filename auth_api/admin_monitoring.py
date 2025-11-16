# auth_api/admin_monitoring.py
# Admin monitoring and logging setup

import logging
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


def setup_admin_monitoring():
    """
    Initialize admin monitoring and audit logging.
    This is called when the auth_api app is ready.
    """
    logger.info("Admin monitoring initialized for auth_api")
    
    # You can add custom admin monitoring logic here
    # For example:
    # - Set up custom admin actions
    # - Configure admin audit logging
    # - Set up admin notifications
    
    # For now, this is a placeholder that allows the app to start
    # without errors
    pass


def log_admin_action(user, action, obj=None, message=""):
    """
    Log an admin action for audit purposes.
    
    Args:
        user: The user performing the action
        action: The type of action (1=add, 2=change, 3=delete)
        obj: The object being acted upon (optional)
        message: Additional message (optional)
    """
    if obj:
        content_type = ContentType.objects.get_for_model(obj)
        LogEntry.objects.create(
            user_id=user.id,
            content_type=content_type,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=action,
            change_message=message
        )
        logger.info(f"Admin action logged: {user.email} performed {action} on {obj}")

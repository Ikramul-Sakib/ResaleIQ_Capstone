"""Helpers for in-app notifications and the admin activity log."""

from .extensions import db
from .models import AdminAction, Notification, User


def notify(user_id: int, type_: str, message: str, link: str | None = None) -> None:
    db.session.add(Notification(user_id=user_id, type=type_, message=message[:500], link=link))


def notify_admins(type_: str, message: str, link: str | None = None) -> None:
    for (admin_id,) in db.session.query(User.id).filter(User.role == "admin", User.is_blocked.is_(False)):
        notify(admin_id, type_, message, link)


def log_admin(admin: User, action: str, target_type: str, target_id: int | None, note: str | None = None) -> None:
    db.session.add(
        AdminAction(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id, note=note)
    )

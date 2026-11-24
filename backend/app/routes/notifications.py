from flask import Blueprint, g, jsonify

from ..extensions import db
from ..models import Notification
from ..security import login_required
from ..validation import json_body
from .messages import unread_message_count
from .orders import cart_count, pending_sales_count

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


def _unread_notifications(user_id: int) -> int:
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


@bp.get("")
@login_required
def list_notifications():
    items = (
        Notification.query.filter_by(user_id=g.user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
        .all()
    )
    return jsonify({"items": [item.to_dict() for item in items], "unread_count": _unread_notifications(g.user.id)})


@bp.get("/summary")
@login_required
def summary():
    """Small payload the frontend polls to show badge counts."""
    return jsonify(
        {
            "unread_notifications": _unread_notifications(g.user.id),
            "unread_messages": unread_message_count(g.user.id),
            "cart_count": cart_count(g.user.id),
            "pending_sales": pending_sales_count(g.user.id),
        }
    )


@bp.post("/read")
@login_required
def mark_read():
    ids = json_body().get("ids")
    query = Notification.query.filter_by(user_id=g.user.id, is_read=False)
    if isinstance(ids, list) and ids:
        query = query.filter(Notification.id.in_([i for i in ids if isinstance(i, int)]))
    query.update({"is_read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"unread_count": _unread_notifications(g.user.id)})

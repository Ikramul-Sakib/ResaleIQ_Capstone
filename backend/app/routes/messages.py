from flask import Blueprint, g, jsonify
from sqlalchemy import func, or_

from ..activity import notify
from ..errors import ApiError
from ..extensions import db
from ..models import Conversation, Listing, Message, Notification, iso, utcnow
from ..security import login_required
from ..validation import Validator, json_body

bp = Blueprint("messages", __name__, url_prefix="/api/conversations")


def _conversation_dict(conversation: Conversation, user_id: int, unread: int = 0) -> dict:
    last = conversation.messages[-1] if conversation.messages else None
    other = conversation.other_user(user_id)
    listing = conversation.listing
    return {
        "id": conversation.id,
        "role": "buyer" if user_id == conversation.buyer_id else "seller",
        "listing": {
            "id": listing.id,
            "title": listing.title,
            "price": listing.price,
            "status": listing.status,
            "image": listing.images[0].url if listing.images else None,
        },
        "other_user": {"id": other.id, "name": other.name},
        "last_message": last.to_dict() if last else None,
        "unread_count": unread,
        "updated_at": iso(conversation.updated_at),
    }


def _get_conversation(conversation_id: int) -> Conversation:
    conversation = db.session.get(Conversation, conversation_id)
    if conversation is None or g.user.id not in (conversation.buyer_id, conversation.seller_id):
        raise ApiError("Conversation not found.", 404)
    return conversation


def _message_body() -> str:
    return Validator(json_body()).string("body", "Message", required=True, max_len=2000).check()["body"]


def _add_message(conversation: Conversation, body: str) -> Message:
    message = Message(conversation_id=conversation.id, sender_id=g.user.id, body=body)
    db.session.add(message)
    conversation.updated_at = utcnow()
    recipient_id = conversation.seller_id if g.user.id == conversation.buyer_id else conversation.buyer_id
    link = f"/messages/{conversation.id}"
    # One unread "new message" notification per conversation is enough.
    if not Notification.query.filter_by(user_id=recipient_id, link=link, is_read=False).first():
        notify(recipient_id, "message", f'{g.user.name} sent you a message about "{conversation.listing.title}".', link)
    return message


def unread_message_count(user_id: int) -> int:
    return (
        db.session.query(func.count(Message.id))
        .join(Conversation)
        .filter(
            or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id),
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .scalar()
    )


@bp.get("")
@login_required
def list_conversations():
    user_id = g.user.id
    conversations = (
        Conversation.query.filter(or_(Conversation.buyer_id == user_id, Conversation.seller_id == user_id))
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    unread = dict(
        db.session.query(Message.conversation_id, func.count(Message.id))
        .filter(
            Message.conversation_id.in_([c.id for c in conversations] or [0]),
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .group_by(Message.conversation_id)
        .all()
    )
    return jsonify({"items": [_conversation_dict(c, user_id, unread.get(c.id, 0)) for c in conversations]})


@bp.post("")
@login_required
def start_conversation():
    data = json_body()
    values = Validator(data).integer("listing_id", "Listing", required=True).string(
        "body", "Message", required=True, max_len=2000
    ).check()
    listing = db.session.get(Listing, values["listing_id"])
    if listing is None or listing.status not in ("approved", "reserved"):
        raise ApiError("This listing is no longer available.", 404)
    if listing.seller_id == g.user.id:
        raise ApiError("You can't message yourself about your own listing.", 400)

    conversation = Conversation.query.filter_by(listing_id=listing.id, buyer_id=g.user.id).first()
    if conversation is None:
        conversation = Conversation(listing_id=listing.id, buyer_id=g.user.id, seller_id=listing.seller_id)
        db.session.add(conversation)
        db.session.flush()
    _add_message(conversation, values["body"])
    db.session.commit()
    return jsonify(_conversation_dict(conversation, g.user.id)), 201


@bp.get("/<int:conversation_id>")
@login_required
def get_conversation(conversation_id: int):
    conversation = _get_conversation(conversation_id)
    changed = False
    for message in conversation.messages:
        if message.sender_id != g.user.id and not message.is_read:
            message.is_read = True
            changed = True
    if changed:
        Notification.query.filter_by(user_id=g.user.id, link=f"/messages/{conversation.id}", is_read=False).update(
            {"is_read": True}
        )
        db.session.commit()
    return jsonify(
        {
            "conversation": _conversation_dict(conversation, g.user.id),
            "messages": [message.to_dict() for message in conversation.messages],
        }
    )


@bp.post("/<int:conversation_id>/messages")
@login_required
def send_message(conversation_id: int):
    conversation = _get_conversation(conversation_id)
    if conversation.listing.status == "removed":
        raise ApiError("This listing was removed, so the conversation is closed.", 409)
    message = _add_message(conversation, _message_body())
    db.session.commit()
    return jsonify(message.to_dict()), 201

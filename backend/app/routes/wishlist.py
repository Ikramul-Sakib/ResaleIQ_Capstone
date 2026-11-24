from flask import Blueprint, g, jsonify
from sqlalchemy.orm import joinedload, selectinload

from ..errors import ApiError
from ..extensions import db
from ..models import PUBLIC_LISTING_STATUSES, Listing, WishlistItem
from ..security import login_required

bp = Blueprint("wishlist", __name__, url_prefix="/api/wishlist")


@bp.get("")
@login_required
def list_wishlist():
    entries = (
        WishlistItem.query.options(
            joinedload(WishlistItem.listing).selectinload(Listing.images),
            joinedload(WishlistItem.listing).joinedload(Listing.category),
        )
        .filter(WishlistItem.user_id == g.user.id)
        .order_by(WishlistItem.created_at.desc())
        .all()
    )
    items = [
        {**entry.listing.to_dict(), "in_wishlist": True}
        for entry in entries
        if entry.listing.status in PUBLIC_LISTING_STATUSES
    ]
    return jsonify({"items": items})


@bp.post("/<int:listing_id>")
@login_required
def add(listing_id: int):
    listing = db.session.get(Listing, listing_id)
    if listing is None or listing.status not in PUBLIC_LISTING_STATUSES:
        raise ApiError("Listing not found.", 404)
    if listing.seller_id == g.user.id:
        raise ApiError("You can't save your own listing.", 400)
    if not WishlistItem.query.filter_by(user_id=g.user.id, listing_id=listing_id).first():
        db.session.add(WishlistItem(user_id=g.user.id, listing_id=listing_id))
        db.session.commit()
    return jsonify({"in_wishlist": True}), 201


@bp.delete("/<int:listing_id>")
@login_required
def remove(listing_id: int):
    WishlistItem.query.filter_by(user_id=g.user.id, listing_id=listing_id).delete()
    db.session.commit()
    return jsonify({"in_wishlist": False})

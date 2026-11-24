from flask import Blueprint, g, jsonify, request
from sqlalchemy.orm import joinedload

from ..activity import notify
from ..errors import ApiError
from ..extensions import db
from ..models import ACTIVE_ORDER_STATUSES, ORDER_STATUSES, PAYMENT_METHODS, CartItem, Listing, Order, Review, utcnow
from ..security import login_required
from ..services.orders import (
    availability_problem,
    close_orders_for_listing,
    create_order,
    release_listing,
    taka,
    validate_checkout,
)
from ..validation import Validator, json_body, page_args, paginate

bp = Blueprint("orders", __name__, url_prefix="/api")


# ---------------------------------------------------------------- cart

def _cart_entries(user_id: int):
    return (
        CartItem.query.options(
            joinedload(CartItem.listing).selectinload(Listing.images),
            joinedload(CartItem.listing).joinedload(Listing.category),
        )
        .filter(CartItem.user_id == user_id)
        .order_by(CartItem.created_at.desc())
        .all()
    )


@bp.get("/cart")
@login_required
def get_cart():
    items, total = [], 0
    for entry in _cart_entries(g.user.id):
        problem = availability_problem(g.user, entry.listing)
        items.append({**entry.listing.to_dict(), "available": problem is None, "problem": problem})
        if problem is None:
            total += entry.listing.price
    return jsonify({"items": items, "total": total, "available_count": sum(1 for i in items if i["available"])})


@bp.post("/cart/<int:listing_id>")
@login_required
def add_to_cart(listing_id: int):
    listing = db.session.get(Listing, listing_id)
    problem = availability_problem(g.user, listing)
    if problem:
        raise ApiError(problem, 409)
    if CartItem.query.filter_by(user_id=g.user.id).count() >= 20:
        raise ApiError("Your cart can hold up to 20 items.", 409)
    if not CartItem.query.filter_by(user_id=g.user.id, listing_id=listing_id).first():
        db.session.add(CartItem(user_id=g.user.id, listing_id=listing_id))
        db.session.commit()
    return jsonify({"in_cart": True, "cart_count": CartItem.query.filter_by(user_id=g.user.id).count()}), 201


@bp.delete("/cart/<int:listing_id>")
@login_required
def remove_from_cart(listing_id: int):
    CartItem.query.filter_by(user_id=g.user.id, listing_id=listing_id).delete()
    db.session.commit()
    return jsonify({"in_cart": False, "cart_count": CartItem.query.filter_by(user_id=g.user.id).count()})


@bp.post("/cart/checkout")
@login_required
def checkout():
    checkout_info = validate_checkout(json_body())
    entries = _cart_entries(g.user.id)
    if not entries:
        raise ApiError("Your cart is empty.", 400)
    created, skipped = [], []
    for entry in entries:
        problem = availability_problem(g.user, entry.listing)
        if problem:
            skipped.append({"listing_id": entry.listing_id, "title": entry.listing.title, "reason": problem})
            continue
        created.append(create_order(g.user, entry.listing, checkout_info))
        db.session.delete(entry)
    if not created:
        db.session.rollback()
        raise ApiError("None of the items in your cart can be ordered right now.", 409)
    db.session.commit()
    return jsonify({"orders": [order.to_dict(g.user.id) for order in created], "skipped": skipped}), 201


# ---------------------------------------------------------------- orders

@bp.post("/orders")
@login_required
def place_order():
    data = json_body()
    values = (
        Validator(data)
        .integer("listing_id", "Listing", required=True)
        .integer("offer_price", "Offer", min_value=1, max_value=50_000_000)
        .check()
    )
    checkout_info = validate_checkout(data)
    listing = db.session.get(Listing, values["listing_id"])
    order = create_order(g.user, listing, checkout_info, values["offer_price"])
    CartItem.query.filter_by(user_id=g.user.id, listing_id=listing.id).delete()
    db.session.commit()
    return jsonify(order.to_dict(g.user.id)), 201


@bp.get("/orders")
@login_required
def list_orders():
    role = request.args.get("role", "buyer")
    column = Order.seller_id if role == "seller" else Order.buyer_id
    query = Order.query.options(joinedload(Order.buyer), joinedload(Order.seller), joinedload(Order.listing),
                                joinedload(Order.review)).filter(column == g.user.id)
    status = request.args.get("status")
    if status == "active":
        query = query.filter(Order.status.in_(ACTIVE_ORDER_STATUSES))
    elif status in ORDER_STATUSES:
        query = query.filter(Order.status == status)
    page, per_page = page_args(default_per_page=20, max_per_page=50)
    items, meta = paginate(query.order_by(Order.updated_at.desc(), Order.id.desc()), page, per_page)
    return jsonify({"items": [order.to_dict(g.user.id) for order in items], **meta})


def _get_order(order_id: int) -> Order:
    order = db.session.get(Order, order_id)
    if order is None or g.user.id not in (order.buyer_id, order.seller_id):
        raise ApiError("Order not found.", 404)
    return order


def _require(order: Order, role: str, statuses: tuple, action: str) -> None:
    owner_id = order.seller_id if role == "seller" else order.buyer_id
    if g.user.id != owner_id:
        raise ApiError(f"Only the {role} can {action}.", 403)
    if order.status not in statuses:
        raise ApiError(f"This order can't be {action.split()[0]}ed now (it is {order.status}).", 409)


def _done(order: Order):
    db.session.commit()
    return jsonify(order.to_dict(g.user.id))


@bp.get("/orders/<int:order_id>")
@login_required
def get_order(order_id: int):
    return jsonify(_get_order(order_id).to_dict(g.user.id))


@bp.post("/orders/<int:order_id>/accept")
@login_required
def accept_order(order_id: int):
    order = _get_order(order_id)
    _require(order, "seller", ("pending",), "accept this order")
    if order.listing is None or order.listing.status != "approved":
        raise ApiError("This item is not available any more, so the order can't be accepted.", 409)
    order.status = "accepted"
    order.accepted_at = utcnow()
    order.listing.status = "reserved"
    close_orders_for_listing(order.listing, "The item was reserved for another buyer.", exclude_id=order.id)
    notify(order.buyer_id, "order",
           f'{order.seller.name} accepted your order for "{order.listing_title}" ({taka(order.price)}).',
           f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/decline")
@login_required
def decline_order(order_id: int):
    order = _get_order(order_id)
    _require(order, "seller", ("pending",), "decline this order")
    reason = Validator(json_body()).string("reason", "Reason", max_len=500).check()["reason"]
    order.status = "declined"
    order.status_note = reason
    order.closed_at = utcnow()
    message = f'{order.seller.name} declined your {"offer" if order.is_offer else "order"} for "{order.listing_title}"'
    notify(order.buyer_id, "order", message + (f": {reason}" if reason else "."), f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/cancel")
@login_required
def cancel_order(order_id: int):
    order = _get_order(order_id)
    role = "buyer" if g.user.id == order.buyer_id else "seller"
    allowed = ("pending", "accepted") if role == "buyer" else ("accepted", "shipped")
    if order.status not in allowed:
        raise ApiError("This order can't be cancelled now." if role == "buyer" or order.status != "pending"
                       else "Decline the order instead of cancelling it.", 409)
    reason = Validator(json_body()).string("reason", "Reason", max_len=500).check()["reason"]
    if order.status in ("accepted", "shipped"):
        release_listing(order)
    order.status = "cancelled"
    order.cancelled_by = role
    order.status_note = reason
    order.closed_at = utcnow()
    other_id = order.seller_id if role == "buyer" else order.buyer_id
    notify(other_id, "order", f'{g.user.name} cancelled the order for "{order.listing_title}"'
           + (f": {reason}" if reason else "."), f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/ship")
@login_required
def ship_order(order_id: int):
    order = _get_order(order_id)
    _require(order, "seller", ("accepted",), "ship this order")
    order.status = "shipped"
    order.shipped_at = utcnow()
    verb = "shipped" if order.delivery_method == "delivery" else "marked as handed over"
    notify(order.buyer_id, "order", f'"{order.listing_title}" was {verb}. Confirm when you receive it.',
           f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/payment")
@login_required
def submit_payment(order_id: int):
    order = _get_order(order_id)
    _require(order, "buyer", ("accepted", "shipped"), "add payment details")
    if order.payment_method == "cod":
        raise ApiError("This order is paid in cash on delivery.", 400)
    trx = Validator(json_body()).string("transaction_id", "Transaction ID", required=True, min_len=6,
                                        max_len=40).check()["transaction_id"]
    order.transaction_id = trx
    notify(order.seller_id, "order",
           f'{order.buyer.name} sent {PAYMENT_METHODS[order.payment_method]} payment details for '
           f'"{order.listing_title}". Please check and confirm.', f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/confirm-payment")
@login_required
def confirm_payment(order_id: int):
    order = _get_order(order_id)
    _require(order, "seller", ("accepted", "shipped", "completed"), "confirm payment")
    order.payment_status = "paid"
    notify(order.buyer_id, "order", f'{order.seller.name} confirmed your payment for "{order.listing_title}".',
           f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/complete")
@login_required
def complete_order(order_id: int):
    order = _get_order(order_id)
    _require(order, "buyer", ("accepted", "shipped"), "confirm that you received the item")
    now = utcnow()
    order.status = "completed"
    order.completed_at = now
    order.payment_status = "paid"
    if order.listing:
        order.listing.status = "sold"
        order.listing.sold_price = order.price
        order.listing.sold_at = now
    notify(order.seller_id, "order", f'{order.buyer.name} received "{order.listing_title}". The sale is complete!',
           f"/orders/{order.id}")
    return _done(order)


@bp.post("/orders/<int:order_id>/review")
@login_required
def review_order(order_id: int):
    order = _get_order(order_id)
    _require(order, "buyer", ("completed",), "review this order")
    if order.review:
        raise ApiError("You have already reviewed this order.", 409)
    values = (
        Validator(json_body())
        .integer("rating", "Rating", required=True, min_value=1, max_value=5)
        .string("comment", "Comment", max_len=1000)
        .check()
    )
    db.session.add(Review(order_id=order.id, reviewer_id=g.user.id, seller_id=order.seller_id,
                          rating=values["rating"], comment=values["comment"]))
    notify(order.seller_id, "review", f'{g.user.name} rated you {values["rating"]}/5 for "{order.listing_title}".',
           f"/sellers/{order.seller_id}")
    db.session.commit()
    db.session.refresh(order)
    return jsonify(order.to_dict(g.user.id)), 201


@bp.get("/users/<int:user_id>/reviews")
def seller_reviews(user_id: int):
    query = Review.query.options(joinedload(Review.reviewer), joinedload(Review.order)).filter(
        Review.seller_id == user_id
    )
    page, per_page = page_args(default_per_page=10, max_per_page=50)
    items, meta = paginate(query.order_by(Review.created_at.desc(), Review.id.desc()), page, per_page)
    return jsonify({"items": [review.to_dict() for review in items], **meta})


def pending_sales_count(user_id: int) -> int:
    return Order.query.filter(Order.seller_id == user_id, Order.status == "pending").count()


def cart_count(user_id: int) -> int:
    return CartItem.query.filter_by(user_id=user_id).count()


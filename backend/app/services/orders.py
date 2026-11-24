"""Order rules shared by the cart, order and admin routes.

Order life cycle:
    pending  -> accepted (item reserved) -> shipped / handed over -> completed (item sold)
    pending  -> declined          (by the seller, or automatically)
    pending / accepted / shipped -> cancelled
"""

import re

from ..activity import notify
from ..errors import ApiError
from ..extensions import db
from ..models import (
    ACTIVE_ORDER_STATUSES,
    DELIVERY_METHODS,
    PAYMENT_METHODS,
    Listing,
    Order,
    User,
    utcnow,
)
from ..validation import Validator

PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{5,18}$")
MIN_OFFER_SHARE = 0.5  # offers below half the asking price are refused


def taka(amount: int) -> str:
    return f"BDT {amount:,}"


def validate_checkout(data) -> dict:
    validator = (
        Validator(data)
        .choice("delivery_method", "Delivery method", DELIVERY_METHODS, required=True)
        .choice("payment_method", "Payment method", PAYMENT_METHODS, required=True)
        .string("contact_phone", "Phone number", required=True, max_len=30)
        .string("delivery_address", "Delivery address", max_len=300)
        .string("note", "Note", max_len=500)
    )
    values = validator.values
    if values.get("contact_phone") and not PHONE_RE.match(values["contact_phone"]):
        validator.add_error("contact_phone", "Enter a valid phone number, e.g. 01712-345678.")
    if values.get("delivery_method") == "delivery" and len(values.get("delivery_address") or "") < 10:
        validator.add_error("delivery_address", "Enter the full delivery address (at least 10 characters).")
    if values.get("delivery_method") == "meetup":
        values["delivery_address"] = None
    return validator.check()


def availability_problem(buyer: User, listing: Listing | None) -> str | None:
    """Why this buyer can't order this listing right now, or None if they can."""
    if listing is None or listing.status not in ("approved", "reserved"):
        return "This item is no longer available."
    if listing.seller_id == buyer.id:
        return "You can't buy your own listing."
    if listing.status == "reserved":
        return "This item is reserved for another buyer."
    if listing.seller is None or listing.seller.is_blocked:
        return "This seller is not accepting orders."
    existing = Order.query.filter(
        Order.listing_id == listing.id, Order.buyer_id == buyer.id, Order.status.in_(ACTIVE_ORDER_STATUSES)
    ).first()
    if existing:
        return "You already have an active order for this item."
    return None


def create_order(buyer: User, listing: Listing, checkout: dict, offer_price: int | None = None) -> Order:
    problem = availability_problem(buyer, listing)
    if problem:
        raise ApiError(problem, 409)

    price, is_offer = listing.price, False
    if offer_price is not None and offer_price != listing.price:
        if offer_price > listing.price:
            raise ApiError("Your offer is higher than the asking price. Use Buy now instead.", 422,
                           {"offer_price": "Offer must be below the asking price."})
        if offer_price < listing.price * MIN_OFFER_SHARE:
            minimum = int(listing.price * MIN_OFFER_SHARE)
            raise ApiError(f"Offers must be at least {taka(minimum)} (half the asking price).", 422,
                           {"offer_price": f"Minimum offer is {taka(minimum)}."})
        price, is_offer = offer_price, True

    order = Order(
        listing_id=listing.id,
        buyer_id=buyer.id,
        seller_id=listing.seller_id,
        listing_title=listing.title,
        listing_image=listing.images[0].filename if listing.images else None,
        list_price=listing.price,
        price=price,
        is_offer=is_offer,
        delivery_method=checkout["delivery_method"],
        delivery_address=checkout.get("delivery_address"),
        contact_phone=checkout["contact_phone"],
        payment_method=checkout["payment_method"],
        buyer_note=checkout.get("note"),
    )
    db.session.add(order)
    db.session.flush()
    what = f"made an offer of {taka(price)}" if is_offer else f"wants to buy it for {taka(price)}"
    notify(listing.seller_id, "order", f'New order: {buyer.name} {what} for "{listing.title}".', f"/orders/{order.id}")
    return order


def release_listing(order: Order) -> None:
    """Put a reserved item back on sale when its accepted order is cancelled."""
    if order.listing and order.listing.status == "reserved":
        order.listing.status = "approved"


def close_orders_for_listing(listing: Listing, reason: str, include_in_progress: bool = False,
                             exclude_id: int | None = None) -> None:
    """Decline waiting orders (and optionally cancel accepted ones) when an item can no longer be sold."""
    statuses = ACTIVE_ORDER_STATUSES if include_in_progress else ("pending",)
    query = Order.query.filter(Order.listing_id == listing.id, Order.status.in_(statuses))
    if exclude_id:
        query = query.filter(Order.id != exclude_id)
    now = utcnow()
    for order in query:
        was_pending = order.status == "pending"
        order.status = "declined" if was_pending else "cancelled"
        order.cancelled_by = None if was_pending else "system"
        order.status_note = reason
        order.closed_at = now
        verb = "was declined" if was_pending else "was cancelled"
        notify(order.buyer_id, "order", f'Your order for "{order.listing_title}" {verb}: {reason}', f"/orders/{order.id}")
        if not was_pending:
            notify(order.seller_id, "order", f'Order for "{order.listing_title}" was cancelled: {reason}', f"/orders/{order.id}")


def has_orders(listing: Listing, statuses) -> bool:
    return Order.query.filter(Order.listing_id == listing.id, Order.status.in_(statuses)).first() is not None

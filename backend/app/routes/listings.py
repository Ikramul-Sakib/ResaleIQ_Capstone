from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, selectinload

from ..activity import notify_admins
from ..errors import ApiError
from ..extensions import db
from ..images import delete_image_files, save_image
from ..models import (
    ACTIVE_ORDER_STATUSES,
    CONDITIONS,
    PUBLIC_LISTING_STATUSES,
    REPORT_REASONS,
    CartItem,
    Category,
    Conversation,
    Listing,
    ListingImage,
    Order,
    Report,
    WishlistItem,
    seller_rating,
    utcnow,
)
from ..security import login_required, optional_user
from ..services.orders import close_orders_for_listing, has_orders
from ..validation import Validator, escape_like, json_body, page_args, paginate

bp = Blueprint("listings", __name__, url_prefix="/api")

SORTS = {
    "newest": (Listing.approved_at.desc(), Listing.id.desc()),
    "oldest": (Listing.approved_at.asc(), Listing.id.asc()),
    "price_asc": (Listing.price.asc(), Listing.id.desc()),
    "price_desc": (Listing.price.desc(), Listing.id.desc()),
}
MAX_PRICE = 50_000_000


def get_listing_or_404(listing_id: int) -> Listing:
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        raise ApiError("Listing not found.", 404)
    return listing


def wishlist_ids(user, listing_ids) -> set[int]:
    if user is None or not listing_ids:
        return set()
    rows = db.session.query(WishlistItem.listing_id).filter(
        WishlistItem.user_id == user.id, WishlistItem.listing_id.in_(listing_ids)
    )
    return {listing_id for (listing_id,) in rows}


def _int_arg(name):
    try:
        return int(request.args[name]) if request.args.get(name, "").strip() else None
    except ValueError:
        return None


@bp.get("/categories")
def list_categories():
    counts = dict(
        db.session.query(Listing.category_id, func.count(Listing.id))
        .filter(Listing.status == "approved")
        .group_by(Listing.category_id)
        .all()
    )
    categories = Category.query.order_by(Category.name).all()
    return jsonify([category.to_dict(listing_count=counts.get(category.id, 0)) for category in categories])


@bp.get("/listings")
def search_listings():
    args = request.args
    query = Listing.query.options(selectinload(Listing.images), joinedload(Listing.category)).filter(
        Listing.status == "approved"
    )

    text = (args.get("q") or "").strip()[:100]
    for term in text.split()[:6]:
        like = f"%{escape_like(term)}%"
        query = query.filter(
            or_(
                Listing.title.ilike(like, escape="\\"),
                Listing.description.ilike(like, escape="\\"),
                Listing.brand.ilike(like, escape="\\"),
                Listing.model.ilike(like, escape="\\"),
            )
        )

    category = (args.get("category") or "").strip()
    if category:
        column = Category.id if category.isdigit() else Category.slug
        query = query.join(Category).filter(column == (int(category) if category.isdigit() else category))

    min_price, max_price = _int_arg("min_price"), _int_arg("max_price")
    if min_price is not None:
        query = query.filter(Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(Listing.price <= max_price)

    conditions = [value for value in (args.get("condition") or "").split(",") if value in CONDITIONS]
    if conditions:
        query = query.filter(Listing.condition.in_(conditions))

    location = (args.get("location") or "").strip()[:100]
    if location:
        query = query.filter(Listing.location.ilike(f"%{escape_like(location)}%", escape="\\"))

    seller_id = _int_arg("seller_id")
    if seller_id is not None:
        query = query.filter(Listing.seller_id == seller_id)

    query = query.order_by(*SORTS.get(args.get("sort"), SORTS["newest"]))
    page, per_page = page_args()
    items, meta = paginate(query, page, per_page)

    saved = wishlist_ids(optional_user(), [item.id for item in items])
    return jsonify({"items": [{**item.to_dict(), "in_wishlist": item.id in saved} for item in items], **meta})


@bp.get("/listings/mine")
@login_required
def my_listings():
    listings = (
        Listing.query.options(selectinload(Listing.images), joinedload(Listing.category))
        .filter(Listing.seller_id == g.user.id)
        .order_by(Listing.updated_at.desc())
        .all()
    )
    stats = {status: 0 for status in ("pending", "approved", "reserved", "rejected", "sold", "removed")}
    for listing in listings:
        stats[listing.status] = stats.get(listing.status, 0) + 1
    stats["total"] = len(listings)
    stats["total_views"] = sum(listing.views for listing in listings)
    stats["sales_value"] = sum(listing.sold_price or 0 for listing in listings if listing.status == "sold")
    return jsonify({"items": [listing.to_dict(private=True) for listing in listings], "stats": stats})


@bp.get("/listings/<int:listing_id>")
def listing_detail(listing_id: int):
    listing = get_listing_or_404(listing_id)
    user = optional_user()
    is_owner = user is not None and user.id == listing.seller_id
    is_admin = user is not None and user.is_admin
    if listing.status not in PUBLIC_LISTING_STATUSES and not (is_owner or is_admin):
        raise ApiError("Listing not found.", 404)

    if listing.status == "approved" and not is_owner:
        listing.views += 1
        db.session.commit()

    data = listing.to_dict(detail=True, private=is_owner or is_admin)
    data["is_owner"] = is_owner
    data["in_wishlist"] = bool(wishlist_ids(user, [listing.id]))
    data["conversation_id"] = None
    data["in_cart"] = False
    data["active_order_id"] = None
    if user is not None and not is_owner:
        conversation = Conversation.query.filter_by(listing_id=listing.id, buyer_id=user.id).first()
        data["conversation_id"] = conversation.id if conversation else None
        data["in_cart"] = CartItem.query.filter_by(user_id=user.id, listing_id=listing.id).first() is not None
        data["active_order_id"] = active_order_id(user.id, listing.id)
    if is_owner:
        data["pending_order_count"] = listing_order_count(listing.id, ("pending",))
        data["active_order_id"] = first_order_id(listing.id, ("accepted", "shipped"))
    data["seller_stats"] = {
        "active_listings": Listing.query.filter_by(seller_id=listing.seller_id, status="approved").count(),
        "sold_listings": Listing.query.filter_by(seller_id=listing.seller_id, status="sold").count(),
        **seller_rating(listing.seller_id),
    }
    return jsonify(data)


def _validate_listing_form(form) -> dict:
    validator = (
        Validator(form)
        .string("title", "Title", required=True, min_len=5, max_len=120)
        .string("description", "Description", required=True, min_len=20, max_len=5000)
        .integer("category_id", "Category", required=True)
        .integer("price", "Price", required=True, min_value=1, max_value=MAX_PRICE)
        .choice("condition", "Condition", CONDITIONS, required=True)
        .string("location", "Location", required=True, min_len=2, max_len=100)
        .string("brand", "Brand", max_len=80)
        .string("model", "Model", max_len=80)
    )
    category_id = validator.values.get("category_id")
    if category_id is not None and db.session.get(Category, category_id) is None:
        validator.add_error("category_id", "Choose a valid category.")
    return validator


def _new_files():
    return [file for file in request.files.getlist("images") if file and file.filename]


def _save_files(files) -> list[str]:
    saved = []
    try:
        for file in files:
            saved.append(save_image(file))
    except Exception:
        delete_image_files(saved)
        raise
    return saved


@bp.post("/listings")
@login_required
def create_listing():
    validator = _validate_listing_form(request.form)
    files = _new_files()
    max_images = current_app.config["MAX_IMAGES"]
    if not files:
        validator.add_error("images", "Add at least one photo.")
    elif len(files) > max_images:
        validator.add_error("images", f"You can add up to {max_images} photos.")
    values = validator.check()

    saved = _save_files(files)
    try:
        listing = Listing(
            seller_id=g.user.id,
            category_id=values["category_id"],
            title=values["title"],
            description=values["description"],
            price=values["price"],
            condition=values["condition"],
            location=values["location"],
            brand=values["brand"],
            model=values["model"],
            status="pending",
        )
        listing.images = [ListingImage(filename=name, sort_order=index) for index, name in enumerate(saved)]
        db.session.add(listing)
        db.session.flush()
        notify_admins("listing_pending", f'New listing "{listing.title}" is waiting for review.', "/admin/listings")
        db.session.commit()
    except Exception:
        db.session.rollback()
        delete_image_files(saved)
        raise
    return jsonify(listing.to_dict(detail=True, private=True)), 201


@bp.put("/listings/<int:listing_id>")
@login_required
def update_listing(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.seller_id != g.user.id:
        raise ApiError("You can only edit your own listings.", 403)
    if listing.status in ("sold", "removed"):
        raise ApiError("Sold or removed listings can't be edited.", 409)
    if listing.status == "reserved":
        raise ApiError("This item is reserved for a buyer. Finish or cancel that order before editing.", 409)
    if has_orders(listing, ("pending",)):
        raise ApiError("Accept or decline the waiting orders for this item before editing it.", 409)

    validator = _validate_listing_form(request.form)
    keep_ids = []
    for raw in request.form.getlist("keep_images"):
        try:
            keep_ids.append(int(raw))
        except ValueError:
            pass
    current = {image.id: image for image in listing.images}
    kept = [current[image_id] for image_id in keep_ids if image_id in current]
    files = _new_files()
    total = len(kept) + len(files)
    max_images = current_app.config["MAX_IMAGES"]
    if total == 0:
        validator.add_error("images", "Add at least one photo.")
    elif total > max_images:
        validator.add_error("images", f"You can add up to {max_images} photos.")
    values = validator.check()

    saved = _save_files(files)
    removed = [image for image in listing.images if image not in kept]
    removed_files = [image.filename for image in removed]
    try:
        for field in ("category_id", "title", "description", "price", "condition", "location", "brand", "model"):
            setattr(listing, field, values[field])
        new_images = [ListingImage(filename=name) for name in saved]
        listing.images = kept + new_images
        for index, image in enumerate(listing.images):
            image.sort_order = index
        if listing.status in ("approved", "rejected"):
            listing.status = "pending"  # every change is reviewed again
            listing.rejection_reason = None
            listing.approved_at = None
            notify_admins("listing_pending", f'Edited listing "{listing.title}" is waiting for review.', "/admin/listings")
        db.session.commit()
    except Exception:
        db.session.rollback()
        delete_image_files(saved)
        raise
    delete_image_files([name for name in removed_files if not has_order_with_image(name)])
    return jsonify(listing.to_dict(detail=True, private=True))


@bp.delete("/listings/<int:listing_id>")
@login_required
def delete_listing(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.seller_id != g.user.id:
        raise ApiError("You can only delete your own listings.", 403)
    if has_orders(listing, ("accepted", "shipped")):
        raise ApiError("This item has an order in progress. Complete or cancel it before deleting.", 409)
    close_orders_for_listing(listing, "The seller deleted this listing.")
    # Keep photos that past orders still show; delete the rest.
    filenames = [image.filename for image in listing.images if not has_order_with_image(image.filename)]
    db.session.delete(listing)
    db.session.commit()
    delete_image_files(filenames)
    return jsonify({"message": "Listing deleted."})


@bp.post("/listings/<int:listing_id>/sold")
@login_required
def mark_sold(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.seller_id != g.user.id:
        raise ApiError("You can only update your own listings.", 403)
    if listing.status == "reserved":
        raise ApiError("This item has an order in progress. It becomes sold when the buyer confirms receipt.", 409)
    if listing.status != "approved":
        raise ApiError("Only approved listings can be marked as sold.", 409)
    values = Validator(json_body()).integer("sold_price", "Sale price", min_value=0, max_value=MAX_PRICE).check()
    close_orders_for_listing(listing, "The item was sold elsewhere.")
    listing.status = "sold"
    listing.sold_price = values["sold_price"] if values["sold_price"] is not None else listing.price
    listing.sold_at = utcnow()
    db.session.commit()
    return jsonify(listing.to_dict(detail=True, private=True))


@bp.post("/listings/<int:listing_id>/report")
@login_required
def report_listing(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.status != "approved":
        raise ApiError("Listing not found.", 404)
    if listing.seller_id == g.user.id:
        raise ApiError("You can't report your own listing.", 400)
    values = (
        Validator(json_body())
        .choice("reason", "Reason", REPORT_REASONS, required=True)
        .string("details", "Details", max_len=1000)
        .check()
    )
    if Report.query.filter_by(listing_id=listing.id, reporter_id=g.user.id, status="open").first():
        raise ApiError("You have already reported this listing. Our team is reviewing it.", 409)
    db.session.add(
        Report(listing_id=listing.id, reporter_id=g.user.id, reason=values["reason"], details=values["details"])
    )
    notify_admins("report", f'Listing "{listing.title}" was reported: {REPORT_REASONS[values["reason"]]}.', "/admin/reports")
    db.session.commit()
    return jsonify({"message": "Thank you. Our team will review this listing."}), 201


def active_order_id(user_id: int, listing_id: int) -> int | None:
    order = Order.query.filter(
        Order.listing_id == listing_id, Order.buyer_id == user_id, Order.status.in_(ACTIVE_ORDER_STATUSES)
    ).first()
    return order.id if order else None


def first_order_id(listing_id: int, statuses) -> int | None:
    order = Order.query.filter(Order.listing_id == listing_id, Order.status.in_(statuses)).first()
    return order.id if order else None


def listing_order_count(listing_id: int, statuses) -> int:
    return Order.query.filter(Order.listing_id == listing_id, Order.status.in_(statuses)).count()


def has_order_with_image(filename: str) -> bool:
    return Order.query.filter(Order.listing_image == filename).first() is not None

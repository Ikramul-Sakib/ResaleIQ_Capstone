import re

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, selectinload

from ..activity import log_admin, notify
from ..errors import ApiError
from ..extensions import db
from ..models import (
    ACTIVE_ORDER_STATUSES,
    LISTING_STATUSES,
    ORDER_STATUSES,
    AdminAction,
    Category,
    Listing,
    Order,
    Report,
    User,
    utcnow,
)
from ..security import admin_required
from ..services.orders import close_orders_for_listing, release_listing
from ..validation import Validator, escape_like, json_body, page_args, paginate
from .listings import get_listing_or_404

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _reason() -> str:
    return Validator(json_body()).string("reason", "Reason", required=True, min_len=5, max_len=500).check()["reason"]


@bp.get("/stats")
@admin_required
def stats():
    listing_counts = dict(db.session.query(Listing.status, func.count(Listing.id)).group_by(Listing.status).all())
    sales_value = db.session.query(func.coalesce(func.sum(Listing.sold_price), 0)).filter(Listing.status == "sold").scalar()
    recent = AdminAction.query.order_by(AdminAction.created_at.desc(), AdminAction.id.desc()).limit(10).all()
    order_counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())
    order_value = db.session.query(func.coalesce(func.sum(Order.price), 0)).filter(Order.status == "completed").scalar()
    return jsonify(
        {
            "users": User.query.count(),
            "blocked_users": User.query.filter_by(is_blocked=True).count(),
            "listings": {status: listing_counts.get(status, 0) for status in LISTING_STATUSES},
            "open_reports": Report.query.filter_by(status="open").count(),
            "sales_value": int(sales_value or 0),
            "orders": {status: order_counts.get(status, 0) for status in ORDER_STATUSES},
            "order_value": int(order_value or 0),
            "recent_actions": [action.to_dict() for action in recent],
        }
    )


@bp.get("/listings")
@admin_required
def admin_listings():
    status = request.args.get("status", "pending")
    query = Listing.query.options(
        selectinload(Listing.images), joinedload(Listing.category), joinedload(Listing.seller)
    )
    if status in LISTING_STATUSES:
        query = query.filter(Listing.status == status)
    text = (request.args.get("q") or "").strip()[:100]
    if text:
        query = query.filter(Listing.title.ilike(f"%{escape_like(text)}%", escape="\\"))
    # Oldest pending listings first so nobody waits too long; otherwise newest first.
    order = Listing.updated_at.asc() if status == "pending" else Listing.updated_at.desc()
    page, per_page = page_args(default_per_page=20, max_per_page=50)
    items, meta = paginate(query.order_by(order, Listing.id), page, per_page)
    return jsonify({"items": [listing.to_dict(detail=True, private=True) for listing in items], **meta})


@bp.post("/listings/<int:listing_id>/approve")
@admin_required
def approve_listing(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.status not in ("pending", "rejected"):
        raise ApiError("Only pending or rejected listings can be approved.", 409)
    listing.status = "approved"
    listing.rejection_reason = None
    listing.approved_at = utcnow()
    notify(listing.seller_id, "listing_approved", f'Your listing "{listing.title}" is now live.', f"/listings/{listing.id}")
    log_admin(g.user, "approve_listing", "listing", listing.id, listing.title)
    db.session.commit()
    return jsonify(listing.to_dict(detail=True, private=True))


@bp.post("/listings/<int:listing_id>/reject")
@admin_required
def reject_listing(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.status != "pending":
        raise ApiError("Only pending listings can be rejected.", 409)
    reason = _reason()
    listing.status = "rejected"
    listing.rejection_reason = reason
    notify(
        listing.seller_id,
        "listing_rejected",
        f'Your listing "{listing.title}" was not approved: {reason}',
        "/dashboard",
    )
    log_admin(g.user, "reject_listing", "listing", listing.id, reason)
    db.session.commit()
    return jsonify(listing.to_dict(detail=True, private=True))


@bp.post("/listings/<int:listing_id>/remove")
@admin_required
def remove_listing(listing_id: int):
    listing = get_listing_or_404(listing_id)
    if listing.status == "removed":
        raise ApiError("This listing is already removed.", 409)
    reason = _reason()
    close_orders_for_listing(listing, "The listing was removed by an administrator.", include_in_progress=True)
    listing.status = "removed"
    listing.rejection_reason = reason
    for report in Report.query.filter_by(listing_id=listing.id, status="open"):
        report.status = "resolved"
        report.resolved_at = utcnow()
    notify(listing.seller_id, "listing_removed", f'Your listing "{listing.title}" was removed: {reason}', "/dashboard")
    log_admin(g.user, "remove_listing", "listing", listing.id, reason)
    db.session.commit()
    return jsonify(listing.to_dict(detail=True, private=True))


@bp.get("/reports")
@admin_required
def list_reports():
    status = request.args.get("status", "open")
    query = Report.query.options(joinedload(Report.reporter), joinedload(Report.listing))
    if status in ("open", "resolved", "dismissed"):
        query = query.filter(Report.status == status)
    page, per_page = page_args(default_per_page=20, max_per_page=50)
    items, meta = paginate(query.order_by(Report.created_at.desc(), Report.id.desc()), page, per_page)
    return jsonify({"items": [report.to_dict() for report in items], **meta})


@bp.post("/reports/<int:report_id>/<action>")
@admin_required
def update_report(report_id: int, action: str):
    if action not in ("resolve", "dismiss"):
        raise ApiError("Not found.", 404)
    report = db.session.get(Report, report_id)
    if report is None:
        raise ApiError("Report not found.", 404)
    report.status = "resolved" if action == "resolve" else "dismissed"
    report.resolved_at = utcnow()
    log_admin(g.user, f"{action}_report", "report", report.id, report.listing.title if report.listing else None)
    db.session.commit()
    return jsonify(report.to_dict())


@bp.get("/users")
@admin_required
def list_users():
    query = User.query
    text = (request.args.get("q") or "").strip()[:100]
    if text:
        like = f"%{escape_like(text)}%"
        query = query.filter(or_(User.name.ilike(like, escape="\\"), User.email.ilike(like, escape="\\")))
    page, per_page = page_args(default_per_page=20, max_per_page=50)
    users, meta = paginate(query.order_by(User.created_at.desc(), User.id.desc()), page, per_page)
    counts = dict(
        db.session.query(Listing.seller_id, func.count(Listing.id))
        .filter(Listing.seller_id.in_([user.id for user in users] or [0]))
        .group_by(Listing.seller_id)
        .all()
    )
    items = [{**user.private_dict(), "listing_count": counts.get(user.id, 0)} for user in users]
    return jsonify({"items": items, **meta})


@bp.post("/users/<int:user_id>/<action>")
@admin_required
def block_user(user_id: int, action: str):
    if action not in ("block", "unblock"):
        raise ApiError("Not found.", 404)
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError("User not found.", 404)
    if user.is_admin:
        raise ApiError("Administrator accounts can't be blocked.", 400)
    user.is_blocked = action == "block"
    log_admin(g.user, f"{action}_user", "user", user.id, user.email)
    db.session.commit()
    return jsonify(user.private_dict())


@bp.get("/actions")
@admin_required
def list_actions():
    page, per_page = page_args(default_per_page=30, max_per_page=100)
    items, meta = paginate(AdminAction.query.order_by(AdminAction.created_at.desc(), AdminAction.id.desc()), page, per_page)
    return jsonify({"items": [action.to_dict() for action in items], **meta})


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "category"


def _category_values():
    data = json_body()
    validator = Validator(data).string("name", "Name", required=True, min_len=2, max_len=80)
    rate = data.get("depreciation_rate")
    if rate in (None, ""):
        validator.values["depreciation_rate"] = 0.2
    else:
        try:
            rate = float(rate)
            if not 0 <= rate <= 0.9:
                raise ValueError
            validator.values["depreciation_rate"] = rate
        except (TypeError, ValueError):
            validator.add_error("depreciation_rate", "Depreciation must be a number between 0 and 0.9.")
    return validator.check()


@bp.post("/categories")
@admin_required
def create_category():
    values = _category_values()
    slug = _slugify(values["name"])
    if Category.query.filter(or_(Category.name == values["name"], Category.slug == slug)).first():
        raise ApiError("A category with this name already exists.", 409, {"name": "Already exists."})
    category = Category(name=values["name"], slug=slug, depreciation_rate=values["depreciation_rate"])
    db.session.add(category)
    db.session.flush()
    log_admin(g.user, "create_category", "category", category.id, category.name)
    db.session.commit()
    return jsonify(category.to_dict(listing_count=0)), 201


@bp.put("/categories/<int:category_id>")
@admin_required
def update_category(category_id: int):
    category = db.session.get(Category, category_id)
    if category is None:
        raise ApiError("Category not found.", 404)
    values = _category_values()
    slug = _slugify(values["name"])
    clash = Category.query.filter(Category.id != category.id, or_(Category.name == values["name"], Category.slug == slug))
    if clash.first():
        raise ApiError("A category with this name already exists.", 409, {"name": "Already exists."})
    category.name, category.slug, category.depreciation_rate = values["name"], slug, values["depreciation_rate"]
    log_admin(g.user, "update_category", "category", category.id, category.name)
    db.session.commit()
    return jsonify(category.to_dict())


@bp.delete("/categories/<int:category_id>")
@admin_required
def delete_category(category_id: int):
    category = db.session.get(Category, category_id)
    if category is None:
        raise ApiError("Category not found.", 404)
    if Listing.query.filter_by(category_id=category.id).first():
        raise ApiError("This category still has listings. Move or delete them first.", 409)
    log_admin(g.user, "delete_category", "category", category.id, category.name)
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted."})


@bp.get("/orders")
@admin_required
def list_orders():
    query = Order.query.options(joinedload(Order.buyer), joinedload(Order.seller), joinedload(Order.listing))
    status = request.args.get("status")
    if status == "active":
        query = query.filter(Order.status.in_(ACTIVE_ORDER_STATUSES))
    elif status in ORDER_STATUSES:
        query = query.filter(Order.status == status)
    text = (request.args.get("q") or "").strip()[:100]
    if text:
        query = query.filter(Order.listing_title.ilike(f"%{escape_like(text)}%", escape="\\"))
    page, per_page = page_args(default_per_page=20, max_per_page=50)
    items, meta = paginate(query.order_by(Order.updated_at.desc(), Order.id.desc()), page, per_page)
    return jsonify({"items": [order.to_dict(admin=True) for order in items], **meta})


@bp.post("/orders/<int:order_id>/cancel")
@admin_required
def cancel_order(order_id: int):
    order = db.session.get(Order, order_id)
    if order is None:
        raise ApiError("Order not found.", 404)
    if order.status not in ACTIVE_ORDER_STATUSES:
        raise ApiError("Only active orders can be cancelled.", 409)
    reason = _reason()
    if order.status in ("accepted", "shipped"):
        release_listing(order)
    order.status = "cancelled"
    order.cancelled_by = "admin"
    order.status_note = reason
    order.closed_at = utcnow()
    for user_id in (order.buyer_id, order.seller_id):
        notify(user_id, "order", f'An administrator cancelled the order for "{order.listing_title}": {reason}',
               f"/orders/{order.id}")
    log_admin(g.user, "cancel_order", "order", order.id, reason)
    db.session.commit()
    return jsonify(order.to_dict(admin=True))

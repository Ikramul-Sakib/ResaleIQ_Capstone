import json
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

CONDITIONS = {
    "new": "New",
    "like_new": "Like new",
    "good": "Good",
    "fair": "Fair",
    "poor": "Poor",
}

# "reserved" = a seller accepted an order and the item is waiting for hand-over.
LISTING_STATUSES = ("pending", "approved", "reserved", "rejected", "sold", "removed")
PUBLIC_LISTING_STATUSES = ("approved", "reserved", "sold")

ORDER_STATUSES = ("pending", "accepted", "shipped", "completed", "declined", "cancelled")
ACTIVE_ORDER_STATUSES = ("pending", "accepted", "shipped")
PAYMENT_METHODS = {"cod": "Cash on delivery", "bkash": "bKash", "nagad": "Nagad"}
DELIVERY_METHODS = {"meetup": "Meet in person", "delivery": "Home delivery"}

REPORT_REASONS = {
    "fraud": "Fraud or scam",
    "misleading": "Misleading information",
    "prohibited": "Prohibited item",
    "duplicate": "Duplicate listing",
    "offensive": "Offensive content",
    "other": "Other",
}


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no time zone type)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") + "Z" if value else None


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    location = db.Column(db.String(100))
    bio = db.Column(db.String(500))
    role = db.Column(db.String(20), nullable=False, default="user")  # user | admin
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    token_version = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    listings = db.relationship("Listing", back_populates="seller", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.token_version = (self.token_version or 0) + 1  # log out old sessions

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "bio": self.bio,
            "member_since": iso(self.created_at),
        }

    def private_dict(self) -> dict:
        return {
            **self.public_dict(),
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_blocked": self.is_blocked,
        }


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    slug = db.Column(db.String(80), nullable=False, unique=True, index=True)
    # Approximate value lost per year, used by the rule-based price estimator.
    depreciation_rate = db.Column(db.Float, nullable=False, default=0.2)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self, listing_count: int | None = None) -> dict:
        data = {"id": self.id, "name": self.name, "slug": self.slug, "depreciation_rate": self.depreciation_rate}
        if listing_count is not None:
            data["listing_count"] = listing_count
        return data


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    brand = db.Column(db.String(80))
    model = db.Column(db.String(80))
    price = db.Column(db.Integer, nullable=False)  # Bangladeshi Taka
    condition = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    rejection_reason = db.Column(db.String(500))
    sold_price = db.Column(db.Integer)
    views = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    approved_at = db.Column(db.DateTime)
    sold_at = db.Column(db.DateTime)

    seller = db.relationship("User", back_populates="listings")
    category = db.relationship("Category")
    images = db.relationship(
        "ListingImage", order_by="ListingImage.sort_order", cascade="all, delete-orphan", back_populates="listing"
    )
    conversations = db.relationship("Conversation", cascade="all, delete-orphan", back_populates="listing")
    reports = db.relationship("Report", cascade="all, delete-orphan", back_populates="listing")
    wishlist_entries = db.relationship("WishlistItem", cascade="all, delete-orphan", back_populates="listing")
    cart_entries = db.relationship("CartItem", cascade="all, delete-orphan", back_populates="listing")
    # Orders are kept (listing_id set to NULL) when a listing is deleted.
    orders = db.relationship("Order", back_populates="listing")

    def to_dict(self, detail: bool = False, private: bool = False) -> dict:
        data = {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "condition": self.condition,
            "condition_label": CONDITIONS.get(self.condition, self.condition),
            "location": self.location,
            "status": self.status,
            "category": {"id": self.category.id, "name": self.category.name, "slug": self.category.slug}
            if self.category
            else None,
            "image": self.images[0].url if self.images else None,
            "views": self.views,
            "seller_id": self.seller_id,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "approved_at": iso(self.approved_at),
        }
        if detail:
            data.update(
                {
                    "description": self.description,
                    "brand": self.brand,
                    "model": self.model,
                    "images": [image.to_dict() for image in self.images],
                    "seller": self.seller.public_dict() if self.seller else None,
                    "sold_at": iso(self.sold_at),
                }
            )
        if private:
            data["rejection_reason"] = self.rejection_reason
            data["sold_price"] = self.sold_price
        return data


class ListingImage(db.Model):
    __tablename__ = "listing_images"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(db.String(64), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    listing = db.relationship("Listing", back_populates="images")

    @property
    def url(self) -> str:
        return f"/uploads/{self.filename}"

    def to_dict(self) -> dict:
        return {"id": self.id, "url": self.url}


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"
    __table_args__ = (db.UniqueConstraint("user_id", "listing_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    listing = db.relationship("Listing", back_populates="wishlist_entries")


class Conversation(db.Model):
    __tablename__ = "conversations"
    __table_args__ = (db.UniqueConstraint("listing_id", "buyer_id"),)

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    listing = db.relationship("Listing", back_populates="conversations")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])
    messages = db.relationship(
        "Message", order_by="Message.created_at", cascade="all, delete-orphan", back_populates="conversation"
    )

    def other_user(self, user_id: int) -> "User":
        return self.seller if user_id == self.buyer_id else self.buyer


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "body": self.body,
            "is_read": self.is_read,
            "created_at": iso(self.created_at),
        }


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason = db.Column(db.String(30), nullable=False)
    details = db.Column(db.String(1000))
    status = db.Column(db.String(20), nullable=False, default="open")  # open | resolved | dismissed
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    resolved_at = db.Column(db.DateTime)

    listing = db.relationship("Listing", back_populates="reports")
    reporter = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reason": self.reason,
            "reason_label": REPORT_REASONS.get(self.reason, self.reason),
            "details": self.details,
            "status": self.status,
            "created_at": iso(self.created_at),
            "resolved_at": iso(self.resolved_at),
            "reporter": {"id": self.reporter.id, "name": self.reporter.name} if self.reporter else None,
            "listing": self.listing.to_dict() if self.listing else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(db.String(40), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "link": self.link,
            "is_read": self.is_read,
            "created_at": iso(self.created_at),
        }


class PriceEstimate(db.Model):
    __tablename__ = "price_estimates"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="SET NULL"))
    inputs = db.Column(db.Text, nullable=False)
    min_price = db.Column(db.Integer, nullable=False)
    recommended_price = db.Column(db.Integer, nullable=False)
    max_price = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(10), nullable=False)  # ai | rules
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "inputs": json.loads(self.inputs),
            "min_price": self.min_price,
            "recommended_price": self.recommended_price,
            "max_price": self.max_price,
            "explanation": json.loads(self.explanation),
            "source": self.source,
            "created_at": iso(self.created_at),
        }


class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User")


class AdminAction(db.Model):
    __tablename__ = "admin_actions"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    action = db.Column(db.String(40), nullable=False)
    target_type = db.Column(db.String(20), nullable=False)
    target_id = db.Column(db.Integer)
    note = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    admin = db.relationship("User")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "admin": self.admin.name if self.admin else "Deleted admin",
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "note": self.note,
            "created_at": iso(self.created_at),
        }


class CartItem(db.Model):
    __tablename__ = "cart_items"
    __table_args__ = (db.UniqueConstraint("user_id", "listing_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    listing = db.relationship("Listing", back_populates="cart_entries")


class Order(db.Model):
    """One buyer buying one listing. Listing details are copied so the order history
    survives even if the seller later deletes the listing."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id", ondelete="SET NULL"), index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    listing_title = db.Column(db.String(120), nullable=False)
    listing_image = db.Column(db.String(100))
    list_price = db.Column(db.Integer, nullable=False)  # asking price when ordered
    price = db.Column(db.Integer, nullable=False)  # agreed price (offer or asking price)
    is_offer = db.Column(db.Boolean, nullable=False, default=False)

    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    delivery_method = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.String(300))
    contact_phone = db.Column(db.String(30), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default="unpaid")  # unpaid | paid
    transaction_id = db.Column(db.String(40))
    buyer_note = db.Column(db.String(500))
    status_note = db.Column(db.String(500))  # reason for decline / cancellation
    cancelled_by = db.Column(db.String(20))  # buyer | seller | admin | system

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    accepted_at = db.Column(db.DateTime)
    shipped_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)  # declined or cancelled

    listing = db.relationship("Listing", back_populates="orders")
    buyer = db.relationship("User", foreign_keys=[buyer_id])
    seller = db.relationship("User", foreign_keys=[seller_id])
    review = db.relationship("Review", uselist=False, back_populates="order", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_ORDER_STATUSES

    def to_dict(self, viewer_id: int | None = None, admin: bool = False) -> dict:
        role = "buyer" if viewer_id == self.buyer_id else "seller" if viewer_id == self.seller_id else None
        # Contact details are shared only once the seller has accepted the order.
        share_contacts = admin or self.status in ("accepted", "shipped", "completed")
        data = {
            "id": self.id,
            "role": role,
            "listing": {
                "id": self.listing_id,
                "title": self.listing_title,
                "image": f"/uploads/{self.listing_image}" if self.listing_image else None,
                "status": self.listing.status if self.listing else "deleted",
            },
            "buyer": {"id": self.buyer.id, "name": self.buyer.name} if self.buyer else None,
            "seller": {"id": self.seller.id, "name": self.seller.name} if self.seller else None,
            "list_price": self.list_price,
            "price": self.price,
            "is_offer": self.is_offer,
            "status": self.status,
            "delivery_method": self.delivery_method,
            "delivery_method_label": DELIVERY_METHODS.get(self.delivery_method, self.delivery_method),
            "payment_method": self.payment_method,
            "payment_method_label": PAYMENT_METHODS.get(self.payment_method, self.payment_method),
            "payment_status": self.payment_status,
            "transaction_id": self.transaction_id,
            "buyer_note": self.buyer_note,
            "status_note": self.status_note,
            "cancelled_by": self.cancelled_by,
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
            "accepted_at": iso(self.accepted_at),
            "shipped_at": iso(self.shipped_at),
            "completed_at": iso(self.completed_at),
            "closed_at": iso(self.closed_at),
            "review": self.review.to_dict() if self.review else None,
        }
        if share_contacts or role == "buyer":
            data["delivery_address"] = self.delivery_address
            data["contact_phone"] = self.contact_phone
        if share_contacts and self.seller:
            data["seller_phone"] = self.seller.phone
        return data


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    order = db.relationship("Order", back_populates="review")
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "reviewer": {"id": self.reviewer.id, "name": self.reviewer.name} if self.reviewer else None,
            "listing_title": self.order.listing_title if self.order else None,
            "created_at": iso(self.created_at),
        }


def seller_rating(user_id: int) -> dict:
    average, count = db.session.query(db.func.avg(Review.rating), db.func.count(Review.id)).filter(
        Review.seller_id == user_id
    ).one()
    return {"rating_avg": round(float(average), 1) if average else None, "rating_count": count}

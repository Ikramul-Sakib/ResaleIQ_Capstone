"""Default data (categories + first admin) and optional demo data."""

import logging
import os
import random
import uuid
from datetime import timedelta

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

from .extensions import db
from .models import Category, Listing, ListingImage, Order, Review, User, utcnow

log = logging.getLogger(__name__)

# name, slug, approximate share of value lost per year
DEFAULT_CATEGORIES = [
    ("Mobile Phones", "mobile-phones", 0.30),
    ("Laptops & Computers", "laptops-computers", 0.25),
    ("Electronics", "electronics", 0.25),
    ("Home Appliances", "home-appliances", 0.15),
    ("Furniture", "furniture", 0.12),
    ("Vehicles", "vehicles", 0.10),
    ("Fashion & Clothing", "fashion-clothing", 0.35),
    ("Books & Education", "books-education", 0.20),
    ("Sports & Fitness", "sports-fitness", 0.20),
    ("Baby & Kids", "baby-kids", 0.25),
    ("Others", "others", 0.20),
]


def seed_defaults() -> None:
    if Category.query.count() == 0:
        for name, slug, rate in DEFAULT_CATEGORIES:
            db.session.add(Category(name=name, slug=slug, depreciation_rate=rate))
        db.session.commit()

    if not User.query.filter_by(role="admin").first():
        config = current_app.config
        admin = User.query.filter_by(email=config["ADMIN_EMAIL"]).first()
        if admin is None:
            admin = User(name="ResaleIQ Admin", email=config["ADMIN_EMAIL"])
            admin.set_password(config["ADMIN_PASSWORD"])
            db.session.add(admin)
        admin.role = "admin"
        db.session.commit()
        log.warning("Created administrator account %s - change its password after first login.", admin.email)


DEMO_USERS = [
    ("Rahim Uddin", "rahim@demo.resaleiq", "Dhaka"),
    ("Nusrat Jahan", "nusrat@demo.resaleiq", "Chattogram"),
    ("Tanvir Ahmed", "tanvir@demo.resaleiq", "Sylhet"),
]

DEMO_LISTINGS = [
    ("mobile-phones", "iPhone 13 128GB Midnight", "Apple", "iPhone 13", 62000, "good", 0),
    ("mobile-phones", "Samsung Galaxy A54 8/256GB", "Samsung", "Galaxy A54", 28500, "like_new", 1),
    ("mobile-phones", "Xiaomi Redmi Note 12 6/128", "Xiaomi", "Redmi Note 12", 14000, "fair", 2),
    ("laptops-computers", "HP Pavilion 15 Core i5 11th Gen", "HP", "Pavilion 15", 48000, "good", 1),
    ("laptops-computers", "MacBook Air M1 8GB/256GB", "Apple", "MacBook Air M1", 72000, "like_new", 0),
    ("electronics", "Sony WH-1000XM4 Headphones", "Sony", "WH-1000XM4", 18500, "good", 2),
    ("home-appliances", "Walton 1.5 Ton Inverter AC", "Walton", "WSI-Inverna", 38000, "good", 0),
    ("furniture", "Solid Wood Study Table with Chair", None, None, 9500, "fair", 1),
    ("vehicles", "Yamaha FZS V3 2021 Motorcycle", "Yamaha", "FZS V3", 215000, "good", 2),
    ("books-education", "HSC Science Complete Book Set", None, None, 1800, "good", 0),
    ("sports-fitness", "Adjustable Dumbbell Set 20kg", None, None, 4200, "like_new", 1),
    ("fashion-clothing", "Men's Leather Jacket (Size L)", None, None, 3500, "like_new", 2),
]

COLORS = [(15, 118, 110), (37, 99, 235), (124, 58, 237), (217, 119, 6), (190, 24, 93), (22, 163, 74)]


def _placeholder_image(title: str, color) -> str:
    image = Image.new("RGB", (1200, 900), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([60, 60, 1140, 840], outline=(255, 255, 255), width=6)
    words, lines, line = title.split(), [], ""
    for word in words:
        if len(line + " " + word) > 22:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    lines.append(line)
    font = None
    for name in ("arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arial.ttf"):
        try:
            font = ImageFont.truetype(name, 64)
            break
        except OSError:
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=64)
        except Exception:
            font = ImageFont.load_default()
    y = 450 - len(lines) * 40
    for text in lines:
        draw.text((600, y), text, fill=(255, 255, 255), anchor="mm", font=font)
        y += 80
    filename = f"{uuid.uuid4().hex}.jpg"
    image.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename), "JPEG", quality=85)
    return filename


def seed_demo() -> int:
    """Create demo sellers and listings so the marketplace isn't empty. Safe to run twice."""
    if User.query.filter(User.email.like("%@demo.resaleiq")).first():
        return 0
    users = []
    for name, email, location in DEMO_USERS:
        user = User(name=name, email=email, location=location, phone="01700-000000")
        user.set_password("Demo@12345")
        db.session.add(user)
        users.append(user)
    db.session.flush()

    categories = {category.slug: category for category in Category.query.all()}
    now = utcnow()
    listings = []
    for index, (slug, title, brand, model, price, condition, seller_index) in enumerate(DEMO_LISTINGS):
        seller = users[seller_index]
        status = "pending" if index in (2, 7) else "approved"
        listing = Listing(
            seller_id=seller.id,
            category_id=categories[slug].id,
            title=title,
            description=(
                f"{title} in {condition.replace('_', ' ')} condition. Used carefully and works perfectly. "
                "Original box and accessories included where available. Price is slightly negotiable."
            ),
            brand=brand,
            model=model,
            price=price,
            condition=condition,
            location=seller.location,
            status=status,
            views=random.randint(5, 180),
            created_at=now - timedelta(days=index),
            approved_at=(now - timedelta(days=index, hours=-2)) if status == "approved" else None,
        )
        listing.images = [ListingImage(filename=_placeholder_image(title, COLORS[index % len(COLORS)]), sort_order=0)]
        db.session.add(listing)
        listings.append(listing)
    db.session.flush()

    # A finished sale with a review, and an offer waiting for the seller.
    headphones, iphone = listings[5], listings[0]
    sale = Order(
        listing_id=headphones.id, buyer_id=users[0].id, seller_id=headphones.seller_id,
        listing_title=headphones.title, listing_image=headphones.images[0].filename,
        list_price=headphones.price, price=17500, is_offer=True, status="completed",
        delivery_method="meetup", contact_phone="01700-000000", payment_method="bkash",
        payment_status="paid", transaction_id="8N7A6B5C4D",
        created_at=now - timedelta(days=3), accepted_at=now - timedelta(days=3),
        shipped_at=now - timedelta(days=2), completed_at=now - timedelta(days=2),
    )
    headphones.status, headphones.sold_price, headphones.sold_at = "sold", 17500, now - timedelta(days=2)
    db.session.add(sale)
    db.session.flush()
    db.session.add(Review(order_id=sale.id, reviewer_id=users[0].id, seller_id=headphones.seller_id, rating=5,
                          comment="Exactly as described and the seller was on time. Recommended!"))
    db.session.add(Order(
        listing_id=iphone.id, buyer_id=users[1].id, seller_id=iphone.seller_id,
        listing_title=iphone.title, listing_image=iphone.images[0].filename,
        list_price=iphone.price, price=58000, is_offer=True, delivery_method="delivery",
        delivery_address="House 12, Road 5, Agrabad, Chattogram", contact_phone="01800-000000",
        payment_method="cod", buyer_note="Can you include the original charger?",
    ))
    db.session.commit()
    return len(DEMO_LISTINGS)

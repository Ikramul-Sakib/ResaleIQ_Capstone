import json
from datetime import timedelta

from flask import Blueprint, current_app, g, jsonify

from ..errors import ApiError
from ..extensions import db
from ..models import CONDITIONS, Category, Listing, PriceEstimate, utcnow
from ..security import login_required
from ..services.pricing import estimate_price
from ..validation import Validator, json_body

bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@bp.get("/status")
def status():
    enabled = bool(current_app.config["GEMINI_API_KEY"])
    return jsonify(
        {
            "ai_enabled": enabled,
            "provider": "Google Gemini" if enabled else None,
            "model": current_app.config["GEMINI_MODEL"] if enabled else None,
        }
    )


@bp.post("/estimate-price")
@login_required
def estimate():
    values = (
        Validator(json_body())
        .string("title", "Product name", required=True, min_len=3, max_len=120)
        .integer("category_id", "Category", required=True)
        .choice("condition", "Condition", CONDITIONS, required=True)
        .string("brand", "Brand", max_len=80)
        .string("model", "Model", max_len=80)
        .string("description", "Description", max_len=1000)
        .integer("original_price", "Original price", min_value=1, max_value=50_000_000)
        .integer("age_months", "Age", min_value=0, max_value=600)
        .integer("listing_id", "Listing")
        .check()
    )
    category = db.session.get(Category, values["category_id"]) if values["category_id"] else None
    if category is None:
        raise ApiError("Please fix the highlighted fields.", 422, {"category_id": "Choose a valid category."})

    listing_id = values.get("listing_id")
    if listing_id is not None:
        listing = db.session.get(Listing, listing_id)
        if listing is None or listing.seller_id != g.user.id:
            listing_id = values["listing_id"] = None

    limit = current_app.config["AI_ESTIMATES_PER_HOUR"]
    recent = PriceEstimate.query.filter(
        PriceEstimate.user_id == g.user.id, PriceEstimate.created_at >= utcnow() - timedelta(hours=1)
    ).count()
    if recent >= limit:
        raise ApiError(f"You can request up to {limit} price estimates per hour. Please try again later.", 429)

    result = estimate_price(current_app.config, values, category)
    db.session.add(
        PriceEstimate(
            user_id=g.user.id,
            listing_id=listing_id,
            inputs=json.dumps(values, ensure_ascii=False),
            min_price=result["min_price"],
            recommended_price=result["recommended_price"],
            max_price=result["max_price"],
            explanation=json.dumps(result["explanation"], ensure_ascii=False),
            source=result["source"],
        )
    )
    db.session.commit()
    return jsonify({**result, "currency": "BDT"})

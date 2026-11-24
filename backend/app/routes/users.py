from flask import Blueprint, g, jsonify
from sqlalchemy import func

from ..errors import ApiError
from ..extensions import db
from ..models import Listing, User, seller_rating
from ..security import create_token, login_required
from ..validation import Validator, json_body

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("/me")
@login_required
def get_me():
    return jsonify({"user": g.user.private_dict()})


@bp.put("/me")
@login_required
def update_me():
    values = (
        Validator(json_body())
        .string("name", "Name", required=True, min_len=2, max_len=100)
        .string("phone", "Phone", max_len=30)
        .string("location", "Location", max_len=100)
        .string("bio", "About you", max_len=500)
        .check()
    )
    user = g.user
    user.name = values["name"]
    user.phone = values["phone"]
    user.location = values["location"]
    user.bio = values["bio"]
    db.session.commit()
    return jsonify({"user": user.private_dict()})


@bp.put("/me/password")
@login_required
def change_password():
    data = json_body()
    values = Validator(data).password("new_password", "New password").check()
    if not g.user.check_password(str(data.get("current_password") or "")):
        raise ApiError("Your current password is incorrect.", 422, {"current_password": "Incorrect password."})
    g.user.set_password(values["new_password"])
    db.session.commit()
    # Old tokens stop working after a password change, so hand back a fresh one.
    return jsonify({"message": "Password updated.", "token": create_token(g.user)})


@bp.get("/<int:user_id>")
def public_profile(user_id: int):
    user = db.session.get(User, user_id)
    if user is None or user.is_blocked:
        raise ApiError("Seller not found.", 404)
    counts = dict(
        db.session.query(Listing.status, func.count(Listing.id))
        .filter(Listing.seller_id == user.id)
        .group_by(Listing.status)
        .all()
    )
    return jsonify(
        {
            "user": user.public_dict(),
            "stats": {
                "active_listings": counts.get("approved", 0),
                "sold_listings": counts.get("sold", 0),
                **seller_rating(user.id),
            },
        }
    )

import hashlib
import logging
import secrets
from datetime import timedelta

from flask import Blueprint, current_app, g, jsonify

from ..errors import ApiError
from ..extensions import db
from ..models import PasswordReset, User, utcnow
from ..security import create_token, login_required
from ..validation import Validator, json_body

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
log = logging.getLogger(__name__)


def _session(user: User):
    return {"token": create_token(user), "user": user.private_dict()}


@bp.post("/register")
def register():
    values = (
        Validator(json_body())
        .string("name", "Name", required=True, min_len=2, max_len=100)
        .email()
        .password()
        .check()
    )
    if User.query.filter_by(email=values["email"]).first():
        raise ApiError("An account with this email already exists.", 409, {"email": "This email is already registered."})
    user = User(name=values["name"], email=values["email"])
    user.set_password(values["password"])
    db.session.add(user)
    db.session.commit()
    return jsonify(_session(user)), 201


@bp.post("/login")
def login():
    data = json_body()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")
    user = User.query.filter_by(email=email).first() if email else None
    if user is None or not user.check_password(password):
        raise ApiError("Incorrect email or password.", 401)
    if user.is_blocked:
        raise ApiError("Your account has been blocked. Contact support for help.", 403)
    return jsonify(_session(user))


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": g.user.private_dict()})


@bp.post("/forgot-password")
def forgot_password():
    values = Validator(json_body()).email().check()
    response = {"message": "If an account exists for this email, a password reset link has been sent."}
    user = User.query.filter_by(email=values["email"]).first()
    if user and not user.is_blocked:
        token = secrets.token_urlsafe(32)
        db.session.add(
            PasswordReset(
                user_id=user.id,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=utcnow() + timedelta(hours=1),
            )
        )
        db.session.commit()
        link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"
        # No email service is configured: the link is written to the server log.
        log.warning("Password reset link for %s: %s", user.email, link)
        if current_app.config["EXPOSE_RESET_LINK"]:
            response["dev_reset_link"] = link
    return jsonify(response)


@bp.post("/reset-password")
def reset_password():
    data = json_body()
    values = Validator(data).string("token", "Reset token", required=True, max_len=200).password().check()
    token_hash = hashlib.sha256(values["token"].encode()).hexdigest()
    reset = PasswordReset.query.filter_by(token_hash=token_hash).first()
    if reset is None or reset.used or reset.expires_at < utcnow():
        raise ApiError("This reset link is invalid or has expired. Request a new one.", 400)
    reset.used = True
    reset.user.set_password(values["password"])
    db.session.commit()
    return jsonify({"message": "Your password has been reset. You can now log in."})

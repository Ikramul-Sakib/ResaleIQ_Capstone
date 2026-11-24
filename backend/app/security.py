"""Login tokens (JWT) and route decorators for authentication and roles."""

from datetime import timedelta
from functools import wraps

import jwt
from flask import current_app, g, request

from .errors import ApiError
from .extensions import db
from .models import User, utcnow


def create_token(user: User) -> str:
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "tv": user.token_version,
        "iat": now,
        "exp": now + timedelta(hours=current_app.config["JWT_EXPIRES_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _user_from_token() -> User | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header[7:].strip()
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user = db.session.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        return None
    if user is None or payload.get("tv") != user.token_version:
        return None  # deleted user, or password changed since the token was issued
    return user


def optional_user() -> User | None:
    user = _user_from_token()
    return None if user is None or user.is_blocked else user


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = _user_from_token()
        if user is None:
            raise ApiError("Please log in to continue.", 401)
        if user.is_blocked:
            raise ApiError("Your account has been blocked. Contact support for help.", 403)
        g.user = user
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not g.user.is_admin:
            raise ApiError("Administrator access is required.", 403)
        return view(*args, **kwargs)

    return wrapper

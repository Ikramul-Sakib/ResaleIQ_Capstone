"""Small input-validation helper that collects all field errors before failing."""

import re

from flask import request

from .errors import ApiError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def json_body() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ApiError("The request body must be a JSON object.")
    return data


class Validator:
    def __init__(self, data):
        self.data = data or {}
        self.errors: dict[str, str] = {}
        self.values: dict = {}

    def _raw(self, name):
        value = self.data.get(name)
        if isinstance(value, str):
            value = value.strip()
        return None if value in ("", None) else value

    def string(self, name, label, required=False, min_len=0, max_len=255):
        value = self._raw(name)
        if value is None:
            if required:
                self.errors[name] = f"{label} is required."
            self.values[name] = None
            return self
        value = str(value)
        if len(value) < min_len:
            self.errors[name] = f"{label} must be at least {min_len} characters."
        elif len(value) > max_len:
            self.errors[name] = f"{label} must be at most {max_len} characters."
        self.values[name] = value
        return self

    def integer(self, name, label, required=False, min_value=None, max_value=None):
        value = self._raw(name)
        if value is None:
            if required:
                self.errors[name] = f"{label} is required."
            self.values[name] = None
            return self
        try:
            number = int(str(value).replace(",", ""))
        except (TypeError, ValueError):
            self.errors[name] = f"{label} must be a whole number."
            self.values[name] = None
            return self
        if min_value is not None and number < min_value:
            self.errors[name] = f"{label} must be at least {min_value:,}."
        elif max_value is not None and number > max_value:
            self.errors[name] = f"{label} must be at most {max_value:,}."
        self.values[name] = number
        return self

    def choice(self, name, label, choices, required=False):
        value = self._raw(name)
        if value is None:
            if required:
                self.errors[name] = f"{label} is required."
        elif value not in choices:
            self.errors[name] = f"Choose a valid {label.lower()}."
        self.values[name] = value
        return self

    def email(self, name="email"):
        value = self._raw(name)
        if value is None:
            self.errors[name] = "Email is required."
        elif len(value) > 255 or not EMAIL_RE.match(value):
            self.errors[name] = "Enter a valid email address."
        self.values[name] = value.lower() if isinstance(value, str) else None
        return self

    def password(self, name="password", label="Password"):
        value = self.data.get(name)
        if not value:
            self.errors[name] = f"{label} is required."
        elif len(value) < 8:
            self.errors[name] = f"{label} must be at least 8 characters."
        elif len(value) > 128:
            self.errors[name] = f"{label} must be at most 128 characters."
        elif not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value)):
            self.errors[name] = f"{label} must contain at least one letter and one number."
        self.values[name] = value
        return self

    def add_error(self, name, message):
        self.errors.setdefault(name, message)
        return self

    def check(self) -> dict:
        if self.errors:
            raise ApiError("Please fix the highlighted fields.", 422, self.errors)
        return self.values


def page_args(default_per_page=12, max_per_page=48) -> tuple[int, int]:
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        per_page = min(max_per_page, max(1, int(request.args.get("per_page", default_per_page))))
    except ValueError:
        per_page = default_per_page
    return page, per_page


def paginate(query, page: int, per_page: int):
    total = query.order_by(None).count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return items, {"page": page, "per_page": per_page, "total": total, "pages": pages}


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

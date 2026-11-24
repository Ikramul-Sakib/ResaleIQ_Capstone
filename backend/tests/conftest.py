import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

ADMIN = {"email": "admin@test.local", "password": "Admin@12345"}


@pytest.fixture
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "test.db").as_posix(),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes-long",
            "ADMIN_EMAIL": ADMIN["email"],
            "ADMIN_PASSWORD": ADMIN["password"],
            "GEMINI_API_KEY": "",
            "EXPOSE_RESET_LINK": True,
        }
    )
    (tmp_path / "uploads").mkdir(exist_ok=True)
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def png_bytes(color=(200, 30, 30), size=(64, 48)) -> io.BytesIO:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(client, name="Test User", email="user@test.local", password="Secret123"):
    response = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["token"]


def admin_token(client):
    response = client.post("/api/auth/login", json=ADMIN)
    assert response.status_code == 200, response.get_json()
    return response.get_json()["token"]


def category_id(client, slug="mobile-phones"):
    return next(c["id"] for c in client.get("/api/categories").get_json() if c["slug"] == slug)


def create_listing(client, token, **overrides):
    data = {
        "title": "iPhone 12 64GB Blue",
        "description": "Well kept phone with original charger and box, battery health 86 percent.",
        "category_id": str(category_id(client)),
        "price": "45000",
        "condition": "good",
        "location": "Dhaka",
        "brand": "Apple",
        "model": "iPhone 12",
        **overrides,
    }
    if "images" not in overrides:
        data["images"] = [(png_bytes(), "phone.png")]
    response = client.post("/api/listings", data=data, headers=auth(token), content_type="multipart/form-data")
    return response

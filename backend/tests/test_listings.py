import io
import os

from conftest import admin_token, auth, category_id, create_listing, png_bytes, register


def approve(client, listing_id):
    response = client.post(f"/api/admin/listings/{listing_id}/approve", headers=auth(admin_token(client)))
    assert response.status_code == 200, response.get_json()


def test_create_listing_saves_image_and_starts_pending(client, app):
    token = register(client)
    response = create_listing(client, token)
    assert response.status_code == 201, response.get_json()
    listing = response.get_json()
    assert listing["status"] == "pending"
    assert len(listing["images"]) == 1
    filename = listing["images"][0]["url"].rsplit("/", 1)[1]
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    assert client.get(listing["images"][0]["url"]).status_code == 200

    # pending listings are hidden from the public
    assert client.get(f"/api/listings/{listing['id']}").status_code == 404
    assert client.get("/api/listings").get_json()["total"] == 0
    # but visible to their owner
    assert client.get(f"/api/listings/{listing['id']}", headers=auth(token)).status_code == 200


def test_listing_requires_a_real_image(client):
    token = register(client)
    fake = (io.BytesIO(b"this is not an image"), "evil.jpg")
    response = create_listing(client, token, images=[fake])
    assert response.status_code == 422
    assert "images" in response.get_json()["error"]["fields"]

    response = create_listing(client, token, images=[])
    assert response.status_code == 422


def test_listing_field_validation(client):
    token = register(client)
    response = create_listing(client, token, title="abc", price="-5", condition="broken", category_id="9999")
    assert response.status_code == 422
    assert {"title", "price", "condition", "category_id"} <= set(response.get_json()["error"]["fields"])


def test_approval_search_and_filters(client):
    token = register(client)
    phone = create_listing(client, token).get_json()
    laptop = create_listing(
        client,
        token,
        title="Dell Inspiron 15 Laptop",
        brand="Dell",
        model="Inspiron",
        category_id=str(category_id(client, "laptops-computers")),
        price="30000",
        condition="fair",
        location="Sylhet",
    ).get_json()
    approve(client, phone["id"])
    approve(client, laptop["id"])

    everything = client.get("/api/listings").get_json()
    assert everything["total"] == 2
    assert client.get("/api/listings?q=iphone").get_json()["total"] == 1
    assert client.get("/api/listings?category=laptops-computers").get_json()["items"][0]["id"] == laptop["id"]
    assert client.get("/api/listings?min_price=40000").get_json()["total"] == 1
    assert client.get("/api/listings?max_price=40000").get_json()["total"] == 1
    assert client.get("/api/listings?condition=fair").get_json()["total"] == 1
    assert client.get("/api/listings?location=sylhet").get_json()["total"] == 1
    cheapest = client.get("/api/listings?sort=price_asc").get_json()["items"][0]
    assert cheapest["id"] == laptop["id"]
    # LIKE wildcards are treated literally
    assert client.get("/api/listings?q=%25").get_json()["total"] == 0


def test_only_owner_can_edit_or_delete(client):
    owner = register(client)
    other = register(client, name="Other", email="other@test.local")
    listing = create_listing(client, owner).get_json()

    edit = {"title": "Hacked title here", "description": "x" * 30, "category_id": str(category_id(client)),
            "price": "1", "condition": "good", "location": "Dhaka"}
    response = client.put(f"/api/listings/{listing['id']}", data=edit, headers=auth(other),
                          content_type="multipart/form-data")
    assert response.status_code == 403
    assert client.delete(f"/api/listings/{listing['id']}", headers=auth(other)).status_code == 403
    assert client.delete(f"/api/listings/{listing['id']}", headers=auth(owner)).status_code == 200


def test_editing_approved_listing_returns_it_to_review(client):
    token = register(client)
    listing = create_listing(client, token).get_json()
    approve(client, listing["id"])
    image_id = listing["images"][0]["id"]
    data = {
        "title": "iPhone 12 64GB Blue - price drop",
        "description": "Well kept phone with original charger and box, battery health 86 percent.",
        "category_id": str(category_id(client)),
        "price": "42000",
        "condition": "good",
        "location": "Dhaka",
        "keep_images": str(image_id),
        "images": [(png_bytes((0, 0, 255)), "second.png")],
    }
    response = client.put(f"/api/listings/{listing['id']}", data=data, headers=auth(token),
                          content_type="multipart/form-data")
    assert response.status_code == 200, response.get_json()
    updated = response.get_json()
    assert updated["status"] == "pending"
    assert updated["price"] == 42000
    assert len(updated["images"]) == 2
    assert updated["images"][0]["id"] == image_id


def test_mark_sold_and_dashboard_stats(client):
    token = register(client)
    listing = create_listing(client, token).get_json()
    assert client.post(f"/api/listings/{listing['id']}/sold", json={}, headers=auth(token)).status_code == 409
    approve(client, listing["id"])
    response = client.post(f"/api/listings/{listing['id']}/sold", json={"sold_price": 44000}, headers=auth(token))
    assert response.status_code == 200
    assert response.get_json()["status"] == "sold"

    mine = client.get("/api/listings/mine", headers=auth(token)).get_json()
    assert mine["stats"]["sold"] == 1
    assert mine["stats"]["sales_value"] == 44000


def test_admin_reject_notifies_seller(client):
    token = register(client)
    listing = create_listing(client, token).get_json()
    admin = admin_token(client)
    response = client.post(f"/api/admin/listings/{listing['id']}/reject", json={"reason": "Photos are blurry"},
                           headers=auth(admin))
    assert response.status_code == 200
    notes = client.get("/api/notifications", headers=auth(token)).get_json()
    assert notes["unread_count"] == 1
    assert "blurry" in notes["items"][0]["message"]
    mine = client.get("/api/listings/mine", headers=auth(token)).get_json()["items"][0]
    assert mine["rejection_reason"] == "Photos are blurry"


def test_non_admin_cannot_use_admin_api(client):
    token = register(client)
    assert client.get("/api/admin/stats", headers=auth(token)).status_code == 403
    assert client.get("/api/admin/stats").status_code == 401


def test_wishlist_and_report(client):
    seller = register(client)
    buyer = register(client, name="Buyer", email="buyer@test.local")
    listing = create_listing(client, seller).get_json()
    approve(client, listing["id"])

    assert client.post(f"/api/wishlist/{listing['id']}", headers=auth(buyer)).status_code == 201
    saved = client.get("/api/wishlist", headers=auth(buyer)).get_json()["items"]
    assert [item["id"] for item in saved] == [listing["id"]]
    assert client.get("/api/listings", headers=auth(buyer)).get_json()["items"][0]["in_wishlist"] is True
    assert client.delete(f"/api/wishlist/{listing['id']}", headers=auth(buyer)).status_code == 200

    report = client.post(f"/api/listings/{listing['id']}/report", json={"reason": "fraud"}, headers=auth(buyer))
    assert report.status_code == 201
    duplicate = client.post(f"/api/listings/{listing['id']}/report", json={"reason": "fraud"}, headers=auth(buyer))
    assert duplicate.status_code == 409

    admin = admin_token(client)
    reports = client.get("/api/admin/reports", headers=auth(admin)).get_json()["items"]
    assert len(reports) == 1
    removed = client.post(f"/api/admin/listings/{listing['id']}/remove", json={"reason": "Confirmed scam listing"},
                          headers=auth(admin))
    assert removed.status_code == 200
    assert client.get("/api/admin/reports", headers=auth(admin)).get_json()["total"] == 0
    assert client.get(f"/api/listings/{listing['id']}").status_code == 404


def test_blocked_user_cannot_log_in(client):
    token = register(client)
    admin = admin_token(client)
    user_id = client.get("/api/auth/me", headers=auth(token)).get_json()["user"]["id"]
    assert client.post(f"/api/admin/users/{user_id}/block", headers=auth(admin)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 403
    assert client.post("/api/auth/login", json={"email": "user@test.local", "password": "Secret123"}).status_code == 403

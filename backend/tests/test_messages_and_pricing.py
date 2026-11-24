from unittest import mock

from conftest import admin_token, auth, category_id, create_listing, register


def approved_listing(client, seller_token, **overrides):
    listing = create_listing(client, seller_token, **overrides).get_json()
    client.post(f"/api/admin/listings/{listing['id']}/approve", headers=auth(admin_token(client)))
    return listing


def test_conversation_flow(client):
    seller = register(client, name="Seller", email="seller@test.local")
    buyer = register(client, name="Buyer", email="buyer@test.local")
    listing = approved_listing(client, seller)

    started = client.post("/api/conversations", json={"listing_id": listing["id"], "body": "Is it available?"},
                          headers=auth(buyer))
    assert started.status_code == 201, started.get_json()
    conversation_id = started.get_json()["id"]

    # same buyer + listing reuses the conversation
    again = client.post("/api/conversations", json={"listing_id": listing["id"], "body": "Hello?"}, headers=auth(buyer))
    assert again.get_json()["id"] == conversation_id

    summary = client.get("/api/notifications/summary", headers=auth(seller)).get_json()
    assert summary["unread_messages"] == 2
    assert summary["unread_notifications"] == 2  # "listing approved" + one per conversation, not per message

    thread = client.get(f"/api/conversations/{conversation_id}", headers=auth(seller)).get_json()
    assert [m["body"] for m in thread["messages"]] == ["Is it available?", "Hello?"]
    assert client.get("/api/notifications/summary", headers=auth(seller)).get_json()["unread_messages"] == 0

    reply = client.post(f"/api/conversations/{conversation_id}/messages", json={"body": "Yes, it is."},
                        headers=auth(seller))
    assert reply.status_code == 201
    listed = client.get("/api/conversations", headers=auth(buyer)).get_json()["items"]
    assert listed[0]["unread_count"] == 1
    assert listed[0]["other_user"]["name"] == "Seller"


def test_outsiders_cannot_read_conversations(client):
    seller = register(client, name="Seller", email="seller@test.local")
    buyer = register(client, name="Buyer", email="buyer@test.local")
    stranger = register(client, name="Stranger", email="stranger@test.local")
    listing = approved_listing(client, seller)
    conversation_id = client.post(
        "/api/conversations", json={"listing_id": listing["id"], "body": "Hi"}, headers=auth(buyer)
    ).get_json()["id"]
    assert client.get(f"/api/conversations/{conversation_id}", headers=auth(stranger)).status_code == 404
    assert client.post("/api/conversations", json={"listing_id": listing["id"], "body": "Me"},
                       headers=auth(seller)).status_code == 400


def test_rule_based_estimate_without_ai(client):
    token = register(client)
    response = client.post(
        "/api/ai/estimate-price",
        json={
            "title": "iPhone 12 64GB",
            "category_id": category_id(client),
            "brand": "Apple",
            "condition": "good",
            "original_price": 90000,
            "age_months": 24,
        },
        headers=auth(token),
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["source"] == "rules"
    assert data["currency"] == "BDT"
    assert 0 < data["min_price"] <= data["recommended_price"] <= data["max_price"] < 90000
    assert data["explanation"]
    assert "not configured" in data["notice"]


def test_estimate_needs_original_price_or_comparables(client):
    token = register(client)
    response = client.post(
        "/api/ai/estimate-price",
        json={"title": "Rare thing", "category_id": category_id(client), "condition": "good"},
        headers=auth(token),
    )
    assert response.status_code == 422
    assert "original_price" in response.get_json()["error"]["fields"]


def test_estimate_uses_comparable_listings(client):
    seller = register(client, name="Seller", email="seller@test.local")
    for price in ("40000", "42000", "44000"):
        approved_listing(client, seller, price=price)
    token = register(client)
    data = client.post(
        "/api/ai/estimate-price",
        json={"title": "iPhone 12 128GB", "category_id": category_id(client), "brand": "Apple", "condition": "good"},
        headers=auth(token),
    ).get_json()
    assert data["comparables_count"] == 3
    assert data["recommended_price"] == 42000


def _fake_gemini_response(payload_text):
    response = mock.Mock(status_code=200)
    response.json.return_value = {"candidates": [{"content": {"parts": [{"text": payload_text}]}}]}
    return response


def test_gemini_estimate_used_when_configured(client, app):
    app.config["GEMINI_API_KEY"] = "test-key"
    token = register(client)
    body = (
        '{"min_price": 50000, "recommended_price": 55000, "max_price": 60000, "confidence": "high", '
        '"explanation": ["Popular model", "Good condition"]}'
    )
    with mock.patch("app.services.pricing.requests.post", return_value=_fake_gemini_response(body)) as post:
        data = client.post(
            "/api/ai/estimate-price",
            json={"title": "iPhone 12", "category_id": category_id(client), "condition": "good",
                  "original_price": 90000, "age_months": 12},
            headers=auth(token),
        ).get_json()
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "test-key"
    assert data["source"] == "ai"
    assert data["recommended_price"] == 55000
    assert data["explanation"] == ["Popular model", "Good condition"]


def test_bad_gemini_answer_falls_back_to_rules(client, app):
    app.config["GEMINI_API_KEY"] = "test-key"
    token = register(client)
    body = '{"min_price": 70000, "recommended_price": 50000, "max_price": 60000}'  # wrong order
    with mock.patch("app.services.pricing.requests.post", return_value=_fake_gemini_response(body)):
        data = client.post(
            "/api/ai/estimate-price",
            json={"title": "iPhone 12", "category_id": category_id(client), "condition": "good",
                  "original_price": 90000},
            headers=auth(token),
        ).get_json()
    assert data["source"] == "rules"
    assert "unavailable" in data["notice"]

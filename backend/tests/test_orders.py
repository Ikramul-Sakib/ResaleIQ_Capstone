from conftest import admin_token, auth, category_id, create_listing, register

CHECKOUT = {"delivery_method": "meetup", "payment_method": "cod", "contact_phone": "01712-345678"}


def approved_listing(client, token, **overrides):
    listing = create_listing(client, token, **overrides).get_json()
    response = client.post(f"/api/admin/listings/{listing['id']}/approve", headers=auth(admin_token(client)))
    assert response.status_code == 200
    return listing


def people(client):
    seller = register(client, name="Seller", email="seller@test.local")
    buyer = register(client, name="Buyer", email="buyer@test.local")
    return seller, buyer


def order(client, token, listing_id, **extra):
    return client.post("/api/orders", json={"listing_id": listing_id, **CHECKOUT, **extra}, headers=auth(token))


def test_full_purchase_flow_with_review(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)

    placed = order(client, buyer, listing["id"], note="Evening pickup please")
    assert placed.status_code == 201, placed.get_json()
    order_id = placed.get_json()["id"]
    assert placed.get_json()["price"] == 45000
    assert client.get("/api/notifications/summary", headers=auth(seller)).get_json()["pending_sales"] == 1

    # seller doesn't see the buyer's phone until accepting
    assert "contact_phone" not in client.get(f"/api/orders/{order_id}", headers=auth(seller)).get_json()

    accepted = client.post(f"/api/orders/{order_id}/accept", headers=auth(seller))
    assert accepted.status_code == 200
    assert accepted.get_json()["contact_phone"] == "01712-345678"
    detail = client.get(f"/api/listings/{listing['id']}").get_json()
    assert detail["status"] == "reserved"
    assert client.get("/api/listings").get_json()["total"] == 0  # reserved items leave search

    assert client.post(f"/api/orders/{order_id}/ship", headers=auth(seller)).status_code == 200
    completed = client.post(f"/api/orders/{order_id}/complete", headers=auth(buyer))
    assert completed.get_json()["status"] == "completed"
    assert completed.get_json()["payment_status"] == "paid"
    sold = client.get(f"/api/listings/{listing['id']}", headers=auth(seller)).get_json()
    assert sold["status"] == "sold" and sold["sold_price"] == 45000

    review = client.post(f"/api/orders/{order_id}/review", json={"rating": 4, "comment": "Good seller"},
                         headers=auth(buyer))
    assert review.status_code == 201
    assert client.post(f"/api/orders/{order_id}/review", json={"rating": 5}, headers=auth(buyer)).status_code == 409

    seller_id = listing["seller_id"]
    profile = client.get(f"/api/users/{seller_id}").get_json()
    assert profile["stats"]["rating_avg"] == 4.0 and profile["stats"]["rating_count"] == 1
    reviews = client.get(f"/api/users/{seller_id}/reviews").get_json()["items"]
    assert reviews[0]["comment"] == "Good seller"


def test_offer_rules(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)
    assert order(client, buyer, listing["id"], offer_price=50000).status_code == 422  # above asking price
    too_low = order(client, buyer, listing["id"], offer_price=10000)
    assert too_low.status_code == 422 and "offer_price" in too_low.get_json()["error"]["fields"]
    offer = order(client, buyer, listing["id"], offer_price=40000)
    assert offer.status_code == 201
    assert offer.get_json()["is_offer"] is True and offer.get_json()["price"] == 40000
    # one active order per buyer per item
    assert order(client, buyer, listing["id"]).status_code == 409


def test_delivery_requires_address_and_valid_phone(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)
    response = order(client, buyer, listing["id"], delivery_method="delivery", contact_phone="abc")
    assert response.status_code == 422
    assert {"delivery_address", "contact_phone"} <= set(response.get_json()["error"]["fields"])


def test_accepting_one_order_declines_the_others(client):
    seller, buyer = people(client)
    other = register(client, name="Other", email="other@test.local")
    listing = approved_listing(client, seller)
    first = order(client, buyer, listing["id"]).get_json()["id"]
    second = order(client, other, listing["id"], offer_price=30000).get_json()["id"]

    client.post(f"/api/orders/{first}/accept", headers=auth(seller))
    assert client.get(f"/api/orders/{second}", headers=auth(other)).get_json()["status"] == "declined"
    # reserved item can't be ordered or added to a cart
    third = register(client, name="Third", email="third@test.local")
    assert order(client, third, listing["id"]).status_code == 409
    assert client.post(f"/api/cart/{listing['id']}", headers=auth(third)).status_code == 409


def test_cancel_accepted_order_releases_item(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)
    order_id = order(client, buyer, listing["id"]).get_json()["id"]
    client.post(f"/api/orders/{order_id}/accept", headers=auth(seller))
    cancelled = client.post(f"/api/orders/{order_id}/cancel", json={"reason": "Changed my mind"}, headers=auth(buyer))
    assert cancelled.status_code == 200 and cancelled.get_json()["cancelled_by"] == "buyer"
    assert client.get(f"/api/listings/{listing['id']}").get_json()["status"] == "approved"


def test_only_the_right_party_can_act(client):
    seller, buyer = people(client)
    stranger = register(client, name="Stranger", email="stranger@test.local")
    listing = approved_listing(client, seller)
    order_id = order(client, buyer, listing["id"]).get_json()["id"]
    assert client.post(f"/api/orders/{order_id}/accept", headers=auth(buyer)).status_code == 403
    assert client.get(f"/api/orders/{order_id}", headers=auth(stranger)).status_code == 404
    assert client.post(f"/api/orders/{order_id}/complete", headers=auth(buyer)).status_code == 409  # not accepted yet
    assert order(client, seller, listing["id"]).status_code == 409  # can't buy own item


def test_mobile_payment_transaction_id(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)
    order_id = order(client, buyer, listing["id"], payment_method="bkash").get_json()["id"]
    assert client.post(f"/api/orders/{order_id}/payment", json={"transaction_id": "ABC123XYZ"},
                       headers=auth(buyer)).status_code == 409  # must be accepted first
    client.post(f"/api/orders/{order_id}/accept", headers=auth(seller))
    paid = client.post(f"/api/orders/{order_id}/payment", json={"transaction_id": "ABC123XYZ"}, headers=auth(buyer))
    assert paid.get_json()["transaction_id"] == "ABC123XYZ"
    confirmed = client.post(f"/api/orders/{order_id}/confirm-payment", headers=auth(seller))
    assert confirmed.get_json()["payment_status"] == "paid"


def test_cart_checkout_creates_one_order_per_item(client):
    seller, buyer = people(client)
    phone = approved_listing(client, seller)
    laptop = approved_listing(client, seller, title="Dell Inspiron 15 Laptop",
                              category_id=str(category_id(client, "laptops-computers")), price="30000")
    for listing in (phone, laptop):
        assert client.post(f"/api/cart/{listing['id']}", headers=auth(buyer)).status_code == 201
    cart = client.get("/api/cart", headers=auth(buyer)).get_json()
    assert cart["total"] == 75000 and cart["available_count"] == 2

    result = client.post("/api/cart/checkout", json=CHECKOUT, headers=auth(buyer))
    assert result.status_code == 201, result.get_json()
    assert len(result.get_json()["orders"]) == 2
    assert client.get("/api/cart", headers=auth(buyer)).get_json()["items"] == []
    purchases = client.get("/api/orders?role=buyer", headers=auth(buyer)).get_json()
    sales = client.get("/api/orders?role=seller&status=pending", headers=auth(seller)).get_json()
    assert purchases["total"] == 2 and sales["total"] == 2


def test_pending_orders_block_edit_and_are_closed_on_delete(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)
    order_id = order(client, buyer, listing["id"]).get_json()["id"]
    edit = {"title": "iPhone 12 64GB Blue", "description": "x" * 30, "category_id": str(category_id(client)),
            "price": "40000", "condition": "good", "location": "Dhaka"}
    response = client.put(f"/api/listings/{listing['id']}", data=edit, headers=auth(seller),
                          content_type="multipart/form-data")
    assert response.status_code == 409
    assert client.delete(f"/api/listings/{listing['id']}", headers=auth(seller)).status_code == 200
    closed = client.get(f"/api/orders/{order_id}", headers=auth(buyer)).get_json()
    assert closed["status"] == "declined"
    assert closed["listing"]["status"] == "deleted"  # order history survives the deleted listing


def test_admin_can_see_and_cancel_orders(client):
    seller, buyer = people(client)
    listing = approved_listing(client, seller)
    order_id = order(client, buyer, listing["id"]).get_json()["id"]
    client.post(f"/api/orders/{order_id}/accept", headers=auth(seller))
    admin = admin_token(client)
    assert client.get("/api/admin/orders?status=active", headers=auth(admin)).get_json()["total"] == 1
    response = client.post(f"/api/admin/orders/{order_id}/cancel", json={"reason": "Buyer reported a scam"},
                           headers=auth(admin))
    assert response.status_code == 200 and response.get_json()["cancelled_by"] == "admin"
    assert client.get(f"/api/listings/{listing['id']}").get_json()["status"] == "approved"
    assert client.get("/api/admin/stats", headers=auth(admin)).get_json()["orders"]["cancelled"] == 1

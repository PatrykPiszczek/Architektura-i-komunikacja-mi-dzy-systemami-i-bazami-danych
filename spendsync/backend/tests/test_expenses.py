from datetime import date


def _make_category(client, auth, name="Food"):
    return client.post("/categories", json={"name": name}, headers=auth).json()["id"]


def _make_expense(client, auth, **overrides):
    payload = {
        "amount": 20.0,
        "currency": "PLN",
        "description": "Coffee",
        "spent_at": str(date.today()),
    }
    payload.update(overrides)
    return client.post("/expenses", json=payload, headers=auth)


def test_create_and_list_expense(client, auth):
    response = _make_expense(client, auth)
    assert response.status_code == 201
    assert response.json()["client_uuid"]

    listing = client.get("/expenses", headers=auth).json()
    assert len(listing) == 1


def test_create_expense_rejects_zero_amount(client, auth):
    response = _make_expense(client, auth, amount=0)
    assert response.status_code == 422
    assert response.json()["detail"] == "Validation failed"


def test_create_expense_unknown_category(client, auth):
    response = _make_expense(client, auth, category_id=999)
    assert response.status_code == 404


def test_search_by_text(client, auth):
    _make_expense(client, auth, description="Pizza margherita")
    _make_expense(client, auth, description="Bus ticket")
    results = client.get("/expenses", params={"q": "pizza"}, headers=auth).json()
    assert len(results) == 1
    assert "Pizza" in results[0]["description"]


def test_search_by_amount_range(client, auth):
    _make_expense(client, auth, amount=10)
    _make_expense(client, auth, amount=100)
    results = client.get("/expenses", params={"min_amount": 50}, headers=auth).json()
    assert len(results) == 1
    assert results[0]["amount"] == 100


def test_search_by_category(client, auth):
    food = _make_category(client, auth, "Food")
    _make_expense(client, auth, category_id=food)
    _make_expense(client, auth)
    results = client.get("/expenses", params={"category_id": food}, headers=auth).json()
    assert len(results) == 1


def test_update_expense_bumps_version(client, auth):
    created = _make_expense(client, auth).json()
    response = client.put(f"/expenses/{created['id']}", json={"amount": 99.0}, headers=auth)
    assert response.status_code == 200
    assert response.json()["amount"] == 99.0
    assert response.json()["version"] == created["version"] + 1


def test_delete_is_soft(client, auth):
    created = _make_expense(client, auth).json()
    assert client.delete(f"/expenses/{created['id']}", headers=auth).status_code == 204
    assert client.get("/expenses", headers=auth).json() == []
    assert client.get(f"/expenses/{created['id']}", headers=auth).status_code == 404


def test_expenses_isolated_per_user(client, auth):
    _make_expense(client, auth)
    other = client.post(
        "/auth/register",
        json={"email": "other@test.pl", "password": "secret1", "display_name": "Other"},
    )
    token = client.post("/auth/login", data={"username": "other@test.pl", "password": "secret1"}).json()
    other_auth = {"Authorization": f"Bearer {token['access_token']}"}
    assert client.get("/expenses", headers=other_auth).json() == []

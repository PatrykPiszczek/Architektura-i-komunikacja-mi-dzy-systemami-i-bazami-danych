from datetime import date


def test_budget_crud(client, auth):
    period = date.today().strftime("%Y-%m")
    created = client.post("/budgets", json={"period": period, "limit_amount": 500.0}, headers=auth)
    assert created.status_code == 201
    budget_id = created.json()["id"]

    updated = client.put(f"/budgets/{budget_id}", json={"limit_amount": 800.0}, headers=auth)
    assert updated.json()["limit_amount"] == 800.0

    assert client.delete(f"/budgets/{budget_id}", headers=auth).status_code == 204


def test_budget_summary_computes_spent(client, auth):
    period = date.today().strftime("%Y-%m")
    food = client.post("/categories", json={"name": "Food"}, headers=auth).json()["id"]
    client.post("/budgets", json={"period": period, "limit_amount": 500.0, "category_id": food}, headers=auth)
    client.post(
        "/expenses",
        json={"amount": 120.0, "spent_at": str(date.today()), "category_id": food},
        headers=auth,
    )
    summary = client.get("/budgets/summary", params={"period": period}, headers=auth).json()
    assert summary[0]["spent"] == 120.0
    assert summary[0]["remaining"] == 380.0
    assert summary[0]["category_name"] == "Food"


def test_invalid_period_rejected(client, auth):
    response = client.post("/budgets", json={"period": "2026/06", "limit_amount": 100.0}, headers=auth)
    assert response.status_code == 422


def test_rates_pln_base(client, auth):
    response = client.get("/rates", params={"code": "PLN"}, headers=auth)
    assert response.status_code == 200
    assert response.json()["rate"] == 1.0

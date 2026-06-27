from datetime import date, datetime, timedelta, timezone
from uuid import uuid4


def _push(client, auth, **overrides):
    change = {
        "client_uuid": str(uuid4()),
        "amount": 30.0,
        "currency": "PLN",
        "description": "Offline expense",
        "spent_at": str(date.today()),
        "base_version": 0,
    }
    change.update(overrides)
    return client.post("/sync/push", json={"changes": [change]}, headers=auth)


def test_push_creates_expense(client, auth):
    response = _push(client, auth)
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "created"
    assert result["expense"]["version"] == 1


def test_pull_returns_pushed_expense(client, auth):
    _push(client, auth)
    pull = client.get("/sync/changes", headers=auth).json()
    assert len(pull["expenses"]) == 1
    assert "server_time" in pull


def test_pull_since_filters_older(client, auth):
    _push(client, auth)
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    pull = client.get("/sync/changes", params={"since": future}, headers=auth).json()
    assert pull["expenses"] == []


def test_push_update_with_matching_version(client, auth):
    uuid = str(uuid4())
    _push(client, auth, client_uuid=uuid)
    response = _push(client, auth, client_uuid=uuid, base_version=1, amount=55.0)
    result = response.json()["results"][0]
    assert result["status"] == "updated"
    assert result["expense"]["amount"] == 55.0
    assert result["expense"]["version"] == 2


def test_conflict_server_wins_on_stale_version(client, auth):
    uuid = str(uuid4())
    _push(client, auth, client_uuid=uuid)
    _push(client, auth, client_uuid=uuid, base_version=1, amount=70.0)
    stale = _push(
        client,
        auth,
        client_uuid=uuid,
        base_version=1,
        amount=999.0,
        updated_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    )
    result = stale.json()["results"][0]
    assert result["status"] == "conflict_server_won"
    assert result["expense"]["amount"] == 70.0


def test_conflict_client_wins_when_newer(client, auth):
    uuid = str(uuid4())
    _push(client, auth, client_uuid=uuid)
    _push(client, auth, client_uuid=uuid, base_version=1, amount=70.0)
    fresh = _push(
        client,
        auth,
        client_uuid=uuid,
        base_version=1,
        amount=123.0,
        updated_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    result = fresh.json()["results"][0]
    assert result["status"] == "conflict_client_won"
    assert result["expense"]["amount"] == 123.0


def test_push_requires_auth(client):
    assert client.post("/sync/push", json={"changes": []}).status_code == 401

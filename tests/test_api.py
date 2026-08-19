"""API integration tests using FastAPI TestClient with a temp-file SQLite DB."""
import os
import tempfile

_tmpdir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test_batwara.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _register(client, name, email, password="secret123"):
    return client.post("/api/auth/register", json={"name": name, "email": email, "password": password})


def _login(client, email, password="secret123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _auth_headers(client, email, password="secret123"):
    res = _login(client, email, password)
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


class TestAuth:
    def test_register_success(self, client):
        res = _register(client, "Ali", "ali@test.com")
        assert res.status_code == 201
        data = res.json()
        assert data["access_token"]
        assert data["user"]["email"] == "ali@test.com"

    def test_register_duplicate_email(self, client):
        _register(client, "Ali2", "ali@test.com")
        res = _register(client, "Ali3", "ali@test.com")
        assert res.status_code == 409

    def test_register_weak_password(self, client):
        res = _register(client, "Weak", "weak@test.com", password="short")
        assert res.status_code == 422

    def test_login_success(self, client):
        res = _login(client, "ali@test.com")
        assert res.status_code == 200
        assert res.json()["user"]["name"] == "Ali"

    def test_login_wrong_password(self, client):
        res = _login(client, "ali@test.com", password="wrongpass1")
        assert res.status_code == 401

    def test_me_requires_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_valid_token(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.get("/api/auth/me", headers=headers)
        assert res.status_code == 200
        assert res.json()["email"] == "ali@test.com"


class TestGroups:
    def test_create_group(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.post("/api/groups", json={"name": "Hostel Trip"}, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Hostel Trip"
        assert data["members"][0]["email"] == "ali@test.com"

    def test_create_group_with_members(self, client):
        _register(client, "Bilal", "bilal@test.com")
        _register(client, "Sara", "sara@test.com")
        headers = _auth_headers(client, "ali@test.com")
        res = client.post(
            "/api/groups",
            json={"name": "Karachi Trip", "member_emails": ["bilal@test.com", "sara@test.com"]},
            headers=headers,
        )
        assert res.status_code == 201
        assert len(res.json()["members"]) == 3

    def test_group_detail_requires_membership(self, client):
        headers = _auth_headers(client, "bilal@test.com")
        res = client.get("/api/groups/1", headers=headers)
        # bilal is a member of group 2 only
        assert res.status_code in (403, 404)

    def test_list_groups(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.get("/api/groups", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) >= 2


class TestExpenses:
    def test_add_equal_expense(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.post(
            "/api/groups/2/expenses",
            json={"description": "Dinner at Kolachi", "amount": 3000, "split_type": "equal"},
            headers=headers,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["amount"] == 3000.0
        assert data["payer"]["email"] == "ali@test.com"

    def test_add_exact_expense(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.post(
            "/api/groups/2/expenses",
            json={
                "description": "Groceries",
                "amount": 1000,
                "split_type": "exact",
                "split_details": {"3": 500, "2": 300, "1": 200},
            },
            headers=headers,
        )
        assert res.status_code == 201

    def test_exact_split_amount_mismatch_rejected(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.post(
            "/api/groups/2/expenses",
            json={
                "description": "Bad split",
                "amount": 1000,
                "split_type": "exact",
                "split_details": {"3": 100, "2": 100},
            },
            headers=headers,
        )
        assert res.status_code == 400

    def test_add_expense_not_member(self, client):
        _register(client, "Outsider", "outsider@test.com")
        headers = _auth_headers(client, "outsider@test.com")
        res = client.post(
            "/api/groups/2/expenses",
            json={"description": "Hack", "amount": 100, "split_type": "equal"},
            headers=headers,
        )
        assert res.status_code == 403

    def test_delete_own_expense(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.delete("/api/groups/2/expenses/2", headers=headers)
        assert res.status_code == 204


class TestSettlements:
    def test_balances_endpoint(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.get("/api/groups/2/settle/balances", headers=headers)
        assert res.status_code == 200
        balances = res.json()
        assert len(balances) == 3

    def test_settlement_plan_endpoint(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.get("/api/groups/2/settle/plan", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "plan" in data
        assert "transactions" in data
        assert data["total_expenses"] > 0

    def test_record_settlement(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.post(
            "/api/groups/2/settle",
            json={"to_user_id": 3, "amount": 500, "note": "JazzCash done"},
            headers=headers,
        )
        assert res.status_code == 201
        assert res.json()["amount"] == 500.0

    def test_settlement_history(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.get("/api/groups/2/settle/history", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_cannot_settle_with_self(self, client):
        headers = _auth_headers(client, "ali@test.com")
        res = client.post(
            "/api/groups/2/settle",
            json={"to_user_id": 1, "amount": 100},
            headers=headers,
        )
        assert res.status_code == 400


class TestHealth:
    def test_health(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

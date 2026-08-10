"""
Shared pytest fixtures for the cost-allocations test suite.

Design principles
-----------------
- Every test gets a *fresh* in-memory store: the seed data is re-applied
  before each test and all tables are cleared afterwards.  This prevents
  state leaking between tests and makes every test independently runnable.
- The FastAPI TestClient is synchronous (Starlette's test transport), so no
  async machinery is needed in most tests.
- Token fixtures are intentionally thin — they call the real /auth/token
  endpoint through the client so auth behaviour is exercised end-to-end.

Available fixtures
------------------
client          – TestClient bound to the app, fresh store per test
admin_token     – Bearer token for the seeded admin user
analyst_token   – Bearer token for the seeded analyst user
viewer_token    – Bearer token for the seeded viewer user
admin_headers   – {"Authorization": "Bearer <token>"} dict for admin
analyst_headers – {"Authorization": "Bearer <token>"} dict for analyst
viewer_headers  – {"Authorization": "Bearer <token>"} dict for viewer
"""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.auth import hash_password


# ---------------------------------------------------------------------------
# Seed constants — mirror app/seed.py so tests can reference them by name
# ---------------------------------------------------------------------------

SEED_USERS = [
    {"username": "admin",   "email": "admin@example.com",   "password": "admin123",   "role": "admin"},
    {"username": "analyst", "email": "analyst@example.com", "password": "analyst123", "role": "analyst"},
    {"username": "viewer",  "email": "viewer@example.com",  "password": "viewer123",  "role": "viewer"},
]

SEED_COST_CENTRES = [
    {"code": "TECH", "name": "Technology",      "description": "IT infrastructure, software, and development"},
    {"code": "FIN",  "name": "Finance",         "description": "Finance and accounting operations"},
    {"code": "HR",   "name": "Human Resources", "description": "People and talent management"},
    {"code": "OPS",  "name": "Operations",      "description": "Core business operations"},
]

SEED_LEGAL_ENTITIES = [
    {"code": "UK001", "name": "Acme UK Ltd",       "country_code": "GBR"},
    {"code": "IE001", "name": "Acme Ireland Ltd",  "country_code": "IRL"},
    {"code": "DE001", "name": "Acme Germany GmbH", "country_code": "DEU"},
]


# ---------------------------------------------------------------------------
# Store reset helpers
# ---------------------------------------------------------------------------

def _clear_store() -> None:
    """Wipe every table and reset all sequences to 0."""
    db.users.clear()
    db.cost_centres.clear()
    db.legal_entities.clear()
    db.periods.clear()
    db.expenses.clear()
    db.activities.clear()
    db.assignments.clear()
    db.distributions.clear()
    db.labels.clear()
    db.submissions.clear()

    # Reset sequences so IDs are predictable across test runs
    for seq in (
        db.seq_users,
        db.seq_cost_centres,
        db.seq_legal_entities,
        db.seq_periods,
        db.seq_expenses,
        db.seq_activities,
        db.seq_assignments,
        db.seq_distributions,
        db.seq_labels,
        db.seq_submissions,
    ):
        seq._val = 0  # noqa: SLF001 — direct reset is intentional in tests


def _seed_store() -> None:
    """Populate the store with the standard set of test fixtures."""
    for u in SEED_USERS:
        uid = db.seq_users.nextval()
        db.users[uid] = {
            "user_id":     uid,
            "username":    u["username"],
            "email":       u["email"],
            "hashed_pwd":  hash_password(u["password"]),
            "role":        u["role"],
            "is_active":   True,
            "created_at":  db.utcnow(),
        }

    for cc in SEED_COST_CENTRES:
        cid = db.seq_cost_centres.nextval()
        db.cost_centres[cid] = {
            "cost_centre_id": cid,
            "code":           cc["code"],
            "name":           cc["name"],
            "description":    cc["description"],
            "is_active":      True,
        }

    for le in SEED_LEGAL_ENTITIES:
        eid = db.seq_legal_entities.nextval()
        db.legal_entities[eid] = {
            "legal_entity_id": eid,
            "code":            le["code"],
            "name":            le["name"],
            "country_code":    le["country_code"],
            "is_active":       True,
        }


# ---------------------------------------------------------------------------
# Core fixture: client with isolated state
# ---------------------------------------------------------------------------

@pytest.fixture()
def client() -> TestClient:
    """
    Return a TestClient backed by a freshly seeded in-memory store.

    State is cleared and re-seeded before each test, then cleared again
    after to avoid bleed into any fixture teardown logic.
    """
    _clear_store()
    _seed_store()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    _clear_store()


# ---------------------------------------------------------------------------
# Token fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_token(client: TestClient) -> str:
    """Bearer token for the seeded admin user."""
    return _acquire_token(client, "admin", "admin123")


@pytest.fixture()
def analyst_token(client: TestClient) -> str:
    """Bearer token for the seeded analyst user."""
    return _acquire_token(client, "analyst", "analyst123")


@pytest.fixture()
def viewer_token(client: TestClient) -> str:
    """Bearer token for the seeded viewer user."""
    return _acquire_token(client, "viewer", "viewer123")


def _acquire_token(client: TestClient, username: str, password: str) -> str:
    """POST to /auth/token and return the raw access_token string."""
    resp = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, (
        f"Token acquisition failed for '{username}': {resp.status_code} {resp.text}"
    )
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Header fixtures (convenience wrappers)
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def analyst_headers(analyst_token: str) -> dict:
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture()
def viewer_headers(viewer_token: str) -> dict:
    return {"Authorization": f"Bearer {viewer_token}"}

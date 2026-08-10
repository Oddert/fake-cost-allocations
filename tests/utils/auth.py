"""
Token acquisition helpers for use in tests.

These functions operate directly against a live TestClient instance.
They are intentionally simple wrappers so that individual tests remain
readable without repeating the form-post boilerplate.

Usage
-----
    from tests.utils.auth import get_token, get_headers

    def test_something(client):
        headers = get_headers(client, "admin", "admin123")
        resp = client.get("/auth/users", headers=headers)
        assert resp.status_code == 200
"""

from fastapi.testclient import TestClient


def get_token(client: TestClient, username: str, password: str) -> str:
    """
    Obtain a JWT Bearer token for the given credentials.

    Raises AssertionError if the login request does not return 200, which
    surfaces as a clear test failure rather than a confusing KeyError.
    """
    resp = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, (
        f"Login failed for user '{username}': HTTP {resp.status_code} — {resp.text}"
    )
    return resp.json()["access_token"]


def get_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    """
    Return an Authorization header dict for the given credentials.

    Suitable for passing directly to TestClient request methods:

        client.get("/some/endpoint", headers=get_headers(client, "admin", "admin123"))
    """
    token = get_token(client, username, password)
    return {"Authorization": f"Bearer {token}"}


def get_token_for_role(client: TestClient, role: str) -> str:
    """
    Obtain a token using the standard seed credentials for a given role.

    Supported roles: "admin", "analyst", "viewer".
    Relies on the seed users created by conftest._seed_store().
    """
    _seed_credentials = {
        "admin":   ("admin",   "admin123"),
        "analyst": ("analyst", "analyst123"),
        "viewer":  ("viewer",  "viewer123"),
    }
    if role not in _seed_credentials:
        raise ValueError(
            f"Unknown role '{role}'. Expected one of: {list(_seed_credentials)}"
        )
    username, password = _seed_credentials[role]
    return get_token(client, username, password)


def get_headers_for_role(client: TestClient, role: str) -> dict[str, str]:
    """
    Return an Authorization header dict for the standard seed user of a given role.

    Supported roles: "admin", "analyst", "viewer".
    """
    return {"Authorization": f"Bearer {get_token_for_role(client, role)}"}

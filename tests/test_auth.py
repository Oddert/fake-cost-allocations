"""
Tests for the authentication endpoints.

Covers the following features from test-cases.md:
  - Feature: login
  - Feature: List users
  - Feature: get user details

Each test maps to a named scenario in test-cases.md.  The scenario name is
used as the test docstring so failures are self-documenting.

Endpoints under test
--------------------
  POST /auth/token
  GET  /auth/users
  TODO POST  /auth/users
  GET  /auth/users/me
  TODO PATCH /auth/users/{user_id}/deactivate
  TODO POST /auth/users/me/change-password
"""

import pytest
from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_forbidden,
    assert_no_sensitive_fields,
    assert_ok,
    assert_token_shape,
    assert_unauthorized,
    assert_user_shape,
)

# ===========================================================================
# Feature: login
# ===========================================================================


class TestLogin:
    """Feature: login — POST /auth/token"""

    def test_successful_login_returns_token(self, client: TestClient):
        """
        Scenario: Successful login with valid credentials
            Given a user exists
            And the user is not deactivated
            When the user logs in with valid credentials
            Then they should receive an access token
        """
        resp = client.post(
            '/auth/token',
            data={'username': 'admin', 'password': 'admin123'},
        )

        assert_ok(resp)
        assert_token_shape(resp.json())

    @pytest.mark.parametrize(
        'username,password',
        [
            ('admin', 'wrongpassword'),
            ('nobody', 'admin123'),
            ('nobody', 'nobody'),
        ],
    )
    def test_failed_login_wrong_credentials_returns_401(
        self, client: TestClient, username: str, password: str
    ):
        """
        Scenario: Failed login with incorrect credentials (wrong user/password)
            When a user logs in with incorrect details
            Then the request is rejected with 401
        """
        resp = client.post(
            '/auth/token',
            data={'username': username, 'password': password},
        )

        assert resp.status_code == 401, (
            f'Expected 401 for bad credentials ({username!r}), '
            f'got {resp.status_code}: {resp.text}'
        )

    @pytest.mark.parametrize(
        'username,password',
        [
            ('admin', ''),
            ('', 'admin123'),
        ],
    )
    def test_failed_login_missing_fields_returns_4xx(
        self, client: TestClient, username: str, password: str
    ):
        """
        Scenario: Failed login with missing fields
            When a user submits a login request with an empty username or password
            Then the request is rejected
            Note: FastAPI form validation returns 422 for missing required fields,
            which is a valid rejection — the test accepts either 401 or 422.
        """
        resp = client.post(
            '/auth/token',
            data={'username': username, 'password': password},
        )

        assert resp.status_code in (401, 422), (
            f'Expected 401 or 422 for missing field ({username!r}/{password!r}), '
            f'got {resp.status_code}: {resp.text}'
        )

    def test_deactivated_user_cannot_login(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: Successful login as an existing user — deactivation blocks login
            Given a user is deactivated
            When the user tries to log in
            Then the request is rejected
        """
        # Deactivate the analyst user via the admin endpoint
        users_resp = client.get('/auth/users', headers=admin_headers)
        analyst = next(u for u in users_resp.json() if u['username'] == 'analyst')
        client.patch(
            f'/auth/users/{analyst["user_id"]}/deactivate',
            headers=admin_headers,
        )

        # Deactivated user cannot obtain a token
        resp = client.post(
            '/auth/token',
            data={'username': 'analyst', 'password': 'analyst123'},
        )

        assert resp.status_code in (401, 403), (
            f'Expected 401 or 403 for deactivated user, got {resp.status_code}: {resp.text}'
        )

    def test_token_response_does_not_leak_sensitive_data(self, client: TestClient):
        """Token response must not contain password or hashed_pwd fields."""
        resp = client.post(
            '/auth/token',
            data={'username': 'viewer', 'password': 'viewer123'},
        )
        assert_ok(resp)
        assert_no_sensitive_fields(resp.json())


# ===========================================================================
# Feature: List users — GET /auth/users
# ===========================================================================


class TestListUsers:
    """Feature: List users — GET /auth/users"""

    def test_non_admin_requests_are_rejected(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: Non-admin requests are rejected
            Given the user is logged in
            And the user does not have the "admin" role
            When the user requests a list of users
            Then the request is rejected with a 403 unprivileged status
        """
        resp = client.get('/auth/users', headers=analyst_headers)
        assert_forbidden(resp)

    def test_unauthenticated_request_is_rejected(self, client: TestClient):
        """
        Scenario: Unauthenticated user tries to access a protected endpoint
            Given the user is not logged in
            When the user requests a list of users
            Then the endpoint rejects the request
        """
        resp = client.get('/auth/users')
        assert_unauthorized(resp)

    def test_admin_gets_full_list_of_users(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: Admin user gets a list of all users
            Given the user is logged in as an admin
            And there exists one or more users
            When the user requests a list of users
            Then the full list of users is returned
        """
        resp = client.get('/auth/users', headers=admin_headers)

        assert_ok(resp)
        users = resp.json()
        assert isinstance(users, list), 'Response should be a list'
        assert len(users) >= 3, f'Expected at least 3 seeded users, got {len(users)}'

        # Verify all seeded usernames are present
        usernames = {u['username'] for u in users}
        assert {'admin', 'analyst', 'viewer'}.issubset(usernames), (
            f'Seeded users missing from list. Got: {usernames}'
        )

    def test_list_users_no_sensitive_data_returned(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: No sensitive data is returned
            Given the user is logged in as an admin
            When the user requests a list of users
            Then the list is returned without any sensitive information
        """
        resp = client.get('/auth/users', headers=admin_headers)

        assert_ok(resp)
        users = resp.json()
        assert_no_sensitive_fields(users)

    def test_list_users_correct_shape(self, client: TestClient, admin_headers: dict):
        """Every user object in the list must conform to the UserResponse schema."""
        resp = client.get('/auth/users', headers=admin_headers)

        assert_ok(resp)
        for user in resp.json():
            assert_user_shape(user)


# ===========================================================================
# Feature: get user details — GET /auth/users/me
# ===========================================================================


class TestGetCurrentUser:
    """Feature: get user details — GET /auth/users/me"""

    def test_user_can_get_their_own_profile(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A user requests their own profile details
            Given a user is logged in
            When the user requests the endpoint
            Then they get their full user profile
        """
        resp = client.get('/auth/users/me', headers=analyst_headers)

        assert_ok(resp)
        data = resp.json()
        assert_user_shape(data)
        assert data['username'] == 'analyst', (
            f"Expected profile for 'analyst', got '{data['username']}'"
        )

    @pytest.mark.parametrize(
        'role,username',
        [
            ('admin', 'admin'),
            ('analyst', 'analyst'),
            ('viewer', 'viewer'),
        ],
    )
    def test_each_role_gets_their_own_profile(
        self, client: TestClient, role: str, username: str
    ):
        """Every role can access /me and receives their own profile, not another user's."""
        from tests.utils.auth import get_headers_for_role

        headers = get_headers_for_role(client, role)

        resp = client.get('/auth/users/me', headers=headers)

        assert_ok(resp)
        data = resp.json()
        assert data['username'] == username
        assert data['role'] == role

    def test_unauthenticated_me_request_is_rejected(self, client: TestClient):
        """
        Scenario: Unauthenticated user tries to access a protected endpoint
            Given the user is not logged in
            When the user requests /auth/users/me
            Then the endpoint rejects the request
        """
        resp = client.get('/auth/users/me')
        assert_unauthorized(resp)

    def test_me_response_has_no_sensitive_fields(
        self, client: TestClient, viewer_headers: dict
    ):
        """The /me response must not expose hashed_pwd or any other sensitive field."""
        resp = client.get('/auth/users/me', headers=viewer_headers)

        assert_ok(resp)
        assert_no_sensitive_fields(resp.json())

    def test_invalid_token_is_rejected(self, client: TestClient):
        """
        Scenario: Authenticated user tries to access a protected endpoint — bad token
            Given the user holds an invalid token
            When the user tries to access /auth/users/me
            Then the endpoint rejects the request
        """
        resp = client.get(
            '/auth/users/me',
            headers={'Authorization': 'Bearer this.is.not.a.valid.token'},
        )
        assert_unauthorized(resp)

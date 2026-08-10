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
  POST  /auth/users
  GET  /auth/users/me
  TODO PATCH /auth/users/{user_id}/deactivate
  TODO POST /auth/users/me/change-password
"""

import pytest
from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_created,
    assert_forbidden,
    assert_no_sensitive_fields,
    assert_ok,
    assert_token_shape,
    assert_unauthorized,
    assert_unprocessable,
    assert_user_shape,
)


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


def _create_user(client: TestClient, headers: dict, payload: dict):
    """POST to /auth/users and return the raw response."""
    return client.post('/auth/users', json=payload, headers=headers)


_VALID_USER = {
    'username': 'newuser',
    'email': 'newuser@example.com',
    'password': 'Password1!',
    'role': 'viewer',
}


class TestCreateUser:
    """Feature: Create user — POST /auth/users"""

    def test_unauthenticated_request_is_rejected(self, client: TestClient):
        """
        Scenario: Unauthenticated user tries to access a protected endpoint
            Given the user is not logged in
            When the user tries to create a new user
            Then the endpoint rejects the request
        """
        resp = _create_user(client, headers={}, payload=_VALID_USER)
        assert_unauthorized(resp)

    @pytest.mark.parametrize('role', ['analyst', 'viewer'])
    def test_non_admin_cannot_create_user(
        self, client: TestClient, analyst_headers: dict, viewer_headers: dict, role: str
    ):
        """
        Scenario: Non-admins cannot register a new user
            Given the user is logged in
            And the user does not have the "admin" role
            When the user tries to register a new user
            Then the request is rejected as unprivileged
        """
        headers = analyst_headers if role == 'analyst' else viewer_headers
        resp = _create_user(client, headers=headers, payload=_VALID_USER)
        assert_forbidden(resp)

    def test_admin_can_create_user(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Admin users can register another user
            Given the user is logged in
            And the user has the "admin" role
            When the user submits the correct details
            Then a new user is created
            And the new user details are returned
            And the database shows one more user
        """
        users_before = client.get('/auth/users', headers=admin_headers).json()
        count_before = len(users_before)

        resp = _create_user(client, headers=admin_headers, payload=_VALID_USER)

        assert_created(resp)
        data = resp.json()
        assert_user_shape(data)
        assert data['username'] == _VALID_USER['username']
        assert data['email'] == _VALID_USER['email']
        assert data['role'] == _VALID_USER['role']
        assert data['is_active'] is True

        # Database count increased by exactly one
        users_after = client.get('/auth/users', headers=admin_headers).json()
        assert len(users_after) == count_before + 1, (
            f'Expected {count_before + 1} users after creation, got {len(users_after)}'
        )

    def test_created_user_appears_in_list(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: Admin users can register another user — new user shows in full list
            After creation the new user is visible in GET /auth/users
        """
        _create_user(client, headers=admin_headers, payload=_VALID_USER)

        users = client.get('/auth/users', headers=admin_headers).json()
        usernames = {u['username'] for u in users}
        assert _VALID_USER['username'] in usernames, (
            f"Newly created user '{_VALID_USER['username']}' not found in user list"
        )

    def test_created_user_response_has_no_sensitive_fields(
        self, client: TestClient, admin_headers: dict
    ):
        """The create-user response must not expose hashed_pwd or any similar field."""
        resp = _create_user(client, headers=admin_headers, payload=_VALID_USER)
        assert_created(resp)
        assert_no_sensitive_fields(resp.json())

    @pytest.mark.parametrize('role', ['admin', 'analyst', 'viewer'])
    def test_created_user_role_is_persisted(
        self, client: TestClient, admin_headers: dict, role: str
    ):
        """
        Scenario: Admin users can register another user — role field is stored correctly
            The role supplied in the request body must match what is returned
            and what is used for subsequent auth checks.
        """
        payload = {
            **_VALID_USER,
            'username': f'roletest_{role}',
            'email': f'{role}test@example.com',
            'role': role,
        }
        resp = _create_user(client, headers=admin_headers, payload=payload)
        assert_created(resp)
        assert resp.json()['role'] == role

    def test_new_user_can_log_in(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Admin users can register another user — new user can authenticate
            After creation, the new user can obtain a token using their credentials.
        """
        _create_user(client, headers=admin_headers, payload=_VALID_USER)

        login_resp = client.post(
            '/auth/token',
            data={
                'username': _VALID_USER['username'],
                'password': _VALID_USER['password'],
            },
        )
        assert login_resp.status_code == 200, (
            f'Newly created user could not log in: {login_resp.status_code} {login_resp.text}'
        )
        assert 'access_token' in login_resp.json()

    @pytest.mark.parametrize(
        'missing_field,payload',
        [
            (
                'username',
                {
                    'email': 'user@example.com',
                    'password': 'Password1!',
                    'role': 'viewer',
                },
            ),
            (
                'email',
                {'username': 'someuser', 'password': 'Password1!', 'role': 'viewer'},
            ),
            (
                'password',
                {'username': 'someuser', 'email': 'user@example.com', 'role': 'viewer'},
            ),
        ],
    )
    def test_missing_required_fields_are_rejected(
        self, client: TestClient, admin_headers: dict, missing_field: str, payload: dict
    ):
        """
        Scenario: Sign-ups missing details are rejected
            Given the user is logged in
            And the user has the "admin" role
            When the user makes a request missing one or more details
            Then the request is rejected
        """
        resp = _create_user(client, headers=admin_headers, payload=payload)
        (
            assert_unprocessable(resp),
            (f"Expected 422 when '{missing_field}' is missing, got {resp.status_code}"),
        )

    def test_empty_role_defaults_to_viewer(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: Sign-ups missing details — role defaults to viewer when omitted
            The role field has a server-side default of "viewer".
            Omitting it should succeed, not be rejected.
        """
        payload = {k: v for k, v in _VALID_USER.items() if k != 'role'}
        resp = _create_user(client, headers=admin_headers, payload=payload)
        assert_created(resp)
        assert resp.json()['role'] == 'viewer'

    @pytest.mark.parametrize(
        'bad_email',
        [
            'notanemail',
            'email@example@com',
            'email.example',
            '@nodomain',
            'spaces in@email.com',
        ],
    )
    def test_invalid_email_is_rejected(
        self, client: TestClient, admin_headers: dict, bad_email: str
    ):
        """
        Scenario: Sign-ups with invalid emails are rejected
            Given the user is logged in
            And the user has the "admin" role
            When the user tries to register another user with a malformed email
            Then the request is rejected
        """
        payload = {**_VALID_USER, 'email': bad_email}
        resp = _create_user(client, headers=admin_headers, payload=payload)
        (
            assert_unprocessable(resp),
            (f"Expected 422 for invalid email '{bad_email}', got {resp.status_code}"),
        )

    def test_duplicate_username_is_rejected(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: Two users of the same username cannot be registered
            Given the user is logged in
            And the user has the "admin" role
            And the database has a user called "user123"
            When the user submits a request to create a user with username "user123"
            Then the request is rejected
            And the originating user is informed of the conflict
        """
        # Create the user once
        payload = {**_VALID_USER, 'username': 'user123', 'email': 'user123@example.com'}
        first = _create_user(client, headers=admin_headers, payload=payload)
        assert_created(first)

        # Attempt to create again with the same username (different email)
        duplicate = _create_user(
            client,
            headers=admin_headers,
            payload={**payload, 'email': 'different@example.com'},
        )
        assert duplicate.status_code == 400, (
            f'Expected 400 for duplicate username, got {duplicate.status_code}: {duplicate.text}'
        )
        # The response must explain the conflict
        detail = str(duplicate.json().get('detail', '')).lower()
        assert 'username' in detail or 'taken' in detail or 'already' in detail, (
            f'Error detail should mention the username conflict, got: {duplicate.json()}'
        )

    def test_duplicate_email_is_rejected(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Two users with the same email cannot be registered
            Duplicate email must be rejected with a clear error message.
        """
        # Create the user once
        payload = {
            **_VALID_USER,
            'username': 'firstuser',
            'email': 'shared@example.com',
        }
        first = _create_user(client, headers=admin_headers, payload=payload)
        assert_created(first)

        # Attempt a second user with the same email (different username)
        duplicate = _create_user(
            client,
            headers=admin_headers,
            payload={**payload, 'username': 'seconduser'},
        )
        assert duplicate.status_code == 400, (
            f'Expected 400 for duplicate email, got {duplicate.status_code}: {duplicate.text}'
        )
        detail = str(duplicate.json().get('detail', '')).lower()
        assert 'email' in detail or 'registered' in detail or 'already' in detail, (
            f'Error detail should mention the email conflict, got: {duplicate.json()}'
        )

    @pytest.mark.xfail(
        reason='Password complexity is not yet enforced in app/routers/auth.py — '
        'UserCreate has no complexity validator on the password field.',
        strict=True,
    )
    @pytest.mark.parametrize(
        'weak_password,username,email',
        [
            (
                'password',
                'user1',
                'user1@example.com',
            ),  # dictionary word, no numbers/symbols
            ('p', 'user2', 'user2@example.com'),  # single character
            ('123', 'user3', 'user3@example.com'),  # digits only
            ('battery-123', 'user4', 'user4@example.com'),  # no uppercase or symbol
            ('horse£', 'user5', 'user5@example.com'),  # non-ASCII symbol but no digits
            ('s*@pl3', 'user6', 'user6@example.com'),  # too short
        ],
    )
    def test_weak_passwords_are_rejected(
        self,
        client: TestClient,
        admin_headers: dict,
        weak_password: str,
        username: str,
        email: str,
    ):
        """
        Scenario: Non-complex passwords are rejected
            Given the user is logged in
            And the user has the "admin" role
            When a request is made to register a new user
            And the password is not sufficiently complex
            Then the request is rejected
        """
        payload = {
            'username': username,
            'email': email,
            'password': weak_password,
            'role': 'viewer',
        }
        resp = _create_user(client, headers=admin_headers, payload=payload)
        assert resp.status_code in (400, 422), (
            f"Expected rejection for weak password '{weak_password}', "
            f'got {resp.status_code}: {resp.text}'
        )

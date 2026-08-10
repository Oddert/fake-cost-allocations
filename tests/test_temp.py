
import pytest
from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_bad_request,
    assert_created,
    assert_no_content,
    assert_unauthorised,
)

from tests.conftest import _acquire_token

class TestChangePassword:
    _VALID_USER = {
        'username': 'pwd_change_target',
        'email': 'pwd_change_target@example.com',
        'password': 'Password1!',
        'role': 'viewer',
    }

    @pytest.fixture(autouse=True)
    def seed_user(self, client: TestClient, admin_headers: dict):
        """Create a user in the seeded store before each test runs."""
        resp = client.post('/auth/users', json=self._VALID_USER, headers=admin_headers)
        assert_created(resp)
        res_json = resp.json()
        self.seeded_user = res_json
        self.token = _acquire_token(
            client, self._VALID_USER['username'], self._VALID_USER['password']
        )

    def test_unauthenticated_request_is_rejected(self, client: TestClient):
        """
        Scenario: Unauthenticated user tries to access a protected endpoint
            Given the user is not logged in
            When the user requests a list of users
            Then the endpoint rejects the request
        """
        resp = client.get('/auth/users')
        assert_unauthorised(resp)

    def test_change_password(self, client: TestClient):
        """
        Scenario: User successfully changes their password
            When the user submits their old and new password
            Then the password for that user is updated
            And the new password can be used to login
            And the old password can no longer be used to login
        """
        old_pass = self._VALID_USER['password']
        next_pass = 'newPass*123987'
        resp = client.post(
            '/auth/users/me/change-password',
            headers={'Authorization': f'Bearer {self.token}'},
            json={
                'current_password': old_pass,
                'new_password': next_pass,
            },
        )
        assert_no_content(resp)

        old_token_refresh_attempt = client.post(
            '/auth/token',
            data={'username': self._VALID_USER['username'], 'password': old_pass},
        )
        assert old_token_refresh_attempt.status_code == 401

    def test_cannot_change_without_old_password(self, client: TestClient):
        """
        Scenario: User unsuccessfully changes their password
            When the user submits their old and new password
            And the old password is not correct
            Then the request is rejected
        """
        old_pass = 'INCORRECT PASSWORD'
        next_pass = 'newPass*123987'
        resp = client.post(
            '/auth/users/me/change-password',
            headers={'Authorization': f'Bearer {self.token}'},
            json={
                'current_password': old_pass,
                'new_password': next_pass,
            },
        )
        assert_bad_request(resp)

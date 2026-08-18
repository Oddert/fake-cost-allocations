"""
Tests for the allocation period endpoints.

Endpoints under test
--------------------
  POST  /periods
  GET   /periods
  GET   /periods/{period_id}
  PATCH /periods/{period_id}
  POST  /periods/{period_id}/lock
"""

import pytest
from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_bad_request,
    assert_created,
    assert_forbidden,
    assert_not_found,
    assert_ok,
    assert_unprocessable,
)


def assert_period_shape(data: dict) -> None:
    required = {
        'period_id',
        'name',
        'mode',
        'fiscal_year',
        'status',
        'created_by',
        'created_at',
    }
    missing = required - data.keys()
    assert not missing, f'Period missing fields: {missing}'
    assert isinstance(data['period_id'], int), 'period_id must be an integer'
    assert data['mode'] in ('budget', 'actual'), (
        f'mode must be budget or actual, got {data["mode"]}'
    )
    assert data['status'] in ('open', 'locked', 'submitted'), (
        f'unexpected status: {data["status"]}'
    )
    assert isinstance(data['fiscal_year'], int), 'fiscal_year must be an integer'


class TestCreatePeriod:
    """Feature: Creating a new allocation period - POST /periods"""

    _PERIOD = {'name': 'FY2027 Budget', 'mode': 'budget', 'fiscal_year': 2027}

    def _create(self, client: TestClient, headers: dict, payload: dict):
        return client.post('/periods', headers=headers, json=payload)

    @pytest.mark.parametrize(
        'role,headers_fixture',
        [
            ('admin', 'admin_headers'),
            ('analyst', 'analyst_headers'),
        ],
    )
    def test_privileged_users_can_create_periods(
        self, client: TestClient, request, role: str, headers_fixture: str
    ):
        """
        Scenario: Privileged users can create a new allocation period
            Given the user holds a valid role (admin or analyst)
            When the user submits new allocation period details
            Then the new allocation period is created and returned
            And it appears in the full list of allocation periods
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._create(client, headers, self._PERIOD)
        assert_created(resp)
        data = resp.json()
        assert_period_shape(data)
        assert data['name'] == self._PERIOD['name']
        assert data['mode'] == self._PERIOD['mode']
        assert data['status'] == 'open'

        period_ids = {
            p['period_id'] for p in client.get('/periods', headers=headers).json()
        }
        assert data['period_id'] in period_ids

    def test_viewers_cannot_create_periods(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: Non-analysts cannot create an allocation period
            Given the user does not hold the "admin" or "analyst" role
            Then the request is rejected with an unprivileged message
        """
        resp = self._create(client, viewer_headers, self._PERIOD)
        assert_forbidden(resp)

    def test_invalid_mode_rejected(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: Invalid mode value is rejected
            The mode field must be 'budget' or 'actual'.
        """
        resp = self._create(
            client, analyst_headers, {**self._PERIOD, 'mode': 'invalid'}
        )
        assert_unprocessable(resp)

    def test_fiscal_year_below_range_rejected(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: fiscal_year below 2000 is rejected (schema: ge=2000)
        """
        resp = self._create(
            client, analyst_headers, {**self._PERIOD, 'fiscal_year': 1999}
        )
        assert_unprocessable(resp)

    def test_fiscal_year_above_range_rejected(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: fiscal_year above 2100 is rejected (schema: le=2100)
        """
        resp = self._create(
            client, analyst_headers, {**self._PERIOD, 'fiscal_year': 2101}
        )
        assert_unprocessable(resp)

    def test_fiscal_month_out_of_range_rejected(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: fiscal_month must be 1-12
        """
        resp = self._create(
            client, analyst_headers, {**self._PERIOD, 'fiscal_month': 13}
        )
        assert_unprocessable(resp)

    def test_fiscal_month_is_optional(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A period can be created without a fiscal_month (annual period)
        """
        resp = self._create(client, analyst_headers, self._PERIOD)
        assert_created(resp)
        assert resp.json()['fiscal_month'] is None


class TestListPeriods:
    """Feature: Get a list of all allocation periods - GET /periods"""

    @pytest.fixture(autouse=True)
    def seed_periods(self, client: TestClient, analyst_headers: dict):
        """Seed a variety of periods for filter tests."""
        periods = [
            {'name': 'FY2025 Budget', 'mode': 'budget', 'fiscal_year': 2025},
            {'name': 'FY2025 Actual', 'mode': 'actual', 'fiscal_year': 2025},
            {'name': 'FY2026 Budget', 'mode': 'budget', 'fiscal_year': 2026},
        ]
        for p in periods:
            client.post('/periods', headers=analyst_headers, json=p)

    def test_returns_all_periods(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of all held allocation periods
            When the user requests allocation periods
            Then a list of all allocation periods is returned
        """
        resp = client.get('/periods', headers=viewer_headers)
        assert_ok(resp)
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        for p in data:
            assert_period_shape(p)

    def test_filter_by_mode(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of only specific modes
            When the user requests allocation periods with a specific mode
            Then all returned periods have that mode value
        """
        resp = client.get('/periods', headers=viewer_headers, params={'mode': 'budget'})
        assert_ok(resp)
        for p in resp.json():
            assert p['mode'] == 'budget', f'Non-budget period returned: {p}'

    def test_filter_by_status(
        self, client: TestClient, viewer_headers: dict, admin_headers: dict
    ):
        """
        Scenario: Get a list of only specific status
            When the user requests allocation periods with a specific status
            Then all returned periods have that status value
        """
        # Lock one period to create a mix
        first_id = client.get('/periods', headers=viewer_headers).json()[0]['period_id']
        client.post(f'/periods/{first_id}/lock', headers=admin_headers)

        resp = client.get(
            '/periods', headers=viewer_headers, params={'status': 'locked'}
        )
        assert_ok(resp)
        assert len(resp.json()) >= 1
        for p in resp.json():
            assert p['status'] == 'locked', f'Non-locked period returned: {p}'

    def test_filter_by_fiscal_year(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of only specific fiscal year
            When the user requests allocation periods with a specific fiscal year
            Then all returned periods have that fiscal year value
        """
        resp = client.get(
            '/periods', headers=viewer_headers, params={'fiscal_year': 2025}
        )
        assert_ok(resp)
        assert len(resp.json()) >= 1
        for p in resp.json():
            assert p['fiscal_year'] == 2025

    def test_filter_by_multiple_params(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of periods with multiple filters
            When the user requests allocation periods with mode, status, and fiscal_year
            Then all returned periods match all filter values
        """
        resp = client.get(
            '/periods',
            headers=viewer_headers,
            params={'mode': 'budget', 'fiscal_year': 2026, 'status': 'open'},
        )
        assert_ok(resp)
        for p in resp.json():
            assert p['mode'] == 'budget'
            assert p['fiscal_year'] == 2026
            assert p['status'] == 'open'


class TestGetPeriod:
    """Feature: Get single allocation period by ID - GET /periods/{period_id}"""

    @pytest.fixture(autouse=True)
    def seed_period(self, client: TestClient, analyst_headers: dict):
        resp = client.post(
            '/periods',
            json={'name': 'Test Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(resp)
        self.seeded_period = resp.json()

    def test_get_period_by_id(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get an allocation period by ID
            When the user requests an allocation period by ID
            Then the allocation period details are returned
        """
        resp = client.get(
            f'/periods/{self.seeded_period["period_id"]}', headers=viewer_headers
        )
        assert_ok(resp)
        assert_period_shape(resp.json())

    def test_missing_period_returns_404(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get an allocation period with a valid-format but non-existent ID
            Then the request is rejected with a not found response
        """
        resp = client.get('/periods/99999', headers=viewer_headers)
        assert_not_found(resp)

    @pytest.mark.parametrize('bad_id', ['hello', '"{}"', '    '])
    def test_invalid_id_returns_422(
        self, client: TestClient, viewer_headers: dict, bad_id
    ):
        """
        Scenario: Get an allocation period with an invalid ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get(f'/periods/{bad_id}', headers=viewer_headers)
        assert_unprocessable(resp)


class TestUpdatePeriod:
    """Feature: Update an allocation period - PATCH /periods/{period_id}"""

    @pytest.fixture(autouse=True)
    def seed_period(self, client: TestClient, analyst_headers: dict):
        resp = client.post(
            '/periods',
            json={'name': 'Test Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(resp)
        self.seeded_period = resp.json()

    def _patch(self, client: TestClient, headers: dict, period_id, payload: dict):
        return client.patch(f'/periods/{period_id}', headers=headers, json=payload)

    @pytest.mark.parametrize(
        'role,headers_fixture',
        [
            ('admin', 'admin_headers'),
            ('analyst', 'analyst_headers'),
        ],
    )
    def test_privileged_users_can_update_period(
        self, client: TestClient, request, role: str, headers_fixture: str
    ):
        """
        Scenario: A privileged user updates an allocation period's details
            Given the user holds a valid role (admin or analyst)
            When the user submits allocation period details
            Then the allocation period is updated and returned
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._patch(
            client,
            headers,
            self.seeded_period['period_id'],
            {'name': 'Updated Name', 'fiscal_month': 3},
        )
        assert_ok(resp)
        data = resp.json()
        assert_period_shape(data)
        assert data['name'] == 'Updated Name'
        assert data['fiscal_month'] == 3

    def test_viewers_cannot_update_periods(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: An unprivileged user updates a period
            Given the user holds the "viewer" role
            Then the request is rejected with an unprivileged error
        """
        resp = self._patch(
            client, viewer_headers, self.seeded_period['period_id'], {'name': 'Nope'}
        )
        assert_forbidden(resp)

    def test_update_locked_period_rejected(
        self, client: TestClient, admin_headers: dict, analyst_headers: dict
    ):
        """
        Scenario: Request to update a locked period
            Given a locked allocation period exists
            When the user submits allocation period details for the locked period
            Then the request is rejected
        """
        client.post(
            f'/periods/{self.seeded_period["period_id"]}/lock', headers=admin_headers
        )
        resp = self._patch(
            client, analyst_headers, self.seeded_period['period_id'], {'name': 'Locked'}
        )
        assert_bad_request(resp)

    def test_update_missing_period_returns_404(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request for a missing period is rejected
            When the user submits allocation period details to a period which does not exist
            Then the request is rejected with not found
        """
        resp = self._patch(client, analyst_headers, 99999, {'name': 'Ghost'})
        assert_not_found(resp)

    @pytest.mark.parametrize('bad_id', ['hello', '"{}"', '    '])
    def test_invalid_id_returns_422(
        self, client: TestClient, analyst_headers: dict, bad_id
    ):
        """
        Scenario: An invalid ID is used in an update
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._patch(client, analyst_headers, bad_id, {'name': 'Bad'})
        assert_unprocessable(resp)

    def test_fiscal_year_cannot_be_updated(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: fiscal_year is not an updatable field (PeriodUpdate schema does not include it)
            When the user submits a fiscal_year in the patch body
            Then fiscal_year on the period is unchanged
        """
        original_year = self.seeded_period['fiscal_year']
        resp = self._patch(
            client,
            analyst_headers,
            self.seeded_period['period_id'],
            {'name': 'Renamed', 'fiscal_year': 2099},
        )
        assert_ok(resp)
        assert resp.json()['fiscal_year'] == original_year, (
            'fiscal_year should not be updatable via PATCH'
        )


class TestLockPeriod:
    """Feature: Lock a period - POST /periods/{period_id}/lock"""

    @pytest.fixture(autouse=True)
    def seed_period(self, client: TestClient, analyst_headers: dict):
        resp = client.post(
            '/periods',
            json={'name': 'Lockable Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(resp)
        self.seeded_period = resp.json()

    def _lock(self, client: TestClient, headers: dict, period_id):
        return client.post(f'/periods/{period_id}/lock', headers=headers)

    def test_admin_can_lock_a_period(self, client: TestClient, admin_headers: dict):
        """
        Scenario: An admin locks an allocation period
            Given the user holds the "admin" role
            And an unlocked allocation period exists
            When the user submits a request to the allocation period ID
            Then the allocation period is locked and returned
        """
        resp = self._lock(client, admin_headers, self.seeded_period['period_id'])
        assert_ok(resp)
        data = resp.json()
        assert_period_shape(data)
        assert data['status'] == 'locked'
        assert data['locked_at'] is not None

    def test_analyst_cannot_lock_a_period(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: An unprivileged user locks an allocation period (analyst)
            Then the request is rejected as unprivileged
        """
        resp = self._lock(client, analyst_headers, self.seeded_period['period_id'])
        assert_forbidden(resp)

    def test_viewer_cannot_lock_a_period(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: An unprivileged user locks an allocation period (viewer)
            Then the request is rejected as unprivileged
        """
        resp = self._lock(client, viewer_headers, self.seeded_period['period_id'])
        assert_forbidden(resp)

    def test_locking_prevents_new_expenses(
        self, client: TestClient, admin_headers: dict, analyst_headers: dict
    ):
        """
        Scenario: An admin locks an allocation period
            And the allocation period can no longer have costs added to it
        """
        # Seed a cost centre so we can attempt an expense
        cc_id = client.get('/cost-centres', headers=admin_headers).json()[0][
            'cost_centre_id'
        ]
        self._lock(client, admin_headers, self.seeded_period['period_id'])

        resp = client.post(
            f'/periods/{self.seeded_period["period_id"]}/expenses',
            headers=analyst_headers,
            json={
                'cost_centre_id': cc_id,
                'description': 'Should fail',
                'amount': '100.00',
            },
        )
        assert_bad_request(resp)

    def test_lock_missing_period_returns_404(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: An invalid ID is used to lock a period — non-existent ID
            Then the request is rejected with not found
        """
        resp = self._lock(client, admin_headers, 99999)
        assert_not_found(resp)

    @pytest.mark.parametrize('bad_id', ['hello', '"{}"', '    '])
    def test_lock_invalid_id_returns_422(
        self, client: TestClient, admin_headers: dict, bad_id
    ):
        """
        Scenario: An invalid ID is used to lock a period
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._lock(client, admin_headers, bad_id)
        assert_unprocessable(resp)

    @pytest.mark.xfail(
        reason=(
            'API returns 400 when a period is already locked rather than 200 with '
            'a notification that no action was taken. Test plan expects idempotent 200.'
        ),
        strict=True,
    )
    def test_locking_already_locked_period_is_idempotent(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: An admin locks an allocation period which is already locked
            Given the user holds the "admin" role
            And that allocation period is already locked
            When the user submits a request to that allocation period ID
            Then the allocation period is returned
            And the user is notified that no action was taken
        """
        self._lock(client, admin_headers, self.seeded_period['period_id'])
        resp = self._lock(client, admin_headers, self.seeded_period['period_id'])
        assert_ok(resp)
        assert resp.json()['status'] == 'locked'

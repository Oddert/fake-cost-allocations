"""
Tests for the activity endpoints.

Endpoints under test
--------------------
  POST   /periods/{period_id}/activities
  GET    /periods/{period_id}/activities
  GET    /periods/{period_id}/activities/{activity_id}
  PATCH  /periods/{period_id}/activities/{activity_id}
  DELETE /periods/{period_id}/activities/{activity_id}
"""

import pytest
from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_bad_request,
    assert_created,
    assert_forbidden,
    assert_no_content,
    assert_not_found,
    assert_ok,
    assert_unprocessable,
)


def assert_activity_shape(data: dict) -> None:
    required = {'activity_id', 'period_id', 'name', 'created_by', 'created_at'}
    missing = required - data.keys()
    assert not missing, f'Activity missing fields: {missing}'
    assert isinstance(data['activity_id'], int), 'activity_id must be an integer'
    assert isinstance(data['period_id'], int), 'period_id must be an integer'
    assert isinstance(data['name'], str) and data['name'], 'name must be a non-empty string'


class TestCreateActivity:
    """Feature: Create an activity - POST /periods/{period_id}/activities"""

    @pytest.fixture(autouse=True)
    def seed_state(self, client: TestClient, analyst_headers: dict):
        period_resp = client.post(
            '/periods',
            json={'name': 'Activity Test Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()
        self._payload = {'name': 'Test Activity', 'description': 'A test activity'}

    def _create(self, client: TestClient, headers: dict, period_id=None, payload=None):
        pid = period_id if period_id is not None else self.period['period_id']
        body = payload if payload is not None else self._payload
        return client.post(f'/periods/{pid}/activities', headers=headers, json=body)

    @pytest.mark.parametrize('role,headers_fixture', [
        ('admin',   'admin_headers'),
        ('analyst', 'analyst_headers'),
    ])
    def test_privileged_users_can_create_activities(
        self, client: TestClient, request, role: str, headers_fixture: str
    ):
        """
        Scenario: A privileged user creates an activity
            Given the user holds a valid role (admin or analyst)
            And an unlocked allocation period exists
            When the user submits a request to create an activity
            Then the activity is created and returned
            And it shows in the list of all activities
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._create(client, headers)
        assert_created(resp)
        data = resp.json()
        assert_activity_shape(data)
        assert data['name'] == self._payload['name']
        assert data['period_id'] == self.period['period_id']

        activity_ids = {a['activity_id'] for a in client.get(
            f'/periods/{self.period["period_id"]}/activities', headers=headers
        ).json()}
        assert data['activity_id'] in activity_ids

    def test_viewers_cannot_create_activities(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: An unprivileged user creates an activity
            Given the user holds the "viewer" role
            Then the request is rejected as unprivileged
        """
        resp = self._create(client, viewer_headers)
        assert_forbidden(resp)

    def test_locked_period_rejects_new_activities(
        self, client: TestClient, admin_headers: dict, analyst_headers: dict
    ):
        """
        Scenario: A request to a locked allocation period is made
            Given a locked allocation period exists
            When the user submits a request to create an activity on the locked period
            Then the request is rejected and an explanation is given
        """
        client.post(f'/periods/{self.period["period_id"]}/lock', headers=admin_headers)
        resp = self._create(client, analyst_headers)
        assert_bad_request(resp)

    def test_invalid_period_id_returns_422(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to an invalid allocation period ID is made
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._create(client, analyst_headers, period_id='hello')
        assert_unprocessable(resp)

    def test_missing_period_returns_404(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to a non-existent allocation period ID is made
            Then the request is rejected with not found
        """
        resp = self._create(client, analyst_headers, period_id=99999)
        assert_not_found(resp)

    def test_description_is_optional(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: An activity can be created without a description
        """
        resp = self._create(client, analyst_headers, payload={'name': 'No Desc Activity'})
        assert_created(resp)
        assert resp.json()['description'] is None

    def test_long_name_rejected(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: Activity name longer than 200 characters is rejected (schema: max_length=200)
        """
        resp = self._create(client, analyst_headers, payload={'name': 'A' * 201})
        assert_unprocessable(resp)


class TestListActivities:
    """Feature: Get all activities - GET /periods/{period_id}/activities"""

    @pytest.fixture(autouse=True)
    def seed_state(self, client: TestClient, analyst_headers: dict):
        period_resp = client.post(
            '/periods',
            json={'name': 'List Activity Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        client.post(
            f'/periods/{self.period["period_id"]}/activities',
            headers=analyst_headers,
            json={'name': 'Seeded Activity'},
        )

    def test_list_activities_for_period(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of activities by allocation period ID
            When the user sends a valid allocation period ID
            Then a list of all activities assigned to that period are returned
        """
        resp = client.get(f'/periods/{self.period["period_id"]}/activities', headers=viewer_headers)
        assert_ok(resp)
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for a in data:
            assert_activity_shape(a)

    def test_invalid_period_id_returns_422(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of activities with an invalid allocation period ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get('/periods/hello/activities', headers=viewer_headers)
        assert_unprocessable(resp)

    def test_missing_period_returns_404(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of activities for a period that does not exist
            Then the request is rejected with not found
        """
        resp = client.get('/periods/99999/activities', headers=viewer_headers)
        assert_not_found(resp)


class TestGetActivity:
    """Feature: Get a single activity by ID - GET /periods/{period_id}/activities/{activity_id}"""

    @pytest.fixture(autouse=True)
    def seed_state(self, client: TestClient, analyst_headers: dict):
        period_resp = client.post(
            '/periods',
            json={'name': 'Get Activity Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        act_resp = client.post(
            f'/periods/{self.period["period_id"]}/activities',
            headers=analyst_headers,
            json={'name': 'Seeded Activity'},
        )
        assert_created(act_resp)
        self.activity = act_resp.json()

    def test_get_activity_by_id(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get an activity by ID
            When the user requests an activity by ID
            Then the matching activity details are returned
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/activities/{self.activity["activity_id"]}',
            headers=viewer_headers,
        )
        assert_ok(resp)
        assert_activity_shape(resp.json())

    def test_invalid_activity_id_returns_422(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get an activity with an invalid activity ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/activities/hello',
            headers=viewer_headers,
        )
        assert_unprocessable(resp)

    def test_invalid_period_id_returns_422(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get an activity with an invalid period ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get(
            f'/periods/hello/activities/{self.activity["activity_id"]}',
            headers=viewer_headers,
        )
        assert_unprocessable(resp)

    def test_missing_activity_returns_404(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a specific activity with a valid-format but non-existent activity ID
            Then the request is rejected with not found
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/activities/99999',
            headers=viewer_headers,
        )
        assert_not_found(resp)

    def test_activity_from_wrong_period_returns_404(
        self, client: TestClient, analyst_headers: dict, viewer_headers: dict
    ):
        """
        Scenario: Get an activity using the correct activity ID but the wrong period ID
            Then the request is rejected with not found
        """
        other_period = client.post(
            '/periods',
            json={'name': 'Other Period', 'mode': 'actual', 'fiscal_year': 2027},
            headers=analyst_headers,
        ).json()

        resp = client.get(
            f'/periods/{other_period["period_id"]}/activities/{self.activity["activity_id"]}',
            headers=viewer_headers,
        )
        assert_not_found(resp)


class TestUpdateActivity:
    """Feature: Update an activity - PATCH /periods/{period_id}/activities/{activity_id}"""

    @pytest.fixture(autouse=True)
    def seed_state(self, client: TestClient, analyst_headers: dict):
        period_resp = client.post(
            '/periods',
            json={'name': 'Update Activity Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        act_resp = client.post(
            f'/periods/{self.period["period_id"]}/activities',
            headers=analyst_headers,
            json={'name': 'Original Name', 'description': 'Original desc'},
        )
        assert_created(act_resp)
        self.activity = act_resp.json()

    def _patch(self, client, headers, period_id=None, activity_id=None, payload=None):
        pid = period_id if period_id is not None else self.period['period_id']
        aid = activity_id if activity_id is not None else self.activity['activity_id']
        body = payload or {'name': 'Updated Name'}
        return client.patch(f'/periods/{pid}/activities/{aid}', headers=headers, json=body)

    @pytest.mark.parametrize('role,headers_fixture', [
        ('admin',   'admin_headers'),
        ('analyst', 'analyst_headers'),
    ])
    def test_privileged_users_can_update_activities(
        self, client: TestClient, request, role: str, headers_fixture: str
    ):
        """
        Scenario: A privileged user updates an activity
            Given the user holds a valid role (admin or analyst)
            And an unlocked allocation period exists
            When the user submits a request to update an activity
            Then the activity is updated and returned
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._patch(
            client, headers,
            payload={'name': 'Revised Name', 'description': 'Revised desc'},
        )
        assert_ok(resp)
        data = resp.json()
        assert_activity_shape(data)
        assert data['name'] == 'Revised Name'
        assert data['description'] == 'Revised desc'

    def test_viewers_cannot_update_activities(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: An unprivileged user updates an activity
            Given the user holds the "viewer" role
            Then the request is rejected as unprivileged
        """
        resp = self._patch(client, viewer_headers)
        assert_forbidden(resp)

    def test_update_on_locked_period_rejected(
        self, client: TestClient, admin_headers: dict, analyst_headers: dict
    ):
        """
        Scenario: A request to a locked allocation period is made
            Given a locked allocation period exists
            When the user submits a request to update an activity on the locked period
            Then the request is rejected and an explanation is given
        """
        client.post(f'/periods/{self.period["period_id"]}/lock', headers=admin_headers)
        resp = self._patch(client, analyst_headers)
        assert_bad_request(resp)

    def test_invalid_period_id_returns_422(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to an invalid allocation period ID is made
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._patch(client, analyst_headers, period_id='hello')
        assert_unprocessable(resp)

    def test_invalid_activity_id_returns_422(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to an invalid activity ID is made
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._patch(client, analyst_headers, activity_id='hello')
        assert_unprocessable(resp)

    def test_missing_activity_returns_404(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to a non-existent activity ID is made
            Then the request is rejected with not found
        """
        resp = self._patch(client, analyst_headers, activity_id=99999)
        assert_not_found(resp)


class TestDeleteActivity:
    """Feature: Delete an activity - DELETE /periods/{period_id}/activities/{activity_id}"""

    @pytest.fixture(autouse=True)
    def seed_state(self, client: TestClient, analyst_headers: dict):
        period_resp = client.post(
            '/periods',
            json={'name': 'Delete Activity Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        act_resp = client.post(
            f'/periods/{self.period["period_id"]}/activities',
            headers=analyst_headers,
            json={'name': 'To Delete'},
        )
        assert_created(act_resp)
        self.activity = act_resp.json()

    def _delete(self, client, headers, period_id=None, activity_id=None):
        pid = period_id if period_id is not None else self.period['period_id']
        aid = activity_id if activity_id is not None else self.activity['activity_id']
        return client.delete(f'/periods/{pid}/activities/{aid}', headers=headers)

    @pytest.mark.parametrize('role,headers_fixture', [
        ('admin',   'admin_headers'),
        ('analyst', 'analyst_headers'),
    ])
    def test_privileged_users_can_delete_activities(
        self, client: TestClient, request, role: str, headers_fixture: str, viewer_headers: dict
    ):
        """
        Scenario: A privileged user deletes an activity
            Given the user holds a valid role (admin or analyst)
            And an unlocked allocation period exists
            When the user submits a request to delete an activity
            Then the activity is deleted (204)
            And the activity does not appear in the full list of activities
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._delete(client, headers)
        assert_no_content(resp)

        remaining = client.get(
            f'/periods/{self.period["period_id"]}/activities', headers=viewer_headers
        ).json()
        ids = {a['activity_id'] for a in remaining}
        assert self.activity['activity_id'] not in ids, 'Deleted activity still present in list'

    def test_viewers_cannot_delete_activities(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: An unprivileged user deletes an activity
            Given the user holds the "viewer" role
            Then the request is rejected as unprivileged
        """
        resp = self._delete(client, viewer_headers)
        assert_forbidden(resp)

    def test_delete_on_locked_period_rejected(
        self, client: TestClient, admin_headers: dict, analyst_headers: dict
    ):
        """
        Scenario: A request to a locked allocation period is made
            Given a locked allocation period exists
            When the user submits a request to delete an activity on the locked period
            Then the request is rejected and an explanation is given
        """
        client.post(f'/periods/{self.period["period_id"]}/lock', headers=admin_headers)
        resp = self._delete(client, analyst_headers)
        assert_bad_request(resp)

    def test_invalid_period_id_returns_422(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to an invalid allocation period ID is made
            Then the request is rejected
        """
        resp = self._delete(client, analyst_headers, period_id='hello')
        assert_unprocessable(resp)

    def test_invalid_activity_id_returns_422(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to an invalid activity ID is made
            Then the request is rejected
        """
        resp = self._delete(client, analyst_headers, activity_id='hello')
        assert_unprocessable(resp)

    def test_missing_activity_returns_404(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: A request to a non-existent activity ID is made
            Then the request is rejected with not found
        """
        resp = self._delete(client, analyst_headers, activity_id=99999)
        assert_not_found(resp)

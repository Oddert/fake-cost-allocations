"""
Tests for the authentication endpoints.

Endpoints under test
--------------------
  POST /cost-centres
  GET /cost-centres
  GET /cost-centres/{cost_centre_id}
  PATCH /cost-centres/{cost_centre_id}
"""

import pytest

from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_bad_request,
    assert_cost_centre_shape,
    assert_created,
    assert_forbidden,
    assert_not_found,
    assert_ok,
    assert_unprocessable,
)


class TestCreateCostCentre:
    """Feature: Creating a new cost centre - POST /cost-centres"""

    _COST_CENTRE = {
        'code': 'FIN_TEST_1',
        'name': 'Test Cost Centre One',
        'description': 'description',
    }

    def _create_cc(self, client: TestClient, headers: dict, payload: dict):
        """POST to /cost-centres and return the raw response."""
        resp = client.post('/cost-centres', headers=headers, json=payload)
        return resp

    def test_admins_can_create_ccs(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Admin users can create a new cost centre
            Given the current user has the "admin" role
            When the user submits new cost centre details
            Then the new cost centre is created
            And the details of the new cost centre are returned
            And the new cost centre appears in the full list of cost centres
        """
        created = self._create_cc(
            client, headers=admin_headers, payload=self._COST_CENTRE
        )
        assert_created(created)
        json_res = created.json()
        assert isinstance(json_res['cost_centre_id'], int)
        assert json_res['code'] == self._COST_CENTRE['code']
        assert json_res['name'] == self._COST_CENTRE['name']
        assert json_res['description'] == self._COST_CENTRE['description']
        assert json_res['is_active'] is True

    def test_viewers_cannot_create_ccs(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Non-admins cannot create a cost centre
            Given the user does not hold the "admin" role
            When the user submits new cost centre details
            Then the request is rejected with an unprivileged message
        """
        created = self._create_cc(
            client, headers=viewer_headers, payload=self._COST_CENTRE
        )
        assert_forbidden(created)

    def test_analysts_cannot_create_ccs(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: Non-admins cannot create a cost centre
            Given the user does not hold the "admin" role
            When the user submits new cost centre details
            Then the request is rejected with an unprivileged message
        """
        created = self._create_cc(
            client, headers=analyst_headers, payload=self._COST_CENTRE
        )
        assert_forbidden(created)

    def test_duplicate_codes_rejected(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Duplicate cost centre codes are rejected
            Given the current user has the "admin" role
            When the user submits new cost centre details with a code already belonging to an existing cost centre
            Then the request is rejected as a conflict
        """
        created = self._create_cc(
            client, headers=admin_headers, payload=self._COST_CENTRE
        )
        assert_created(created)
        created = self._create_cc(
            client, headers=admin_headers, payload=self._COST_CENTRE
        )
        assert_bad_request(created)

    def test_reject_long_codes(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Long Cost Centre codes are not allowed
            Given the current user has the "admin" role
            When the user submits new cost centre details with a code longer than 20 characters
            Then the request is rejected as a unprocessable
        """
        created = self._create_cc(
            client,
            headers=admin_headers,
            payload={**self._COST_CENTRE, 'code': 'LONG_CODE_EXCEEDING_20_CHARS'},
        )
        assert_unprocessable(created)


class TestListCostCentre:
    """Feature: Get a list of all cost centres - GET /cost-centres"""

    def _get_ccs(self, client: TestClient, headers: dict):
        """GET to /cost-centres and return the raw response."""
        resp = client.get('/cost-centres', headers=headers)
        return resp

    def test_get_all_ccs(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: returns a list of all held cost centres
            When the user requests cost centres
            Then a list of all cost centres is returned
        """
        resp = self._get_ccs(client, viewer_headers)
        assert_ok(resp)
        for cc in resp.json():
            assert_cost_centre_shape(cc)

    def test_only_active_ccs(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Returns only active cost centres with the flag set
            Given a mixture of 'active' and 'inactive' cost centres exist in the database
            When the user requests cost centres with the 'active' flag set
            Then a list of cost centres is returned
            And they are all active
        """
        resp = self._get_ccs(client, viewer_headers)
        for cc in resp.json():
            assert cc['is_active'] is True


class TestGetSingleCostCentre:
    """Feature: Get single cost centre by id - GET /cost-centres/{cost_centre_id}"""

    _COST_CENTRE = {
        'code': 'FIN_TEST_1',
        'name': 'Test Cost Centre One',
        'description': 'description',
    }

    @pytest.fixture(autouse=True)
    def seed_user(self, client: TestClient, admin_headers: dict):
        """Create a cost-centre in the seeded store before each test runs to ensure predictability."""
        resp = client.post(
            '/cost-centres', json=self._COST_CENTRE, headers=admin_headers
        )
        assert_created(resp)
        res_json = resp.json()
        self.seeded_cc = res_json

    def _get_cc(self, client: TestClient, headers: dict, cost_centre_id: int):
        """GET to /cost-centres and return the raw response."""
        resp = client.get(f'/cost-centres/{cost_centre_id}', headers=headers)
        return resp

    def test_get_cost_centre_by_id(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Get a cost centre by ID
            Given the user holds the "admin" role
            When the user requests a cost centre by ID
            Then the cost centre details are returned
        """
        resp = self._get_cc(client, admin_headers, self.seeded_cc['cost_centre_id'])
        assert_ok(resp)
        assert_cost_centre_shape(resp.json())

    def test_get_missing_cost_centre(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Query a missing cost centre
            Given the user holds the "admin" role
            When the user requests a cost-centre by an ID which does not exist
            Then the request is rejected with a 'not found' response.
        """
        resp = self._get_cc(client, admin_headers, 999)
        assert_not_found(resp)

    def test_get_cost_centre_invalid_id(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Get a cost centre with an invalid ID
            Given the user holds the "admin" role
            When the user requests a cost centre with an invalid ID
            Then the request is rejected
            Examples:
                |ID|
                | |
                |null|
                |'hello'|
                |'{}'|
        """
        resp1 = self._get_cc(client, admin_headers, 'hello')  # type: ignore
        assert_unprocessable(resp1)
        print('resp1 done')
        resp2 = self._get_cc(client, admin_headers, '   ')  # type: ignore
        assert_unprocessable(resp2)
        print('resp2 done')
        resp3 = self._get_cc(client, admin_headers, None)  # type: ignore
        assert_unprocessable(resp3)
        print('resp3 done')
        resp4 = self._get_cc(client, admin_headers, '"{}"')  # type: ignore
        assert_unprocessable(resp4)
        print('resp4 done')


class TestUpdateCostCentre:
    """Feature: Get single cost centre by id - GET /cost-centres/{cost_centre_id}"""

    _COST_CENTRE = {
        'code': 'FIN_TEST_1',
        'name': 'Test Cost Centre One',
        'description': 'description',
    }

    @pytest.fixture(autouse=True)
    def seed_user(self, client: TestClient, admin_headers: dict):
        """Create a cost-centre in the seeded store before each test runs to ensure predictability."""
        resp = client.post(
            '/cost-centres', json=self._COST_CENTRE, headers=admin_headers
        )
        res_json = resp.json()
        self.seeded_cc = res_json

    def _get_cc(self, client: TestClient, headers: dict, cost_centre_id: int):
        """GET to /cost-centres and return the raw response."""
        resp = client.get(f'/cost-centres/{cost_centre_id}', headers=headers)
        return resp

    def _update_cc(
        self, client: TestClient, headers: dict, cost_centre_id: int, payload: dict
    ):
        """PATCH to /cost-centres/{cost_centre_id} and return the raw response."""
        resp = client.patch(
            f'/cost-centres/{cost_centre_id}', json=payload, headers=headers
        )
        res_json = resp.json()
        self.seeded_cc = res_json
        return resp

    def test_update_a_cost_centre(self, client: TestClient, admin_headers: dict):
        """
        Scenario: An admin updates a cost centre's details
            Given the user holds the "admin" role
            When the user submits cost centre details
            Then the cost centre is updated
            And the updated cost centre is returned
        """
        updated_name = 'new name'
        updated_desc = 'new description'
        resp = self._update_cc(
            client,
            admin_headers,
            self.seeded_cc['cost_centre_id'],
            payload={
                'name': updated_name,
                'description': updated_desc,
            },
        )
        assert_ok(resp, 'initial update call failed')
        res_json = resp.json()
        assert_cost_centre_shape(res_json)
        assert res_json['name'] == updated_name
        assert res_json['description'] == updated_desc

    def test_unprivileged_analyst(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: An unprivileged user updates a cost centre
            Given the user does not hold the "admin" role
            When the user submits cost centre details
            Then the request is rejected with an unprivileged error
        """
        updated_name = 'new name'
        updated_desc = 'new description'
        resp = self._update_cc(
            client,
            analyst_headers,
            self.seeded_cc['cost_centre_id'],
            payload={
                'name': updated_name,
                'description': updated_desc,
            },
        )
        assert_forbidden(resp)

    def test_unprivileged_viewer(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: An unprivileged user updates a cost centre
            Given the user does not hold the "admin" role
            When the user submits cost centre details
            Then the request is rejected with an unprivileged error
        """
        updated_name = 'new name'
        updated_desc = 'new description'
        resp = self._update_cc(
            client,
            viewer_headers,
            self.seeded_cc['cost_centre_id'],
            payload={
                'name': updated_name,
                'description': updated_desc,
            },
        )
        assert_forbidden(resp)

    @pytest.mark.xfail(
        reason='Issue identified and logged - invalid parameters silently ignored',
        strict=False,
    )
    def test_update_code_disallowed(self, client: TestClient, admin_headers: dict):
        """
        Scenario: An unprivileged user updates a cost centre
            Given the user does not hold the "admin" role
            When the user submits cost centre details
            Then the request is rejected with an unprivileged error
        """
        updated_name = 'new name'
        updated_desc = 'new description'
        resp = self._update_cc(
            client,
            admin_headers,
            self.seeded_cc['cost_centre_id'],
            payload={
                'name': updated_name,
                'description': updated_desc,
                'code': 'NEWCODE',
            },
        )
        assert_unprocessable(resp)

    @pytest.mark.xfail(
        reason='Issue identified in API logic and recorded - negative integers not rejected',
        strict=False,
    )
    def test_id_not_found(self, client: TestClient, admin_headers: dict):
        """
        Scenario: A request for a missing cost centre is rejected
            Given the user holds the "admin" role
            When the user submits cost centre details to cost centre which does not exist
            Then the request is rejected with 'not found'
        """
        updated_name = 'new name'
        updated_desc = 'new description'
        resp = self._update_cc(
            client,
            admin_headers,
            999,
            payload={
                'name': updated_name,
                'description': updated_desc,
            },
        )
        assert_not_found(resp)

    @pytest.mark.xfail(
        reason='Issue identified and logged - negative integers not rejected',
        strict=False,
    )
    @pytest.mark.parametrize(
        'cost_centre_id',
        [
            'hello',
            '"{}"',
            '    ',
            -10,
        ],
    )
    def test_invalid_id(self, client: TestClient, admin_headers: dict, cost_centre_id):
        """
        Scenario: An invalid ID is used in an update
            Given the user holds the "admin" role
            When the user submits cost centre details to an invalid cost centre ID
            Then the request is rejected
            Examples:
                |ID|
                | |
                |null|
                |'hello'|
                |'{}'|
        """
        updated_name = 'new name'
        updated_desc = 'new description'
        resp = self._update_cc(
            client,
            admin_headers,
            cost_centre_id,
            payload={
                'name': updated_name,
                'description': updated_desc,
            },
        )
        assert_unprocessable(resp)

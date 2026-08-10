import pytest  # noqa: F401
from fastapi.testclient import TestClient

from tests.utils.assertions import (
    assert_bad_request,  # noqa: F401
    assert_created,  # noqa: F401
    assert_forbidden,  # noqa: F401
    assert_no_content,  # noqa: F401
    assert_no_sensitive_fields,  # noqa: F401
    assert_not_found,  # noqa: F401
    assert_ok,  # noqa: F401
    assert_token_shape,  # noqa: F401
    assert_unauthorised,  # noqa: F401
    assert_unprocessable,  # noqa: F401
    assert_user_shape,  # noqa: F401
)

from tests.utils.assertions import assert_cost_centre_shape


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

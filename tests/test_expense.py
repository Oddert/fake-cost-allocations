"""
Tests for the expense endpoints.

Endpoints under test
--------------------
  POST   /periods/{period_id}/expenses
  GET    /periods/{period_id}/expenses
  GET    /periods/{period_id}/expenses/{expense_id}
  PATCH  /periods/{period_id}/expenses/{expense_id}
  DELETE /periods/{period_id}/expenses/{expense_id}
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


def assert_expense_shape(data: dict) -> None:
    required = {
        'expense_id',
        'period_id',
        'cost_centre_id',
        'description',
        'amount',
        'created_by',
        'created_at',
    }
    missing = required - data.keys()
    assert not missing, f'Expense missing fields: {missing}'
    assert isinstance(data['expense_id'], int), 'expense_id must be an integer'
    assert isinstance(data['period_id'], int), 'period_id must be an integer'
    assert isinstance(data['cost_centre_id'], int), 'cost_centre_id must be an integer'


class TestCreateExpense:
    """Feature: Create an expense - POST /periods/{period_id}/expenses"""

    @pytest.fixture(autouse=True)
    def seed_state(
        self, client: TestClient, analyst_headers: dict, admin_headers: dict
    ):
        """Seed an open period and record a cost_centre_id for expense creation."""
        period_resp = client.post(
            '/periods',
            json={'name': 'Expense Test Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        self.cc_id = client.get('/cost-centres', headers=admin_headers).json()[0][
            'cost_centre_id'
        ]

        self._expense_payload = {
            'cost_centre_id': self.cc_id,
            'description': 'Test expense',
            'amount': '500.00',
        }

    def _create(self, client: TestClient, headers: dict, period_id=None, payload=None):
        pid = period_id if period_id is not None else self.period['period_id']
        body = payload if payload is not None else self._expense_payload
        return client.post(f'/periods/{pid}/expenses', headers=headers, json=body)

    @pytest.mark.parametrize(
        'role,headers_fixture',
        [
            ('admin', 'admin_headers'),
            ('analyst', 'analyst_headers'),
        ],
    )
    def test_privileged_users_can_create_expenses(
        self, client: TestClient, request, role: str, headers_fixture: str
    ):
        """
        Scenario: A privileged user creates an expense
            Given the user holds a valid role (admin or analyst)
            And an unlocked allocation period exists
            When the user submits a request to create an expense
            Then the expense is created and returned
            And it shows in the list of all expenses
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._create(client, headers)
        assert_created(resp)
        data = resp.json()
        assert_expense_shape(data)
        assert data['description'] == self._expense_payload['description']

        expense_ids = {
            e['expense_id']
            for e in client.get(
                f'/periods/{self.period["period_id"]}/expenses', headers=headers
            ).json()
        }
        assert data['expense_id'] in expense_ids

    def test_viewers_cannot_create_expenses(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: An unprivileged user creates an expense
            Given the user holds the "viewer" role
            Then the request is rejected as unprivileged
        """
        resp = self._create(client, viewer_headers)
        assert_forbidden(resp)

    def test_locked_period_rejects_new_expenses(
        self, client: TestClient, admin_headers: dict, analyst_headers: dict
    ):
        """
        Scenario: A request to a locked allocation period is made
            Given a locked allocation period exists
            When the user submits a request to create an expense on the locked period
            Then the request is rejected and an explanation is given
        """
        client.post(f'/periods/{self.period["period_id"]}/lock', headers=admin_headers)
        resp = self._create(client, analyst_headers)
        assert_bad_request(resp)

    def test_invalid_period_id_returns_422(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to an invalid allocation period ID is made
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._create(client, analyst_headers, period_id='hello')
        assert_unprocessable(resp)

    def test_missing_period_returns_404(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to a non-existent allocation period ID is made
            Then the request is rejected with not found
        """
        resp = self._create(client, analyst_headers, period_id=99999)
        assert_not_found(resp)

    def test_invalid_cost_centre_rejected(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request referencing a non-existent cost_centre_id is rejected
        """
        resp = self._create(
            client,
            analyst_headers,
            payload={**self._expense_payload, 'cost_centre_id': 99999},
        )
        assert_bad_request(resp)

    def test_zero_amount_rejected(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: Amount must be greater than zero (schema: gt=0)
        """
        resp = self._create(
            client,
            analyst_headers,
            payload={**self._expense_payload, 'amount': '0.00'},
        )
        assert_unprocessable(resp)

    def test_negative_amount_rejected(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: Negative amounts are rejected (schema: gt=0)
        """
        resp = self._create(
            client,
            analyst_headers,
            payload={**self._expense_payload, 'amount': '-50.00'},
        )
        assert_unprocessable(resp)


class TestListExpenses:
    """Feature: Get all expenses - GET /periods/{period_id}/expenses"""

    @pytest.fixture(autouse=True)
    def seed_state(
        self, client: TestClient, analyst_headers: dict, admin_headers: dict
    ):
        period_resp = client.post(
            '/periods',
            json={'name': 'Expense List Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        cc_id = client.get('/cost-centres', headers=admin_headers).json()[0][
            'cost_centre_id'
        ]
        client.post(
            f'/periods/{self.period["period_id"]}/expenses',
            headers=analyst_headers,
            json={'cost_centre_id': cc_id, 'description': 'First', 'amount': '100.00'},
        )

    def test_list_expenses_for_period(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of expenses by allocation period ID
            When the user sends a valid allocation period ID
            Then a list of all expenses assigned to that period are returned
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/expenses', headers=viewer_headers
        )
        assert_ok(resp)
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for e in data:
            assert_expense_shape(e)

    def test_invalid_period_id_returns_422(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: Get a list of expenses with an invalid allocation period ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get('/periods/hello/expenses', headers=viewer_headers)
        assert_unprocessable(resp)

    def test_missing_period_returns_404(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a list of expenses for a period that does not exist
            Then the request is rejected with not found
        """
        resp = client.get('/periods/99999/expenses', headers=viewer_headers)
        assert_not_found(resp)


class TestGetExpense:
    """Feature: Get single expense - GET /periods/{period_id}/expenses/{expense_id}"""

    @pytest.fixture(autouse=True)
    def seed_state(
        self, client: TestClient, analyst_headers: dict, admin_headers: dict
    ):
        period_resp = client.post(
            '/periods',
            json={'name': 'Get Expense Period', 'mode': 'budget', 'fiscal_year': 2027},
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        cc_id = client.get('/cost-centres', headers=admin_headers).json()[0][
            'cost_centre_id'
        ]
        exp_resp = client.post(
            f'/periods/{self.period["period_id"]}/expenses',
            headers=analyst_headers,
            json={'cost_centre_id': cc_id, 'description': 'Seeded', 'amount': '200.00'},
        )
        assert_created(exp_resp)
        self.expense = exp_resp.json()

    def test_get_expense_by_id(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get an expense by ID
            When the user requests an expense by ID
            Then the matching expense details are returned
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/expenses/{self.expense["expense_id"]}',
            headers=viewer_headers,
        )
        assert_ok(resp)
        assert_expense_shape(resp.json())

    def test_invalid_expense_id_returns_422(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: Get an expense with an invalid expense ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/expenses/hello',
            headers=viewer_headers,
        )
        assert_unprocessable(resp)

    def test_invalid_period_id_returns_422(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: Get an expense with an invalid period ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get(
            f'/periods/hello/expenses/{self.expense["expense_id"]}',
            headers=viewer_headers,
        )
        assert_unprocessable(resp)

    def test_missing_expense_returns_404(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: Get a single expense with a valid-format but non-existent expense ID
            Then the request is rejected with not found
        """
        resp = client.get(
            f'/periods/{self.period["period_id"]}/expenses/99999',
            headers=viewer_headers,
        )
        assert_not_found(resp)

    def test_expense_from_wrong_period_returns_404(
        self,
        client: TestClient,
        analyst_headers: dict,
        admin_headers: dict,
        viewer_headers: dict,
    ):
        """
        Scenario: Get an expense using the correct expense ID but the wrong period ID
            Then the request is rejected with not found
        """
        other_period = client.post(
            '/periods',
            json={'name': 'Other Period', 'mode': 'actual', 'fiscal_year': 2027},
            headers=analyst_headers,
        ).json()

        resp = client.get(
            f'/periods/{other_period["period_id"]}/expenses/{self.expense["expense_id"]}',
            headers=viewer_headers,
        )
        assert_not_found(resp)


class TestUpdateExpense:
    """Feature: Update an expense - PATCH /periods/{period_id}/expenses/{expense_id}"""

    @pytest.fixture(autouse=True)
    def seed_state(
        self, client: TestClient, analyst_headers: dict, admin_headers: dict
    ):
        period_resp = client.post(
            '/periods',
            json={
                'name': 'Update Expense Period',
                'mode': 'budget',
                'fiscal_year': 2027,
            },
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        cc_id = client.get('/cost-centres', headers=admin_headers).json()[0][
            'cost_centre_id'
        ]
        exp_resp = client.post(
            f'/periods/{self.period["period_id"]}/expenses',
            headers=analyst_headers,
            json={
                'cost_centre_id': cc_id,
                'description': 'Original',
                'amount': '300.00',
            },
        )
        assert_created(exp_resp)
        self.expense = exp_resp.json()

    def _patch(self, client, headers, period_id=None, expense_id=None, payload=None):
        pid = period_id if period_id is not None else self.period['period_id']
        eid = expense_id if expense_id is not None else self.expense['expense_id']
        body = payload or {'description': 'Updated'}
        return client.patch(
            f'/periods/{pid}/expenses/{eid}', headers=headers, json=body
        )

    @pytest.mark.parametrize(
        'role,headers_fixture',
        [
            ('admin', 'admin_headers'),
            ('analyst', 'analyst_headers'),
        ],
    )
    def test_privileged_users_can_update_expenses(
        self, client: TestClient, request, role: str, headers_fixture: str
    ):
        """
        Scenario: A privileged user updates an expense
            Given the user holds a valid role (admin or analyst)
            And an unlocked allocation period exists
            When the user submits a request to update an expense
            Then the expense is updated and returned
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._patch(
            client, headers, payload={'description': 'Revised', 'amount': '999.00'}
        )
        assert_ok(resp)
        data = resp.json()
        assert_expense_shape(data)
        assert data['description'] == 'Revised'

    def test_viewers_cannot_update_expenses(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: An unprivileged user updates an expense
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
            When the user submits a request to update an expense on the locked period
            Then the request is rejected and an explanation is given
        """
        client.post(f'/periods/{self.period["period_id"]}/lock', headers=admin_headers)
        resp = self._patch(client, analyst_headers)
        assert_bad_request(resp)

    def test_invalid_period_id_returns_422(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to an invalid allocation period ID is made
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._patch(client, analyst_headers, period_id='hello')
        assert_unprocessable(resp)

    def test_invalid_expense_id_returns_422(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to an invalid expense ID is made
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._patch(client, analyst_headers, expense_id='hello')
        assert_unprocessable(resp)

    def test_missing_expense_returns_404(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to a non-existent expense ID is made
            Then the request is rejected with not found
        """
        resp = self._patch(client, analyst_headers, expense_id=99999)
        assert_not_found(resp)


class TestDeleteExpense:
    """Feature: Delete an expense - DELETE /periods/{period_id}/expenses/{expense_id}"""

    @pytest.fixture(autouse=True)
    def seed_state(
        self, client: TestClient, analyst_headers: dict, admin_headers: dict
    ):
        period_resp = client.post(
            '/periods',
            json={
                'name': 'Delete Expense Period',
                'mode': 'budget',
                'fiscal_year': 2027,
            },
            headers=analyst_headers,
        )
        assert_created(period_resp)
        self.period = period_resp.json()

        cc_id = client.get('/cost-centres', headers=admin_headers).json()[0][
            'cost_centre_id'
        ]
        exp_resp = client.post(
            f'/periods/{self.period["period_id"]}/expenses',
            headers=analyst_headers,
            json={
                'cost_centre_id': cc_id,
                'description': 'To Delete',
                'amount': '50.00',
            },
        )
        assert_created(exp_resp)
        self.expense = exp_resp.json()

    def _delete(self, client, headers, period_id=None, expense_id=None):
        pid = period_id if period_id is not None else self.period['period_id']
        eid = expense_id if expense_id is not None else self.expense['expense_id']
        return client.delete(f'/periods/{pid}/expenses/{eid}', headers=headers)

    @pytest.mark.parametrize(
        'role,headers_fixture',
        [
            ('admin', 'admin_headers'),
            ('analyst', 'analyst_headers'),
        ],
    )
    def test_privileged_users_can_delete_expenses(
        self,
        client: TestClient,
        request,
        role: str,
        headers_fixture: str,
        viewer_headers: dict,
    ):
        """
        Scenario: A privileged user deletes an expense
            Given the user holds a valid role (admin or analyst)
            And an unlocked allocation period exists
            When the user submits a request to delete an expense
            Then the expense is deleted (204)
            And the expense does not appear in the full list of expenses
            Examples: |admin| |analyst|
        """
        headers = request.getfixturevalue(headers_fixture)
        resp = self._delete(client, headers)
        assert_no_content(resp)

        remaining = client.get(
            f'/periods/{self.period["period_id"]}/expenses', headers=viewer_headers
        ).json()
        ids = {e['expense_id'] for e in remaining}
        assert self.expense['expense_id'] not in ids, (
            'Deleted expense still present in list'
        )

    def test_viewers_cannot_delete_expenses(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: An unprivileged user deletes an expense
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
            When the user submits a request to delete an expense on the locked period
            Then the request is rejected and an explanation is given
        """
        client.post(f'/periods/{self.period["period_id"]}/lock', headers=admin_headers)
        resp = self._delete(client, analyst_headers)
        assert_bad_request(resp)

    def test_invalid_period_id_returns_422(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to an invalid allocation period ID is made
            Then the request is rejected
        """
        resp = self._delete(client, analyst_headers, period_id='hello')
        assert_unprocessable(resp)

    def test_invalid_expense_id_returns_422(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to an invalid expense ID is made
            Then the request is rejected
        """
        resp = self._delete(client, analyst_headers, expense_id='hello')
        assert_unprocessable(resp)

    def test_missing_expense_returns_404(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: A request to a non-existent expense ID is made
            Then the request is rejected with not found
        """
        resp = self._delete(client, analyst_headers, expense_id=99999)
        assert_not_found(resp)

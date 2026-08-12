"""
Tests for the legal entity endpoints.

Endpoints under test
--------------------
  POST  /legal-entities
  GET   /legal-entities
  GET   /legal-entities/{legal_entity_id}
  PATCH /legal-entities/{legal_entity_id}
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


def assert_legal_entity_shape(data: dict) -> None:
    required = {'legal_entity_id', 'code', 'name', 'is_active'}
    missing = required - data.keys()
    assert not missing, f'LegalEntity missing fields: {missing}'
    assert isinstance(data['legal_entity_id'], int), 'legal_entity_id must be an integer'
    assert isinstance(data['code'], str) and data['code'], 'code must be a non-empty string'
    assert isinstance(data['name'], str) and data['name'], 'name must be a non-empty string'
    assert isinstance(data['is_active'], bool), 'is_active must be a boolean'
    if data.get('country_code') is not None:
        assert isinstance(data['country_code'], str), 'country_code must be a string'


class TestCreateLegalEntity:
    """Feature: Creating a new legal entity - POST /legal-entities"""

    _LEGAL_ENTITY = {
        'code': 'FR001',
        'name': 'Acme France SAS',
        'country_code': 'FRA',
    }

    def _create_le(self, client: TestClient, headers: dict, payload: dict):
        return client.post('/legal-entities', headers=headers, json=payload)

    def test_admins_can_create_legal_entities(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Admin users can create a new legal entity
            Given the current user has the "admin" role
            When the user submits new legal entity details
            Then the new legal entity is created
            And the details of the new legal entity are returned
            And the new legal entity appears in the full list of legal entities
        """
        resp = self._create_le(client, admin_headers, self._LEGAL_ENTITY)
        assert_created(resp)
        data = resp.json()
        assert_legal_entity_shape(data)
        assert data['code'] == self._LEGAL_ENTITY['code']
        assert data['name'] == self._LEGAL_ENTITY['name']
        assert data['country_code'] == self._LEGAL_ENTITY['country_code']
        assert data['is_active'] is True

        codes = {le['code'] for le in client.get('/legal-entities', headers=admin_headers).json()}
        assert self._LEGAL_ENTITY['code'] in codes

    def test_viewers_cannot_create_legal_entities(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Non-admins cannot create a legal entity
            Given the user does not hold the "admin" role (viewer)
            Then the request is rejected with an unprivileged message
        """
        resp = self._create_le(client, viewer_headers, self._LEGAL_ENTITY)
        assert_forbidden(resp)

    def test_analysts_cannot_create_legal_entities(self, client: TestClient, analyst_headers: dict):
        """
        Scenario: Non-admins cannot create a legal entity
            Given the user does not hold the "admin" role (analyst)
            Then the request is rejected with an unprivileged message
        """
        resp = self._create_le(client, analyst_headers, self._LEGAL_ENTITY)
        assert_forbidden(resp)

    def test_duplicate_codes_are_rejected(self, client: TestClient, admin_headers: dict):
        """
        Scenario: Duplicate legal entity codes are rejected
            Given the current user has the "admin" role
            When the user submits an LE code already belonging to an existing legal entity
            Then the request is rejected as a conflict
        """
        self._create_le(client, admin_headers, self._LEGAL_ENTITY)
        resp = self._create_le(client, admin_headers, self._LEGAL_ENTITY)
        assert_bad_request(resp)

    def test_reject_long_codes(self, client: TestClient, admin_headers: dict):
        """
        Scenario: code longer than 20 characters is rejected
        """
        resp = self._create_le(
            client, admin_headers,
            {**self._LEGAL_ENTITY, 'code': 'A_CODE_THAT_IS_WAY_TOO_LONG_FOR_THE_FIELD'},
        )
        assert_unprocessable(resp)

    def test_reject_long_country_codes(self, client: TestClient, admin_headers: dict):
        """
        Scenario: country_code longer than 3 characters is rejected
        """
        resp = self._create_le(
            client, admin_headers,
            {**self._LEGAL_ENTITY, 'country_code': 'TOOLONG'},
        )
        assert_unprocessable(resp)

    def test_country_code_is_optional(self, client: TestClient, admin_headers: dict):
        """
        Scenario: A legal entity can be created without a country_code
        """
        resp = self._create_le(client, admin_headers, {'code': 'NO001', 'name': 'Acme No Country'})
        assert_created(resp)
        assert resp.json()['country_code'] is None


class TestListLegalEntities:
    """Feature: Get a list of all legal entities - GET /legal-entities"""

    def test_returns_list_of_legal_entities(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: returns a list of all held legal entities
            When the user requests legal entities
            Then a list of all legal entities is returned
        """
        resp = client.get('/legal-entities', headers=viewer_headers)
        assert_ok(resp)
        for le in resp.json():
            assert_legal_entity_shape(le)

    def test_active_only_flag_filters_inactive(
        self, client: TestClient, admin_headers: dict, viewer_headers: dict
    ):
        """
        Scenario: Returns only active legal entities with the active flag set
            Given a mixture of active and inactive legal entities exist
            When the user requests legal entities with active_only=True
            Then only active legal entities are returned
        """
        le_id = client.get('/legal-entities', headers=admin_headers).json()[0]['legal_entity_id']
        client.patch(f'/legal-entities/{le_id}', headers=admin_headers, json={'is_active': False})

        resp = client.get('/legal-entities', headers=viewer_headers, params={'active_only': True})
        assert_ok(resp)
        for le in resp.json():
            assert le['is_active'] is True, (
                f"Inactive entity {le['code']} returned when active_only=True"
            )

    def test_all_returned_when_active_only_false(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: Returns all legal entities including inactive when active_only=False
        """
        le_id = client.get('/legal-entities', headers=admin_headers).json()[0]['legal_entity_id']
        client.patch(f'/legal-entities/{le_id}', headers=admin_headers, json={'is_active': False})

        resp = client.get('/legal-entities', headers=admin_headers, params={'active_only': False})
        assert_ok(resp)
        statuses = {le['is_active'] for le in resp.json()}
        assert False in statuses, 'Expected at least one inactive entity when active_only=False'


class TestGetLegalEntity:
    """Feature: Get single legal entity by ID - GET /legal-entities/{legal_entity_id}"""

    _LEGAL_ENTITY = {'code': 'FR001', 'name': 'Acme France SAS', 'country_code': 'FRA'}

    @pytest.fixture(autouse=True)
    def seed_legal_entity(self, client: TestClient, admin_headers: dict):
        resp = client.post('/legal-entities', json=self._LEGAL_ENTITY, headers=admin_headers)
        assert_created(resp)
        self.seeded_le = resp.json()

    def test_get_legal_entity_by_id(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a legal entity by ID
            When the user requests a legal entity by ID
            Then the legal entity details are returned
        """
        resp = client.get(f'/legal-entities/{self.seeded_le["legal_entity_id"]}', headers=viewer_headers)
        assert_ok(resp)
        assert_legal_entity_shape(resp.json())
        assert resp.json()['code'] == self._LEGAL_ENTITY['code']

    def test_missing_legal_entity_returns_404(self, client: TestClient, viewer_headers: dict):
        """
        Scenario: Get a legal entity with a valid-format but non-existent ID
            Then the request is rejected with a not found response
        """
        resp = client.get('/legal-entities/99999', headers=viewer_headers)
        assert_not_found(resp)

    @pytest.mark.parametrize('bad_id', ['hello', '"{}"', '    '])
    def test_invalid_id_returns_422(self, client: TestClient, viewer_headers: dict, bad_id):
        """
        Scenario: Get a legal entity with an invalid ID
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = client.get(f'/legal-entities/{bad_id}', headers=viewer_headers)
        assert_unprocessable(resp)


class TestUpdateLegalEntity:
    """Feature: Update a legal entity - PATCH /legal-entities/{legal_entity_id}"""

    _LEGAL_ENTITY = {'code': 'FR001', 'name': 'Acme France SAS', 'country_code': 'FRA'}

    @pytest.fixture(autouse=True)
    def seed_legal_entity(self, client: TestClient, admin_headers: dict):
        resp = client.post('/legal-entities', json=self._LEGAL_ENTITY, headers=admin_headers)
        assert_created(resp)
        self.seeded_le = resp.json()

    def _patch(self, client: TestClient, headers: dict, le_id, payload: dict):
        return client.patch(f'/legal-entities/{le_id}', headers=headers, json=payload)

    def test_admin_can_update_name_country_and_active_status(
        self, client: TestClient, admin_headers: dict
    ):
        """
        Scenario: An admin updates a legal entity's details
            Given the user holds the "admin" role
            When the user submits legal entity details
            Then the legal entity is updated and the updated legal entity is returned
        """
        resp = self._patch(
            client, admin_headers, self.seeded_le['legal_entity_id'],
            {'name': 'Acme France Revised', 'country_code': 'FRA', 'is_active': False},
        )
        assert_ok(resp)
        data = resp.json()
        assert_legal_entity_shape(data)
        assert data['name'] == 'Acme France Revised'
        assert data['is_active'] is False

    def test_analysts_cannot_update_legal_entities(
        self, client: TestClient, analyst_headers: dict
    ):
        """
        Scenario: An unprivileged user (analyst) updates a legal entity
            Then the request is rejected with an unprivileged error
        """
        resp = self._patch(client, analyst_headers, self.seeded_le['legal_entity_id'], {'name': 'Nope'})
        assert_forbidden(resp)

    def test_viewers_cannot_update_legal_entities(
        self, client: TestClient, viewer_headers: dict
    ):
        """
        Scenario: An unprivileged user (viewer) updates a legal entity
            Then the request is rejected with an unprivileged error
        """
        resp = self._patch(client, viewer_headers, self.seeded_le['legal_entity_id'], {'name': 'Nope'})
        assert_forbidden(resp)

    def test_update_missing_id_returns_404(self, client: TestClient, admin_headers: dict):
        """
        Scenario: An invalid ID is used in an update — non-existent entity
            Then the request is rejected with not found
        """
        resp = self._patch(client, admin_headers, 99999, {'name': 'Ghost'})
        assert_not_found(resp)

    @pytest.mark.parametrize('bad_id', ['hello', '"{}"', '    '])
    def test_invalid_id_returns_422(self, client: TestClient, admin_headers: dict, bad_id):
        """
        Scenario: An invalid ID is used in an update
            Then the request is rejected
            Examples: |hello| |'{}'| | |
        """
        resp = self._patch(client, admin_headers, bad_id, {'name': 'Bad ID'})
        assert_unprocessable(resp)

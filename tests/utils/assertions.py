"""
Shared assertion helpers for the cost-allocations test suite.

Based on learned best-practice in PICoE SE and use of standard API response handlers: https://docs.pytest.org/en/stable/how-to/assert.html#assertions-about-expected-exceptions
"""

from __future__ import annotations

from httpx import Response

# Fields that must never be present in any response body
SENSITIVE_FIELDS = frozenset(
    {
        'hashed_pwd',
        'password',
        'hashed_password',
        'secret',
        'token_secret',
    }
)


def assert_ok(resp: Response, msg: str = '') -> None:
    """Assert the response is 200 OK."""
    _assert_status(resp, 200, msg)


def assert_created(resp: Response, msg: str = '') -> None:
    """Assert the response is 201 Created."""
    _assert_status(resp, 201, msg)


def assert_no_content(resp: Response, msg: str = '') -> None:
    """Assert the response is 204 No Content."""
    _assert_status(resp, 204, msg)


def assert_bad_request(resp: Response, msg: str = '') -> None:
    """Assert the response is 400 Bad Request."""
    _assert_status(resp, 400, msg)


def assert_unauthorised(resp: Response, msg: str = '') -> None:
    """Assert the response is 401 Unauthorized."""
    _assert_status(resp, 401, msg)


def assert_forbidden(resp: Response, msg: str = '') -> None:
    """Assert the response is 403 Forbidden."""
    _assert_status(resp, 403, msg)


def assert_not_found(resp: Response, msg: str = '') -> None:
    """Assert the response is 404 Not Found."""
    _assert_status(resp, 404, msg)


def assert_conflict(resp: Response, msg: str = '') -> None:
    """Assert the response is 409 Conflict."""
    _assert_status(resp, 409, msg)


def assert_unprocessable(resp: Response, msg: str = '') -> None:
    """Assert the response is 422 Unprocessable Entity."""
    _assert_status(resp, 422, msg)


def _assert_status(resp: Response, expected: int, msg: str) -> None:
    suffix = f' — {msg}' if msg else ''
    assert resp.status_code == expected, (
        f'Expected HTTP {expected}, got {resp.status_code}{suffix}\n'
        f'Response body: {resp.text}'
    )


# Security helpers for common occurrences


def assert_no_sensitive_fields(data: dict | list) -> None:
    """
    Recursively assert that no sensitive field names appear anywhere in
    the response data.
    """
    items = data if isinstance(data, list) else [data]
    for item in items:
        _check_object(item)


def _check_object(obj: dict) -> None:
    for key, value in obj.items():
        assert key not in SENSITIVE_FIELDS, (
            f"Sensitive field '{key}' found in response body. "
            'This field must never be returned by the API.'
        )
        if isinstance(value, dict):
            _check_object(value)
        elif isinstance(value, list):
            for element in value:
                if isinstance(element, dict):
                    _check_object(element)


def assert_token_shape(data: dict) -> None:
    """Assert a token response contains the expected fields."""
    assert 'access_token' in data, f"Missing 'access_token' in response: {data}"
    assert 'token_type' in data, f"Missing 'token_type' in response: {data}"
    assert data['token_type'] == 'bearer', (
        f"Expected token_type 'bearer', got '{data['token_type']}'"
    )
    assert isinstance(data['access_token'], str), 'access_token must be a string'
    assert len(data['access_token']) > 0, 'access_token must not be empty'


def assert_user_shape(data: dict) -> None:
    """
    Assert a user response object has the correct shape and no sensitive fields.
    """
    required = {'user_id', 'username', 'email', 'role', 'is_active'}
    missing = required - data.keys()
    assert not missing, f'UserResponse missing fields: {missing}'

    assert isinstance(data['user_id'], int), 'user_id must be an integer'
    assert isinstance(data['username'], str) and data['username'], (
        'username must be a non-empty string'
    )
    assert isinstance(data['email'], str) and '@' in data['email'], (
        'email must be a valid string'
    )
    assert data['role'] in ('admin', 'analyst', 'viewer'), (
        f"role must be one of admin/analyst/viewer, got '{data['role']}'"
    )
    assert isinstance(data['is_active'], bool), 'is_active must be a boolean'

    assert_no_sensitive_fields(data)


def assert_cost_centre_shape(data: dict) -> None:
    """
    Assert a cost centre object has the correct shape and no sensitive fields.
    """
    required = {'code', 'name', 'is_active'}
    missing = required - data.keys()
    assert not missing, f'UserResponse missing fields: {missing}'

    assert isinstance(data['code'], str) and data['code'], (
        'code must be a non-empty string'
    )
    assert isinstance(data['description'], str) and data['description'], (
        'description must be a non-empty string'
    )
    if data['description']:
        assert isinstance(data['description'], str), (
            'description must be a valid string or null'
        )
    if data['cost_centre_id']:
        assert isinstance(data['cost_centre_id'], int), (
            'cost_centre_id must be a valid string or null'
        )
    assert isinstance(data['is_active'], bool), 'is_active must be a boolean'

    assert_no_sensitive_fields(data)


def assert_error_detail(resp: Response, fragment: str) -> None:
    """
    Assert the response body contains a 'detail' field whose string
    representation includes the given fragment (case-insensitive).
    """
    body = resp.json()
    assert 'detail' in body, f"No 'detail' key in error response: {body}"
    detail = body['detail']
    detail_str = str(detail).lower()
    assert fragment.lower() in detail_str, (
        f"Expected error detail to contain '{fragment}', got: {detail}"
    )

# Test Cases

setup-teardown|scenario
---|---
database is empty|database is reset on each requests with seed data
protected endpoints|endpoints require a valid authentication token

feature|scenario
---|---
auth|all endpoints reject non-authenticated users
login|successful login as an existing user
login|failed login with incorrect credentials
list users|rejects if insufficient privileges
list users|returns a list of existing users
list users|does not return private data
create user|rejects requests without username, email, password
create user|rejects requests from a non-admin
create user|creates a user with correct details
create user|shows the new user in the full list
create user|allows login form the new user
create user|informs of an existing user if a duplicate is requested
create user|enforces a level of password complexity
get user details|returns the current user profile only
deactivate user|rejects non-admin requests
deactivate user|returns confirmation of a deactivated user
deactivate user|user can no longer login after deactivation
change password|user can change their own password if they supply the old one
change password|old password can no longer be used
create new cost centre|rejects requests from non-admins
create new cost centre|rejects requests for a duplicate code
create new cost centre|returns a list of cost centres
get all cost centres|returns a list of all held cost centers
get cost centre by id|if a valid ID is supplied returns that cost center
get cost centre by id|if no valid ID returns a 404 message
patch cost centre by id|allows admins to update a cost centre's details name, description, is_active
patch cost centre by id|rejects non-admin requests
create legal entity|allows admins to create a new LE
create legal entity|rejects non-admin requests
create legal entity|rejects requests to create a duplicate LE code
list legal entities|returns a list of all LEs
get legal entity|returns an LE for a specific code
get legal entity|returns 404 if an incorrect code is supplied
get legal entity|returns 422 if an no code is supplied
patch legal entity|allows admins to update an LE's name, country_code, and active status
patch legal entity|rejects non-admin requests
create allocation period|allows analysts and up to create an allocation
create allocation period|rejects non-analyst requests
get all periods|returns list of all allocation periods
get period by ID|returns a specific allocation period matching an ID
get period by ID|returns 404 for an invalid ID
get period by ID|returns 422 for a missing ID
patch period|allows analysts and up to update a period's name and month
patch period|rejects non-analyst requests
patch period|rejects requests if the period is locked.
patch period|returns 404 requests if the period ID is invalid
patch period|returns 422 if the period ID is missing
lock a period|allows admins to lock a period, returning that period
lock a period|rejects non-admin requests
lock a period|returns 404 for an invalid ID
lock a period|returns 422 for a missing ID
lock a period|returns 204 if the period is already locked
create expense|allows analysts and up to create a new expense on a period
create expense|rejects non-analyst requests
create expense|rejects requests if the period ID is invalid
create expense|rejects requests if the period ID is locked
get all expenses|returns list of all expenses for a period
get all expenses|rejects requests for an invalid period ID
get single expense|returns an expense matching an ID
get single expense|returns 404 for an invalid period ID
get single expense|returns 404 for an invalid expense ID
patch expense|rejects requests from non analyst+
patch expense|allows expenses to be updated
patch expense|returns 404 for an invalid period ID
patch expense|returns 404 for an invalid expense ID
delete expense|rejects requests from non analyst+
delete expense|allows analysts+ to delete an expense
delete expense|rejects requests to delete a closed period expense
delete expense|returns 404 for an invalid period ID
delete expense|returns 404 for an invalid expense ID
create an activity|allows analyst+ to create a new period
create an activity|rejects requests from non-analysts
create an activity|rejects requests for invalid period IDs
get all activities|returns a list of all activities for a period
get all activities|rejects requests with an invalid period ID
get a specific activity|returns a specific activity matching an activity ID
get a specific activity|rejects requests for an invalid activity ID
get a specific activity|rejects requests for an invalid period ID
patch an activity|allows analyst+ to update an activity's name and description in an open period
patch an activity|rejects requests from non-analyst+
patch an activity|rejects requests with an invalid period ID
patch an activity|rejects requests with an invalid activity ID
patch an activity|rejects requests to update an activity in a closed period
delete an activity|allows analyst+ to delete an activity in an open period
delete an activity|rejects requests from non-analyst+
delete an activity|rejects requests with an invalid period ID
delete an activity|rejects requests with an invalid activity ID
delete an activity|rejects requests to delete an activity in a closed period

## Gherkin syntax

Feature: Protected Endpoints
    Scenario: Unauthenticated user tries to access a protected endpoint
    Given: the user is not logged in
    When the user tries to access the endpoint
    Then the endpoint rejects the request

    Scenario: Authenticated user tries to access a protected endpoint
    Given: the user holds a valid token
    When the user tries to access the endpoint
    Then the endpoint validates the user
    And allows the request to be processed

Feature: login
    Scenario: Successful login with valid credentials
        Given a user exists
        When the user logs in with valid credentials
        Then they should receive an access token

    Scenario: Failed login with incorrect credentials
        When a user logs in with incorrect details
        Then the request is rejected

Feature: List users
    Scenario: Non-admin requests are rejected
        Given the user is logged in
        And the user does not have the "admin" role
        When the user requests a list of users
        Then the request is rejected with a 403 unprivileged status

    Scenario: Admin user gets a list of all users
        Given the user is logged in as an admin
        And there exists one or more users
        When the user requests a list of users
        Then the full list of users is returned

    Scenario: No sensitive data is returned
        Given the user is logged in as an admin
        And there exists one or more users
        When the user requests a list of users
        Then the list is returned without any sensitive information

Feature: Create user
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And the user's token is valid

    Scenario: Sign-ups missing details are rejected
        Given the user is logged in
        And the user has the "admin" role
        When the user makes a request missing one or more details
        Then the request is rejected
        Examples:
            |username|email|password|
            |user123||password|
            ||<user123@gmail.com>|password|
            |user123|<user123@gmail.com>||

    Scenario: Sign-ups with invalid emails are rejected
        Given the user is logged in
        And the user has the "admin" role
        When the user tries to register another user with a malformed email
        Then the request is rejected
        Examples:
            |username|email|password|
            |user123||password|
            |user123|bademail|password|
            |user123|email@example@com|password|
            |user123|email.example|password|

    Scenario: Non-admins cannot register a new user
        Given the user is logged in
        And the user does not have the "admin" role
        When the user tries to register a new user
        Then the request is rejected as unprivileged

    Scenario: Admin users can register another user
        Given the user is logged in
        And the user has the "admin" role
        When the user submits the correct details
        Then a new user is created
        And the new user details are returned
        And the database shows one more user

    Scenario: Two users of the same username cannot be registered
        Given the user is logged in
        And the user has the "admin" role
        And the database has a user called "user123"
        When the user submits a request to create a user with username "user123"
        Then the request is rejected
        And the originating user is informed of the conflict

    Scenario: Non-complex passwords are rejected
        Given the user is logged in
        And the user has the "admin" role
        When a request is made to register a new user
        And the password is not sufficiently complex
        Then the request is rejected
        Examples:
            |username|email|password|
            |user1|<user1@exmaple.com>|password|
            |user2|<user2@exmaple.com>|p|
            |user3|<user3@exmaple.com>|123|
            |user4|<user4@exmaple.com>|battery-123|
            |user5|<user5@exmaple.com>|horse£|
            |user5|<user5@exmaple.com>|s*@pl3|

Feature: get user details
    Scenario: returns the current user profile only

Feature: deactivate user
    Scenario: rejects non-admin requests
    Scenario: returns confirmation of a deactivated user
    Scenario: user can no longer login after deactivation

Feature: change password
    Scenario: user can change their own password if they supply the old one
    Scenario: old password can no longer be used

Feature: create new cost centre
    Scenario: rejects requests from non-admins
    Scenario: rejects requests for a duplicate code
    Scenario: returns a list of cost centres

Feature: get all cost centres
    Scenario: returns a list of all held cost centers

Feature: get cost centre by id
    Scenario: if a valid ID is supplied returns that cost center
    Scenario: if no valid ID returns a 404 message

Feature: patch cost centre by id
    Scenario: allows admins to update a cost centre's details name, description, is_active
    Scenario: rejects non-admin requests

Feature: create legal entity
    Scenario: allows admins to create a new LE
    Scenario: rejects non-admin requests
    Scenario: rejects requests to create a duplicate LE code

Feature: list legal entities
    Scenario: returns a list of all LEs

Feature: get legal entity
    Scenario: returns an LE for a specific code
    Scenario: returns 404 if an incorrect code is supplied
    Scenario: returns 422 if an no code is supplied

Feature: patch legal entity
    Scenario: allows admins to update an LE's name, country_code, and active status
    Scenario: rejects non-admin requests

Feature: create allocation period
    Scenario: allows analysts and up to create an allocation
    Scenario: rejects non-analyst requests

Feature: get all periods
    Scenario: returns list of all allocation periods

Feature: get period by ID
    Scenario: returns a specific allocation period matching an ID
    Scenario: returns 404 for an invalid ID
    Scenario: returns 422 for a missing ID

Feature: patch period
    Scenario: allows analysts and up to update a period's name and month
    Scenario: rejects non-analyst requests
    Scenario: rejects requests if the period is locked.
    Scenario: returns 404 requests if the period ID is invalid
    Scenario: returns 422 if the period ID is missing

Feature: lock a period
    Scenario: allows admins to lock a period, returning that period
    Scenario: rejects non-admin requests
    Scenario: returns 404 for an invalid ID
    Scenario: returns 422 for a missing ID
    Scenario: returns 204 if the period is already locked

Feature: create expense
    Scenario: allows analysts and up to create a new expense on a period
    Scenario: rejects non-analyst requests
    Scenario: rejects requests if the period ID is invalid
    Scenario: rejects requests if the period ID is locked

Feature: get all expenses
    Scenario: returns list of all expenses for a period
    Scenario: rejects requests for an invalid period ID

Feature: get single expense
    Scenario: returns an expense matching an ID
    Scenario: returns 404 for an invalid period ID
    Scenario: returns 404 for an invalid expense ID

Feature: patch expense
    Scenario: rejects requests from non analyst+
    Scenario: allows expenses to be updated
    Scenario: returns 404 for an invalid period ID
    Scenario: returns 404 for an invalid expense ID

Feature: delete expense
    Scenario: rejects requests from non analyst+
    Scenario: allows analysts+ to delete an expense
    Scenario: rejects requests to delete a closed period expense
    Scenario: returns 404 for an invalid period ID
    Scenario: returns 404 for an invalid expense ID

Feature: create an activity
    Scenario: allows analyst+ to create a new period
    Scenario: rejects requests from non-analysts
    Scenario: rejects requests for invalid period IDs

Feature: get all activities
    Scenario: returns a list of all activities for a period
    Scenario: rejects requests with an invalid period ID

Feature: get a specific activity
    Scenario: returns a specific activity matching an activity ID
    Scenario: rejects requests for an invalid activity ID
    Scenario: rejects requests for an invalid period ID

Feature: patch an activity
    Scenario: allows analyst+ to update an activity's name and description in an open period
    Scenario: rejects requests from non-analyst+
    Scenario: rejects requests with an invalid period ID
    Scenario: rejects requests with an invalid activity ID
    Scenario: rejects requests to update an activity in a closed period

Feature: delete an activity
    Scenario: allows analyst+ to delete an activity in an open period
    Scenario: rejects requests from non-analyst+
    Scenario: rejects requests with an invalid period ID
    Scenario: rejects requests with an invalid activity ID
    Scenario: rejects requests to delete an activity in a closed period

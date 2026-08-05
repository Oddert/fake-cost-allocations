# Test Cases

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
        And the user is not deactivated
        When the user logs in with valid credentials
        Then they should receive an access token

    Scenario: Failed login with incorrect credentials
        When a user logs in with incorrect details
        Then the request is rejected

Feature: List users
    Scenario: Non-admin requests are rejected
        Given the user is logged in
        And the user is not deactivated
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
        And the user is not deactivated
        And the requesting user is logged in as this user
        And the user's token is valid

    Scenario: Sign-ups missing details are rejected
        Given the user is logged in
        And the user has the "admin" role
        When the user makes a request missing one or more details
        Then the request is rejected
        Examples:
            |username|email|password|
            |user123| |password|
            | |<user123@gmail.com>|password|
            |user123|<user123@gmail.com>| |

    Scenario: Sign-ups with invalid emails are rejected
        Given the user is logged in
        And the user has the "admin" role
        When the user tries to register another user with a malformed email
        Then the request is rejected
        Examples:
            |username|email|password|
            |user123| |password|
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
    Scenario: A user requests their own profile details
        Given a user is logged in
        When the user requests the endpoint
        Then they get their full user profile

Feature: Deactivating a user
    Background:
        Given one admin user exists
        And the admin user is not deactivated
        And another user exists
        And the other user is not deactivated

    Scenario: rejects non-admin requests
        Given the user is logged in
        And the user does not have the "admin" role
        When the user attempts to deactivate another user
        Then the request is rejected

    Scenario: user cannot deactivate themselves
        Given the user is logged in
        And the user has the "admin" role
        When the user attempt to deactivate their own account
        Then the request is rejected

    Scenario: An admin deactivates a user
        Given the user is logged in
        And the user has the "admin" role
        When the user attempts to deactivate another user
        Then the user is deactivated
        And the details of the deactivated user are returned
        And the deactivated user details can no longer login

Feature: change password
    Background:
        Given a user exists in the database
        And the user is not deactivated
        And the current user is logged in

    Scenario: User successfully changes their password
        When the user submits their old and new password
        Then the password for that user is updated
        And the new password can be used to login
        And the old password can no longer be used to login

    Scenario: User unsuccessfully changes their password
        When the user submits their old and new password
        And the old password is not correct
        Then the request is rejected

Feature: Creating a new cost centre
    Background:
        Given a user exists in the database
        And the requesting user is logged in
        And at least one other cost centre exists in the database

    Scenario: Admin users can create a new cost center
        Given the current user has the "admin" role
        When the user submits new cost centre details
        Then the new cost centre is created
        And the details of the new cost centre are returned
        And the new cost centre appears in the full list of cost centres

    Scenario: Non-admins cannot create a cost centre
        Given the user does not hold the "admin" role
        When the user submits new cost centre details
        Then the request is rejected with an unprivileged message

    Scenario: Duplicate cost centre codes are rejected
        Given the current user has the "admin" role
        When the user submits new cost centre details with a code already belonging to an existing cost centre
        Then the request is rejected as a conflict

Feature: Get a list of all cost centres
    Scenario: returns a list of all held cost centres
        Given a user exists in the database
        And the requesting user is logged in as this user
        And the user holds the "admin" role
        And at least one other cost centre exists in the database
        When the user requests cost centres
        Then a list of all cost centres is returned

Feature: Get single cost centre by id
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one cost centre exists in the database

    Scenario: Get a cost centre by ID
        Given the user holds the "admin" role
        When the user requests a cost centre by ID
        Then the cost centre details are returned

    Scenario: Get a cost-centre by ID without a correct role
        Given the user does not hold the "admin" role
        When the user requests a cost-centre by ID
        Then the request is rejected as unprivileged

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

Feature: Update a cost centre
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least other cost centre exists in the database

    Scenario: An admin updates a cost centre's details
        Given the user holds the "admin" role
        When the user submits cost centre details
        Then the cost centre is updated
        And the updated cost centre is returned

    Scenario: An invalid ID is used in an update
        Given the user holds the "admin" role
        When the user submits cost centre details to an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: An unprivileged user updates a cost centre
        Given the user does not hold the "admin" role
        When the user submits cost centre details
        Then the request is rejected with an unprivileged error

Feature: Creating a new legal entity
    Background:
        Given a user exists in the database
        And the requesting user is logged in
        And at least one other legal entity exists in the database

    Scenario: Admin users can create a new cost center
        Given the current user has the "admin" role
        When the user submits new legal entity details
        Then the new legal entity is created
        And the details of the new legal entity are returned
        And the new legal entity appears in the full list of legal entities

    Scenario: Non-admins cannot create a legal entity
        Given the user does not hold the "admin" role
        When the user submits new legal entity details
        Then the request is rejected with an unprivileged message

    Scenario: Duplicate legal entity codes are rejected
        Given the current user has the "admin" role
        When the user submits new legal entity details with an LE code already belonging to an existing legal entity
        Then the request is rejected as a conflict

Feature: Get a list of all legal entities
    Scenario: returns a list of all held legal entities
        Given a user exists in the database
        And the requesting user is logged in as this user
        And the user holds the "admin" role
        And at least one other cost centre exists in the database
        When the user requests legal entities
        Then a list of all legal entities is returned

Feature: Get single legal entity by id
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And the user holds the "admin" role
        And at least one legal entity exists in the database

    Scenario: Get a legal entity by ID
        When the user requests a legal entity by ID
        Then the legal entity details are returned

    Scenario: Get a legal entity with an invalid ID
        When the user requests a legal entity with an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Update a legal entity
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one other legal entity exists in the database

    Scenario: An admin updates a legal entity's details
        Given the user holds the "admin" role
        When the user submits legal entity details
        Then the legal entity is updated
        And the updated legal entity is returned

    Scenario: rejects invalid IDs
        Given the user holds the "admin" role
        When the user submits legal entity details to an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Creating a new allocation period
    Background:
        Given a user exists in the database
        And the requesting user is logged in
        And at least one other allocation period exists in the database

    Scenario: Admin users can create a new cost center
        Given the current user has the "admin" role
        Or the current user has the "analyst" role
        When the user submits new allocation period details
        Then the new allocation period is created
        And the details of the new allocation period are returned
        And the new allocation period appears in the full list of allocation periods

    Scenario: Non-admins cannot create a allocation period
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits new allocation period details
        Then the request is rejected with an unprivileged message

    Scenario: Duplicate allocation period codes are rejected
        Given the current user has the "admin" role
        Or the current user has the "analyst" role
        When the user submits new allocation period details with a code already belonging to an existing allocation period
        Then the request is rejected as a conflict

Feature: Get a list of all allocation periods
    Scenario: returns a list of all held allocation periods
        Given a user exists in the database
        And the requesting user is logged in as this user
        And the user holds the "admin" role
        Or the current user has the "analyst" role
        And at least one other allocation period exists in the database
        When the user requests allocation periods
        Then a list of all allocation periods is returned

Feature: Get single allocation period by id
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: Get a allocation period by ID
        Given the user holds the "admin" role
        Or the current user has the "analyst" role
        When the user requests a allocation period by ID
        Then the allocation period details are returned

    Scenario: Get a allocation period by ID without a correct role
        Given the user does not hold the "admin" role
        And the current user does not hold the "analyst" role
        When the user requests a allocation period by ID
        Then the request is rejected as unprivileged

    Scenario: Get a allocation period with an invalid ID
        When the user requests a allocation period with an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Update a cost centre
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one other cost centre exists in the database

    Scenario: An admin updates a allocation period's details
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits allocation period details
        Then the allocation period is updated
        And the updated allocation period is returned

    Scenario: An invalid ID is used in an update
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits allocation period details to an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: An unprivileged user updates a period
        Given the user does not hold the "admin" role
        Or the user holds the "analyst" role
        When the user submits allocation period details
        Then the request is rejected with an unprivileged error

    Scenario: Request to update a locked period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits allocation period details for the locked period
        Then the request is rejected

Feature: lock a period
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user

    Scenario: A privileged user an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to an allocation period ID
        Then the allocation period is locked
        And the allocation period can no longer have costs added to it
        And the updated allocation period is returned

    Scenario: An unprivileged user locks an allocation period
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to an allocation period ID
        Then the request is rejected as unprivileged

    Scenario: An invalid ID is used to lock a period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request using an invalid allocation period ID
        Then the request is rejected as unprivileged
        Examples: 
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: An unprivileged user locks an allocation period which is already locked
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        And an unlocked allocation period exists in the database
        And that allocation period is locked
        When the user submits a request to an allocation period ID
        Then allocation period is returned
        And the user is notified that no action was taken

Feature: Create an expense
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: A privileged user creates an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to create an expense on an allocation period
        Then the expense is created
        And the expense is returned
        And the expense shows in the list of all expenses

    Scenario: An unprivileged user creates an expense
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits a request to create an expense
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to create an expense on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits a request to create an expense on the locked period
        Then the request is rejected
        And an explanation is given

Feature: get all expenses
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one expense exists assigned to an allocation period

    Scenario: Get a list of expenses by allocation period ID
        When the user sends a valid allocation period ID
        Then a list of all expenses assigned to that period are returned

    Scenario: Get a list of expenses with an invalid allocation period ID
        When the user sends an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: get single expense
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one expense exists assigned to an allocation period

    Scenario: Get an expense by ID
        When the user requests an expense by ID
        Then the matching expense details are returned

    Scenario: Get an expense with an invalid expense ID
        When the user requests an expense using an invalid expense ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: Get an expense with an invalid period ID
        When the user requests an expense using an invalid period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Update an expense
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one expense exists assigned to an allocation period

    Scenario: A privileged user updates an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to update an expense on an allocation period
        Then the expense is updated
        And the expense is returned

    Scenario: An unprivileged user updates an expense
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits a request to update an expense
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an expense on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid allocation expense ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an expense on an invalid allocation expense ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits a request to create an expense on the locked period
        Then the request is rejected
        And an explanation is given

Feature: Delete an expense
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one expense exists assigned to an allocation period

    Scenario: A privileged user deletes an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to update an expense on an allocation period
        Then the expense is deleted
        And the expense is returned
        And the expense does not appear in the full list of expenses

    Scenario: An unprivileged user deletes an expense
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits a request to update an expense
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an expense on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid allocation expense ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an expense on an invalid allocation expense ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits a request to create an expense on the locked period
        Then the request is rejected
        And an explanation is given

Feature: Create an activity
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: A privileged user creates an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to create an activity on an allocation period
        Then the activity is created
        And the activity is returned
        And the activity shows in the list of all activities

    Scenario: An unprivileged user creates an activity
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits a request to create an activity
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to create an activity on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits a request to create an activity on the locked period
        Then the request is rejected
        And an explanation is given

Feature: Get all activities
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one expense exists assigned to an allocation period

    Scenario: Get a list of activities by allocation period ID
        When the user sends a valid allocation period ID
        Then a list of all activities assigned to that period are returned

    Scenario: Get a list of activities with an invalid allocation period ID
        When the user sends an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Get a single activity by ID
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one activity exists assigned to an allocation period

    Scenario: Get an activity by ID
        When the user requests an activity by ID
        Then the matching activity details are returned

    Scenario: Get an activity with an invalid activity ID
        When the user requests an activity using an invalid activity ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: Get an activity with an invalid period ID
        When the user requests an activity using an invalid period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Update an activity
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one activity exists assigned to an allocation period

    Scenario: A privileged user updates an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to update an activity on an allocation period
        Then the activity is updated
        And the activity is returned

    Scenario: An unprivileged user updates an activity
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits a request to update an activity
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an activity on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid allocation activity ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an activity on an invalid allocation activity ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits a request to create an activity on the locked period
        Then the request is rejected
        And an explanation is given

Feature: Delete an activity
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one activity exists assigned to an allocation period

    Scenario: A privileged user deletes an allocation period
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And an unlocked allocation period exists in the database
        When the user submits a request to update an activity on an allocation period
        Then the activity is deleted
        And the activity is returned
        And the activity does not appear in the full list of activities

    Scenario: An unprivileged user deletes an activity
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits a request to update an activity
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an activity on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid allocation activity ID is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        When the user submits a request to update an activity on an invalid allocation activity ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds the "admin" role
        Or the user holds the "analyst" role
        And a locked allocation period exists in the database
        When the user submits a request to create an activity on the locked period
        Then the request is rejected
        And an explanation is given

# Test Cases

## Non-Functional Requirements

Feature: Code quality and conformity
    Scenario: No linter violations are present
        Given the Ruff linting configuration supplied
        And the linting configuration matches the team's standard
        When the linter is run in 'check' mode
        Then no errors are returned

    Scenario: Code conforms to linting style formatters
        Given the Ruff linting configuration supplied
        And the linting configuration matches the team's standard
        When the linter is run in 'format' mode
        Then the code will be auto-fixed
        And no additional formatting issues will be reported which must be manually addressed

    Scenario: Type hints are used
        When the code is manually reviewed
        Then the all variables without an implicit type have a type annotation
        And all function arguments have a type annotation
        And type chains are not interrupted
        And the annotations are correct against the expected functionality

    Scenario: Type security is robust
        Given the code is viewed in an IDE with a Pylance plugin
        And the Pylance type settings are on
        When the code is viewed
        Then no type violations are reported

    Scenario: No commented (out) code is present
        When the code is manually reviewed
        Then no commented blocks of code are present

    Scenario: Variable names are clear
        When the code is manually reviewed
        Then variable names are found to be consistent, readable, and semantic

    Scenario: Static code quality scans yield no unjustified violations
        Given a static code-quality scanning tool
        When the scan is run against the codebase
        Then no errors are reported

    Scenario: Folder structure and code splitting aligns with the team's standard
        Given the team has a standard method of structuring an API codebase
        And the team has typical naming conventions for files contained
        And the team has defined rules about where to place aspects of functionality
        When the code structure is manually reviewed
        Then the structure is found to conform

    Scenario: Code complexity is kept as low as possible
        When the application logic is manually reviewed
        Then the code is found to perform well against Big O principles
        And no excessive branching is used
        And no recursive logic is present

    Scenario: Application memory performance is efficient
        Given the application is run in an IDE
        When the statistics on memory are viewed
        Then no memory leaks are found

    Scenario: Large lists of data are paginated
        When endpoints providing lists of entities are queried
        Then the lists are paginated by default

Feature: Inline documentation
    Scenario: Logic is robustly documented with inline comments
        When the files are manually reviewed
        Then any sufficiently complex logic is accompanied with explanatory docstrings
        And the language used is comprehensive but accessible
        And the comments are found to adequately explain the behaviour of the code

    Scenario: API endpoints are well documented
        When the API documentation is viewed
        Then all endpoints have explanatory docstrings
        And the docstrings explain the function of the endpoint in accessible but robust language
        And the usage schema's explain the expected request-response formats
        And the exception conditions are explained

    Scenario: All functions include docstrings
        When the codebase is manually reviewed
        Then all functions are found to have a docstring
        And the docstring provides a comprehensive description of what the function does
        And the function arguments are described with their expected types
        And the return value(s) are described
        And the possible exceptions are listed

    Scenario: Variable names are high quality
        When the codebase is manually reviewed
        Then all variable names are found to be consistent, readable, and semantic
        And no variables are shorter than three characters unless their purpose is immediately apparent
        And names are relevant to their usage and context

Feature: Static security
    Scenario: static SAST scans result in no errors
        Given a static security scanning tool
        When the scan is run against the codebase
        Then no errors are reported

    Scenario: Dependency scans result in no issues
        Given a static dependency scanning tool
        When the scan is run against the codebase
        Then no package vulnerabilities are reported
        And package versions are tightly defined
        And packages are all recent versions

Feature: OpenAPI linting conformity
    Scenario: Static linting against OpenAPI standards yields no errors
        Given a static linting configuration using Spectral is defined
        And the rulesets are aligned with the team's standards
        When the scan is run
        Then no errors are reported
        And no style violations are reported

Feature: FCA & SOX compliance
    Scenario: Data held is non proprietary and can be exported to other systems
        When the data tables are manually reviewed
        Then the data is found to be of high quality
        And the table names and column names are clear
        And anything unclear is explained using comments or another form of documentation
        And no application-specific data is mixed with financial data

    Scenario: An audit trail allows clear transaction history to be viewed for at least 7 years
        Given some data exists in the database
        When the data tables are manually reviewed
        Then data for the past seven years is visible
        And there are no gaps in the audit trail
        And all changes made are recorded and viewable
        And change history can be 'replayed' by examination of the transaction history

    Scenario: Transaction events are logged and searchable
        Given some data exists in the database
        When the transaction history is manually reviewed
        Then all changes made to the main data tables are recorded and viewable
        And there are no gaps in the audit trail
        And change history can be 'replayed' by examination of the transaction history

    Scenario: Data is backed up and secure from tampering and loss
        When the database is examined
        Then a backup process is found
        And the backup is deemed secure

    Scenario: Data is stored on sovereign territories within the same regulatory environment as the bank
        When the database is examined
        Then it is found to reside physically and under the jurisdiction of the UK

    Scenario: Security breach events are recorded and reported to SOX auditors
        When the security logs are viewed
        Then all breaches are clearly logged and documented

    Scenario: Controls are in place to restrict addition of new users
        When new users are added to the system
        Then a clear audit trail, approval and justification is recorded

Feature: ISO/IEC27001 Compliance
    Scenario: The application passes an audit by a dedicated audit team
        Given an internal SOX audit team is available
        When and audit is conducted
        Then the team reports no failings

    Scenario: The responsibilities and ownership of the system are documented and understood
        Given roles and responsibilities for positions such as ownership, delivery, retesting, maintenance, and stakeholder management are defined
        When documentation for the project is read
        The roles and responsibilities are recorded

    Scenario: All system and data locations are documented
        When the application stores or accesses data of any kind
        Then the data sources are accounted for in application documentation

    Scenario: Data access is controlled with RBAC on the principle of least privilege
        When data is accessed
        Then access is controlled by specific roles

    Scenario: Data at-rest is encrypted
        When data is stored
        Then the data is encrypted securely

    Scenario: All API requests are logged
        When an API call is made to any endpoint
        Then the request is logged via an external service
        And sufficient detail on the nature of the request is retained

    Scenario: No extraneous information is exposed
        When the endpoints are manually reviewed
        Then no instances of extraneous information exposure is found

Feature: GDPR Compliance
    Scenario: No personally identifiable information is stored unless absolutely necessary
        When the data is manually inspected
        Then the data is not found to hold any personal identifiable information (PII)

Feature: Database schema compatibility
    Scenario: Primary key columns are complex and unique strings (UUID)
        When records are stored in the database
        Then the primary key column is a unique string in UUID format

    Scenario: Column types are compatible with Oracle data types
        When the codebase is manually reviewed
        And its column data types are compared to Oracle database data types
        Then no incompatibilities are found.

    Scenario: Database actions like transactions are compatible with Oracle
        When the codebase is manually inspected
        Then the transaction logic is found to be compatible with Oracle
        And the method of interacting with the database is found to be efficient

## Functional Requirements

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

    Scenario: Successful login as an existing user — deactivation blocks login
        Given a user is deactivated
        When the user tries to log in
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

Feature: Create new user
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
            |username|email|password|role|
            |user123| |password|viewer|
            | |<user123@gmail.com>|password|viewer|
            |user123|<user123@gmail.com>| |viewer|
            |user123|<user123@gmail.com>|password||

    Scenario: Sign-ups with invalid emails are rejected
        Given the user is logged in
        And the user has the "admin" role
        When the user tries to register another user with a malformed email
        Then the request is rejected
        Examples:
            |username|email|password|role|
            |user123| |password|viewer|
            |user123|bademail|password|viewer|
            |user123|email@example@com|password|viewer|
            |user123|email.example|password|viewer|

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
            |username|email|password|role|
            |user1|<user1@exmaple.com>|password|viewer|
            |user2|<user2@exmaple.com>|p|viewer|
            |user3|<user3@exmaple.com>|123|viewer|
            |user4|<user4@exmaple.com>|battery-123|viewer|
            |user5|<user5@exmaple.com>|horse£|viewer|
            |user5|<user5@exmaple.com>|s*@pl3|viewer|

Feature: get user details
    Scenario: A user requests their own profile details
        Given a user is logged in
        When the user requests the endpoint
        Then they get their full user profile

    Scenario: No sensitive details are returned
        Given a user is logged in
        When the user requests the endpoint
        Then they do not receive any private data (e.g. password)

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

    Scenario: Admin users can create a new cost centre
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

    Scenario: Long Cost Centre codes are not allowed
        Given the current user has the "admin" role
        When the user submits new cost centre details with a code longer than 20 characters
        Then the request is rejected as a unprocessable

Feature: Get a list of all cost centres
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one other cost centre exists in the database

    Scenario: returns a list of all held cost centres
        When the user requests cost centres
        Then a list of all cost centres is returned

    Scenario: Returns only active cost centres with the flag set
        Given a mixture of 'active' and 'inactive' cost centres exist in the database
        When the user requests cost centres with the 'active' flag set
        Then a list of cost centres is returned
        And they are all active

Feature: Get single cost centre by id
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one cost centre exists in the database

    Scenario: Get a cost centre by ID
        Given the user holds the "admin" role
        When the user requests a cost centre by ID
        Then the cost centre details are returned

    Scenario: Query a missing cost centre
        Given the user holds the "admin" role
        When the user requests a cost-centre by an ID which does not exist
        Then the request is rejected with a 'not found' response.

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
        And at least one other cost centre exists in the database

    Scenario: An admin updates a cost centre's details
        Given the user holds the "admin" role
        When the user submits cost centre details
        Then the cost centre is updated
        And the updated cost centre is returned

    Scenario: A request for a missing cost centre is rejected
        Given the user holds the "admin" role
        When the user submits cost centre details to cost centre which does not exist
        Then the request is rejected with 'not found'

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

    Scenario: An unprivileged user updates a cost centre
        Given the user does not hold the "admin" role
        When the user submits cost centre details
        Then the request is rejected with an unprivileged error

    Scenario: A cost centre code cannot be changed
        Given the user does not hold the "admin" role
        When the user submits cost centre details including a code
        Then the request is rejected as unprocessable

Feature: Creating a new legal entity
    Background:
        Given a user exists in the database
        And the requesting user is logged in
        And at least one other legal entity exists in the database

    Scenario: Admin users can create a new legal entity
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
        And at least one legal entity exists in the database
        When the user requests legal entities
        Then a list of all legal entities is returned

Feature: Get single legal entity by ID
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

    Scenario: An invalid ID is used in an update
        Given the user holds the "admin" role
        When the user submits legal entity details to an invalid legal entity ID
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

    Scenario: Privileged users can create a new allocation period
        Given the user holds a valid role "<role>"
        When the user submits new allocation period details
        Then the new allocation period is created
        And the details of the new allocation period are returned
        And the new allocation period appears in the full list of allocation periods
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: Non-analysts cannot create an allocation period
        Given the user does not hold the "admin" role
        And the user does not hold the "analyst" role
        When the user submits new allocation period details
        Then the request is rejected with an unprivileged message

    Scenario: Duplicate allocation period names are rejected
        Given the user holds a valid role "<role>"
        When the user submits new allocation period details with a name already belonging to an existing allocation period in the same fiscal year
        Then the request is rejected as a conflict
        Examples:
            |role|
            |admin|
            |analyst|

Feature: Get a list of all allocation periods
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: Get a list of all held allocation periods
        When the user requests allocation periods
        Then a list of all allocation periods is returned

    Scenario: Get a list of only specific modes
        Given at least one allocation in the database as the requested mode
        And at least one allocation in the database as a different mode
        When the user requests allocation periods with a specific mode
        Then a list of all allocation periods is returned
        And all the allocations have the same mode value

    Scenario: Get a list of only specific status
        Given at least one allocation in the database as the requested status
        And at least one allocation in the database as a different status
        When the user requests allocation periods with a specific status
        Then a list of all allocation periods is returned
        And all the allocations have the same status value

    Scenario: Get a list of only specific fiscal year
        Given at least one allocation in the database as the requested fiscal year
        And at least one allocation in the database as a different fiscal year
        When the user requests allocation periods with a specific fiscal year
        Then a list of all allocation periods is returned
        And all the allocations have the same fiscal year value

    Scenario: Get a list of periods with multiple filters
        Given a mixture of allocations exist in the database with varying mode, status, and fiscal year values
        When the user requests allocation periods with a specific fiscal year, mode and status
        Then a list of all allocation periods is returned
        And all the allocations have the same fiscal year, mode and status values

Feature: Get single allocation period by ID
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: Get an allocation period by ID
        When the user requests an allocation period by ID
        Then the allocation period details are returned

    Scenario: Get an allocation period with an invalid ID
        When the user requests an allocation period with an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

Feature: Update an allocation period
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one other allocation period exists in the database

    Scenario: A privileged user updates an allocation period's details
        Given the user holds a valid role "<role>"
        When the user submits allocation period details
        Then the allocation period is updated
        And the updated allocation period is returned
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An invalid ID is used in an update
        Given the user holds the "admin" role
        When the user submits allocation period details to an invalid ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: An unprivileged user updates a period
        Given the user holds the "viewer" role
        When the user submits allocation period details
        Then the request is rejected with an unprivileged error

    Scenario: Request to update a locked period
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits allocation period details for the locked period
        Then the request is rejected
        Examples:
            |role|
            |admin|
            |analyst|

Feature: lock a period
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user

    Scenario: An admin locks an allocation period
        Given the user holds the "admin" role
        And an unlocked allocation period exists in the database
        When the user submits a request to an allocation period ID
        Then the allocation period is locked
        And the allocation period can no longer have costs added to it
        And the updated allocation period is returned

    Scenario: An unprivileged user locks an allocation period
        Given the user does not hold the "admin" role
        And an unlocked allocation period exists in the database
        When the user submits a request to an allocation period ID
        Then the request is rejected as unprivileged

    Scenario: An invalid ID is used to lock a period
        Given the user holds the "admin" role
        And an unlocked allocation period exists in the database
        When the user submits a request using an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: An admin locks an allocation period which is already locked
        Given the user holds the "admin" role
        And an allocation period exists in the database
        And that allocation period is already locked
        When the user submits a request to that allocation period ID
        Then the allocation period is returned
        And the user is notified that no action was taken

Feature: Create an expense
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: A privileged user creates an expense
        Given the user holds a valid role "<role>"
        And an unlocked allocation period exists in the database
        When the user submits a request to create an expense on an allocation period
        Then the expense is created
        And the expense is returned
        And the expense shows in the list of all expenses
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An unprivileged user creates an expense
        Given the user holds the "viewer" role
        When the user submits a request to create an expense
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        When the user submits a request to create an expense on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits a request to create an expense on the locked period
        Then the request is rejected
        And an explanation is given
        Examples:
            |role|
            |admin|
            |analyst|

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

    Scenario: A privileged user updates an expense
        Given the user holds a valid role "<role>"
        And an unlocked allocation period exists in the database
        When the user submits a request to update an expense on an allocation period
        Then the expense is updated
        And the expense is returned
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An unprivileged user updates an expense
        Given the user holds the "viewer" role
        When the user submits a request to update an expense
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        When the user submits a request to update an expense on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid expense ID is made
        Given the user holds the "admin" role
        When the user submits a request to update an expense on an invalid expense ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits a request to update an expense on the locked period
        Then the request is rejected
        And an explanation is given
        Examples:
            |role|
            |admin|
            |analyst|

Feature: Delete an expense
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one expense exists assigned to an allocation period

    Scenario: A privileged user deletes an expense
        Given the user holds a valid role "<role>"
        And an unlocked allocation period exists in the database
        When the user submits a request to delete an expense on an allocation period
        Then the expense is deleted
        And the expense does not appear in the full list of expenses
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An unprivileged user deletes an expense
        Given the user holds the "viewer" role
        When the user submits a request to delete an expense
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        When the user submits a request to delete an expense on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid expense ID is made
        Given the user holds the "admin" role
        When the user submits a request to delete an expense on an invalid expense ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits a request to delete an expense on the locked period
        Then the request is rejected
        And an explanation is given
        Examples:
            |role|
            |admin|
            |analyst|

Feature: Create an activity
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database

    Scenario: A privileged user creates an activity
        Given the user holds a valid role "<role>"
        And an unlocked allocation period exists in the database
        When the user submits a request to create an activity on an allocation period
        Then the activity is created
        And the activity is returned
        And the activity shows in the list of all activities
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An unprivileged user creates an activity
        Given the user holds the "viewer" role
        When the user submits a request to create an activity
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        When the user submits a request to create an activity on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits a request to create an activity on the locked period
        Then the request is rejected
        And an explanation is given
        Examples:
            |role|
            |admin|
            |analyst|

Feature: Get all activities
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one activity exists assigned to an allocation period

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

    Scenario: A privileged user updates an activity
        Given the user holds a valid role "<role>"
        And an unlocked allocation period exists in the database
        When the user submits a request to update an activity on an allocation period
        Then the activity is updated
        And the activity is returned
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An unprivileged user updates an activity
        Given the user holds the "viewer" role
        When the user submits a request to update an activity
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        When the user submits a request to update an activity on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid activity ID is made
        Given the user holds the "admin" role
        When the user submits a request to update an activity on an invalid activity ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits a request to update an activity on the locked period
        Then the request is rejected
        And an explanation is given
        Examples:
            |role|
            |admin|
            |analyst|

Feature: Delete an activity
    Background:
        Given a user exists in the database
        And the requesting user is logged in as this user
        And at least one allocation period exists in the database
        And at least one activity exists assigned to an allocation period

    Scenario: A privileged user deletes an activity
        Given the user holds a valid role "<role>"
        And an unlocked allocation period exists in the database
        When the user submits a request to delete an activity on an allocation period
        Then the activity is deleted
        And the activity does not appear in the full list of activities
        Examples:
            |role|
            |admin|
            |analyst|

    Scenario: An unprivileged user deletes an activity
        Given the user holds the "viewer" role
        When the user submits a request to delete an activity
        Then the request is rejected as unprivileged

    Scenario: A request to an invalid allocation period ID is made
        Given the user holds the "admin" role
        When the user submits a request to delete an activity on an invalid allocation period ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to an invalid activity ID is made
        Given the user holds the "admin" role
        When the user submits a request to delete an activity on an invalid activity ID
        Then the request is rejected
        Examples:
            |ID|
            | |
            |null|
            |'hello'|
            |'{}'|

    Scenario: A request to a locked allocation period is made
        Given the user holds a valid role "<role>"
        And a locked allocation period exists in the database
        When the user submits a request to delete an activity on the locked period
        Then the request is rejected
        And an explanation is given
        Examples:
            |role|
            |admin|
            |analyst|

Feature: General Security
    Scenario: Strong header settings are used
        When an API request is made
        No architecture information is revealed in the headers

    Scenario: Strong CORs controls are in place
        When an API request is made
        CORs headers are sent defining valid sources
        And the settings on the CORs headers are restrictive

    Scenario: Environment variables and configs are securely read in from hosting services when hosted
        Given the application is running in a hosted (cloud) environment
        When the application references any sensitive variables
        Then the application reads these from a secure credentials store

    Scenario: Environment variables and configs are securely read in from env files when running in localhost
        Given the application is running on localhost
        When the application references any sensitive variables
        Then the application reads these safely from a credentials file excluded from version control

    Scenario: All database logic is wrapped in at least one exception catch
        When any call to an external service is made
        And an unexpected exception occurs
        Then an exception handler allows the application to gracefully fail

    Scenario: Exceptions exposed are safe
        When any exception is caught
        And an error is propagated back to the endpoint
        Then clear explanatory errors are provided
        And no sensitive information is exposed

    Scenario: Database transactions are abstracted via use of an ORM
        When any interaction with the database takes place
        Then the transaction is abstracted by using an ORM

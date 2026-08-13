# Test Cases

## Non-Functional Requirements

Feature: Code quality and conformity
    Scenario: No linter violations are present
    Scenario: Code conforms to linting style formatters
    Scenario: Type hints are used
    Scenario: Type security is robust
    Scenario: No commented (out) code is present
    Scenario: Variable names are clear
    Scenario: Static code quality scans yield no unjustified violations
    Scenario: Folder structure and code splitting aligns with the team's standard
    Scenario: Code complexity is kept as low as possible
    Scenario: Application memory performance is efficient
    Scenario: Large lists of data are paginated
Feature: Inline documentation
    Scenario: Logic is robustly documented with inline comments
    Scenario: API endpoints are well documented
    Scenario: All functions include docstrings
    Scenario: Variable names are high quality
Feature: Static security
    Scenario: static SAST scans result in no errors
    Scenario: Dependency scans result in no issues
Feature: OpenAPI linting conformity
    Scenario: Static linting against OpenAPI standards yields no errors
Feature: FCA & SOX compliance
    Scenario: Data held is non proprietary and can be exported to other systems
    Scenario: An audit trail allows clear transaction history to be viewed for at least 7 years
    Scenario: Transaction events are logged and searchable
    Scenario: Data is backed up and secure from tampering and loss
    Scenario: Data is stored on sovereign territories within the same regulatory environment as the bank
    Scenario: Security breach events are recorded and reported to SOX auditors
    Scenario: Controls are in place to restrict addition of new users
Feature: ISO/IEC27001 Compliance
    Scenario: The application passes an audit by a dedicated audit team
    Scenario: The responsibilities and ownership of the system are documented and understood
    Scenario: All system and data locations are documented
    Scenario: Data access is controlled with RBAC on the principle of least privilege
    Scenario: Data at-rest is encrypted
    Scenario: All API requests are logged
    Scenario: No extraneous information is exposed
Feature: GDPR Compliance
    Scenario: No personally identifiable information is stored unless absolutely necessary
Feature: Database schema compatibility
    Scenario: Primary key columns are complex and unique strings (UUID)
    Scenario: Column types are compatible with Oracle data types
    Scenario: Database actions like transactions are compatible with Oracle

## Functional Requirements

Feature: Protected Endpoints
    Scenario: Unauthenticated user tries to access a protected endpoint
    Scenario: Authenticated user tries to access a protected endpoint
Feature: login
    Scenario: Successful login with valid credentials
    Scenario: Failed login with incorrect credentials
    Scenario: Successful login as an existing user — deactivation blocks login
Feature: List users
    Scenario: Non-admin requests are rejected
    Scenario: Admin user gets a list of all users
    Scenario: No sensitive data is returned
Feature: Create new user
    Scenario: Sign-ups missing details are rejected
    Scenario: Sign-ups with invalid emails are rejected
    Scenario: Non-admins cannot register a new user
    Scenario: Admin users can register another user
    Scenario: Two users of the same username cannot be registered
    Scenario: Non-complex passwords are rejected
Feature: get user details
    Scenario: A user requests their own profile details
    Scenario: No sensitive details are returned
Feature: Deactivating a user
    Scenario: rejects non-admin requests
    Scenario: user cannot deactivate themselves
    Scenario: An admin deactivates a user
Feature: change password
    Scenario: User successfully changes their password
    Scenario: User unsuccessfully changes their password
Feature: Creating a new cost centre
    Scenario: Admin users can create a new cost centre
    Scenario: Non-admins cannot create a cost centre
    Scenario: Duplicate cost centre codes are rejected
    Scenario: Long Cost Centre codes are not allowed
Feature: Get a list of all cost centres
    Scenario: returns a list of all held cost centres
    Scenario: Returns only active cost centres with the flag set
Feature: Get single cost centre by id
    Scenario: Get a cost centre by ID
    Scenario: Query a missing cost centre
    Scenario: Get a cost centre with an invalid ID
Feature: Update a cost centre
    Scenario: An admin updates a cost centre's details
    Scenario: A request for a missing cost centre is rejected
    Scenario: An invalid ID is used in an update
    Scenario: An unprivileged user updates a cost centre
    Scenario: A cost centre code cannot be changed
Feature: Creating a new legal entity
    Scenario: Admin users can create a new legal entity
    Scenario: Non-admins cannot create a legal entity
    Scenario: Duplicate legal entity codes are rejected
Feature: Get a list of all legal entities
    Scenario: returns a list of all held legal entities
Feature: Get single legal entity by ID
    Scenario: Get a legal entity by ID
    Scenario: Get a legal entity with an invalid ID
Feature: Update a legal entity
    Scenario: An admin updates a legal entity's details
    Scenario: An invalid ID is used in an update
Feature: Creating a new allocation period
    Scenario: Privileged users can create a new allocation period
    Scenario: Non-analysts cannot create an allocation period
    Scenario: Duplicate allocation period names are rejected
Feature: Get a list of all allocation periods
    Scenario: Get a list of all held allocation periods
    Scenario: Get a list of only specific modes
    Scenario: Get a list of only specific status
    Scenario: Get a list of only specific fiscal year
    Scenario: Get a list of periods with multiple filters
Feature: Get single allocation period by ID
    Scenario: Get an allocation period by ID
    Scenario: Get an allocation period with an invalid ID
Feature: Update an allocation period
    Scenario: A privileged user updates an allocation period's details
    Scenario: An invalid ID is used in an update
    Scenario: An unprivileged user updates a period
    Scenario: Request to update a locked period
Feature: lock a period
    Scenario: An admin locks an allocation period
    Scenario: An unprivileged user locks an allocation period
    Scenario: An invalid ID is used to lock a period
    Scenario: An admin locks an allocation period which is already locked
Feature: Create an expense
    Scenario: A privileged user creates an expense
    Scenario: An unprivileged user creates an expense
    Scenario: A request to an invalid allocation period ID is made
    Scenario: A request to a locked allocation period is made
Feature: get all expenses
    Scenario: Get a list of expenses by allocation period ID
    Scenario: Get a list of expenses with an invalid allocation period ID
Feature: get single expense
    Scenario: Get an expense by ID
    Scenario: Get an expense with an invalid expense ID
    Scenario: Get an expense with an invalid period ID
Feature: Update an expense
    Scenario: A privileged user updates an expense
    Scenario: An unprivileged user updates an expense
    Scenario: A request to an invalid allocation period ID is made
    Scenario: A request to an invalid expense ID is made
    Scenario: A request to a locked allocation period is made
Feature: Delete an expense
    Scenario: A privileged user deletes an expense
    Scenario: An unprivileged user deletes an expense
    Scenario: A request to an invalid allocation period ID is made
    Scenario: A request to an invalid expense ID is made
    Scenario: A request to a locked allocation period is made
Feature: Create an activity
    Scenario: A privileged user creates an activity
    Scenario: An unprivileged user creates an activity
    Scenario: A request to an invalid allocation period ID is made
    Scenario: A request to a locked allocation period is made
Feature: Get all activities
    Scenario: Get a list of activities by allocation period ID
    Scenario: Get a list of activities with an invalid allocation period ID
Feature: Get a single activity by ID
    Scenario: Get an activity by ID
    Scenario: Get an activity with an invalid activity ID
    Scenario: Get an activity with an invalid period ID
Feature: Update an activity
    Scenario: A privileged user updates an activity
    Scenario: An unprivileged user updates an activity
    Scenario: A request to an invalid allocation period ID is made
    Scenario: A request to an invalid activity ID is made
    Scenario: A request to a locked allocation period is made
Feature: Delete an activity
    Scenario: A privileged user deletes an activity
    Scenario: An unprivileged user deletes an activity
    Scenario: A request to an invalid allocation period ID is made
    Scenario: A request to an invalid activity ID is made
    Scenario: A request to a locked allocation period is made
Feature: General Security
    Scenario: Strong header settings are used
    Scenario: Strong CORs controls are in place
    Scenario: Environment variables and configs are securely read in from hosting services when hosted
    Scenario: Environment variables and configs are securely read in from env files when running in localhost
    Scenario: All database logic is wrapped in at least one exception catch
    Scenario: Exceptions exposed are safe
    Scenario: Database transactions are abstracted via use of an ORM
    Scenario: Safe financial data handling
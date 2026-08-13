# Defect findings

Requirement|Scenario|Defect|Notes
---|---|---
CA-REQ-001|No linter violations are present|9 Violations found, 7 fixable with auto-fix|Overlap with other requirements such as ambiguous variable names
CA-REQ-002|Code conforms to standard style guides|16 files found with style violations, fixable with ruff format
CA-REQ-002|Code conforms to standard style guides|Various instances of scoped imports / imports not at top of file
CA-REQ-002|Code conforms to standard style guides|Various instances of unused imports
CA-REQ-002|Code conforms to standard style guides|API flow logic and data processing logic is combined. The data logic must be abstracted to a service to support clean code, test mocking via dependency injection, unit testing of data concerns vs API flow
CA-REQ-002|Code conforms to standard style guides|API endpoints provide data without any metadata. Standards would require the use of standard response formatters.
CA-REQ-003|Code uses strong typing|Endpoints in `reference.py` set the user object to None despite type requiring the variable be defined
CA-REQ-003|Code uses strong typing|All DB interactions type their return format as a generic `dict`.
CA-REQ-003|Code uses strong typing|Multiple instances of API request body's being spread into a dict for database injection, potential injection attack vector
CA-REQ-003|Code uses strong typing|Allocation periods default their `created_by` field to an integer
CA-REQ-005|No unnecessary data is exposed|Health check endpoint reveals quantities of data held including users
CA-REQ-005|No unnecessary data is exposed|Inclusion of a list users endpoint is a potential GDPR violation
CA-REQ-005|No unnecessary data is exposed|No controls on viewing legal entities
CA-REQ-005|No unnecessary data is exposed|No controls on viewing expenses
CA-REQ-005|No unnecessary data is exposed|No controls on viewing activities
CA-REQ-006|Folder structure conforms to standard|All CRUD endpoints for Cost Centres, Legal Entities, Allocation Periods, and Activities are contained in a single resource file with an ambiguous name
CA-REQ-006|Folder structure conforms to standard|No meaningful folder structure beyond `routers` used
CA-REQ-006|Folder structure conforms to standard|Config file, DB abstraction, entry point, seeds and auth all listed next to one another
CA-REQ-006|Folder structure conforms to standard|No clear entry point specified
CA-REQ-007|Code complexity is low|No password complexity is enforced
CA-REQ-009|Code logic is robustly documented with inline comments|Majority of API handling logic is uncommented
CA-REQ-009|Code logic is robustly documented with inline comments|Non-standard block comments are used even for single functions
CA-REQ-009|Code logic is robustly documented with inline comments|Pydantic request-response models do not have class dosctrings
CA-REQ-009|Code logic is robustly documented with inline comments|May comments use invalid ASCII characters (most commonly em-dashes)
CA-REQ-009|Code logic is robustly documented with inline comments|Comment in main.py references a hard-coded localhost URL and port number
CA-REQ-010|API endpoints are well documented|FastAPI description uses inconsistent whitespace, references seed data, reveals internal logic, uses non ASCII characters.
CA-REQ-010|API endpoints are well documented|Endpoint descriptions are minimal and insufficient
CA-REQ-011|All functions include docstrings|Multiple instances of functions missing docstrings
CA-REQ-011|All functions include docstrings|Multiple instances of function docstrings not including arguments
CA-REQ-012|Variable names are high quality|Function `list_periods` reuses name 'status' from a top-level import
CA-REQ-012|Variable names are high quality|API uses snake-case variable names instead of camel-case
CA-REQ-012|Variable names are high quality|Use of a generic open-period checker function with a default raise condition is ambiguous due to unclear name and usage
CA-REQ-012|Variable names are high quality|Multiple instances of single-letter variable names
CA-REQ-012|Variable names are high quality|Multiple instances of generic variable names like `row`, and `rid` (row ID)
CA-REQ-012|Variable names are high quality|Generic class names such as the singleton class `Settings`, app may use multiple config classes in the future as per other projects
CA-REQ-015|Static linting against OpenAPI standards yields no errors|Only some endpoints explicitly list a default response status code
CA-REQ-017|An audit trail allows clear transaction history to be viewed for at least 7 years|Multiple entities can be deleted with no record of their having existed
CA-REQ-018|Transaction events are logged and searchable|No records are kept of changes being made
CA-REQ-022|Controls are in place to restrict addition of new users|No approvals are required to justify a new user. No signup reason is recorded
CA-REQ-022|Controls are in place to restrict addition of new users|No record is kept of who created a new user or why
CA-REQ-022|Controls are in place to restrict addition of new users|No justification or reason is recorded when a user is deactivated
CA-REQ-026|Data access is controlled with RBAC on the principle of least privilege|No ability exists to change or revoke a user's role
CA-REQ-026|Data access is controlled with RBAC on the principle of least privilege|User accounts and roles have no scheduled expiration or review mandiated
CA-REQ-026|Data access is controlled with RBAC on the principle of least privilege|No ability exists to restore a deactivated user
CA-REQ-026|Data access is controlled with RBAC on the principle of least privilege|Endpoint protection applies a ranking system to roles assuming each inherits the privileges of the last. Roles should be accumulated instead of using inheritance.
CA-REQ-027|Data at-rest is encrypted|No encryption is enforced at application level. No instruction to implement DB-level encryption is present
CA-REQ-028|All API requests are logged|No logger is used
CA-REQ-029|No extraneous information is exposed|The health check endpoint lists quantity totals of records in each table
CA-REQ-031|Primary key columns are complex and unique strings (UUID)|Primary key columns are integers
CA-REQ-033|Database actions like transactions are compatible with Oracle|In some cases database interaction logic is contained in the API endpoint instead of being abstracted. This will be re-written to work cross-platform
CA-REQ-033|Database actions like transactions are compatible with Oracle|No control on where seeds will run, seed file runs on every restart
CA-REQ-070|Strong CORs controls and other header settings are used|CORs headers use wildcards with no restrictions
CA-REQ-071|Environment and config variables are securely handled|Application has no capacity to read in a credentials service
CA-REQ-071|Environment and config variables are securely handled|Use of enum types which are not abstracted to a constants file potentially leading to code drift and security control breakdown
CA-REQ-071|Environment and config variables are securely handled|Application loads credentials using a relative path
CA-REQ-071|Environment and config variables are securely handled|Application does not use a safe credentials loader such as ConfigParser potentially leading to secrets injection or logic faults
CA-REQ-071|Environment and config variables are securely handled|Application holds a JWT secret key hard-coded
CA-REQ-072|All database logic is wrapped in at least one exception catch|Majority of endpoints have no fallback try/except
CA-REQ-073|Database transactions are abstracted via use of an ORM|All database interactions are manual
CA-REQ-073|Database transactions are abstracted via use of an ORM|No SQL injection sanitisation is used anywhere

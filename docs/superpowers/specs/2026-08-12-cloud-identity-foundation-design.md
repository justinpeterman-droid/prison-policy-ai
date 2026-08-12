# Cloud Identity Foundation Design

**Date:** 2026-08-12<br>
**Status:** Approved for implementation planning<br>
**Parent:** [Access + Cloud Run Master Design](2026-08-12-access-cloud-run-master-design.md)

## Purpose

Replace shared `ACCESS_CODE` / `ADMIN_CODE` authorization for the new Access API
with individual employee accounts, secure PIN authentication, optional
Windows-bound persistent sessions, User/Admin authorization, administrator
step-up confirmation, and append-only audit records.

The existing shared-code browser login remains available during the parallel
pilot. It does not authenticate `/api/v1` requests and is not a fallback path
around individual authorization.

## Scope

- Cloud SQL PostgreSQL connection and migration foundation.
- Staff identity records that can exist with or without an application account.
- User/Admin accounts linked one-to-one with staff records.
- PIN enrollment, verification, change, reset, expiry, and lockout.
- Short-lived access tokens and rotating renewal tokens.
- Optional persistent sessions for both User and Admin accounts.
- Session listing and revocation.
- Administrator step-up tokens for sensitive operations.
- Request authentication and role authorization helpers.
- Append-only authentication and administrative audit events.
- Rate limits and safe errors.
- `/api/v1/auth`, `/api/v1/me`, and foundational administrator account APIs.

## Non-goals

- Report ownership or report authorization.
- Access form implementation.
- Replacing the existing browser login during the pilot.
- Google Workspace, Active Directory, Entra ID, or Windows integrated sign-in.
- Biometric authentication or multifactor authentication in the first release.
- Readable PIN recovery.
- Direct Cloud SQL access from Access.

## Technology decisions

- SQLAlchemy 2.x owns application persistence mappings.
- Alembic owns ordered, reversible schema migrations.
- Psycopg 3 is the PostgreSQL driver.
- `argon2-cffi` implements Argon2id PIN hashing.
- Opaque tokens are generated from at least 256 bits of cryptographic
  randomness. Only SHA-256 token hashes are stored in Cloud SQL.
- UTC is used for all database timestamps and API time values.
- UUID values are server-generated and never derived from employee numbers.
- The OpenAPI contract under `openapi/access-v1.yaml` is authoritative for
  request and response shapes.

## Data model

### `staff_members`

- `id`: UUID primary key.
- `employee_number`: normalized string, unique among all staff records.
- `rank`, `first_name`, `last_name`, `shift`: required roster attributes except
  rank may be empty.
- `is_active`: whether the person may be selected for new reports.
- `created_at`, `updated_at`.

Employee numbers are display/business identifiers, not authorization secrets.
Normalization trims surrounding whitespace and compares case-insensitively.
Changing an employee number does not change the UUID or break report history.

### `accounts`

- `id`: UUID primary key.
- `staff_member_id`: unique foreign key.
- `role`: `user` or `admin`.
- `status`: `active`, `locked`, or `deactivated`.
- `pin_hash`: Argon2id encoded hash.
- `must_change_pin`: boolean.
- `temporary_pin_expires_at`: nullable UTC timestamp.
- `failed_attempts`: consecutive failed verification count.
- `lock_cycle`: number of repeated lock cycles since the last success.
- `locked_until`: nullable UTC timestamp.
- `auth_version`: monotonically increasing integer used to revoke all sessions.
- `last_login_at`, `created_at`, `updated_at`, `deactivated_at`.

An account is never hard-deleted through the API. Deactivation preserves its
staff link, report history, revisions, and audits.

### `sessions`

- `id`: UUID primary key.
- `account_id`: foreign key.
- `auth_version`: copied from the account at issuance.
- `access_token_hash`, `access_expires_at`.
- `renewal_token_hash`, `renewal_expires_at`: required rotating renewal
  credential. A nonpersistent client holds it only in memory; a persistent
  client may DPAPI-encrypt it on disk.
- `renewal_family_id`: stable identifier used for rotation/reuse detection.
- `device_id_hash`: hash of a random Access installation identifier.
- `device_label`: bounded safe label such as workstation name; never used as an
  authorization factor.
- `persistent`: boolean selected by the employee.
- `last_used_at`, `created_at`, `revoked_at`, `revoke_reason`.

The renewal token is returned only at creation/rotation. Access DPAPI-encrypts
it for the current Windows user. Cloud Run never receives or stores Windows
login credentials.

### `admin_step_up_tokens`

- `id`: UUID primary key.
- `session_id`: foreign key.
- `token_hash`.
- `issued_at`, `expires_at`, `used_at`, `revoked_at`.
- `purpose`: bounded enum or action family.

Step-up tokens expire five minutes after PIN confirmation and may be scoped to
one sensitive action. Admin Center elevation expires after 15 minutes of
inactivity. An Admin account may remain signed in persistently while its Admin
Center is locked.

### `browser_handoffs`

- `id`: UUID primary key.
- `account_id`, `session_id`: issuing Admin identity.
- `token_hash`: SHA-256 hash of a 256-bit one-time secret.
- `purpose`: `review_lab`.
- `expires_at`: 60 seconds after issue.
- `redeemed_at`, `revoked_at`, `created_at`.

An elevated Admin may issue one handoff. Access opens
`https://<managed-host>/access-handoff#<one-time-token>`. The fragment is not
sent in the initial HTTP request or referrer. The landing page posts it once to
`POST /api/browser-handoffs/redeem`, immediately removes the fragment from
browser history, and receives an individual HttpOnly, Secure, SameSite=Lax
browser session before redirecting to `/review-lab`. The browser session expires
after 30 minutes of inactivity and is not persistent. Shared `ADMIN_CODE` is not
used by this flow.

### `audit_events`

- `id`: UUID primary key.
- `occurred_at` UTC.
- `actor_account_id` and `actor_staff_member_id`: both nullable only for an
  unknown failed-login actor or the one-time `system.initial_admin_bootstrapped`
  event. Every other event requires both actor IDs.
- `action`: stable action code.
- `target_type`, `target_id`: bounded identifiers.
- `result`: `success`, `denied`, or `failed`.
- `request_id`.
- `client_version`, `device_id_hash`, and safe network metadata.
- `details`: validated JSONB containing identifiers/state changes but no PIN,
  token, field notes, or report narrative.

Application roles cannot update or delete audit events. A dedicated insert-only
database pathway writes them.

## PIN rules

- Accepted characters are ASCII `A-Z`, `a-z`, and `0-9` only.
- Length is 4 through 8 characters.
- Leading zeroes are preserved.
- Letters are case-insensitive. The normalized value is uppercase before
  Argon2id hashing and verification.
- Six through eight characters are recommended in the UI; administrators
  receive the same permitted range.
- PINs are rejected when equal to the employee number or obvious repeated and
  sequential values such as `0000`, `1111`, `1234`, or `ABCD`.
- Submitted current/new PIN text is accepted only over HTTPS, held for the
  duration of verification, and never logged or reflected. The only readable
  outputs are newly generated temporary PINs: ordinary Admin creation/reset
  returns one once, while initial-Admin bootstrap writes one directly to its
  dedicated Secret Manager version and never returns it from the job/workflow.

Argon2id uses 64 MiB memory, three iterations, parallelism 1, a 16-byte random
salt, and a 32-byte hash. The implementation benchmark must verify that one
check remains below 500 ms on the selected Cloud Run minimum instance. Stored
hashes include algorithm parameters, allowing a later reviewed
rehash-on-login upgrade.

## Account lifecycle

### Creation

An administrator selects or creates a staff member, assigns User/Admin, and
requests a temporary PIN. Cloud Run generates a random 8-character alphanumeric
temporary PIN, stores only its Argon2id hash, sets a 24-hour expiry, and returns
the readable temporary value exactly once to the administrator.

The administrator communicates it through an agency-approved channel. The
employee must replace it on first successful sign-in before any other API is
available.

The initial Admin is the sole system-created account. A dedicated bootstrap
service acquires a PostgreSQL transaction-scoped advisory lock, verifies that
the `accounts` table contains zero rows and that the approved target staff row
is active, then creates exactly one Admin account with a random temporary PIN,
24-hour expiry, and mandatory first-use change. The account insert and distinct
`system.initial_admin_bootstrapped` audit insert are one transaction and roll
back together. The audit actor IDs are null only for this system operation and
its details contain only an opaque operation UUID and the SHA-256 of the
external approval reference. Bootstrap fails permanently once any account row
exists; it never becomes an alternate account-creation or recovery path.

### PIN change

An authenticated employee supplies the current PIN and a conforming new PIN.
Success increments `auth_version`, revokes every other session, rotates the
current session, and creates an audit event. The employee remains signed in on
the current device with newly issued tokens.

### Administrative reset

An administrator with a valid five-minute step-up token requests a reset.
Cloud Run creates a new one-time temporary PIN, increments `auth_version`,
revokes every session, and records both administrator and target IDs. The
administrator cannot choose or view the old PIN.

### Lockout

- Attempts 1 through 4 return the same generic invalid-credentials response.
- Attempt 5 creates a 15-minute lock.
- A later five-failure cycle creates a 30-minute lock, then 60 minutes; further
  cycles double to a maximum of 24 hours.
- Successful verification resets `failed_attempts` and `lock_cycle`.
- Deactivated and locked accounts return the same external sign-in failure
  shape as unknown accounts while the audit result preserves the reason.
- Administrators can clear a lock through a step-up-protected operation.

### Deactivation and role change

Deactivation or any role change increments `auth_version` and revokes all
sessions. A deactivated employee remains a staff/history record but cannot sign
in or be selected for a new report unless the staff record remains separately
active by explicit administrator choice.

The service prevents an administrator from removing/deactivating the last
active Admin account.

## Session behavior

### Sign-in response

A valid sign-in returns:

- 15-minute opaque access token.
- Rotating renewal token for the life of the Access process. When **Keep me
  signed in** is selected, Access may additionally persist it through DPAPI.
- Account/staff profile, role, and PIN-change requirement.
- Access and renewal expiry timestamps.
- Server time and request ID.

Access keeps the access token in memory. It stores a renewal token only after
DPAPI encryption succeeds. If DPAPI storage fails, the client discards the
renewal token and treats the session as nonpersistent.

### Renewal

- A persistent renewal token expires after 30 days without use.
- A nonpersistent renewal token expires after 12 hours, is kept in memory only,
  and is explicitly revoked during a normal Access shutdown.
- Each valid use revokes the previous token and returns a new token in the same
  family.
- Reuse of an already-rotated token revokes the entire family and requires a
  fresh PIN sign-in.
- Renewal verifies account status, role/auth version, device ID hash, and token
  expiry before issuing a new pair.
- A nonpersistent session can rotate its in-memory renewal token while Access
  remains open. Closing Access revokes it; a crash leaves only a server-side
  token that expires within 12 hours and was never written to disk.

### Logout

- **Sign out of this computer** revokes the current session family and removes
  the local DPAPI token.
- **Sign out everywhere** increments `auth_version`, revokes all sessions, and
  removes the local DPAPI token.
- Server revocation succeeds even if the client cannot delete its local copy;
  the unusable copy is deleted at next startup.

### Administrator persistence and elevation

Admins may select **Keep me signed in**. Persistent sign-in restores the
account's reporting capabilities without re-entering the PIN. Opening the Admin
Center after 15 minutes of Admin inactivity requires PIN confirmation. Sensitive
changes additionally require a step-up token issued within five minutes.

## API surface

`GET /api/v1/client-policy` is the public bootstrap operation. Its closed
release-one data object has exactly nine required safe fields:
`release_version`, `latest_client_version`, `minimum_client_version`,
`minimum_server_version`, `api_version`, `release_notes`,
`read_only_required`, `review_lab_origin`, and
`field_notes_max_characters`. The last field is the integer `30000`, sourced
from one backend constant rather than an environment variable or the canonical
release-version projection.

### Employee authentication

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/renew`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-all`
- `POST /api/v1/auth/change-pin`
- `POST /api/v1/auth/admin-step-up`
- `GET /api/v1/auth/sessions`
- `DELETE /api/v1/auth/sessions/{session_id}`
- `GET /api/v1/me`

### Administrator account foundation

- `GET /api/v1/admin/staff`
- `POST /api/v1/admin/staff`
- `PATCH /api/v1/admin/staff/{staff_id}`
- `GET /api/v1/admin/accounts`
- `POST /api/v1/admin/accounts`
- `PATCH /api/v1/admin/accounts/{account_id}`
- `POST /api/v1/admin/accounts/{account_id}/reset-pin`
- `POST /api/v1/admin/accounts/{account_id}/unlock`
- `POST /api/v1/admin/accounts/{account_id}/revoke-sessions`
- `POST /api/v1/admin/review-lab-handoffs`

The one-time browser landing/redeem surface is deliberately outside Access
bearer-token routes:

- `GET /access-handoff`
- `POST /api/browser-handoffs/redeem`

All list endpoints are paginated and bounded. Sensitive mutations require a
valid step-up token. Every response follows the program-level envelope and
request-ID rules.

## Authorization middleware

Authentication resolves a bearer access token to a live session and account.
It verifies token hash, expiry, revocation, account status, and `auth_version`.
The resolved actor is attached to request context. Downstream routes use
declarative helpers such as `require_role("admin")` and record-specific policy
functions; they never trust `account_id`, `employee_number`, or `role` values
from request JSON.

Existing browser cookies do not authenticate `/api/v1`. Access bearer tokens do
not authenticate legacy browser pages.

## Rate limiting and safe responses

- Per-account lockout is authoritative.
- Application rate limits additionally cover normalized employee number,
  device ID, and network source without relying on one shared facility IP.
- Cloud Armor provides broad abuse controls; Flask owns identity-aware limits.
- Unknown employee, wrong PIN, deactivated, and locked responses use one safe
  external message and code.
- The common structured request event contains exactly `request_id`, `action`,
  `result`, `latency_ms`, `latency_bucket`, `http_status_class`, `error_code`,
  `client_version`, and `dependency`. Action, result, bucket, error, and
  dependency values are bounded stable codes; client version is parsed rather
  than copied from a raw header. The event never contains employee/staff/account
  identity, names, PINs, tokens, device/network identity, headers, query/path
  values, request/response bodies, field notes, or report content.
- Authentication endpoints never reflect submitted values.

## Audit action codes

At minimum:

- `auth.login_succeeded`, `auth.login_failed`, `auth.locked`
- `auth.session_renewed`, `auth.session_revoked`, `auth.logout_all`
- `auth.pin_changed`, `auth.pin_reset`, `auth.step_up_succeeded`,
  `auth.step_up_failed`
- `admin.staff_created`, `admin.staff_updated`
- `admin.account_created`, `admin.account_role_changed`,
  `admin.account_deactivated`, `admin.account_reactivated`,
  `admin.account_unlocked`
- `admin.review_lab_handoff_issued`,
  `admin.review_lab_handoff_redeemed`
- `system.initial_admin_bootstrapped`

## Failure behavior

- Database unavailability returns 503 with a request ID and does not pretend a
  sign-in or account mutation succeeded.
- Audit insert failure causes a protected mutation to roll back. A successful
  login may proceed only when its required audit event commits in the same
  transaction or a guaranteed outbox record commits with it.
- Initial-Admin bootstrap uses transaction-scoped advisory locking. Concurrent
  attempts produce at most one account, and any account/audit failure leaves
  both absent so the operation may be safely retried while the account count is
  still zero.
- Renewal races allow one rotation winner; the losing/reused token triggers the
  defined family-revocation behavior.
- An ordinary Admin-created/reset temporary PIN is returned once. If that
  response is lost, an authenticated administrator performs another reset; the
  server never retrieves the prior value. Initial-Admin bootstrap never returns
  its PIN in a response: the authorized custodian retrieves only the dedicated
  secret version. Once the first Account commits, loss of that version is an
  enrollment incident and never authorizes a second bootstrap.

## Testing

### Unit tests

- Employee-number and PIN normalization.
- PIN policy, obvious-value rejection, Argon2id verification, and rehash.
- Temporary PIN generation and 24-hour expiry.
- Zero-account first-Admin bootstrap, active-staff enforcement, advisory-lock
  concurrency, approval-reference hashing, and null-actor audit exception.
- Lock cycles, durations, success reset, and safe external errors.
- Opaque token hashing, access expiry, renewal rotation, reuse detection, and
  auth-version revocation.
- User/Admin role checks and last-active-admin protection.
- Audit payload redaction and allowed detail schema.

### Integration tests

- Alembic upgrade and downgrade on an empty and populated PostgreSQL database.
- Account creation through first sign-in and mandatory PIN change.
- Concurrent first-Admin attempts create exactly one Admin; any later attempt
  fails after any account exists, and audit failure rolls back the account.
- Persistent/nonpersistent User and Admin session flows.
- PIN change/reset/deactivation/role change revokes the expected sessions.
- Admin Center lock and five-minute sensitive-action step-up.
- Cross-role endpoint denial and legacy cookie isolation.
- Concurrent renewal and session-reuse attack handling.
- Database/audit failure rollback.
- Rate limits with multiple employees behind one network source.
- One-time Review Lab handoff issue, fragment redemption, expiry, replay
  rejection, individual attribution, and nonpersistent browser-session expiry.

### Security verification

- No readable PIN or token in Cloud SQL, Flask logs, Cloud Logging, exceptions,
  or test artifacts. API responses never contain an existing credential; the
  sole PIN-response exception is an ordinary newly generated Admin
  create/reset temporary PIN returned once. Initial-Admin bootstrap responses
  never contain a PIN.
- Brute-force and account-enumeration behavior.
- Session theft/replay, rotation, and revocation behavior.
- Authorization bypass attempts using modified employee/account/role fields.
- Attempts to reuse bootstrap for a second account, inactive staff, a User
  role, or an unapproved/plaintext approval reference.

## Acceptance criteria

1. Staff identity and application accounts are separate, stable, and linked.
2. An active employee signs in with a conforming PIN and receives an in-memory
   rotating session; only the persistent option permits DPAPI storage beyond
   the current Access process.
3. Both roles may persist on the current Windows account; Admin Center
   elevation and sensitive operations still require the specified PIN checks.
4. No readable PIN or bearer token is persisted server-side or logged.
5. Temporary PIN, first-use change, lockout, reset, deactivation, role change,
   and last-admin protections behave exactly as specified.
6. Renewal rotation, reuse detection, expiry, device binding, and logout scopes
   are enforced.
7. Legacy shared-code sessions cannot authenticate Access APIs, and Access
   tokens cannot authenticate legacy pages.
8. Every authentication/account action creates a safe, attributable,
   append-only audit event.
9. Review Lab handoff never exposes a PIN, Access token, or shared code; it is
   single-use, expires in 60 seconds, and creates an attributable nonpersistent
   browser session.
10. Authorization helpers derive the actor from the server session and pass the
    complete focused and regression test suites.
11. A fail-closed, transaction-serialized bootstrap creates the first Admin
    only while zero accounts exist, forces PIN change within 24 hours, records
    the dedicated null-actor system audit event, and cannot create any later
    account.

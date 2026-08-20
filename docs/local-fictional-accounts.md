# Local Fictional Accounts

For local development only, seed the standard fictional Officer and Administrator accounts after applying the database migrations:

```bash
python -m alembic upgrade head
python scripts/seed_fictional_accounts.py
```

The command reads `DATABASE_URL` and refuses to run unless it points to a loopback PostgreSQL host (`localhost`, `127.0.0.1`, or `::1`) **with no URI query parameters**. Query parameters are rejected because libpq/psycopg connection options such as `host`, `hostaddr`, or `service` can redirect an apparently local URI to a different database. It is intentionally not a production staff-provisioning tool.

The command is safe to rerun. Existing fictional rows are refreshed to the same local fixture values rather than duplicated, and existing sessions for those accounts are invalidated through the account authorization version.

Standard local credentials:

- Officer: `TEST-1001` / `Z9Y8X7`
- Administrator: `TEST-9001` / `Q7W9E2`

These values match the repository's existing fictional integration fixtures so this command can replace the temporary test-fixture seeding workaround without creating a second set of local credentials.

Do not reuse these credentials outside local development or commit real staff identities to fixtures, examples, screenshots, or documentation.

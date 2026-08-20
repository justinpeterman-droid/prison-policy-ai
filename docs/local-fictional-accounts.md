# Local Fictional Accounts

For local development only, seed the standard fictional Officer and Administrator accounts with:

```bash
python scripts/seed_fictional_accounts.py
```

The command reads `DATABASE_URL` and refuses to run unless it points to a loopback PostgreSQL host (`localhost`, `127.0.0.1`, or `::1`). It is intentionally not a production staff-provisioning tool.

The command is safe to rerun. Existing fictional rows are refreshed to the standard local values rather than duplicated.

Standard local credentials:

- Officer: `TEST-1001` / `Z9Y8X7`
- Administrator: `TEST-9001` / `A7B8C9`

Do not reuse these credentials outside local development or commit real staff identities to fixtures, examples, screenshots, or documentation.

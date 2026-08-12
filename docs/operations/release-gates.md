# Release Gates

- `CLOSED`: one or more required evidence items is absent; dependent work cannot enter production scope.
- `READY_FOR_TEST`: test-only prerequisites are reviewed and all test data is fictional.
- `READY_FOR_PRODUCTION`: every production prerequisite, restore exercise, rollback exercise, security review, and written acceptance is recorded externally.

No coding agent may promote a gate based on local tests, inferred configuration, or self-review. Gate transitions require externally reviewed evidence; Git records only the resulting state and external reference classification, never identities, secrets, operational values, or evidence contents.

Store completed records in the agency-approved system of record.

# Environment Register Template

Record test and production separately in the external system of record. Git contains field names only.

| Isolation field | Required external evidence |
|---|---|
| Project/resource boundary | Distinct approved environment scope |
| Region | Approved service location |
| Cloud SQL instance and database | Isolated database boundary |
| Cloud Run API and worker | Isolated runtime boundary |
| Cloud Tasks queue | Isolated queue boundary |
| Storage buckets | Isolated private bucket boundary |
| Managed hostname and DNS | Isolated endpoint authority |
| Runtime and workflow identities | Least-privilege identity boundary |
| Discovery Engine data store | Separate test/production index boundary |
| WIF provider | Environment-scoped trust boundary |
| Secret Manager namespace | Isolated secret-container boundary |
| Audit data | Isolated retention/access boundary |

Production data is prohibited in test. Agents record only whether isolation evidence was reviewed, never its identifiers or contents.

Store completed records in the agency-approved system of record.

# External Prerequisites

This register records gate state only. Agents may record whether evidence was reviewed, but never the evidence contents, identities, infrastructure values, credentials, or operational records.

| Gate | Required evidence | Repository state when evidence is absent |
|---|---|---|
| EXT-01 Separate cloud environments | Approved test and production project/resource isolation | CLOSED |
| EXT-02 Regional placement | Production regional services approved for us-central1 | CLOSED |
| EXT-03 DNS and certificates | Managed test and production hostnames and DNS authority | CLOSED |
| EXT-04 Billing and budgets | Billing owner, budget amounts, and escalation destinations | CLOSED |
| EXT-05 WIF trust | Repository, branch/ref, provider, and environment trust conditions | CLOSED |
| EXT-06 Runtime secrets | Named human custodian and approved Secret Manager population procedure | CLOSED |
| EXT-07 Access trusted location | Narrow managed local installation directory and ACL policy | CLOSED |
| EXT-08 Managed signing policy | Agency-approved `.accde` trust mechanism and managed-signing service interface/policy that never exports private key material | CLOSED |
| EXT-09 Workstation matrix | Every supported or excluded workstation class recorded | CLOSED |
| EXT-10 Network allowlist | Proxy, firewall, TLS inspection, DNS, and Google endpoint decisions | CLOSED |
| EXT-11 Initial roster correction | Approved duplicate, missing-ID, invalid-shift, and ambiguous-name mapping | CLOSED |
| EXT-12 Initial Admin enrollment | Approved private request creation/hash, protected zero-account bootstrap, authorized PIN custodian communication, and secret-version disable/destruction procedure | CLOSED |
| EXT-13 Security and records review | Data classification, retention, export, printing, and incident requirements | CLOSED |
| EXT-14 Pilot authorization | Named 5-10 employees, two administrators, training, support, and real-data approval | CLOSED |
| EXT-15 Written production acceptance | Business, IT/security, and records-management sign-off | CLOSED |
| EXT-16 GitHub protected environments | Exact six environments, reviewer counts, refs/heads/main policies, workflow allowlist, and environment-scoped WIF variables verified by a GitHub administrator | CLOSED |

Store completed records in the agency-approved system of record.

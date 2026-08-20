# Guided Operations Web Pilot Runbook

Use this runbook only after the release gates have externally reviewed evidence.
The repository stays on a reversible route mode until owners approve otherwise.
An agent does not perform production steps.

1. Complete test environment acceptance with fictional accounts and fictional
   records only.
2. Set `WEB_APP_MODE=preview` through the approved configuration process and
   conduct internal review at `/workspace`.
3. Run a small fictional-data usability exercise with officers and administrators.
4. Obtain authorization for a limited pilot using real production accounts; do
   not put participant identities in Git.
5. Review parity with Access and the legacy Jinja experience, including reports,
   permissions, paperwork, printing, and sign-out.
6. Triage issues, preserve request IDs and logs, repair in test, and repeat the
   relevant acceptance checks.
7. Hold an explicit go/no-go review for `primary`; only the authorized owners may
   approve the configuration change.
8. Observe the post-cutover system against the agreed support and security plan.
9. Hold a separate, explicit legacy-retirement review after the pilot evidence is
   complete. Do not retire a legacy surface as part of this pilot runbook.

Store completed records in the agency-approved system of record.

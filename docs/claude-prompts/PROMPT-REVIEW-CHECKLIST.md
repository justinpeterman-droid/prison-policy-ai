# Claude Prompt Review Checklist

Use this checklist before giving any task prompt to Claude Code and again when reviewing its handoff.

## Before execution

- [ ] The prompt sequence, task ID, title, detailed-plan heading, filename, and README index agree.
- [ ] Baseline commit is exactly `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d` and is an ancestor of the reviewed starting commit.
- [ ] Prerequisite task commits and both required reviews are complete.
- [ ] The worktree contains no unexpected overlapping edits; no reset, checkout-discard, clean, stash, or destructive recovery is proposed.
- [ ] Every create/modify/delete path matches the detailed task's Files section; consume-only files remain read-only.
- [ ] The prompt repeats the binding interfaces, locked wire rules, exact errors, and stop conditions relevant to the task.
- [ ] Red, focused, regression, sensitive-data, and whitespace checks are exact and runnable in the declared environment.
- [ ] Fixtures and examples are fictional; no real employee, inmate, report, PIN, token, cloud identifier, or production evidence is requested.
- [ ] The prompt explicitly forbids push, merge, cloud deploy/apply, migration invocation, traffic shift, signing, publication, secret changes, and production access.

## Handoff review

- [ ] Claude reported a red phase before implementation or explained a plan-defined environmental stop.
- [ ] `git diff --name-status` is wholly inside the allowlist, including exact authorized deletions.
- [ ] No unrelated user changes were altered, staged, deleted, or hidden.
- [ ] The exact focused and regression commands passed; skipped external/Windows/cloud checks are named as gates rather than claimed complete.
- [ ] `git diff --check` passed.
- [ ] Sensitive-data/log scans passed and test data is fictional.
- [ ] The implementation did not weaken authentication, authorization, idempotency, revision history, audit attribution, environment isolation, or release provenance.
- [ ] One focused commit uses the exact required message.
- [ ] The handoff includes SHA, files, commands/results, interfaces, assumptions, risks, blockers, and remaining external evidence.
- [ ] Claude explicitly confirmed that it did not push, merge, deploy, apply, invoke production jobs, shift traffic, sign, publish, change secrets, or access production data.

## Stop and return to plan review when

- a required file/interface/example is missing;
- current reviewed plans conflict with the prompt;
- an external prerequisite is closed;
- a requested action falls outside the task allowlist;
- a test would require production credentials/data or an unapproved cloud/Windows target;
- a schema, migration, route, error code, security boundary, or release source would need to change outside the declared task.

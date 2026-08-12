# Sequence 017 — RP-08: Policy Expert `/api/v1` Contract

Copy everything below into a fresh Claude Code session.

---

Implement only RP-08, “Policy Expert `/api/v1` contract.” Use TDD, one focused commit, hand off, and stop.

## Objective

Expose the existing cited Policy Expert through a bounded synchronous individual-auth API while preserving browser behavior, cleaning history consistently, enforcing 90-second budget and transactional idempotency, and deliberately avoiding persistence of questions/answers/citation text. Repeated keys must never silently repeat provider cost.

## Repository control

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Baseline ancestor: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/rp-08-policy-expert-api`
- Predecessor on current reviewed `main`: `feat: add private report job worker`.

```powershell
git status --short --untracked-files=all
if((git branch --show-current) -ne 'main'){throw 'Start from current reviewed main.'}
git merge-base --is-ancestor 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d HEAD
if($LASTEXITCODE -ne 0){throw 'Reviewed baseline is not an ancestor.'}
git log --oneline 6692b10e4f2aae3f76fd0f32e04fdf3a1180362d..HEAD
git log --format="%s"|Select-String -SimpleMatch "feat: add private report job worker"
git switch -c claude/rp-08-policy-expert-api
```

Require clean tracked/index state; tolerate only untouched pre-existing `.superpowers/`. Read intervening reviewed changes if main advanced; stop for missing/unreviewed/conflicting prerequisites. Never reset/stash/clean user work.

## Required reading

- `AGENTS.md`; roadmap shared HTTP/idempotency/error/sensitive-log rules.
- Report plan exact RP-08 section with history limits, idempotency outcomes, provider/error behavior, tests/OpenAPI.
- Report/master specs.
- Consume-only existing `backend/webapp/routes/chat.py`, `backend/pipeline/query.py`, answer/citation/error helpers/tests, ID-06 idempotency/audit, API envelope/OpenAPI.

## Exact allowed files

- Modify: `backend/webapp/routes/chat.py`
- Create: `backend/webapp/api_v1/policy.py`
- Modify: `backend/webapp/api_v1/__init__.py`
- Modify: `openapi/access-v1.yaml`
- Create: `tests/unit/test_policy_v1.py`
- Create: `tests/contract/test_policy_examples.py`

Consume-only: query/retrieval/citation/error helpers, plans/specs, prior APIs/tests. No engine/retrieval prompt/index, DB model, report, worker, legacy response, README, Access, or infra edits.

## Locked interfaces and wire rules

- Produce shared `clean_policy_history(raw) -> list[dict[str,str]]` and exact `POST /api/v1/policy/questions`; browser route imports same cleaner and preserves answer/citations/sources/retrieved-source shape.
- One closed question request; preserve current bounded history limits (maximum six after cleaning per tests). Require bearer, compatible client, request ID, and `Idempotency-Key`.
- Canonically hash normalized question/history without logging/persisting them. Claim ID-06 idempotency before provider. Record only hash/result status/latency bucket/response SHA, never question, answer, passage/source text.
- Duplicate key while running returns `409 request_in_progress`. Completed duplicate returns `409 idempotent_response_unavailable`, never response replay or second provider call. Client may intentionally ask again only with new key.
- Enforce 90-second server budget, call existing `answer_question`, return approved citations/source titles/passages, audit stable IDs/latency/result only. Translate existing `classify_error()` categories to stable safe API errors; no HTML/stack/infrastructure detail.
- Unit/contract tests monkeypatch provider; no Google credentials/network. Existing browser shapes unchanged.

## TDD procedure

1. Add failing bounded/invalid history, closed request, safe errors, idempotency running/completed/changed payload, no-persist/log, citation contract, browser parity tests first.
2. Run red:

   ```powershell
   python -m pytest tests/unit/test_policy_v1.py tests/contract/test_policy_examples.py -v
   ```

   Expected: FAIL with missing module or 404.
3. Promote history cleaner without limit drift; implement route with same-transaction idempotency/audit metadata and explicit provider budget/error handling.
4. Add closed OpenAPI request/response/citation/errors/examples. No sensitive idempotent response storage.
5. Run policy/browser regressions:

   ```powershell
   python -m pytest tests/unit/test_policy_v1.py tests/contract/test_policy_examples.py tests/unit/test_chat_history.py tests/unit/test_chat_errors.py tests/unit/test_citations.py tests/unit/test_retrieval.py -v
   ```

   Expected: PASS; browser response shapes unchanged; provider fake called no more than once per key.
6. Run allowlist/whitespace:

   ```powershell
   $allowed=@('backend/webapp/routes/chat.py','backend/webapp/api_v1/policy.py','backend/webapp/api_v1/__init__.py','openapi/access-v1.yaml','tests/unit/test_policy_v1.py','tests/contract/test_policy_examples.py')
   $changed=@((git diff --name-only),(git diff --cached --name-only),(git ls-files --others --exclude-standard))|Sort-Object -Unique
   $unexpected=$changed|Where-Object{$_ -notin $allowed -and $_ -notlike '.superpowers/*'}
   if($unexpected){$unexpected;throw 'Changed-file allowlist violation.'}
   git diff --check
   $taskChanged=@($changed|Where-Object{$_ -in $allowed})
   if(-not $taskChanged){throw 'No allowlisted task changes to stage.'}
   git add -A -- $taskChanged
   $staged=@(git diff --cached --name-only)|Sort-Object -Unique
   $unexpectedStaged=$staged|Where-Object{$_ -notin $allowed}
   if($unexpectedStaged){$unexpectedStaged;throw 'Staged-file allowlist violation.'}
   git diff --cached --name-status
   git diff --cached --check
   ```

## Security, non-goals, acceptance

Fictional questions/answers only; fakes, no ADC. Never persist/log/audit question, answer, history, citation passage/source text, token/PIN/employee/inmate/report data or raw body. Do not make Policy asynchronous, store response for replay, change retrieval/citation behavior, or build Access/infra. Acceptance: red evidence; bounded shared cleaner; exact idempotency outcomes/no repeat; safe 90-second error contract; browser parity; OpenAPI/tests/allowlist/whitespace green.

## Commit and handoff

```powershell
git commit -m "feat: expose cited policy expert api"
```

The final handoff must explicitly report task and branch; starting SHA, current-reviewed baseline ancestry, final SHA, commit SHA, and exact commit message; every changed/deleted file; red, focused, and regression commands with exit results; unstaged and staged allowlist results plus both `git diff --check` and `git diff --cached --check`; interfaces consumed and produced; security, privacy, and fictional-data checks; assumptions, risks, deviations, `NOT RUN` checks, and remaining external gates; and confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or accessed in production.

Do not push. Handoff start/ancestry/prerequisite/branch/commit/files/red/green/provider-call/idempotency/browser/security/deviation/risk. Stop for missing review/prerequisite, dirty overlap, required real provider/ADC, allowlist expansion, behavior/contract conflict. Never push/merge/deploy/apply/sign/publish/change secrets/access production/delete/destructive Git/touch `.superpowers/`.

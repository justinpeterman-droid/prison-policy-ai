# Claude Code Prompt 041 — OP-09: Build the .NET 8 Updater, Release Manifest, Access Signing, and Publication Pipeline

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **041**, task **OP-09: Build the .NET 8 Updater, Release Manifest, Access Signing, and Publication Pipeline**.

## Objective, outcome, and rationale

Build and locally verify a .NET 8 Windows updater, five-minute server-mediated update-grant API, strict signed-manifest contract, bitness-aware Access package definitions, release scripts, validation workflow, and protected publication workflow. The updater must receive credentials only through the AC-09 current-user named pipe, download only through authenticated Cloud Run API routes, authenticate provenance, install atomically, preserve the previous client, validate through `ValidateRelease`, and roll back automatically. This session may build/test local unsigned binaries, fictional fixtures, API code, and workflow definitions only—it must never invoke organizational signing, publish/upload anything, distribute an `.accde`, or access signing material.

## Repository, baseline, branch, and preflight

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Anchor baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-09-signed-access-updater`
- Commit: `feat: add signed access update and release pipeline`

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The anchor must be an ancestor of current reviewed `main`. Inspect `git log --oneline $TaskBase..HEAD`, all prerequisite plans/handoffs/reviews, and verify OP-01 through OP-08 plus AC-01/AC-09 outputs, supported matrix evidence, fake-API/COM validation, Access build/export consistency, and stable client-policy contracts exist and are reviewed. Branch from current `HEAD` using `git switch -c claude/op-09-signed-access-updater`. Stop on failed ancestry/review/prerequisites, conflict, existing branch, or overlapping/unsafe dirty work. Never reset, clean, restore, stash, overwrite, or delete user work.

## Required reading

Read `AGENTS.md`; approved deployment and Access User designs; roadmap global constraints, exact-nine client policy, update-grant/wire contracts, version projection, Gate E, task order, agent protocol; OP-01 approved `.accde` trust mechanism and EXT-16 policy; the approved managed-signing service interface/policy; OP-03 access-release identity outputs and `client-update-grant-key`; OP-04 API-only release storage/hostname; OP-08 version registry and backend descriptor; AC-01/AC-09 build, current-user named-pipe, fake-launcher, and `ValidateRelease` contracts; current identity/idempotency/session middleware, `/api/v1/client-policy`, and OpenAPI; and the detailed plan from the exact OP-09 heading to the OP-10 separator. `release/version.json`, its schema/hash, backend descriptor, Access source/build output, `backend/webapp/api_v1/client_policy.py`, and external evidence are consume-only.

## Exact allowed files

Create only:

- `access-updater/SLUT.AccessUpdater.sln`
- `access-updater/src/SLUT.AccessUpdater/SLUT.AccessUpdater.csproj`
- `access-updater/src/SLUT.AccessUpdater/packages.lock.json`
- `access-updater/src/SLUT.AccessUpdater/Program.cs`
- `access-updater/src/SLUT.AccessUpdater/Configuration/UpdateRequest.cs`
- `access-updater/src/SLUT.AccessUpdater/Configuration/UpdateRequestPipe.cs`
- `access-updater/src/SLUT.AccessUpdater/Download/ProtectedReleaseClient.cs`
- `access-updater/src/SLUT.AccessUpdater/Manifest/ReleaseManifest.cs`
- `access-updater/src/SLUT.AccessUpdater/Manifest/ManifestVerifier.cs`
- `access-updater/src/SLUT.AccessUpdater/Security/HashVerifier.cs`
- `access-updater/src/SLUT.AccessUpdater/Security/AuthenticodeVerifier.cs`
- `access-updater/src/SLUT.AccessUpdater/Install/AccessProcessCoordinator.cs`
- `access-updater/src/SLUT.AccessUpdater/Install/AtomicInstaller.cs`
- `access-updater/src/SLUT.AccessUpdater/Install/RollbackManager.cs`
- `access-updater/src/SLUT.AccessUpdater/Validation/ClientValidator.cs`
- `access-updater/src/SLUT.AccessUpdater/Telemetry/SafeUpdateLog.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/SLUT.AccessUpdater.Tests.csproj`
- `access-updater/tests/SLUT.AccessUpdater.Tests/packages.lock.json`
- `access-updater/tests/SLUT.AccessUpdater.Tests/ManifestVerifierTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/HashVerifierTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/AuthenticodeVerifierTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/AtomicInstallerTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/RollbackManagerTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/ClientValidatorTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/SafeUpdateLogTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/UpdateRequestPipeTests.cs`
- `access-updater/tests/SLUT.AccessUpdater.Tests/ProtectedReleaseClientTests.cs`
- `release/access-release.schema.json`
- `release/fixtures/access-release.fixture.json`
- `scripts/release/New-AccessReleaseManifest.ps1`
- `scripts/release/Test-AccessReleaseManifest.ps1`
- `scripts/release/Invoke-ManagedSigning.ps1`
- `scripts/release/Test-AccessSignatures.ps1`
- `scripts/release/Publish-AccessRelease.ps1`
- `.github/workflows/access-validate.yml`
- `.github/workflows/access-release.yml`
- `backend/identity/update_grants.py`
- `backend/webapp/api_v1/client_updates.py`
- `tests/unit/test_update_grants.py`
- `tests/integration/test_client_update_api.py`
- `tests/contract/test_client_update_contract.py`
- `tests/contract/test_client_release_policy.py`
- `tests/unit/test_access_release_workflow.py`
- `docs/runbooks/access-deploy-update-rollback.md`

Modify only:

- `.gitignore`
- `backend/webapp/api_v1/__init__.py`
- `openapi/access-v1.yaml`

No deletion is authorized. Do not modify `backend/webapp/api_v1/client_policy.py`, `release/version.json`, backend descriptor/provenance, Access `.accdb`/exports/build automation/tests, OP-03/OP-04 Terraform, or OP-08 workflows.

## Locked manifest, updater, and API interfaces

- Target `.NET 8`, `net8.0-windows`, self-contained `win-x64`; add `win-arm64` only if OP-01 inventory requires it. Access packages are `SLUT-Client-access32.accde` and/or `SLUT-Client-access64.accde` only for inventoried supported classes.
- Schema fields exactly: `schema_version`, `release_version`, `api_version`, `minimum_server_version`, `minimum_client_version`, `source_commit`, `version_registry_sha256`, `released_at`, `channel`, `release_notes_url`, `rollback_notes_url`, `manifest_signature`, `updater`, `packages`.
- Every updater/package descriptor has stable `package_id`, file name, positive byte size, SHA-256, signer subject, signer thumbprint, Windows architecture, and Access bitness. It has no bucket/object path, signed URL, or credential. `additionalProperties: false` at every object level; SemVer, API `v1`, 40-hex commit, 64-hex hashes/thumbprints, UTC time, HTTPS docs, at least one package.
- Fixture is entirely fictional: `0.0.0-test`, `https://example.invalid/`, zero-valued test hashes and clearly fixture-only trust/signature material.
- Implement the exact immutable C# records in OP-09 Step 5, replacing the old path concept with `PackageId`. `ManifestVerifier` performs strict JSON, detached CMS, Windows chain/expected publisher, schema/version, HTTPS documentation URL, package ID, and constant-time hash checks; injectable fake trust provider only for tests. Manifest/grant signer thumbprints are descriptive signed metadata, never trust anchors; trust comes only from the approved managed-signing/Windows policy and expected publisher identity.
- Implement `issue_update_grant(*, key: bytes, session_id: UUID, account_auth_version: int, release_version: str, package_id: str, manifest_sha256: str, now: datetime, nonce: UUID) -> str` and `verify_update_grant(raw_grant: str, *, key: bytes, now: datetime) -> UpdateGrantClaims`. Use canonical HMAC serialization, constant-time verification, dedicated `CLIENT_UPDATE_GRANT_KEY`, and exact five-minute expiry. Claims contain only those values plus issued/expiry; readable grants are never persisted or logged.
- `POST /api/v1/client-updates/grants` uses normal bearer auth plus `X-Client-Version`, `X-Request-ID`, `Idempotency-Key`, and a body closed to exactly `access_bitness` plus `windows_architecture`. Release-one OpenAPI enums include Access `x86|x64` and Windows `x64`; another architecture requires explicit OP-01 inventory approval and same-task schema/tests. Use `{"access_bitness":"x64","windows_architecture":"x64"}` as the exact fictional example and reject unsupported combinations before issue. Server-select one package from the current protected immutable signed manifest; require its release/API/minimum versions to match the runtime registry projection; never accept hash/package/release/signer input from Access. The first closed response contains exactly `update_grant`, `expires_at`, `release_version`, `package_id`, `manifest_sha256`, `manifest_size_bytes`, `signer_thumbprint`, and `one_time_value_unavailable: false`; an identical-key replay returns the same metadata, no grant, and `one_time_value_unavailable: true`; a changed payload conflicts.
- `GET /api/v1/client-updates/manifest`, `GET /api/v1/client-updates/manifest-signature`, and `GET /api/v1/client-updates/packages/{package_id}` authenticate only with `Authorization: UpdateGrant <grant>`. Every call verifies HMAC/expiry, reloads live session/account, checks auth version, and serves only the bound immutable release/package/hash through API-only release-bucket read. Permit bounded identical-object/range resume within five minutes. Never redirect or expose bucket/object path, signed URL, storage credential, grant, bearer, actor/session ID, or PII.
- The helper starts with exactly two positional command-line arguments: random pipe name and request ID. It creates one named-pipe server using .NET `PipeOptions.CurrentUserOnly`; accepts one four-byte-length-prefixed UTF-8 closed JSON message no larger than 64 KiB; rejects timeout, second connection, trailing/oversized/unknown data; then closes. No update grant/bearer, endpoint, install path, person/report value, or other sensitive value enters arguments, environment, registry, clipboard, disk, or logs.
- `UpdateRequest` has exactly `schema_version`, `api_base_url`, `update_grant`, `expires_at`, `release_version`, `package_id`, `manifest_sha256`, `manifest_size_bytes`, `signer_thumbprint`, `access_bitness`, `windows_architecture`, `current_client_version`, `install_path`, and `request_id`. Derive only the three fixed API paths from validated HTTPS `api_base_url`; disable redirects; authenticate only with UpdateGrant; enforce byte/time/content/hash bounds; use unique LocalAppData temp; clear grant references before logging.
- Reject altered bytes/claims, size/hash mismatch, untrusted or wrong publisher, signer metadata mismatch, expired grant, revoked session/auth-version change, wrong package, traversal, API origin/path substitution, non-HTTPS, and extra request/manifest properties.
- Verify manifest/signatures/size/hash/publisher before install. Ask Access to save/close with bounded wait and no silent kill. Candidate/current/previous share a volume; atomically move current→previous and candidate→current; preserve previous until next accepted release. Through COM invoke AC-09 `ValidateRelease()` and strictly parse only its safe version/source/API/signature/startup JSON; rollback and revalidate prior on failure.
- Exit codes exactly: `0`, `10`, `20`, `21`, `22`, `23`, `24`, `25`, `26`, `27` with meanings from the plan.
- Safe log only UTC, releases, stage, exit, request ID, hash prefix, elapsed. Never pipe name/payload, URL query/fragment, bearer/update grant, bucket/object, person/report/session/account/device/profile/install path/machine/file content/signing private data; bounded LocalAppData outside trusted application directory.
- Generate manifest solely from read-only validated `release/version.json` and expected hash, actual artifacts, Access metadata, and backend descriptor; no override/second notes source. Create detached CMS `access-release.json.p7s`.
- Managed-signing script submits digest/reference using ephemeral WIF or approved interactive auth; no local PFX/key import, no key material. Publish script revalidates, writes only immutable versioned signed user artifacts/manifest/notes, preserves previous, and requires external approval.
- `/api/v1/client-policy` remains exactly the nine required public safe fields for every caller and contains no package/hash/signer/grant/URL metadata. Selected package metadata exists only in the authenticated grant response and signed manifest. Below-minimum clients can authenticate/read/recover/export but mutations return `client_upgrade_required`.
- Register the new blueprint in `backend/webapp/api_v1/__init__.py`, document the closed schemas/security/range/content rules in OpenAPI, and keep package delivery behind the managed hostname/API-mediated private bucket boundary.

## Workflow boundaries

- `access-validate.yml` uses an approved Windows/Access runner later to check export consistency, VBA references/unsafe declarations/secrets, local unsigned `.accde`, fake-API/COM/named-pipe/`ValidateRelease` smoke, updater build/test/RIDs; any uploaded test evidence is conspicuously unsigned, fictional, short-lived, and unusable as a release.
- `access-release.yml` is manual only, environment exactly `access-release`, requires externally verified EXT-16/two reviewers/`refs/heads/main`, and uses only `vars.GCP_ACCESS_RELEASE_WIF_PROVIDER` plus `vars.GCP_ACCESS_RELEASE_SERVICE_ACCOUNT` matching OP-03.
- Before any release signing/publication action, the workflow requires externally reviewed actual signed helper/ACCDE, complete supported workstation/bitness matrix, endpoint-protection, trusted-location/ACL, protected-update-API, and managed-signing evidence. It then consumes approved backend/client evidence and exact registry hash, rebuilds/tests, requests managed signing without key access, validates/publishes immutable objects. It never creates/weakens environment policy, runs on push, uses deploy/apply/rollback identity, or reads application secrets.
- Pin every third-party action to a reviewed full SHA.

## TDD and local-only verification

1. Write the exact Python contract/workflow tests from OP-09 Step 1; update-grant unit, PostgreSQL API integration, and OpenAPI contract tests—including proof that the raw grant is absent from idempotency storage and every database value—and all named C# manifest, protected-client, pipe, negative, atomic, and log tests from Step 2 before implementation.
2. Run:

```powershell
python -m pytest tests/contract/test_client_release_policy.py -q
python -m pytest tests/unit/test_update_grants.py tests/integration/test_client_update_api.py tests/contract/test_client_update_contract.py -q
dotnet test access-updater/SLUT.AccessUpdater.sln --configuration Release
```

Expected red: schema/fixture, update-grant module/routes, and solution absent. Do not count unrelated runtime/tool failure as the expected red; report missing prerequisites separately.
3. Implement grant/API, schema/fixture, updater, tests, scripts, workflows, OpenAPI contract, and runbook in plan order. Preserve the exact-nine client-policy implementation unchanged.
4. Run exactly:

```powershell
dotnet restore access-updater/SLUT.AccessUpdater.sln --locked-mode
dotnet build access-updater/SLUT.AccessUpdater.sln --configuration Release --no-restore
dotnet test access-updater/SLUT.AccessUpdater.sln --configuration Release --no-build
dotnet publish access-updater/src/SLUT.AccessUpdater/SLUT.AccessUpdater.csproj --configuration Release --runtime win-x64 --self-contained true --no-build
python -m json.tool release/access-release.schema.json | Out-Null
python -m json.tool release/fixtures/access-release.fixture.json | Out-Null
python -m pytest tests/contract/test_client_release_policy.py tests/unit/test_access_release_workflow.py -q
python -m pytest tests/unit/test_update_grants.py tests/integration/test_client_update_api.py tests/contract/test_client_update_contract.py -q
powershell -File scripts/release/New-AccessReleaseManifest.ps1 -FixtureMode
powershell -File scripts/release/Test-AccessReleaseManifest.ps1 -FixtureMode
python scripts/ci/check_workflow_pins.py
git diff --check
```

Expected: locked build/tests/publish-to-local-output, fictional manifest/signature checks, grant/API/OpenAPI contracts, exact-nine client policy, and workflow pins pass; no Access package is distributed, managed signing called, or artifact published/uploaded. Do not run `access-release.yml`, managed signing without fixture mode, publication, real Access COM, cloud/storage endpoints, or an organizational certificate.

## External gates and absolute stop boundary

Before editing, require reviewed evidence of the agency-approved `.accde` trust mechanism, the approved managed-signing service interface/policy, and verified EXT-16 protected-environment policy. These are design/authorization prerequisites; never invent substitutes. Actual signed helper/ACCDE artifacts, completed workstation/bitness matrix, endpoint-protection result, narrow trusted-location/ACL result, and deployed protected-endpoint evidence may remain pending while this task implements and tests the local unsigned helper, fictional fixtures, API, and workflows. They are mandatory hard gates before the release workflow can declare readiness or sign/publish, and the workflow/runbook must enforce that distinction. Even when prerequisites are verified, this Claude Code session must never export/read a private key, invoke a signing service, create a certificate, publish/upload, obtain release WIF, use real protected URLs/tokens, or package/distribute user artifacts. Production versioning is externally reviewed; do not edit it.

## Security/privacy and non-goals

No editable `.accdb`, source export, fixture, build intermediate, signing key/private material, token, credential, personal/report data, or local path identity enters a user package/log. Do not update Office, change Access source, change the exact-nine client policy, create cloud resources, broaden existing authorization, or redesign AC-09 IPC. Implement only the declared update-grant authorization boundary. No push, merge, deploy, workflow dispatch, Terraform apply, signing, publication/upload, secret change, cloud/production access, or destructive Git/filesystem action.

Explicitly—even though this task designs signing and publication workflows—do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Python and C# expected red states were observed first.
- [ ] Strict schema/fictional fixture and exact immutable records exist.
- [ ] Grant first/replay semantics, five-minute scope, live session/auth-version revalidation, and exact Bearer/UpdateGrant routes pass.
- [ ] Named pipe is current-user-only/one-message/64 KiB; only pipe name and request ID enter arguments; all sensitive surfaces are redacted.
- [ ] Client policy remains exactly nine fields; selected package metadata exists only in the closed grant response/signed manifest; no storage path/redirect/credential is exposed.
- [ ] All tamper/trust/path/HTTPS/expiry/revocation/wrong-package/extra-field tests fail closed.
- [ ] Atomic install, validation, rollback, exit codes, and safe telemetry are exact.
- [ ] Registry remains read-only sole source; scripts revalidate all provenance/signatures.
- [ ] Workflows are pinned, manual/protected where required, dedicated-WIF, and no-key.
- [ ] Local unsigned implementation is clearly separated from mandatory signed-artifact/matrix/endpoint-protection release-readiness evidence.
- [ ] Below-minimum recovery/read/export remains possible while mutation is blocked.
- [ ] All local checks pass without Access COM, organization signing, or publication.
- [ ] Only exact allowed files changed and exact one-commit message used.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; run the workflow-pin check and inspect task changes/output for keys/PFX, credentials, real URLs/data, command-line secrets, production versions, unsigned publication, generated `bin/obj/publish`, or editable Access artifacts. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'access-updater/SLUT.AccessUpdater.sln'
    'access-updater/src/SLUT.AccessUpdater/SLUT.AccessUpdater.csproj'
    'access-updater/src/SLUT.AccessUpdater/packages.lock.json'
    'access-updater/src/SLUT.AccessUpdater/Program.cs'
    'access-updater/src/SLUT.AccessUpdater/Configuration/UpdateRequest.cs'
    'access-updater/src/SLUT.AccessUpdater/Configuration/UpdateRequestPipe.cs'
    'access-updater/src/SLUT.AccessUpdater/Download/ProtectedReleaseClient.cs'
    'access-updater/src/SLUT.AccessUpdater/Manifest/ReleaseManifest.cs'
    'access-updater/src/SLUT.AccessUpdater/Manifest/ManifestVerifier.cs'
    'access-updater/src/SLUT.AccessUpdater/Security/HashVerifier.cs'
    'access-updater/src/SLUT.AccessUpdater/Security/AuthenticodeVerifier.cs'
    'access-updater/src/SLUT.AccessUpdater/Install/AccessProcessCoordinator.cs'
    'access-updater/src/SLUT.AccessUpdater/Install/AtomicInstaller.cs'
    'access-updater/src/SLUT.AccessUpdater/Install/RollbackManager.cs'
    'access-updater/src/SLUT.AccessUpdater/Validation/ClientValidator.cs'
    'access-updater/src/SLUT.AccessUpdater/Telemetry/SafeUpdateLog.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/SLUT.AccessUpdater.Tests.csproj'
    'access-updater/tests/SLUT.AccessUpdater.Tests/packages.lock.json'
    'access-updater/tests/SLUT.AccessUpdater.Tests/ManifestVerifierTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/HashVerifierTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/AuthenticodeVerifierTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/AtomicInstallerTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/RollbackManagerTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/ClientValidatorTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/SafeUpdateLogTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/UpdateRequestPipeTests.cs'
    'access-updater/tests/SLUT.AccessUpdater.Tests/ProtectedReleaseClientTests.cs'
    'release/access-release.schema.json'
    'release/fixtures/access-release.fixture.json'
    'scripts/release/New-AccessReleaseManifest.ps1'
    'scripts/release/Test-AccessReleaseManifest.ps1'
    'scripts/release/Invoke-ManagedSigning.ps1'
    'scripts/release/Test-AccessSignatures.ps1'
    'scripts/release/Publish-AccessRelease.ps1'
    '.github/workflows/access-validate.yml'
    '.github/workflows/access-release.yml'
    'backend/identity/update_grants.py'
    'backend/webapp/api_v1/client_updates.py'
    'tests/unit/test_update_grants.py'
    'tests/integration/test_client_update_api.py'
    'tests/contract/test_client_update_contract.py'
    'tests/contract/test_client_release_policy.py'
    'tests/unit/test_access_release_workflow.py'
    'docs/runbooks/access-deploy-update-rollback.md'
    '.gitignore'
    'backend/webapp/api_v1/__init__.py'
    'openapi/access-v1.yaml'
)
$changed = @(
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
) | Sort-Object -Unique
$unexpected = $changed | Where-Object { $_ -notin $allowed -and $_ -notlike '.superpowers/*' }
if ($unexpected) { $unexpected; throw 'Changed-file allowlist violation.' }
git diff --name-status $TaskStart
git diff --check
git add -A -- $allowed
$staged = @(git diff --cached --name-only) | Sort-Object -Unique
$unexpectedStaged = $staged | Where-Object { $_ -notin $allowed }
if ($unexpectedStaged) { $unexpectedStaged; throw 'Staged-file allowlist violation.' }
git diff --cached --name-status
git diff --cached --check
git commit -m "feat: add signed access update and release pipeline"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including five-minute grant/one-time replay, exact-nine policy, protected routes/storage mediation, named-pipe request, manifest/updater/exit-code/workflow contracts, and exact locally tested RIDs/bitness; security/privacy results plus confirmation that no organization signing/publication/COM/cloud operation occurred; assumptions, risks, deviations, NOT RUN items with reasons, and remaining signed-artifact/matrix/endpoint-protection/release gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published/uploaded, secrets-changed, or run against/accessed in production. Independent specification review precedes code-quality review.

Stop without committing if the approved `.accde` trust mechanism, managed-signing interface/policy, or EXT-16 authorization is unproven; a real private key/token would be needed; even the local baseline target cannot be derived; release data conflicts with registry/backend evidence; client recovery would be blocked; a test cannot run safely; or any prohibited action is required. A pending completed production matrix or signed/endpoint-protection artifact result must be recorded as a release-readiness gate, not misreported as a reason to skip safe local unsigned implementation. Never substitute an assumed Authenticode mechanism for proven Access trust.

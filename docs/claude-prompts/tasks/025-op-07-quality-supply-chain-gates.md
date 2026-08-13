# Claude Code Prompt 025 — OP-07: Enforce Backend, Container, SBOM, Vulnerability, and Pages Quality Gates

Copy everything below this line into a fresh Claude Code session.

---

Implement sequence **025**, task **OP-07: Enforce Backend, Container, SBOM, Vulnerability, and Pages Quality Gates**.

## Objective, outcome, and rationale

Replace best-effort checks with deterministic required backend/container/security gates and an exact Pages artifact allowlist. Produce hash-locked developer dependencies, reproducible static/test checks, a digest-pinned non-root image, SPDX SBOM and vulnerability contracts, full-SHA workflow pinning, and a Pages distribution that cannot expose backend, Access, infrastructure, test, release, or operational material.

## Repository, baseline, branch, and preflight

- Root: `C:\Users\justi\OneDrive\Documents\New project\prison-policy-ai`
- Anchor baseline: `6692b10e4f2aae3f76fd0f32e04fdf3a1180362d`
- Branch: `claude/op-07-quality-supply-chain`
- Commit: `ci: enforce backend container and pages release gates`

```powershell
$TaskBase = "6692b10e4f2aae3f76fd0f32e04fdf3a1180362d"
git status --short
if ((git branch --show-current) -ne 'main') { throw "Start from current reviewed main." }
git rev-parse HEAD
git merge-base --is-ancestor $TaskBase HEAD
$TaskStart = (git rev-parse HEAD).Trim()
```

The anchor must be an ancestor of current reviewed `main`. Inspect `git log --oneline $TaskBase..HEAD`, prerequisite plans/handoffs, and verify every intervening commit is reviewed, backend contracts and OP-01 through OP-06 outputs exist, and no conflict exists. Branch from current `HEAD` using `git switch -c claude/op-07-quality-supply-chain`. Stop if the branch exists, ancestry/reviews/prerequisites fail, or dirty work overlaps/makes switching unsafe. Leave unrelated user work untouched. Never reset, clean, restore, stash, overwrite, or delete it.

## Required reading

Read `AGENTS.md`; approved deployment design; roadmap global constraints/program gates/agent protocol; OP-01 Pages safety invariant; OP-06 Docker/runtime contract; existing workflows, Dockerfile, `.dockerignore`, dependency files, pytest configuration, and image optimizer; and the detailed plan from the exact OP-07 heading through the OP-08 separator.

## Exact allowed files

Create only:

- `requirements-dev.in`
- `requirements-dev.lock`
- `pyproject.toml`
- `.github/workflows/backend-quality.yml`
- `.github/workflows/container-security.yml`
- `scripts/ci/check_sensitive_output.py`
- `scripts/ci/check_workflow_pins.py`
- `scripts/ci/validate_sbom.py`
- `scripts/ci/build_pages_dist.py`
- `tests/unit/test_ci_release_gates.py`
- `tests/unit/test_pages_publish_scope.py`
- `tests/unit/test_container_contract.py`
- `docs/operations/software-supply-chain.md`
- `docs/operations/vulnerability-exceptions.md`

Modify only:

- `.github/workflows/tests.yml`
- `.github/workflows/codacy.yml`
- `.github/workflows/pages.yml`
- `Dockerfile`
- `.dockerignore`

No deletion is authorized. Generated `pages-dist/`, SBOM/report outputs, caches, virtual environments, and images are test artifacts and must not be committed.

## Locked interfaces

- Required status checks exactly: `backend-quality-3.12`, `backend-quality-3.14`, `postgres-integration-17`, `openapi-contract`, `security-redaction`, `container-build`, `sbom`, `container-vulnerability`, `terraform-static`, `pages-scope`.
- No required job uses `continue-on-error: true`. Every third-party action uses a reviewed full 40-character commit SHA.
- `requirements-dev.in` references application requirements plus pytest, coverage, Ruff, mypy, pip-audit, pip-tools, OpenAPI validation, PostgreSQL support. `requirements-dev.lock` pins/hashes every transitive dependency.
- `pyproject.toml` provides Ruff format/lint, mypy Python 3.12 plus explicit overrides, and existing pytest paths/markers while preserving `pytest.ini`.
- CI runs Python 3.12 and 3.14, PostgreSQL 17 integration, OpenAPI, security/redaction, and existing policy/report/Word regressions without production credentials.
- Base image is the reviewed Chainguard Python 3.14 runtime `chainguard/python@sha256:8fab86fb761aeb18723f4f1b1baa330bd59d64e92abdc5b980d1bbd9399c297d`, resolved from its public Docker Registry manifest on 2026-08-13 after the current Docker Official `python:3.14-slim` digest was found to retain fixable Critical/High CVEs. Do not retain a symbolic digest or tag-only reference in the implementation. The multi-stage image installs runtime-only dependencies, runs non-root, has a health check, retains command override, and excludes Access/Terraform/release/test/operational sources. CI must continue to reject any fixable Critical/High runtime finding and validate the exact runtime digest's SBOM and signature/provenance before release.
- Sensitive-output validator scans tracked text/test output/SARIF/SBOM/logs for forbidden secret/PII keys with only explicit fictional allowlists.
- SBOM validator requires SPDX metadata, exact image digest, package licenses, and no environment values/file contents. Container workflow builds without pushing, scans OS/Python/Docker/IaC, fails on fixable Critical/High, uploads safe artifacts, and provides provenance.
- Codacy is supplemental/non-authoritative and may not mask native required-check failure.
- `scripts/ci/build_pages_dist.py` contains exact `ALLOWED = ("index.html", "frontend/forms")`, builds a fresh `pages-dist`, rejects symlinks/unexpected/source-map/secret-like files. Pages uploads only `pages-dist`.
- Vulnerability exceptions initially say exactly `No active exceptions.`; future schema requires ID, digest/package, severity/exploitability, owner role, issue, compensating control, approval date, fixed expiry—no blanket ignore.

## TDD and local verification

1. Write `test_pages_publish_scope.py` exactly from OP-07 Step 1, then implement equally strict `test_ci_release_gates.py` and `test_container_contract.py` from that step before production changes.
2. Run:

```powershell
python -m pytest tests/unit/test_pages_publish_scope.py tests/unit/test_ci_release_gates.py tests/unit/test_container_contract.py -q
```

Expected red: Pages scope is too broad, workflows/scripts are absent, and base image is mutable. Do not count unrelated collection failures.
3. Generate the hashed lock only with the plan commands. Because pip-tools classifies `pip` and `setuptools` as unsafe and otherwise omits them, use `--allow-unsafe` with `--generate-hashes` so those declared build tools are present and hashed in the lock. Network access to official package/provider registries is acceptable; credentials and private indexes are not.
4. Resolve/review the reconciled hardened Python 3.14 base manifest rather than inventing a digest.
5. Implement checks/workflows/image/Pages/governance, then run:

```powershell
python scripts/ci/check_workflow_pins.py
python scripts/ci/build_pages_dist.py
python scripts/ci/check_sensitive_output.py --paths pages-dist
python -m ruff check backend tests scripts
python -m ruff format --check backend tests scripts
python -m mypy backend
python -m pytest tests/unit -q
python -m pytest tests/integration tests/contract tests/security -q
python scripts/optimize_images.py --check
docker build --tag prison-policy-ai:op07-local .
python scripts/ci/validate_sbom.py --image prison-policy-ai:op07-local --output tests/output/sbom-op07.spdx.json
python -m pytest tests/unit/test_pages_publish_scope.py tests/unit/test_ci_release_gates.py tests/unit/test_container_contract.py -q
git diff --check
```

Expected: all quality gates pass locally, image is non-root, SBOM validates, Pages contains only the allowlist, and no image is pushed. If the plan's toolchain is unavailable, report the blocker; do not substitute an unreviewed tool or fake output.

## External gates and local-only boundary

Workflow branch protection/status requirements are configured externally by administrators, not here. This task designs workflows and runs equivalent local commands only. Do not trigger GitHub Actions, upload artifacts to GitHub, authenticate to Google, query production, push an image, attest/publish remotely, or change repository settings. Dependency and base-manifest downloads use only public official distribution sources.

## Security/privacy and non-goals

All fixtures are fictional. No credentials, service-account/signing keys, real report/roster data, employee/inmate identifiers, PINs/tokens, or environment values may enter workflows, logs, SBOMs, reports, or Pages. Do not change application behavior, Terraform resources, release workflows, or Access source. Do not grant credentials to CI. No push, merge, deploy, workflow invocation, image push, Terraform apply, sign/publish, secret change, cloud/production access, or destructive Git/filesystem action.

Explicitly: do not push, merge, deploy, run Terraform apply, sign, publish, access or change secrets, access production, or perform destructive actions.

## Acceptance checklist

- [ ] Named tests were red first for the expected reasons.
- [ ] Dev lock is complete, hashed, reproducible, and documented.
- [ ] Ten exact required checks exist and fail closed with full-SHA actions.
- [ ] Base image digest is officially resolved/reviewed; runtime is minimal/non-root/healthy.
- [ ] SBOM, vulnerability, workflow-pin, and sensitive-output validators are strict.
- [ ] Pages artifact has exactly root `index.html` and `frontend/forms/` and no forbidden source.
- [ ] Codacy is explicitly supplemental; exception governance is complete with no active exception.
- [ ] Full local suite passes; no image/workflow/artifact was pushed or invoked remotely.
- [ ] Only exact allowed paths changed and exact one-commit message used.

## Diff, commit, and handoff

Check the union of unstaged, staged, and untracked paths against the exact allowlist, ignoring only user-owned `.superpowers/*`; run the workflow pin validator and inspect task changes for credentials, real data, mutable actions/images, `continue-on-error`, broad Pages scope, and generated artifacts. Then stage only exact allowlisted paths and re-check the index:

```powershell
$allowed = @(
    'requirements-dev.in'
    'requirements-dev.lock'
    'pyproject.toml'
    '.github/workflows/backend-quality.yml'
    '.github/workflows/container-security.yml'
    'scripts/ci/check_sensitive_output.py'
    'scripts/ci/check_workflow_pins.py'
    'scripts/ci/validate_sbom.py'
    'scripts/ci/build_pages_dist.py'
    'tests/unit/test_ci_release_gates.py'
    'tests/unit/test_pages_publish_scope.py'
    'tests/unit/test_container_contract.py'
    'docs/operations/software-supply-chain.md'
    'docs/operations/vulnerability-exceptions.md'
    '.github/workflows/tests.yml'
    '.github/workflows/codacy.yml'
    '.github/workflows/pages.yml'
    'Dockerfile'
    '.dockerignore'
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
git commit -m "ci: enforce backend container and pages release gates"
git status --short
git show --stat --oneline HEAD
git diff --name-status $TaskStart HEAD
```

Return: task ID/title and branch; starting SHA, final SHA, commit SHA, and exact commit message; complete changed/deleted file list; red, focused, and regression commands with exit results; unstaged/staged allowlist results plus both `git diff --check` and `git diff --cached --check` results; interfaces produced and consumed, including exact pins/status checks/image digest/Pages contents and vulnerability status/exceptions; security/privacy and sensitive-output results plus confirmation of no remote action; assumptions, risks, deviations, NOT RUN items with reasons, and remaining external gates; and explicit confirmation that nothing was pushed, merged, deployed, applied, workflow-invoked, migrated, traffic-shifted, signed, published, secrets-changed, or run against/accessed in production. Independent specification review precedes code-quality review.

Stop without committing if an action/base/dependency pin cannot be verified, a fixable Critical/High remains, SBOM cannot bind the digest, required CI needs credentials, Pages cannot be made exact, prerequisite checks are absent, or a prohibited operation is required. Never waive/ignore a gate to make it green.

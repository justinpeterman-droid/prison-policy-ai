# Quality Baseline Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the existing Ruff and mypy defects that currently block OP-07's required quality gates, without weakening those gates or changing application contracts.

**Architecture:** Treat lint and typing diagnostics as real source defects. Fix import placement/order, unused/redefined symbols, syntax-style violations, and undefined names in the source that produces them; preserve externally visible interfaces. Add or extend focused regression tests only when a typing/lint correction changes a branch or data-flow edge, then run the complete required quality commands from an OP-07 hash-locked environment.

**Tech Stack:** Python 3.12/3.14, Ruff, mypy, pytest, Flask, SQLAlchemy, Pydantic.

## Global Constraints

- Do not add `exclude`, blanket `ignore`, broad per-file ignores, `# noqa`, or `# type: ignore` solely to hide a pre-existing defect.
- Retain OP-07's required commands exactly: `python -m ruff check backend tests scripts`, `python -m ruff format --check backend tests scripts`, and `python -m mypy backend`.
- Preserve all reviewed identity, audit, idempotency, report revision, AI-job, telemetry, and API/OpenAPI behavior; no runtime simplification just to satisfy types.
- Use only fictional test data. Do not access cloud, production, secrets, real rosters, reports, or PINs.
- Every changed behavior receives a focused test before its implementation; formatting-only edits require the relevant Ruff command as evidence.
- The resulting branch must be cleanly reviewable and run the same focused/unit/security suites before OP-07 resumes.

---

### Task 1: Correct Ruff violations at their source

**Files:**
- Modify only the files reported by `python -m ruff check backend tests scripts`; no configuration suppression is allowed.
- Test: existing focused test file(s) for each behavior-affecting correction.

**Interfaces:**
- Consumes: current reviewed runtime/API/service behavior and Ruff's reported I001, E501, E/F findings.
- Produces: zero Ruff diagnostics across `backend`, `tests`, and `scripts` without changed public contracts.

- [ ] **Step 1: Capture the failing source inventory**

Run:

```powershell
python -m ruff check backend tests scripts --output-format=concise | Tee-Object -FilePath tests/output/quality-baseline-ruff.txt
python -m ruff format --check backend tests scripts
```

Expected: the existing inventory is nonzero; preserve the command output as local evidence only and do not commit it.

- [ ] **Step 2: Repair imports and lexical style mechanically**

For each I001/E401/E402/E501/E701/E702/E741/F541 entry, move imports to legal module scope, split one-line statements/imports, wrap literals without changing values, and replace ambiguous one-character names with semantically equivalent local names. Re-run Ruff after each cohesive file group.

- [ ] **Step 3: Repair semantic Ruff findings with tests first**

For every F401/F811/F821/F841 finding, first run the smallest existing test that executes the affected module. Remove only genuinely unused imports/locals, rename accidental redefinitions, and define/fix the referenced symbol at its intended ownership layer. If behavior changes, write a focused regression assertion before the source correction.

- [ ] **Step 4: Verify the Ruff gate**

Run:

```powershell
python -m ruff check backend tests scripts
python -m ruff format --check backend tests scripts
python -m pytest tests/unit tests/security -q
```

Expected: both Ruff commands exit zero; tests prove no behavior regression.

- [ ] **Step 5: Commit the isolated lint correction**

```powershell
git add backend tests scripts
git commit -m "fix: remediate backend lint baseline"
```

### Task 2: Correct mypy defects in backend interfaces and data flow

**Files:**
- Modify only backend modules reported by `python -m mypy backend`, plus focused tests when behavior needs proof.
- Test: focused existing unit/integration tests for affected service/API boundaries.

**Interfaces:**
- Consumes: reviewed call signatures, SQLAlchemy model nullability, request DTOs, external-client adapters, and immutable result types.
- Produces: `python -m mypy backend` exits zero with meaningful source annotations and guards.

- [ ] **Step 1: Capture the failing type inventory**

Run:

```powershell
python -m mypy backend | Tee-Object -FilePath tests/output/quality-baseline-mypy.txt
```

Expected: current errors are grouped by actual `arg-type`, `assignment`, `attr-defined`, `union-attr`, `operator`, `return-value`, and overload categories. Do not commit the output.

- [ ] **Step 2: Fix nullable and union data-flow failures**

For every `union-attr`, optional assignment, or return-value failure, establish the domain invariant at the boundary with a safe explicit guard or a correctly typed optional return. Preserve existing concealment/error behavior and cover the branch with the nearest focused test.

- [ ] **Step 3: Fix argument, model, and adapter type mismatches**

For every `arg-type`, `attr-defined`, overload, and operator failure, use the reviewed DTO/model/protocol type rather than casting. Introduce a narrow protocol or typed helper only when it mirrors an existing runtime interface. Never use `Any` or a blanket `cast` to erase an incompatibility.

- [ ] **Step 4: Add missing local annotations**

For `var-annotated` and assignment issues, annotate values at creation using their actual immutable DTO, SQLAlchemy result, collection, or scalar type. Keep Pydantic/SQLAlchemy runtime behavior unchanged.

- [ ] **Step 5: Verify type and behavioral gates**

Run:

```powershell
python -m mypy backend
python -m ruff check backend tests scripts
python -m pytest tests/unit tests/security -q
python -m pytest tests/integration tests/contract tests/security -q
```

Expected: mypy and Ruff exit zero. Any integration dependency failure is investigated against the predecessor before being classified external.

- [ ] **Step 6: Commit the isolated type correction**

```powershell
git add backend tests
git commit -m "fix: remediate backend typing baseline"
```

### Task 3: Independently verify the quality baseline and OP-07 resumption readiness

**Files:**
- No production changes unless a reviewer identifies a concrete defect from Tasks 1–2.
- Test: complete quality command sequence.

**Interfaces:**
- Consumes: Tasks 1–2 and OP-07's hash-locked toolchain.
- Produces: review evidence that OP-07 can enforce rather than hide the gates.

- [ ] **Step 1: Run the complete local static-quality sequence**

Run in the lock-verified Python environment:

```powershell
python -m ruff check backend tests scripts
python -m ruff format --check backend tests scripts
python -m mypy backend
python -m pytest tests/unit -q
python -m pytest tests/integration tests/contract tests/security -q
git diff --check
```

- [ ] **Step 2: Perform independent review**

Review the complete commit range for (a) configuration suppression, unsafe casts, or lost guards; (b) API/audit/transaction regressions; and (c) test coverage for all non-mechanical corrections. A P0/P1 finding enters the normal fix/re-review loop before OP-07 resumes.

- [ ] **Step 3: Record the prerequisite completion**

Append a concise evidence entry to the implementation checklist indicating that the quality baseline is verified. Do not mark OP-07 complete until its container/SBOM and workflow work is itself implemented and independently reviewed.

## Self-Review

- Spec coverage: Task 1 covers every current Ruff class; Task 2 covers every current mypy class without hiding diagnostics; Task 3 proves the exact OP-07 quality commands.
- Placeholder scan: no suppression, deferred implementation, or unspecified behavior is used as a step.
- Type consistency: corrections use existing reviewed interfaces rather than alternative parallel types.

## Execution Handoff

Execute this prerequisite using subagent-driven development: one fresh implementation/review loop per task, followed by an independent whole-range review before OP-07 resumes.

# Handoff Runbook

Tasks that need **live access** (GCP `gcloud`/ADC, Cloud Run, GitHub repo
settings) which the coding session couldn't do itself. Everything here is
prepared in code; this is the "press the buttons" list. Ordered by priority.

Project: `gen-lang-client-0968389176` · Region: `us-central1` · Service: `prison-policy-ai`

Two open PRs:
- **PR #22** (`claude/claude-md-docs-2cv50x`) — CLAUDE.md, security/quality hardening, test + eval harness, and the policy-chat citation/grounding + retrieval rework. All real checks green; ready to merge.
- **PR #23** (`claude/wif-keyless-deploy`) — keyless deploy (WIF). **Draft — do the GCP setup in §3 first.**

> The only red check on PR #22 is `github-advanced-security`, a GitHub-side
> infrastructure failure (its agentic scanner requests an unsupported model and
> exits). It is not caused by the diff and is not fixable from the repo — see §6
> to silence it. CodeQL/pytest/Codacy are green.

---

## 1. Fix the feedback widget — set `GITHUB_TOKEN` (highest priority; user-facing)

The 💬 Feedback widget fails because the Cloud Run service has no `GITHUB_TOKEN`,
so `/api/feedback` can't open issues. The deploy workflow never sets it. Add it:

```bash
# Option A — Secret Manager (preferred: keeps the token out of the service config)
printf '<TOKEN>' | gcloud secrets create github-feedback-token \
  --data-file=- --project gen-lang-client-0968389176
gcloud run services update prison-policy-ai --region us-central1 \
  --project gen-lang-client-0968389176 \
  --update-secrets GITHUB_TOKEN=github-feedback-token:latest

# Option B — plain env var
gcloud run services update prison-policy-ai --region us-central1 \
  --project gen-lang-client-0968389176 \
  --update-env-vars GITHUB_TOKEN=<TOKEN>
```

Token: a fine-grained PAT with **Issues: Read and write** on
`justinpeterman-droid/prison-policy-ai` (or a classic PAT with `repo`).
Verify: submit feedback in the app → a new issue should appear on the repo.

---

## 2. Run the policy-chat eval baseline (needs GCP ADC)

Establishes the baseline for the RAG improvements just landed (citation grounding,
retrieval augment/trim). Do this from the repo root with ADC available
(`gcloud auth application-default login` for the project, or a service-account
JSON in `GOOGLE_APPLICATION_CREDENTIALS`):

```bash
pip install -r requirements.txt
PYTHONPATH=. python3 tests/eval/run_eval.py            # full scorecard
PYTHONPATH=. python3 tests/eval/run_eval.py --gate-only
```

Output: a scorecard on stdout + `tests/eval/output/results.json`. **Share the
scorecard** so the next RAG lever (semantic reranker, extractive segments) can be
targeted against real numbers. Tune `tests/eval/cases.jsonl` `expect_sources` to
the real doc titles once you see them in the results.

Also useful (report pipeline, needs ADC):
```bash
PYTHONPATH=. python3 tests/test_pipeline.py --all --compare
```

---

## 3. PR #23 — Workload Identity Federation setup, then merge

Do the one-time GCP setup, set the two repo secrets, then mark PR #23 ready and
merge. **The full `gcloud` runbook is in the PR #23 description** (pool + provider
+ SA impersonation). Summary:

1. Create the deploy service account + grant deploy roles.
2. Create the Workload Identity Pool + GitHub OIDC provider (scoped to this repo).
3. Bind the repo to impersonate the SA.
4. Set repo secrets `GCP_WIF_PROVIDER` and `GCP_DEPLOY_SA` (Settings → Secrets → Actions).
5. Merge PR #23. After the next deploy is green, **delete the old `GCP_SA_KEY`
   secret** and revoke that service-account key.

Do NOT merge PR #23 before steps 1–4, or the deploy breaks.

---

## 4. Verify the Gemini model in prod (#9)

The default is now `gemini-flash-latest` (auto-tracks the current GA Flash). If
you want a frozen version, set it explicitly:

```bash
gcloud run services update prison-policy-ai --region us-central1 \
  --project gen-lang-client-0968389176 \
  --update-env-vars GENERATION_MODEL=gemini-3.6-flash
```

Also confirm the model **location** serves your chosen id (chat uses the `global`
endpoint via `GCP_MODEL_LOCATION`/`AGENT_BUILDER_LOCATION`).

---

## 5. Merge PR #22 and deploy

PR #22 is green (except the infra check in §6). Merge it. Deploy happens
automatically on push to `main` via `.github/workflows/cloud-run.yml` — **note
that workflow still uses the old `GCP_SA_KEY` until PR #23 is merged.** Manual
deploy if needed:

```bash
gcloud run deploy prison-policy-ai --source . --region us-central1 \
  --project gen-lang-client-0968389176 --allow-unauthenticated
```

After deploy, sanity-check: `/health` → 200, log in, ask the policy chat a
question and confirm answers now show inline `[n]` citations mapped to the source
chips, and that a "can I date an inmate?" question still returns the PREA
prohibition.

---

## 6. (Optional) Silence the broken `github-advanced-security` check

It fails on every commit (GitHub-side, unfixable from the repo). To stop the
noise without losing real coverage: **repo Settings → Code security → Code
scanning** and disable the agentic/"autofind" default-setup scanner (or that
specific check). CodeQL code scanning — which caught the real clear-text-logging
and workflow-permission issues — is separate and should stay on.

---

## Still open / not done (by decision)

- **#1 access code** — left as-is per your call.
- **Stricter RAG grounding** — uncited answers are currently *flagged*
  (`UNGROUNDED_NOTE`), not blocked, to protect passage-less PREA/DOMAIN_RULES
  answers. A stricter "block unless a domain rule fired" mode is a possible
  follow-up.
- **Semantic reranker** — **shipped** (`backend/pipeline/rerank.py`), on by
  default and fails open. Two things still need the live env:
  1. **Confirm it is actually reaching the Ranking API.** It fails open
     *silently*, so a working chat proves nothing.
     `PYTHONPATH=. python3 scripts/check_search.py "use of force"` now reports
     whether the ranker ran, its latency, and whether it changed the order. If
     it prints `UNAVAILABLE`, the service account is likely missing
     `discoveryengine.rankingConfigs.rank` — grant
     `roles/discoveryengine.viewer` on the project.
  2. **Measure it** against the eval set (§2): run once plain, once with
     `--no-rerank`, and compare answer pass-rate. Reranking cannot change
     *which* documents were retrieved, only which reach the generator, so
     watch answer quality rather than retrieval hit-rate.
- **Next RAG lever** — extractive segments. Implemented but **dead in
  production**: the data store rejects the extractive-content spec (400), so
  search runs permanently in snippets-only fallback and the richer passages
  RC-5 added never reach anyone. Needs a data store provisioned for extractive
  content; that is a corpus/data-store change, not a code change.

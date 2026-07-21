#!/usr/bin/env python3
"""Check for new Claude Code PR branches, merge into main, and trigger deploy."""
import subprocess, sys, json
from pathlib import Path

REPO = Path(r"C:\Users\justi\workspace\prison-policy-ai")
GCLOUD = r"C:\CloudSDK\google-cloud-sdk\bin\gcloud.cmd"

def run(cmd, **kw):
    result = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, timeout=kw.pop("timeout", 30), **kw)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

# 1. Fetch latest
print("Fetching...")
out, err, rc = run(["git", "fetch", "origin"], timeout=60)
if rc != 0:
    print(f"Fetch failed: {err}")
    sys.exit(1)

# 2. Find Claude branches with new commits
out, err, rc = run(["git", "branch", "-r"])
branches = [b.strip() for b in out.split("\n") if "origin/claude/" in b]

if not branches:
    print("No Claude branches found.")
    sys.exit(0)

for branch in branches:
    # Check if branch has commits not in main
    out, err, rc = run(["git", "log", "--oneline", f"main..{branch}"])
    if not out.strip():
        print(f"{branch}: already merged, skipping")
        continue

    commits = out.strip().split("\n")
    print(f"\n{branch}: {len(commits)} new commits")

    # Show what changed
    for c in commits:
        print(f"  {c}")

    # Merge
    print("Merging...")
    merge_msg = f"Merge Claude Code: {'; '.join(c.split(' ',1)[1][:60] for c in commits[:3])}"
    out, err, rc = run(["git", "merge", branch, "--no-ff", "-m", merge_msg], timeout=30)
    if rc != 0:
        print(f"Merge failed: {err}")
        # Abort merge if conflicted
        run(["git", "merge", "--abort"])
        continue

    # Push
    print("Pushing...")
    out, err, rc = run(["git", "push", "origin", "main"], timeout=30)
    if rc != 0:
        print(f"Push failed: {err}")
        continue

    # Deploy
    print("Deploying...")
    result = subprocess.run(
        [GCLOUD, "run", "deploy", "prison-policy-ai",
         "--source", ".", "--region", "us-central1",
         "--allow-unauthenticated", "--project", "gen-lang-client-0968389176"],
        cwd=str(REPO), capture_output=True, text=True, timeout=600
    )
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    if result.returncode != 0:
        print(f"Deploy failed: {result.stderr[:500]}")
        continue

    print("Done — merged and deployed.")

print("\nCheck complete.")

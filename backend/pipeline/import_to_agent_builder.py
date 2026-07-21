"""Import policy PDFs from GCS into the Agent Builder data store.

Usage:
  python import_to_agent_builder.py          # import all
  python import_to_agent_builder.py --count 5 # import first 5 only
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error
import subprocess

PROJECT = "gen-lang-client-0968389176"
LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "global")
DATA_STORE_ID = os.getenv("AGENT_BUILDER_DATA_STORE", "prison-policies-ds")
BUCKET = f"gs://{PROJECT}-policy-ai"

BASE = (
    f"projects/{PROJECT}/locations/{LOCATION}"
    f"/collections/default_collection/dataStores/{DATA_STORE_ID}"
    f"/branches/default_branch"
)

def gcloud(args):
    result = subprocess.run(
        [r"C:\CloudSDK\google-cloud-sdk\bin\gcloud.cmd"] + args,
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

stdout, stderr, rc = gcloud(["auth", "print-access-token"])
if rc != 0:
    print(f"Error getting token: {stderr}")
    sys.exit(1)
TOKEN = stdout.strip()

def api(method, path, body=None, timeout=120):
    url = f"https://discoveryengine.googleapis.com/v1beta/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.code, "body": e.read().decode()[:2000]}

def wait_for_operation(op_name, timeout=300):
    """Poll a long-running operation until done."""
    start = time.time()
    while time.time() - start < timeout:
        status, op = api("GET", op_name)
        if op.get("done"):
            if "response" in op:
                return True, op["response"]
            elif "error" in op:
                return False, op["error"]
        time.sleep(5)
    return False, "timeout"

# 1. List PDFs
print("=== Listing GCS PDFs ===")
stdout, stderr, rc = gcloud(["storage", "ls", f"{BUCKET}/pdfs/"])
if rc != 0:
    print(f"ERROR: {stderr}")
    sys.exit(1)

pdf_uris = [line.strip() for line in stdout.split("\n") if line.strip().endswith(".pdf")]
print(f"  Found {len(pdf_uris)} PDFs")

# Limit for testing
limit_arg = None
for a in sys.argv:
    if a == "--count" or limit_arg is not None:
        if a != "--count":
            limit_arg = int(a)
            break
        limit_arg = None  # signal next arg
if limit_arg:
    pdf_uris = pdf_uris[:limit_arg]
    print(f"  Limited to {len(pdf_uris)}")

# 2. Import in batches of 50 (smaller batches = less risk)
BATCH_SIZE = 50
print(f"\n=== Importing {len(pdf_uris)} documents ===")
errors = []
imported = 0

for batch_num, i in enumerate(range(0, len(pdf_uris), BATCH_SIZE)):
    batch = pdf_uris[i : i + BATCH_SIZE]
    print(f"  Batch {batch_num + 1}: {len(batch)} files...", end=" ", flush=True)

    body = {
        "gcsSource": {"inputUris": batch},
        "reconciliationMode": "INCREMENTAL",
    }
    status, result = api("POST", f"{BASE}/documents:import", body)

    if "name" in result and not result.get("done", True):
        # Long-running operation
        ok, detail = wait_for_operation(result["name"])
        if ok:
            success_count = detail.get("successCount", len(batch))
            failure_count = detail.get("failureCount", 0)
            print(f"OK ({success_count} success)")
            imported += success_count
            if failure_count:
                errors.append(f"Batch {batch_num+1}: {failure_count} failures")
        else:
            print(f"FAIL: {json.dumps(detail)[:200]}")
            errors.append(f"Batch {batch_num+1}: {detail}")
    elif status == 200:
        print("OK")
        imported += len(batch)
    else:
        print(f"HTTP {status}")
        errors.append(f"Batch {batch_num+1}: HTTP {status}")

if errors:
    print(f"\n❌ {len(errors)} errors:")
    for e in errors[:5]:
        print(f"  - {e}")
else:
    print(f"\n✅ All {imported} documents imported!")

print(f"\nNote: Documents may take a few minutes to appear in search results.")

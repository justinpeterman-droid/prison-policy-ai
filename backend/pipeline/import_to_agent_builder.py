"""Import policy PDFs from GCS into the Agent Builder data store.

Usage: python import_to_agent_builder.py

Requires: PDFs uploaded to gs://gen-lang-client-0968389176-policy-ai/pdfs/
          and the data store already created in the console.
"""
import os
import subprocess
import json
import urllib.request
import urllib.error
import time

PROJECT = "gen-lang-client-0968389176"
LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "global")
DATA_STORE_ID = os.getenv("AGENT_BUILDER_DATA_STORE", "prison-policies-ds")
BUCKET = f"gs://{PROJECT}-policy-ai"

def gcloud(args):
    result = subprocess.run(
        [r'C:\CloudSDK\google-cloud-sdk\bin\gcloud.cmd'] + args,
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

stdout, stderr, rc = gcloud(['auth', 'print-access-token'])
if rc != 0:
    print(f"Error getting token: {stderr}")
    exit(1)
token = stdout.strip()

def api(method, path, body=None, timeout=60):
    url = f"https://discoveryengine.googleapis.com/v1beta/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Goog-User-Project", PROJECT)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.code, "body": e.read().decode()[:2000]}

# 1. Check data store exists
print("=== Checking data store ===")
ds_path = f"projects/{PROJECT}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE_ID}"
status, ds = api("GET", ds_path)
if status != 200:
    print(f"ERROR: Data store not found (status {status})")
    print(json.dumps(ds, indent=2)[:500])
    print("\nYou must create the data store in the console first:")
    print("  https://console.cloud.google.com/gen-app-builder")
    exit(1)
print(f"  Data store: {ds['name']}")
print(f"  State: {ds.get('state')}")

# 2. List PDFs in GCS
print("\n=== Listing GCS PDFs ===")
stdout, stderr, rc = gcloud(['storage', 'ls', f'{BUCKET}/pdfs/'])
if rc != 0:
    print(f"ERROR listing GCS: {stderr}")
    exit(1)

pdf_uris = [line.strip() for line in stdout.split('\n') if line.strip().endswith('.pdf')]
print(f"  Found {len(pdf_uris)} PDFs")

if not pdf_uris:
    print("No PDFs found. Upload them first:")
    print(f'  gcloud storage cp -r "C:\\Users\\justi\\workspace\\prison-policy-ai\\pdfs" "{BUCKET}/pdfs/"')
    exit(1)

# 3. Import documents in batches of 100 (API limit)
print(f"\n=== Importing {len(pdf_uris)} documents ===")
branch = f"{ds_path}/branches/default_branch"

BATCH_SIZE = 100
errors = []
for batch_num, i in enumerate(range(0, len(pdf_uris), BATCH_SIZE)):
    batch = pdf_uris[i:i + BATCH_SIZE]
    print(f"  Batch {batch_num + 1}/{(len(pdf_uris) + BATCH_SIZE - 1) // BATCH_SIZE}: {len(batch)} files")

    body = {
        "gcsSource": {
            "inputUris": batch,
        },
        "reconciliationMode": "INCREMENTAL",
    }
    status, result = api("POST", f"{branch}/documents:import", body, timeout=120)
    print(f"    Status: {status}")

    if "name" in result and not result.get("done", True):
        op_name = result["name"]
        for j in range(150):  # 5 min max per batch
            time.sleep(2)
            s, op = api("GET", op_name)
            if op.get("done"):
                if "response" in op:
                    print(f"    Complete! {op['response']}")
                elif "error" in op:
                    print(f"    Error: {op['error']}")
                    errors.append(f"Batch {batch_num + 1}: {op['error']}")
                break
            if j % 15 == 0:
                print(f"      ... importing ({j * 2}s)")
        else:
            print("    Timed out waiting for import.")
            errors.append(f"Batch {batch_num + 1}: timeout")
    elif status != 200:
        errors.append(f"Batch {batch_num + 1}: HTTP {status}")
        print(f"    Error: {json.dumps(result, indent=2)[:500]}")

if errors:
    print(f"\n❌ {len(errors)} batch(es) had errors:")
    for e in errors:
        print(f"  - {e}")
else:
    print(f"\n✅ All {len(pdf_uris)} documents imported successfully!")

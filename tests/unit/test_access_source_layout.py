from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "access-client"

EXPECTED_VENDOR = {
    "JsonConverter.bas": (
        44164,
        "1c240aa3c7ef536c25bf44061b02b0fadeb39bfb449f67c419822650e23f6169",
    ),
    "LICENSE.txt": (
        1075,
        "f902104a3e36daea3a33f7adfcd25c5ac69791e9164b83a81b8d0b235728c9bd",
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_access_master_and_source_manifest_exist():
    assert (CLIENT / "SLUT-Client.accdb").is_file()
    manifest = json.loads((CLIENT / "src" / "manifest.json").read_text("utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["database"] == "SLUT-Client.accdb"
    assert [item["name"] for item in manifest["objects"]] == [
        "AutoExec",
        "frmErrorDialog",
        "frmLogin",
        "frmShell",
        "JsonConverter",
        "TestAssert",
        "TestRunner",
    ]


def test_access_has_no_local_application_tables():
    schema = json.loads((CLIENT / "src" / "tables" / "schema.json").read_text("utf-8"))
    assert schema == {"schema_version": 1, "tables": []}


def test_vba_json_231_is_pinned_by_bytes_and_hash():
    vendor = CLIENT / "vendor" / "json"
    for name, expected in EXPECTED_VENDOR.items():
        path = vendor / name
        assert path.stat().st_size == expected[0]
        assert sha256(path) == expected[1]
    version = (vendor / "VERSION.txt").read_text("utf-8")
    assert "v2.3.1" in version
    assert "1e49ba826b979d1851029dc965ecb6a3ead2a32c" in version


def test_pinned_vendor_files_disable_checkout_line_ending_conversion():
    files = [
        "access-client/vendor/json/JsonConverter.bas",
        "access-client/vendor/json/LICENSE.txt",
    ]
    result = subprocess.run(
        ["git", "check-attr", "text", "--", *files],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert all(line.endswith(": text: unset") for line in result.stdout.splitlines())


def test_reports_and_queries_have_no_access_objects():
    assert list((CLIENT / "src" / "reports").glob("*.txt")) == []
    assert list((CLIENT / "src" / "queries").glob("*.sql")) == []


def test_manifested_forms_exclude_access_volatile_export_metadata():
    manifest = json.loads((CLIENT / "src" / "manifest.json").read_text("utf-8"))
    forms = [item for item in manifest["objects"] if item["type"] == "form"]
    for form in forms:
        text = (CLIENT / "src" / form["path"]).read_text("utf-8")
        assert "Checksum =" not in text
        assert "NameMap = Begin" not in text
        assert text.count("    NoSaveCTIWhenDisabled =1") == 1

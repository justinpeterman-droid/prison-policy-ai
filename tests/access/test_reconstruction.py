from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from access_com import invoke_access_script


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "access-client"
REBUILD_ROOT = ROOT / "tests" / "output" / "access-rebuild"


def _access_process_ids() -> set[int]:
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "$ErrorActionPreference = 'SilentlyContinue'; @(Get-Process -Name MSACCESS).ForEach({ $_.Id }); exit 0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return {int(line) for line in completed.stdout.splitlines() if line.strip()}


def _wait_for_owned_access_processes(process_ids: set[int], timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = process_ids & _access_process_ids()
        if not remaining:
            return
        time.sleep(0.25)
    raise AssertionError(f"Access processes created by this test did not exit: {sorted(remaining)}")


def _fresh_rebuild_paths() -> tuple[Path, Path]:
    root = REBUILD_ROOT / uuid.uuid4().hex
    root.mkdir(parents=True)
    return root / "SLUT-Client.rebuilt.accdb", root / "exported"


@pytest.mark.access_com
def test_import_reexport_is_canonical():
    rebuilt, exported = _fresh_rebuild_paths()
    before_import = _access_process_ids()
    invoke_access_script(
        CLIENT / "build" / "ImportAccessSource.ps1",
        Source=CLIENT / "src",
        Database=rebuilt,
        Configuration="Test",
    )
    _wait_for_owned_access_processes(_access_process_ids() - before_import)
    before_export = _access_process_ids()
    invoke_access_script(
        CLIENT / "build" / "ExportAccessSource.ps1",
        Database=rebuilt,
        Output=exported,
        Check=True,
    )
    _wait_for_owned_access_processes(_access_process_ids() - before_export)
    expected = json.loads((CLIENT / "src" / "manifest.json").read_text("utf-8"))
    actual = json.loads((exported / "manifest.json").read_text("utf-8"))
    assert actual["objects"] == expected["objects"]


@pytest.mark.access_com
def test_export_contains_every_import_dependency():
    root = REBUILD_ROOT / uuid.uuid4().hex
    root.mkdir(parents=True)
    exported = root / "exported"
    database = root / "SLUT-Client.export.accdb"
    shutil.copy2(CLIENT / "SLUT-Client.accdb", database)
    invoke_access_script(
        CLIENT / "build" / "ExportAccessSource.ps1",
        Database=database,
        Output=exported,
        SourceRoot=CLIENT / "src",
        Check=True,
    )

    manifest = json.loads((exported / "manifest.json").read_text("utf-8"))
    required = [
        exported / "project.json",
        exported / "tables" / "schema.json",
        *[exported / item["path"] for item in manifest["objects"]],
    ]
    assert all(path.is_file() for path in required)

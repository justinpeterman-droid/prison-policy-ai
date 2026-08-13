from __future__ import annotations

import json
from pathlib import Path

import pytest

from access_com import invoke_access_script


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "access-client"


@pytest.mark.access_com
def test_import_reexport_is_canonical(tmp_path: Path):
    rebuilt = tmp_path / "SLUT-Client.rebuilt.accdb"
    exported = tmp_path / "exported"
    invoke_access_script(
        CLIENT / "build" / "ImportAccessSource.ps1",
        Source=CLIENT / "src",
        Database=rebuilt,
        Configuration="Test",
    )
    invoke_access_script(
        CLIENT / "build" / "ExportAccessSource.ps1",
        Database=rebuilt,
        Output=exported,
        Check=True,
    )
    expected = json.loads((CLIENT / "src" / "manifest.json").read_text("utf-8"))
    actual = json.loads((exported / "manifest.json").read_text("utf-8"))
    assert actual["objects"] == expected["objects"]


@pytest.mark.access_com
def test_export_contains_every_import_dependency(tmp_path: Path):
    exported = tmp_path / "exported"
    invoke_access_script(
        CLIENT / "build" / "ExportAccessSource.ps1",
        Database=CLIENT / "SLUT-Client.accdb",
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

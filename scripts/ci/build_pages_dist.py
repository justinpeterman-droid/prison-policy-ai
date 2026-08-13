"""Build the deliberately tiny GitHub Pages artifact."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "pages-dist"
ALLOWED = ("index.html", "frontend/forms")
FORBIDDEN_SUFFIXES = {".map"}
FORBIDDEN_TOKENS = ("secret", "token", "password", "private_key", "access_code", "admin_code", "pin")


def reject(path: Path) -> None:
    relative = path.relative_to(DESTINATION)
    if (
        path.is_symlink()
        or path.suffix in FORBIDDEN_SUFFIXES
        or any(token in relative.name.lower() for token in FORBIDDEN_TOKENS)
    ):
        raise ValueError(f"unsafe Pages artifact member: {relative}")


def main() -> int:
    if DESTINATION.exists():
        shutil.rmtree(DESTINATION)
    DESTINATION.mkdir()
    shutil.copy2(ROOT / "index.html", DESTINATION / "index.html")
    shutil.copytree(ROOT / "frontend" / "forms", DESTINATION / "frontend" / "forms", symlinks=True)
    actual = {
        str(path.relative_to(DESTINATION)).replace("\\", "/") for path in DESTINATION.rglob("*") if path.is_file()
    }
    if not {"index.html", "frontend/forms/index.html"} <= actual:
        raise ValueError("Pages artifact is incomplete")
    for member in DESTINATION.rglob("*"):
        reject(member)
    return 0


if __name__ == "__main__":
    sys.exit(main())

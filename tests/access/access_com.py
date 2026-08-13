from __future__ import annotations

import subprocess
from pathlib import Path


def invoke_access_script(script: Path, timeout: int = 180, **parameters: object) -> str:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
    ]
    for name, value in parameters.items():
        command.extend([f"-{name}", str(value)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{script.name} failed with {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed.stdout

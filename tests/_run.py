"""Clean-environment launcher for test_pipeline.py.

Spawns a subprocess with the Hermes venv stripped from PYTHONPATH,
so vertexai/grpc imports resolve from the correct site-packages.
"""
import subprocess
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERMES_HOME = os.path.join(os.environ.get("HOME", ""), "AppData", "Local", "hermes", "hermes-agent")

def main():
    args = sys.argv[1:]

    # Build clean sys.path: Python 3.14 site-packages only
    py_paths = [
        PROJECT_ROOT,
        # Standard lib paths from Python 3.14
        r"C:\Python314\Lib",
        r"C:\Python314\Lib\site-packages",
        r"C:\Python314\DLLs",
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(py_paths)
    env["GCP_MODEL_LOCATION"] = "global"
    env.pop("VIRTUAL_ENV", None)
    # Remove any hermes-specific env
    for k in list(env):
        if k.startswith("HERMES_"):
            del env[k]

    cmd = [r"C:\Python314\python.exe", os.path.join(PROJECT_ROOT, "tests", "test_pipeline.py")] + args
    return subprocess.call(cmd, env=env)

if __name__ == "__main__":
    sys.exit(main())

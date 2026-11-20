import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(request_data, *, catalog="data/catalog.json", env=None):
    """Run the documented CLI entry point in a child process."""
    if os.name != "nt" and shutil.which("bash"):
        command = ["bash", "./run", "--catalog", str(catalog)]
    else:
        # run is a POSIX shell script; invoke the same main.py entry point on Windows.
        command = [sys.executable, "main.py", "--catalog", str(catalog)]
    process_env = os.environ.copy()
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT_SECONDS"):
        process_env.pop(key, None)
    process_env["PYTHONUTF8"] = "1"
    process_env["LLM_API_KEY"] = ""
    if env:
        process_env.update(env)
    completed = subprocess.run(
        command,
        input=json.dumps(request_data, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        cwd=ROOT,
        env=process_env,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed

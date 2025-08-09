import subprocess
from typing import Tuple

def kubectl_apply_dry_run(manifest_path: str) -> Tuple[bool, str]:
    # Runs server-side dry-run; caller is responsible for RBAC and namespace scoping.
    cmd = ["kubectl", "apply", "--dry-run=server", "-f", manifest_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0
    return ok, proc.stdout + proc.stderr

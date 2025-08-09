import subprocess
from typing import Tuple

def psql_exec(conn_str: str, sql: str) -> Tuple[bool, str]:
    proc = subprocess.run(["psql", conn_str, "-c", sql], capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr

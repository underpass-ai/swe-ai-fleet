import subprocess


def helm_lint(chart_dir: str) -> tuple[bool, str]:
    proc = subprocess.run(["helm", "lint", chart_dir], capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr

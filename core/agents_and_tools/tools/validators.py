"""
Input validation and security checks for tool operations.

Prevents command injection, path traversal, and other security issues.
"""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def kube_lint_stub(_doc: str) -> dict[str, Any]:
    """
    Placeholder for kubeconform/kubeval result.

    Args:
        _doc: Kubernetes YAML document (unused, placeholder function)

    Returns:
        Validation result
    """
    return {"ok": True, "issues": []}


def validate_path(path: str | Path, workspace_path: str | Path) -> bool:
    """
    Validate that path is within workspace (prevent path traversal).

    Args:
        path: Path to validate
        workspace_path: Workspace root directory

    Returns:
        True if path is safe

    Raises:
        ValueError: If path is outside workspace
    """
    workspace = Path(workspace_path).resolve()
    target = Path(path)

    # If relative, make it relative to workspace
    if not target.is_absolute():
        target = workspace / target

    # Resolve and check if within workspace
    resolved = target.resolve()

    try:
        resolved.relative_to(workspace)
        return True
    except ValueError:
        raise ValueError(f"Path outside workspace: {path}") from None


def validate_url(url: str, allow_localhost: bool = False) -> bool:
    """
    Validate URL for security.

    Args:
        url: URL to validate
        allow_localhost: Allow requests to localhost/127.0.0.1

    Returns:
        True if URL is safe

    Raises:
        ValueError: If URL is invalid or forbidden
    """
    parsed = urlparse(url)

    # Must have scheme
    if not parsed.scheme:
        raise ValueError("URL must have scheme (http:// or https://)")

    # Only http/https allowed
    if parsed.scheme not in ["http", "https"]:
        raise ValueError(f"Only http:// and https:// allowed, got: {parsed.scheme}")

    # Check localhost restrictions
    if not allow_localhost:
        forbidden_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        if parsed.hostname in forbidden_hosts:
            raise ValueError(
                f"Requests to {parsed.hostname} not allowed. "
                "Enable allow_localhost if needed."
            )

    return True


def validate_git_url(url: str) -> bool:
    """
    Validate Git repository URL.

    Args:
        url: Git repository URL

    Returns:
        True if URL is safe

    Raises:
        ValueError: If URL is invalid
    """
    # Only https and git@ URLs allowed (no file://, etc.)
    if not (url.startswith("https://") or url.startswith("git@")):
        raise ValueError("Only https:// and git@ URLs allowed for git operations")

    # Basic pattern validation
    if url.startswith("https://"):
        # Should be https://domain/path.git or https://domain/path
        if not re.match(r"^https://[a-zA-Z0-9\-\.]+/[\w\-/]+\.git$|^https://[a-zA-Z0-9\-\.]+/[\w\-/]+$", url):
            raise ValueError(f"Invalid Git URL format: {url}")
    elif url.startswith("git@"):
        # Should be git@domain:path.git
        if not re.match(r"^git@[a-zA-Z0-9\-\.]+:[\w\-/]+\.git$", url):
            raise ValueError(f"Invalid Git SSH URL format: {url}")

    return True


def validate_command_args(args: list[str]) -> bool:
    """
    Validate command arguments for injection attacks.

    Args:
        args: Command arguments

    Returns:
        True if arguments are safe

    Raises:
        ValueError: If arguments contain dangerous patterns
    """
    dangerous_patterns = [
        r";\s*",  # Command chaining
        r"\|\s*",  # Pipe to another command
        r"&&",  # AND command
        r"\|\|",  # OR command
        r"`",  # Command substitution
        r"\$\(",  # Command substitution
        r">\s*",  # Output redirection
        r"<\s*",  # Input redirection
    ]

    for arg in args:
        for pattern in dangerous_patterns:
            if re.search(pattern, arg):
                raise ValueError(
                    f"Dangerous pattern detected in argument: {arg}. "
                    f"Pattern: {pattern}"
                )

    return True


def validate_env_vars(env: dict[str, str]) -> bool:
    """
    Validate environment variables.

    Args:
        env: Environment variables dict

    Returns:
        True if env vars are safe

    Raises:
        ValueError: If env vars contain dangerous values
    """
    # Check for dangerous PATH manipulations
    if "PATH" in env:
        path_value = env["PATH"]
        # Ensure no relative paths in PATH
        if ".." in path_value:
            raise ValueError("PATH cannot contain .. (parent directory)")

    # Check for LD_PRELOAD attacks
    if "LD_PRELOAD" in env:
        raise ValueError("LD_PRELOAD not allowed (security risk)")

    # Check for LD_LIBRARY_PATH attacks
    if "LD_LIBRARY_PATH" in env:
        lib_path = env["LD_LIBRARY_PATH"]
        # Security: We're CHECKING for /tmp usage (not using it), this is validation logic
        if ".." in lib_path or lib_path.startswith("/tmp"):
            raise ValueError("LD_LIBRARY_PATH contains suspicious path")

    return True


def validate_container_image(image: str) -> bool:
    """
    Validate container image name.

    Args:
        image: Container image name

    Returns:
        True if image name is valid

    Raises:
        ValueError: If image name is invalid
    """
    # Basic format: [registry/]name[:tag]
    pattern = r"^([a-zA-Z0-9\-\.]+/)?[a-zA-Z0-9\-_/]+(:[a-zA-Z0-9\-_\.]+)?$"

    if not re.match(pattern, image):
        raise ValueError(f"Invalid container image format: {image}")

    # Prevent pulling from suspicious registries (optional)
    # You might want to whitelist specific registries here

    return True


def validate_database_connection_string(conn_str: str, db_type: str) -> bool:
    """
    Validate database connection string.

    Args:
        conn_str: Connection string
        db_type: Database type (postgresql, redis, neo4j)

    Returns:
        True if connection string is valid

    Raises:
        ValueError: If connection string is invalid
    """
    if db_type == "postgresql":
        if not conn_str.startswith("postgresql://") and not conn_str.startswith("postgres://"):
            raise ValueError("PostgreSQL connection string must start with postgresql://")

    elif db_type == "redis":
        if not conn_str.startswith("redis://") and not conn_str.startswith("rediss://"):
            raise ValueError("Redis connection string must start with redis:// or rediss://")

    elif db_type == "neo4j":
        if not conn_str.startswith("bolt://") and not conn_str.startswith("bolt+s://"):
            raise ValueError("Neo4j connection string must start with bolt:// or bolt+s://")

    else:
        raise ValueError(f"Unknown database type: {db_type}")

    return True


def sanitize_log_output(output: str, max_length: int = 10000) -> str:
    """
    Sanitize log output for safe display/storage.

    Args:
        output: Raw log output
        max_length: Maximum length to keep

    Returns:
        Sanitized output
    """
    # Truncate if too long
    if len(output) > max_length:
        output = output[:max_length] + "\n... (truncated)"

    # Remove ANSI color codes
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    output = ansi_escape.sub("", output)

    return output

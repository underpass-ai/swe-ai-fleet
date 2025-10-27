"""
Test execution tool for agent workspace.

Supports multiple test frameworks: pytest, go test, npm test, cargo test.
"""

import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

TestFramework = Literal["pytest", "go", "npm", "cargo", "make"]


@dataclass
class TestResult:
    """Result of a test execution."""

    success: bool
    framework: TestFramework
    stdout: str
    stderr: str
    exit_code: int
    metadata: dict[str, Any]


class TestTool:
    """
    Test execution tool for workspace execution.

    Security:
    - All tests run in workspace directory only
    - Timeout protection (default: 10 minutes)
    - Resource limits respected
    - Audit trail of all test runs
    """

    DEFAULT_TIMEOUT = 600  # 10 minutes

    @staticmethod
    def create(workspace_path: str | Path, audit_callback: Callable | None = None) -> "TestTool":
        """Factory method to create TestTool instance."""
        return TestTool(workspace_path, audit_callback)

    def __init__(self, workspace_path: str | Path, audit_callback: Callable | None = None):
        """
        Initialize Test tool.

        Args:
            workspace_path: Root workspace directory
            audit_callback: Optional callback for audit logging
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.audit_callback = audit_callback
        
        # Initialize mapper for domain conversion
        self.mapper = self._get_mapper()

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

    def _audit(self, framework: str, params: dict[str, Any], result: TestResult) -> None:
        """Log test execution to audit trail."""
        if self.audit_callback:
            self.audit_callback(
                {
                    "tool": "test",
                    "operation": framework,
                    "params": params,
                    "success": result.success,
                    "metadata": {"exit_code": result.exit_code, "framework": framework},
                    "workspace": str(self.workspace_path),
                }
            )

    def pytest(
        self,
        path: str | Path = ".",
        markers: str | None = None,
        verbose: bool = False,
        coverage: bool = False,
        junit_xml: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> TestResult:
        """
        Run pytest tests.

        Args:
            path: Test path or directory (default: current directory)
            markers: Pytest markers to filter (e.g., "not e2e and not integration")
            verbose: Verbose output
            coverage: Enable coverage reporting
            junit_xml: Path to save JUnit XML report
            timeout: Timeout in seconds

        Returns:
            TestResult with test execution results
        """
        cmd = ["pytest"]

        # Add path
        if path != ".":
            cmd.append(str(path))

        # Add markers
        if markers:
            cmd.extend(["-m", markers])

        # Verbose
        if verbose:
            cmd.append("-v")

        # Coverage
        if coverage:
            cmd.extend(["--cov=core", "--cov-report=xml", "--cov-report=term"])

        # JUnit XML output
        if junit_xml:
            cmd.extend(["--junitxml", junit_xml])

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

            test_result = TestResult(
                success=result.returncode == 0,
                framework="pytest",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={
                    "cmd": cmd,
                    "path": str(path),
                    "markers": markers,
                    "coverage": coverage,
                },
            )

            self._audit("pytest", {"path": str(path), "markers": markers}, test_result)
            return test_result

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                framework="pytest",
                stdout="",
                stderr=f"Tests timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return TestResult(
                success=False,
                framework="pytest",
                stdout="",
                stderr=f"Error running pytest: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def go_test(
        self,
        package: str = "./...",
        verbose: bool = False,
        coverage: bool = False,
        race: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> TestResult:
        """
        Run Go tests.

        Args:
            package: Go package path (default: ./... for all packages)
            verbose: Verbose output
            coverage: Enable coverage reporting
            race: Enable race detector
            timeout: Timeout in seconds

        Returns:
            TestResult with test execution results
        """
        cmd = ["go", "test"]

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend(["-coverprofile=coverage.out", "-covermode=atomic"])

        if race:
            cmd.append("-race")

        cmd.append(package)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            test_result = TestResult(
                success=result.returncode == 0,
                framework="go",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={
                    "cmd": cmd,
                    "package": package,
                    "coverage": coverage,
                    "race": race,
                },
            )

            self._audit("go_test", {"package": package}, test_result)
            return test_result

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                framework="go",
                stdout="",
                stderr=f"Tests timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return TestResult(
                success=False,
                framework="go",
                stdout="",
                stderr=f"Error running go test: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def npm_test(
        self,
        script: str = "test",
        verbose: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> TestResult:
        """
        Run npm test script.

        Args:
            script: npm script name (default: "test")
            verbose: Verbose output
            timeout: Timeout in seconds

        Returns:
            TestResult with test execution results
        """
        cmd = ["npm", "run", script]

        if verbose:
            cmd.append("--verbose")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            test_result = TestResult(
                success=result.returncode == 0,
                framework="npm",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "script": script},
            )

            self._audit("npm_test", {"script": script}, test_result)
            return test_result

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                framework="npm",
                stdout="",
                stderr=f"Tests timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return TestResult(
                success=False,
                framework="npm",
                stdout="",
                stderr=f"Error running npm test: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def cargo_test(
        self,
        package: str | None = None,
        verbose: bool = False,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> TestResult:
        """
        Run Cargo tests (Rust).

        Args:
            package: Specific package to test (None for all)
            verbose: Verbose output
            timeout: Timeout in seconds

        Returns:
            TestResult with test execution results
        """
        cmd = ["cargo", "test"]

        if package:
            cmd.extend(["--package", package])

        if verbose:
            cmd.append("--verbose")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            test_result = TestResult(
                success=result.returncode == 0,
                framework="cargo",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "package": package},
            )

            self._audit("cargo_test", {"package": package}, test_result)
            return test_result

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                framework="cargo",
                stdout="",
                stderr=f"Tests timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return TestResult(
                success=False,
                framework="cargo",
                stdout="",
                stderr=f"Error running cargo test: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def make_test(
        self,
        target: str = "test",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> TestResult:
        """
        Run make test target.

        Args:
            target: Make target name (default: "test")
            timeout: Timeout in seconds

        Returns:
            TestResult with test execution results
        """
        cmd = ["make", target]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            test_result = TestResult(
                success=result.returncode == 0,
                framework="make",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "target": target},
            )

            self._audit("make_test", {"target": target}, test_result)
            return test_result

        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                framework="make",
                stdout="",
                stderr=f"Tests timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return TestResult(
                success=False,
                framework="make",
                stdout="",
                stderr=f"Error running make: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )


    def get_operations(self) -> dict[str, Any]:
        """Return dictionary mapping operation names to method callables."""
        return {
            "pytest": self.pytest,
            "go_test": self.go_test,
            "npm_test": self.npm_test,
            "cargo_test": self.cargo_test,
            "make_test": self.make_test,
        }

    def execute(self, operation: str, **params: Any) -> TestResult:
        """
        Execute a test operation by name.

        Args:
            operation: Name of the operation
            **params: Operation parameters

        Returns:
            TestResult

        Raises:
            ValueError: If operation is not supported
        """
        operations = self.get_operations()
        method = operations.get(operation)
        if not method:
            raise ValueError(f"Unknown test operation: {operation}")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for TestTool results."""
        from core.agents_and_tools.agents.infrastructure.mappers.test_result_mapper import TestResultMapper
        return TestResultMapper()
    
    def get_mapper(self):
        """Return the tool's mapper instance."""
        return self.mapper


# Convenience function for use in agent tasks
def execute_test(
    framework: TestFramework,
    workspace_path: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute tests from agent workspace.

    Args:
        framework: Test framework to use
        workspace_path: Workspace directory path
        **kwargs: Framework-specific parameters

    Returns:
        Dictionary with test result

    Examples:
        # Python tests
        result = execute_test("pytest", "/workspace", markers="not e2e")

        # Go tests
        result = execute_test("go", "/workspace", package="./pkg/...")

        # npm tests
        result = execute_test("npm", "/workspace", script="test")
    """
    tool = TestTool(workspace_path)

    # Map framework to method
    method_map = {
        "pytest": "pytest",
        "go": "go_test",
        "npm": "npm_test",
        "cargo": "cargo_test",
        "make": "make_test",
    }

    method_name = method_map.get(framework)
    if not method_name:
        return {
            "success": False,
            "framework": framework,
            "error": f"Unknown test framework: {framework}",
        }

    method = getattr(tool, method_name)
    result = method(**kwargs)

    return {
        "success": result.success,
        "framework": result.framework,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "metadata": result.metadata,
    }


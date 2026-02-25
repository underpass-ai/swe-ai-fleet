#!/usr/bin/env python3
"""E2E test: data-driven workspace tool catalog orchestration.

Reads tool_catalog.yaml and invokes every tool once against the workspace API.
Each entry declares its args, expected outcome, and optional output checks.

Adding a new tool = adding one YAML entry. No Python changes required.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

# PyYAML is available in the container image (installed via pip).
import yaml

from workspace_common import (
    WorkspaceE2EBase,
    print_error,
    print_info,
    print_step,
    print_success,
    print_warning,
)

CATALOG_FILE = Path(__file__).with_name("tool_catalog.yaml")


# ── Setup file definitions ───────────────────────────────────────────
# Files written into the workspace before tool execution begins.
SETUP_FILES: list[dict[str, str]] = [
    {"path": "notes/flow.txt", "content": "line1\ncoverage-marker\nline3\n"},
    {"path": "go.mod", "content": "module e2e/sample\n\ngo 1.22\n"},
    {
        "path": "sample.go",
        "content": "package sample\n\nfunc Add(a, b int) int {\n\treturn a + b\n}\n",
    },
    {
        "path": "sample_test.go",
        "content": (
            "package sample\n\n"
            'import "testing"\n\n'
            "func TestAdd(t *testing.T) {\n"
            "\tif got := Add(2, 3); got != 5 {\n"
            '\t\tt.Fatalf("expected 5, got %d", got)\n'
            "\t}\n"
            "}\n"
        ),
    },
    {
        "path": "package.json",
        "content": (
            "{\n"
            '  "name": "e2e-node-sample",\n'
            '  "version": "1.0.0",\n'
            '  "private": true,\n'
            '  "scripts": {\n'
            '    "build": "echo build-ok",\n'
            '    "test": "echo test-ok",\n'
            '    "lint": "echo lint-ok",\n'
            '    "typecheck": "echo typecheck-ok"\n'
            "  }\n"
            "}\n"
        ),
    },
    {
        "path": "Cargo.toml",
        "content": (
            "[package]\n"
            'name = "e2e_rust_sample"\n'
            'version = "0.1.0"\n'
            'edition = "2021"\n'
            "\n[dependencies]\n"
        ),
    },
    {"path": "src/main.rs", "content": 'fn main() {\n    println!("hello");\n}\n'},
    {"path": "tests/test_sample.py", "content": "def test_smoke() -> None:\n    assert 1 + 1 == 2\n"},
    {
        "path": "Dockerfile",
        "content": (
            "FROM busybox:1.36\n"
            "WORKDIR /app\n"
            "USER 65532:65532\n"
            'CMD ["sh", "-c", "echo ok"]\n'
        ),
    },
    {"path": "csrc/main.c", "content": "int main(void){return 0;}\n"},
    {"path": "csrc/main_test.c", "content": "int main(void){return 0;}\n"},
    {"path": ".workspace-dist/report.txt", "content": "workspace artifact payload\n"},
    {"path": "tmp/e2e-source.txt", "content": "move me\n"},
    {"path": "tmp/delete-me.txt", "content": "delete me\n"},
]


class ToolCatalogOrchestrationE2E(WorkspaceE2EBase):
    """Data-driven workspace tool catalog E2E test."""

    def __init__(self) -> None:
        self.workspace_git_repo_url = os.getenv(
            "WORKSPACE_GIT_REPO_URL",
            "https://github.com/octocat/Hello-World.git",
        ).strip()
        self.workspace_git_repo_ref = os.getenv("WORKSPACE_GIT_REPO_REF", "").strip()

        super().__init__(
            test_id="15-workspace-vllm-tool-orchestration",
            run_id_prefix="e2e-ws-vllm",
            workspace_url=os.getenv(
                "WORKSPACE_URL",
                "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
            ),
            evidence_file=os.getenv("EVIDENCE_FILE", f"/tmp/e2e-15-{int(time.time())}.json"),
        )

        self.git_repo_ready = bool(self.workspace_git_repo_url)
        self.benchmark_profile_id = os.getenv("BENCH_PROFILE_ID", "bench.workspace").strip() or "bench.workspace"
        self.benchmark_profile_routes = ["/healthz"]

        # Template variables available via $var substitution in YAML args.
        self._vars: dict[str, str] = {
            "run_id": self.run_id,
            "flow_file_path": "notes/flow.txt",
            "git_checkout_branch": f"e2e/ws-gap-001-{int(time.time())}",
            "fs_patch_diff": (
                "diff --git a/notes/flow.txt b/notes/flow.txt\n"
                "--- a/notes/flow.txt\n"
                "+++ b/notes/flow.txt\n"
                "@@ -1,3 +1,3 @@\n"
                " line1\n"
                " coverage-marker\n"
                "-line3\n"
                "+line-three-updated\n"
            ),
            "git_check_patch": (
                "diff --git a/notes/flow.txt b/notes/flow.txt\n"
                "--- a/notes/flow.txt\n"
                "+++ b/notes/flow.txt\n"
                "@@ -1,2 +1,2 @@\n"
                "-line1\n"
                "+line-one\n"
                " coverage-marker\n"
            ),
            "benchmark_profile_id": self.benchmark_profile_id,
            # Captured at runtime from tool outputs:
            "k8s_pod_name": "workspace",
            "last_container_id": "sim-e2e-container",
        }

        self.main_session_id = ""
        self.benchmark_session_id = ""
        self.available_tools: list[str] = []
        self.fs_read_tool = ""
        self.fs_write_tool = ""

    # ── Template substitution ────────────────────────────────────────
    def _substitute(self, value: Any) -> Any:
        """Recursively replace $var references in args with runtime values."""
        if isinstance(value, str):
            # Full-value replacement: "$var" -> vars[var]
            if value.startswith("$") and value[1:] in self._vars:
                return self._vars[value[1:]]
            # Inline replacement: "prefix-$var-suffix"
            result = value
            for var_name, var_value in self._vars.items():
                result = result.replace(f"${var_name}", str(var_value))
            return result
        if isinstance(value, dict):
            return {k: self._substitute(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._substitute(item) for item in value]
        return value

    # ── Catalog loading ──────────────────────────────────────────────
    def _load_catalog(self) -> list[dict[str, Any]]:
        with open(CATALOG_FILE, encoding="utf-8") as fh:
            entries = yaml.safe_load(fh)
        if not isinstance(entries, list):
            raise RuntimeError(f"tool_catalog.yaml must be a list, got {type(entries).__name__}")
        return entries

    def _resolve_tool_name(self, entry: dict[str, Any]) -> str | None:
        """Return the actual catalog name for a tool entry, handling aliases."""
        name = entry["name"]
        if name in self.available_tools:
            return name
        for alias in entry.get("aliases", []):
            if alias in self.available_tools:
                return alias
        return None

    # ── Output capture ───────────────────────────────────────────────
    def _capture_vars(self, captures: dict[str, str], output: dict[str, Any]) -> None:
        """Extract runtime variables from tool output."""
        for var_name, field_path in captures.items():
            value = self._resolve_output_field(output, field_path)
            if value is not None:
                self._vars[var_name] = str(value).strip()

    @staticmethod
    def _resolve_output_field(output: Any, field_path: str) -> Any:
        """Resolve a dotted field path like 'pods[0].name' from output."""
        current = output
        for part in field_path.split("."):
            if current is None:
                return None
            # Handle array index: "pods[0]"
            if "[" in part and part.endswith("]"):
                key, idx_str = part[:-1].split("[", 1)
                if key and isinstance(current, dict):
                    current = current.get(key)
                if isinstance(current, list):
                    idx = int(idx_str)
                    current = current[idx] if idx < len(current) else None
                else:
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    # ── Output checks ────────────────────────────────────────────────
    def _run_checks(
        self, tool_name: str, checks: list[dict[str, Any]], output: dict[str, Any]
    ) -> None:
        """Validate output fields against declarative checks."""
        for check in checks:
            field = check.get("field", "")
            value = self._resolve_output_field(output, field)

            if "contains" in check:
                if not isinstance(value, str) or check["contains"] not in value:
                    raise RuntimeError(
                        f"{tool_name}: output.{field} must contain {check['contains']!r}, got {value!r}"
                    )

            if "min" in check:
                if not isinstance(value, (int, float)) or value < check["min"]:
                    raise RuntimeError(
                        f"{tool_name}: output.{field} must be >= {check['min']}, got {value!r}"
                    )

            if "equals" in check:
                if value != check["equals"]:
                    raise RuntimeError(
                        f"{tool_name}: output.{field} must equal {check['equals']!r}, got {value!r}"
                    )

            if check.get("not_empty"):
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"{tool_name}: output.{field} must be non-empty string, got {value!r}"
                    )

            if "one_of" in check:
                if value not in check["one_of"]:
                    raise RuntimeError(
                        f"{tool_name}: output.{field} must be one of {check['one_of']}, got {value!r}"
                    )

    # ── Soft error matching ──────────────────────────────────────────
    @staticmethod
    def _matches_soft_error(
        soft_errors: list[dict[str, str]], error: dict[str, Any]
    ) -> bool:
        """Check if a tool failure matches any declared soft error pattern."""
        err_code = str(error.get("code", "")).strip()
        err_message = str(error.get("message", "")).strip().lower()

        for pattern in soft_errors:
            code_match = pattern.get("code", "") == err_code
            msg_filter = pattern.get("message_contains", "").lower()
            msg_match = not msg_filter or msg_filter in err_message
            if code_match and msg_match:
                return True
        return False

    # ── Session setup ────────────────────────────────────────────────
    def _setup_main_session(self) -> str:
        payload: dict[str, Any] = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "agent-vllm-orchestrator",
                "roles": ["developer"],
            },
            "metadata": {
                "allowed_git_remotes": "origin",
                "allowed_git_ref_prefixes": "*",
            },
            "expires_in_seconds": 3600,
        }
        if self.workspace_git_repo_url:
            payload["repo_url"] = self.workspace_git_repo_url
        if self.workspace_git_repo_ref:
            payload["repo_ref"] = self.workspace_git_repo_ref

        try:
            return self.create_session(payload=payload)
        except RuntimeError:
            if not self.workspace_git_repo_url:
                raise
            print_warning("session with repo_url failed; retrying without repo")
            self.git_repo_ready = False
            fallback = {
                "principal": payload["principal"],
                "metadata": payload["metadata"],
                "expires_in_seconds": payload["expires_in_seconds"],
            }
            return self.create_session(payload=fallback)

    def _setup_benchmark_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "agent-vllm-benchmark",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": self.benchmark_profile_id,
                "connection_profiles_json": json.dumps(
                    [
                        {
                            "id": self.benchmark_profile_id,
                            "kind": "http",
                            "description": "E2E benchmark profile",
                            "read_only": True,
                            "scopes": {"routes": self.benchmark_profile_routes},
                        }
                    ]
                ),
            },
            "expires_in_seconds": 3600,
        }
        return self.create_session(payload=payload)

    # ── Workspace file scaffolding ───────────────────────────────────
    def _write_setup_files(self) -> None:
        for entry in SETUP_FILES:
            self.invoke(
                session_id=self.main_session_id,
                tool_name=self.fs_write_tool,
                args={
                    "path": entry["path"],
                    "content": entry["content"],
                    "create_parents": True,
                },
                approved=True,
            )

    # ── Catalog discovery ────────────────────────────────────────────
    def _discover_catalog(self) -> list[str]:
        status, body = self.request("GET", f"/v1/sessions/{self.main_session_id}/tools")
        if status != 200:
            raise RuntimeError(f"tools.list failed ({status}): {body}")
        tools = [t.get("name", "").strip() for t in body.get("tools", [])]
        return [t for t in tools if t]

    def _resolve_fs_aliases(self) -> None:
        for candidate in ("fs.read_file", "fs.read"):
            if candidate in self.available_tools:
                self.fs_read_tool = candidate
                break
        for candidate in ("fs.write_file", "fs.write"):
            if candidate in self.available_tools:
                self.fs_write_tool = candidate
                break
        if not self.fs_read_tool:
            raise RuntimeError("catalog missing fs read tool")
        if not self.fs_write_tool:
            raise RuntimeError("catalog missing fs write tool")

    # ── Main execution loop ──────────────────────────────────────────
    def _execute_catalog(self, catalog: list[dict[str, Any]]) -> None:
        executed: set[str] = set()

        for entry in catalog:
            tool_name = self._resolve_tool_name(entry)
            if tool_name is None:
                # Tool not in workspace catalog — skip silently.
                continue

            args = self._substitute(entry.get("args", {}))
            approved = bool(entry.get("approved", False))
            strict = bool(entry.get("strict", False))
            requires_git = bool(entry.get("requires_git", False))
            soft_errors = entry.get("soft_errors", [])
            checks = entry.get("checks", [])
            captures = entry.get("captures", {})
            session_type = entry.get("session", "main")

            target_session = self.main_session_id
            if session_type == "benchmark" and self.benchmark_session_id:
                target_session = self.benchmark_session_id
            elif session_type == "benchmark" and not self.benchmark_session_id:
                print_warning(f"skipping {tool_name}: no benchmark session")
                continue

            http_status, body, invocation = self.invoke(
                session_id=target_session,
                tool_name=tool_name,
                args=args,
                approved=approved,
                timeout=120,
            )
            executed.add(tool_name)

            inv_status = ""
            error: dict[str, Any] = {}
            output: dict[str, Any] = {}
            if isinstance(invocation, dict):
                inv_status = str(invocation.get("status", "")).strip()
                error = invocation.get("error") if isinstance(invocation.get("error"), dict) else {}
                output = invocation.get("output") if isinstance(invocation.get("output"), dict) else {}

            # ── Capture runtime variables ────────────────────────────
            if captures and inv_status == "succeeded":
                self._capture_vars(captures, output)

            # ── Evaluate result ──────────────────────────────────────
            if inv_status == "succeeded":
                if checks:
                    self._run_checks(tool_name, checks, output)
                print_info(f"tool={tool_name} status=succeeded")
                continue

            # Tool failed — check if it matches a soft error pattern.
            if soft_errors and error and self._matches_soft_error(soft_errors, error):
                # For git tools: if the failure is repo-related, mark git as unavailable.
                if requires_git:
                    self.git_repo_ready = False
                print_warning(f"{tool_name} soft error: {error.get('code')} — continuing")
                continue

            # Strict tools that depend on git: relax when repo is unavailable.
            if requires_git and strict and not self.git_repo_ready:
                print_warning(f"{tool_name} skipped (git repo unavailable)")
                continue

            # Strict failure.
            if strict:
                raise RuntimeError(
                    f"{tool_name}: expected succeeded, got {inv_status} — error={error}"
                )

            # Non-strict, non-soft: any status is acceptable for coverage.
            if inv_status == "failed":
                print_warning(f"{tool_name} failed (non-strict): {error.get('code', 'unknown')}")
            else:
                print_info(f"tool={tool_name} status={inv_status}")

        # ── Verify coverage ──────────────────────────────────────────
        missing = sorted(t for t in self.available_tools if t not in executed)
        if missing:
            print_warning(f"tools not in catalog (not executed): {missing}")

        self.record_step(
            "tool_execution_coverage",
            "passed",
            data={
                "executed_count": len(executed),
                "available_count": len(self.available_tools),
                "not_in_catalog": missing,
            },
        )
        print_success(f"Executed {len(executed)}/{len(self.available_tools)} tools")

    # ── Entrypoint ───────────────────────────────────────────────────
    def run(self) -> int:
        print()
        print(f"{'=' * 80}")
        print("Workspace Tool Catalog Orchestration E2E Test (data-driven)")
        print(f"{'=' * 80}")
        print()
        print(f"  WORKSPACE_URL: {self.workspace_url}")
        print(f"  GIT_REPO_URL:  {self.workspace_git_repo_url}")
        print(f"  GIT_REPO_REF:  {self.workspace_git_repo_ref}")
        print(f"  CATALOG_FILE:  {CATALOG_FILE}")
        print(f"  EVIDENCE_FILE: {self.evidence_file}")
        print()

        final_status = "failed"
        error_message = ""

        try:
            # Step 1: Health + session + catalog discovery
            print_step(1, "Workspace health, session, and catalog discovery")

            status, body = self.request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed: {status} {body}")
            print_success("Workspace API healthy")

            self.main_session_id = self._setup_main_session()
            self.available_tools = self._discover_catalog()
            if not self.available_tools:
                raise RuntimeError("tool catalog is empty")

            self._resolve_fs_aliases()
            self.record_step(
                "catalog_discovered",
                "passed",
                data={
                    "tool_count": len(self.available_tools),
                    "fs_read": self.fs_read_tool,
                    "fs_write": self.fs_write_tool,
                    "git_repo_ready": self.git_repo_ready,
                },
            )
            print_success(f"Discovered {len(self.available_tools)} tools")

            # Benchmark session (optional)
            if "api.benchmark" in self.available_tools:
                self.benchmark_session_id = self._setup_benchmark_session()
                print_success("Benchmark session ready")

            # Step 2: Setup workspace files
            print_step(2, "Setup workspace scaffold files")
            self._write_setup_files()
            self.record_step("setup_files", "passed")
            print_success(f"Wrote {len(SETUP_FILES)} scaffold files")

            # Step 3: Execute catalog
            print_step(3, "Execute tool catalog (data-driven)")
            catalog = self._load_catalog()
            self.evidence["tool_catalog"] = sorted(self.available_tools)
            self.evidence["catalog_entries"] = len(catalog)
            self._execute_catalog(catalog)

            print()
            print(f"{'=' * 80}")
            print("E2E test PASSED")
            print(f"{'=' * 80}")
            print()
            final_status = "passed"
            return 0

        except Exception as exc:
            error_message = str(exc)
            print_error(f"E2E test FAILED: {exc}")
            return 1

        finally:
            self.cleanup_sessions()
            self.write_evidence(final_status, error_message=error_message)


def main() -> int:
    test = ToolCatalogOrchestrationE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())

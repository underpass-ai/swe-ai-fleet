#!/usr/bin/env python3
"""E2E test: repo analysis summaries (CAT-014)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def print_step(step: int, description: str) -> None:
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}OK {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}WARN {message}{Colors.NC}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}ERROR {message}{Colors.NC}")


class WorkspaceRepoAnalysisSummariesE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-31-{int(time.time())}.json")
        self.run_id = f"e2e-ws-repo-analysis-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "31-workspace-repo-analysis-summaries",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "steps": [],
            "sessions": [],
            "invocations": [],
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: int = 60,
    ) -> tuple[int, dict[str, Any]]:
        url = self.workspace_url + path
        data = None
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("WORKSPACE_AUTH_TOKEN", "").strip()
        if auth_token:
            headers.update({
                os.getenv("WORKSPACE_AUTH_TOKEN_HEADER", "X-Workspace-Auth-Token"): auth_token,
                os.getenv("WORKSPACE_AUTH_TENANT_HEADER", "X-Workspace-Tenant-Id"): os.getenv("WORKSPACE_AUTH_TENANT_ID", "e2e-tenant"),
                os.getenv("WORKSPACE_AUTH_ACTOR_HEADER", "X-Workspace-Actor-Id"): os.getenv("WORKSPACE_AUTH_ACTOR_ID", "e2e-workspace"),
                os.getenv("WORKSPACE_AUTH_ROLES_HEADER", "X-Workspace-Roles"): os.getenv("WORKSPACE_AUTH_ROLES", "developer,devops"),
            })
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return response.getcode(), (json.loads(body) if body else {})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except Exception:
                parsed = {"raw": body}
            return exc.code, parsed

    def _record_step(self, name: str, status: str, data: Any | None = None) -> None:
        entry: dict[str, Any] = {"at": self._now_iso(), "step": name, "status": status}
        if data is not None:
            entry["data"] = data
        self.evidence["steps"].append(entry)

    def _extract_error(self, invocation: dict[str, Any] | None, body: dict[str, Any]) -> dict[str, Any]:
        if isinstance(invocation, dict) and isinstance(invocation.get("error"), dict):
            return invocation["error"]
        if isinstance(body.get("error"), dict):
            return body["error"]
        return {}

    def _record_invocation(
        self,
        *,
        session_id: str,
        tool: str,
        http_status: int,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
    ) -> None:
        error = self._extract_error(invocation, body)
        self.evidence["invocations"].append(
            {
                "at": self._now_iso(),
                "session_id": session_id,
                "tool": tool,
                "http_status": http_status,
                "invocation_id": invocation.get("id") if isinstance(invocation, dict) else None,
                "invocation_status": invocation.get("status") if isinstance(invocation, dict) else None,
                "error_code": error.get("code"),
                "error_message": error.get("message"),
            }
        )

    def _create_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "e2e-repo-analysis",
                "roles": ["developer"],
            },
            "allowed_paths": ["."],
            "expires_in_seconds": 3600,
        }
        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")
        session_id = str(body.get("session", {}).get("id", "")).strip()
        if not session_id:
            raise RuntimeError(f"create session missing id: {body}")

        self.sessions.append(session_id)
        self.evidence["sessions"].append({"at": self._now_iso(), "session_id": session_id, "payload": payload})
        return session_id

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool = False,
        timeout: int = 120,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        self.invocation_counter += 1
        payload = {
            "correlation_id": f"{self.run_id}-{self.invocation_counter:04d}",
            "approved": approved,
            "args": args,
        }
        status, body = self._request(
            "POST",
            f"/v1/sessions/{session_id}/tools/{tool_name}/invoke",
            payload,
            timeout=timeout,
        )
        invocation = body.get("invocation") if isinstance(body, dict) else None
        self._record_invocation(
            session_id=session_id,
            tool=tool_name,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
            body=body if isinstance(body, dict) else {},
        )
        return status, body, invocation if isinstance(invocation, dict) else None

    def _assert_succeeded(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "succeeded":
            error = self._extract_error(invocation, body)
            code = str(error.get("code", "")).strip()
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({code})")

    def _assert_artifact_present(self, invocation_id: str, artifact_name: str) -> None:
        status, body = self._request("GET", f"/v1/invocations/{invocation_id}/artifacts")
        if status != 200:
            raise RuntimeError(f"list invocation artifacts failed ({status}): {body}")
        names = [
            str(item.get("name", "")).strip()
            for item in body.get("artifacts", [])
            if isinstance(item, dict)
        ]
        if artifact_name not in names:
            raise RuntimeError(f"artifact {artifact_name} not found for invocation {invocation_id}: {names}")

    def _write_evidence(self, status: str, error_message: str = "") -> None:
        self.evidence["status"] = status
        self.evidence["ended_at"] = self._now_iso()
        if error_message:
            self.evidence["error_message"] = error_message

        try:
            with open(self.evidence_file, "w", encoding="utf-8") as handle:
                json.dump(self.evidence, handle, ensure_ascii=False, indent=2)
            print_warning(f"Evidence file: {self.evidence_file}")
        except Exception as exc:
            print_warning(f"Could not write evidence file: {exc}")

        print("EVIDENCE_JSON_START")
        print(json.dumps(self.evidence, ensure_ascii=False, indent=2))
        print("EVIDENCE_JSON_END")

    def cleanup(self) -> None:
        for session_id in self.sessions:
            try:
                self._request("DELETE", f"/v1/sessions/{session_id}")
            except Exception:
                pass

    def run(self) -> int:
        final_status = "failed"
        error_message = ""
        try:
            print_step(1, "Workspace health")
            status, body = self._request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")
            self._record_step("health", "passed")
            print_success("Workspace API is healthy")

            print_step(2, "Session and catalog checks")
            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            required_tools = [
                "repo.test_failures_summary",
                "repo.stacktrace_summary",
            ]
            missing = [tool for tool in required_tools if tool not in tools]
            if missing:
                raise RuntimeError(f"catalog missing tools: {missing}")
            self._record_step("catalog", "passed", {"tool_count": len(tools), "required_tools": required_tools})
            print_success("Catalog exposes CAT-014 tools")

            print_step(3, "Invoke repo.test_failures_summary with synthetic output")
            synthetic_failures = "\n".join(
                [
                    "--- FAIL: TestCreateTodo (0.00s)",
                    "FAILED tests/test_todo.py::test_add - AssertionError: expected 1 got 0",
                    "test service::tests::it_updates ... FAILED",
                ]
            )
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="repo.test_failures_summary",
                args={"output": synthetic_failures, "max_failures": 10},
            )
            self._assert_succeeded(invocation=inv, body=body, label="repo.test_failures_summary")
            summary_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            failed_count = int(summary_output.get("failed_count", 0))
            if failed_count < 2:
                raise RuntimeError(f"repo.test_failures_summary failed_count too low: {summary_output}")
            invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(invocation_id, "test-failures-summary.json")
            self._record_step("repo_test_failures_summary", "passed", {"failed_count": failed_count})
            print_success("repo.test_failures_summary succeeded")

            print_step(4, "Invoke repo.stacktrace_summary with synthetic output")
            synthetic_stacktrace = "\n".join(
                [
                    "panic: runtime error: index out of range",
                    "goroutine 1 [running]:",
                    "main.main()",
                    "/workspace/repo/main.go:11 +0x29",
                    "",
                    "Traceback (most recent call last):",
                    "File \"/workspace/repo/test_app.py\", line 10, in test_fail",
                    "assert 1 == 2",
                ]
            )
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="repo.stacktrace_summary",
                args={"output": synthetic_stacktrace, "max_traces": 5, "max_frames": 10},
            )
            self._assert_succeeded(invocation=inv, body=body, label="repo.stacktrace_summary")
            summary_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            trace_count = int(summary_output.get("trace_count", 0))
            if trace_count < 2:
                raise RuntimeError(f"repo.stacktrace_summary trace_count too low: {summary_output}")
            invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(invocation_id, "stacktrace-summary.json")
            self._record_step("repo_stacktrace_summary", "passed", {"trace_count": trace_count})
            print_success("repo.stacktrace_summary succeeded")

            final_status = "passed"
            self._record_step("test_result", "passed")
            print_success("E2E 31 completed successfully")
            return 0
        except Exception as exc:
            error_message = str(exc)
            print_error(error_message)
            self._record_step("failure", "failed", {"error": error_message})
            return 1
        finally:
            self.cleanup()
            self._write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceRepoAnalysisSummariesE2E().run()


if __name__ == "__main__":
    sys.exit(main())

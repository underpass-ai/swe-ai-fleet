#!/usr/bin/env python3
"""E2E test: K8s tools runtime gating on local workspace backend."""

from __future__ import annotations

import json
import os
import subprocess
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


class WorkspaceK8sRuntimeGatingE2E:
    def __init__(self) -> None:
        self.start_local_workspace = os.getenv("START_LOCAL_WORKSPACE", "true").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        self.workspace_port = int(os.getenv("WORKSPACE_PORT", "50053"))
        self.workspace_url = os.getenv("WORKSPACE_URL", f"http://127.0.0.1:{self.workspace_port}").rstrip("/")
        self.workspace_binary = os.getenv("WORKSPACE_BINARY", "/usr/local/bin/workspace-service")
        self.workspace_log_file = os.getenv("WORKSPACE_LOG_FILE", "/tmp/workspace-runtime-gating.log")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-41-{int(time.time())}.json")

        self.run_id = f"e2e-ws-k8s-runtime-gating-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0
        self.workspace_process: subprocess.Popen[str] | None = None
        self.workspace_log_handle = None

        self.evidence: dict[str, Any] = {
            "test_id": "41-workspace-k8s-runtime-gating",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "workspace_port": self.workspace_port,
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
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("WORKSPACE_AUTH_TOKEN", "").strip()
        if auth_token:
            headers.update(
                {
                    os.getenv("WORKSPACE_AUTH_TOKEN_HEADER", "X-Workspace-Auth-Token"): auth_token,
                    os.getenv("WORKSPACE_AUTH_TENANT_HEADER", "X-Workspace-Tenant-Id"): os.getenv(
                        "WORKSPACE_AUTH_TENANT_ID",
                        "e2e-tenant",
                    ),
                    os.getenv("WORKSPACE_AUTH_ACTOR_HEADER", "X-Workspace-Actor-Id"): os.getenv(
                        "WORKSPACE_AUTH_ACTOR_ID",
                        "e2e-workspace",
                    ),
                    os.getenv("WORKSPACE_AUTH_ROLES_HEADER", "X-Workspace-Roles"): os.getenv(
                        "WORKSPACE_AUTH_ROLES",
                        "developer,devops",
                    ),
                }
            )
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
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
        approved: bool,
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
                "approved": approved,
                "http_status": http_status,
                "invocation_id": invocation.get("id") if isinstance(invocation, dict) else None,
                "invocation_status": invocation.get("status") if isinstance(invocation, dict) else None,
                "error_code": error.get("code"),
                "error_message": error.get("message"),
            }
        )

    def _tail_workspace_log(self, lines: int = 60) -> str:
        try:
            with open(self.workspace_log_file, "r", encoding="utf-8", errors="replace") as handle:
                all_lines = handle.readlines()
            return "".join(all_lines[-lines:])
        except Exception:
            return ""

    def _start_local_workspace_service(self) -> None:
        if not self.start_local_workspace:
            self._record_step("workspace_bootstrap", "skipped", {"reason": "START_LOCAL_WORKSPACE=false"})
            return

        if not os.path.exists(self.workspace_binary):
            raise RuntimeError(f"workspace binary not found: {self.workspace_binary}")

        os.makedirs("/tmp/swe-workspaces", exist_ok=True)
        os.makedirs("/tmp/swe-artifacts", exist_ok=True)

        env = os.environ.copy()
        env["PORT"] = str(self.workspace_port)
        env["WORKSPACE_BACKEND"] = "local"
        env["WORKSPACE_ROOT"] = "/tmp/swe-workspaces"
        env["ARTIFACT_ROOT"] = "/tmp/swe-artifacts"
        env["INVOCATION_STORE_BACKEND"] = "memory"
        env["SESSION_STORE_BACKEND"] = "memory"
        env["LOG_LEVEL"] = "info"

        self.workspace_log_handle = open(self.workspace_log_file, "w", encoding="utf-8")
        self.workspace_process = subprocess.Popen(
            [self.workspace_binary],
            stdout=self.workspace_log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
        )

        health_path = "/healthz"
        deadline = time.time() + 50
        while time.time() < deadline:
            if self.workspace_process.poll() is not None:
                raise RuntimeError(
                    "local workspace process exited unexpectedly\n"
                    f"last logs:\n{self._tail_workspace_log()}"
                )
            try:
                status, body = self._request("GET", health_path, timeout=3)
                if status == 200 and body.get("status") == "ok":
                    self._record_step(
                        "workspace_bootstrap",
                        "passed",
                        {"workspace_url": self.workspace_url, "workspace_log_file": self.workspace_log_file},
                    )
                    print_success("Local workspace service started")
                    return
            except Exception:
                pass
            time.sleep(0.5)

        raise RuntimeError(
            "timed out waiting for local workspace service\n"
            f"last logs:\n{self._tail_workspace_log()}"
        )

    def _stop_local_workspace_service(self) -> None:
        if self.workspace_process is not None and self.workspace_process.poll() is None:
            self.workspace_process.terminate()
            try:
                self.workspace_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.workspace_process.kill()
                self.workspace_process.wait(timeout=5)
        if self.workspace_log_handle is not None:
            self.workspace_log_handle.close()
            self.workspace_log_handle = None

    def _create_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "e2e-k8s-runtime-gating",
                "roles": ["platform_admin"],
            },
            "metadata": {
                "allowed_k8s_namespaces": "swe-ai-fleet",
            },
            "expires_in_seconds": 1800,
        }
        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")
        session = body.get("session", {})
        session_id = str(session.get("id", "")).strip()
        if not session_id:
            raise RuntimeError(f"create session missing id: {body}")

        runtime_kind = str(session.get("runtime", {}).get("kind", "")).strip()
        if runtime_kind != "local":
            raise RuntimeError(f"expected local runtime session, got runtime.kind={runtime_kind!r}")

        self.sessions.append(session_id)
        self.evidence["sessions"].append(
            {"at": self._now_iso(), "session_id": session_id, "runtime_kind": runtime_kind, "payload": payload}
        )
        return session_id

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool,
        timeout: int = 60,
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
            payload=payload,
            timeout=timeout,
        )
        invocation = body.get("invocation") if isinstance(body, dict) else None
        self._record_invocation(
            session_id=session_id,
            tool=tool_name,
            approved=approved,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
            body=body if isinstance(body, dict) else {},
        )
        return status, body, invocation if isinstance(invocation, dict) else None

    def _assert_error_code(
        self,
        *,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
        expected_code: str,
        label: str,
    ) -> dict[str, Any]:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code != expected_code:
            raise RuntimeError(f"{label}: expected error_code={expected_code}, got={code}, error={error}")
        return error

    def _assert_succeeded(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> dict[str, Any]:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({self._extract_error(invocation, body)})")
        output = invocation.get("output")
        if not isinstance(output, dict):
            raise RuntimeError(f"{label}: missing output payload")
        return output

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
            print_step(1, "Bootstrap local workspace runtime")
            self._start_local_workspace_service()
            status, body = self._request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")
            self._record_step("health", "passed")
            print_success("Workspace API healthy in local runtime")

            print_step(2, "Create session and verify runtime-aware catalog")
            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            k8s_tools = sorted([name for name in tools if name.startswith("k8s.")])
            if k8s_tools:
                raise RuntimeError(f"k8s tools must be hidden in local runtime, found: {k8s_tools}")
            if "fs.list" not in tools:
                raise RuntimeError("expected non-cluster tool fs.list in catalog")
            self._record_step(
                "catalog_runtime_filter",
                "passed",
                {"tool_count": len(tools), "k8s_tools_listed": len(k8s_tools)},
            )
            print_success("Catalog hides k8s.* tools in local runtime")

            print_step(3, "Invoke hidden k8s tool without approval")
            http_status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_pods",
                args={"namespace": "swe-ai-fleet", "max_pods": 1},
                approved=False,
            )
            error = self._assert_error_code(
                invocation=inv,
                body=body,
                expected_code="policy_denied",
                label="k8s.get_pods runtime deny (unapproved)",
            )
            if http_status != 403:
                raise RuntimeError(f"expected HTTP 403 for runtime deny, got {http_status}")
            if "kubernetes runtime" not in str(error.get("message", "")).lower():
                raise RuntimeError(f"expected runtime deny message mentioning kubernetes runtime, got {error}")
            self._record_step("invoke_runtime_deny_unapproved", "passed")
            print_success("Direct invoke denied with policy_denied in local runtime")

            print_step(4, "Invoke hidden k8s tool with approval still denied")
            http_status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_pods",
                args={"namespace": "swe-ai-fleet", "max_pods": 1},
                approved=True,
            )
            error = self._assert_error_code(
                invocation=inv,
                body=body,
                expected_code="policy_denied",
                label="k8s.get_pods runtime deny (approved)",
            )
            if http_status != 403:
                raise RuntimeError(f"expected HTTP 403 for runtime deny, got {http_status}")
            if "kubernetes runtime" not in str(error.get("message", "")).lower():
                raise RuntimeError(f"expected runtime deny message mentioning kubernetes runtime, got {error}")
            self._record_step("invoke_runtime_deny_approved", "passed")
            print_success("Approval does not bypass runtime gating")

            print_step(5, "Non-cluster tool still operates")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.list",
                args={"path": ".", "recursive": False, "max_entries": 20},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.list")
            if not isinstance(output.get("entries"), list):
                raise RuntimeError(f"fs.list returned invalid entries payload: {output}")
            self._record_step(
                "non_cluster_tool_succeeds",
                "passed",
                {"count": output.get("count", 0)},
            )
            print_success("Non-cluster tools remain functional")

            final_status = "passed"
            self._record_step("final", "passed")
            return 0
        except Exception as exc:
            error_message = str(exc)
            self._record_step("failure", "failed", {"error": error_message})
            print_error(error_message)
            return 1
        finally:
            self.cleanup()
            self._stop_local_workspace_service()
            self._write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceK8sRuntimeGatingE2E().run()


if __name__ == "__main__":
    sys.exit(main())
